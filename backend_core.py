import hashlib

doc_chunks: dict = {}
vector_stores: dict = {}


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


def _store_key(doc_id: str, provider: str, api_key: str) -> str:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return f"{doc_id}::{provider}::{key_hash}"


def get_embeddings(provider: str, api_key: str):
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(openai_api_key=api_key)
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
    raise ValueError(f"Unknown provider: {provider}")


def get_or_build_vectorstore(doc_id: str, provider: str, api_key: str):
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


def get_llm(provider: str, api_key: str):
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, temperature=0.3, max_tokens=1200)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.3)
    raise ValueError(f"Unknown provider: {provider}")


RAG_SYSTEM_PROMPT = """You are a precise document assistant. Your task is to answer the user's question using ONLY the document excerpts provided below.

Rules:
1. Base your answer STRICTLY on the provided excerpts, do not use any outside knowledge.
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
        context_parts.append(f"[Excerpt {i + 1}]\n{doc.page_content}")
        sources.append(
            {
                "excerpt": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
                "relevance_score": round(float(score), 4),
            }
        )

    context = "\n\n".join(context_parts)
    prompt = RAG_SYSTEM_PROMPT.format(context=context) + f"\n\nQuestion: {question}\n\nAnswer:"

    llm = get_llm(provider, api_key)
    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"answer": response.content.strip(), "sources": sources, "chunks_built": built}


def summarize_doc(doc_id: str, provider: str, api_key: str) -> str:
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
