import os
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── In-memory stores ────────────────────────────────────────
# doc_id -> list of text chunks
doc_chunks: dict = {}
# (doc_id, provider, key_hash) -> FAISS vectorstore
vector_stores: dict = {}


# ── PDF helpers ─────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    import pdfplumber
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def count_pages(file_path: str) -> int:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


def split_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# ── Embedding & vectorstore ─────────────────────────────────

def _store_key(doc_id: str, provider: str, api_key: str) -> str:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return f"{doc_id}::{provider}::{key_hash}"


def get_embeddings(provider: str, api_key: str):
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(openai_api_key=api_key)
    elif provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
    raise ValueError(f"Unknown provider: {provider}")


def get_or_build_vectorstore(doc_id: str, provider: str, api_key: str):
    """Return cached FAISS store or build it from stored chunks."""
    from langchain_community.vectorstores import FAISS

    skey = _store_key(doc_id, provider, api_key)
    if skey in vector_stores:
        return vector_stores[skey], False

    if doc_id not in doc_chunks:
        raise ValueError("Document not found. Please re-upload the PDF.")

    chunks = doc_chunks[doc_id]
    embeddings = get_embeddings(provider, api_key)
    store = FAISS.from_texts(chunks, embeddings)
    vector_stores[skey] = store
    return store, True


# ── LLM helpers ─────────────────────────────────────────────

def get_llm(provider: str, api_key: str):
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, temperature=0.3, max_tokens=1200)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.3)
    raise ValueError(f"Unknown provider: {provider}")


# ── RAG chain ────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are a precise document assistant. Your task is to answer the user's question using ONLY the document excerpts provided below.

Rules:
1. Base your answer STRICTLY on the provided excerpts — do not use any outside knowledge.
2. If the answer is NOT found in the excerpts, respond with: "This information is not found in the uploaded document."
3. Quote relevant sections where helpful.
4. Be concise and clear.

Document excerpts:
---
{context}
---"""


def rag_answer(doc_id: str, question: str, provider: str, api_key: str, top_k: int = 5) -> dict:
    store, built = get_or_build_vectorstore(doc_id, provider, api_key)

    docs = store.similarity_search_with_score(question, k=top_k)
    if not docs:
        return {"answer": "No relevant content found in the document.", "sources": [], "chunks_built": built}

    context_parts = []
    sources = []
    for i, (doc, score) in enumerate(docs):
        context_parts.append(f"[Excerpt {i+1}]\n{doc.page_content}")
        sources.append({
            "excerpt": doc.page_content[:300] + ("…" if len(doc.page_content) > 300 else ""),
            "relevance_score": round(float(score), 4),
        })

    context = "\n\n".join(context_parts)
    prompt = RAG_SYSTEM_PROMPT.format(context=context) + f"\n\nQuestion: {question}\n\nAnswer:"

    llm = get_llm(provider, api_key)
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip()

    return {"answer": answer, "sources": sources, "chunks_built": built}


# ── Summarization ────────────────────────────────────────────

SUMMARY_PROMPT = """You are an expert summarizer. Read the following document content and write a clear, structured summary that captures:
- The main topic and purpose
- Key findings, arguments, or points
- Any conclusions or recommendations

Be thorough but concise. Use plain language.

Document content:
{text}

Summary:"""


def summarize_doc(doc_id: str, provider: str, api_key: str) -> str:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain.chains.summarize import load_summarize_chain
    from langchain_core.documents import Document

    if doc_id not in doc_chunks:
        raise ValueError("Document not found. Please re-upload the PDF.")

    chunks = doc_chunks[doc_id]
    llm = get_llm(provider, api_key)

    lc_docs = [Document(page_content=chunk) for chunk in chunks]

    if len(lc_docs) <= 6:
        chain = load_summarize_chain(llm, chain_type="stuff")
    else:
        chain = load_summarize_chain(llm, chain_type="map_reduce")

    result = chain.invoke(lc_docs)
    return result.get("output_text", "").strip()


# ── Routes ───────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "docs_loaded": len(doc_chunks), "stores_cached": len(vector_stores)})


@app.route("/api/process-pdf", methods=["POST"])
def process_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    file_bytes = file.read()
    doc_id = hashlib.md5(file.filename.encode() + file_bytes[:512]).hexdigest()[:16]

    save_path = os.path.join(UPLOAD_FOLDER, f"{doc_id}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    try:
        raw_text = extract_text_from_pdf(save_path)
        if not raw_text.strip():
            return jsonify({"error": "Could not extract text from this PDF. It may be image-based or password-protected."}), 400

        chunks = split_into_chunks(raw_text)
        doc_chunks[doc_id] = chunks

        page_count = count_pages(save_path)
        word_count = len(raw_text.split())
        char_count = len(raw_text)

        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "filename": file.filename,
            "page_count": page_count,
            "word_count": word_count,
            "char_count": char_count,
            "chunk_count": len(chunks),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    question = data.get("question", "").strip()
    doc_id = data.get("doc_id", "").strip()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai").lower()

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if not doc_id:
        return jsonify({"error": "Document ID is required"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if provider not in ("openai", "gemini"):
        return jsonify({"error": f"Unknown provider: {provider}"}), 400

    try:
        result = rag_answer(doc_id, question, provider, api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    doc_id = data.get("doc_id", "").strip()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai").lower()

    if not doc_id:
        return jsonify({"error": "Document ID is required"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if provider not in ("openai", "gemini"):
        return jsonify({"error": f"Unknown provider: {provider}"}), 400

    try:
        summary = summarize_doc(doc_id, provider, api_key)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    text = data.get("text", "").strip()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai").lower()
    target_lang = data.get("target_lang", "Urdu")

    if not text:
        return jsonify({"error": "Text is required"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if provider not in ("openai", "gemini"):
        return jsonify({"error": f"Unknown provider: {provider}"}), 400

    try:
        prompt = (
            f"Translate the following text into {target_lang}. "
            f"Produce only the translated text — no explanations, no notes, no original text.\n\n"
            f"{text}"
        )
        llm = get_llm(provider, api_key)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        translated = response.content.strip()
        return jsonify({"translated": translated, "target_lang": target_lang})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
