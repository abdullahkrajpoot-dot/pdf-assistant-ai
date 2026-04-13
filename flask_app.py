import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_text_from_pdf(file_path: str) -> str:
    import pdfplumber
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def get_openai_answer(question: str, context: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a helpful assistant that answers questions based on provided document content. "
        "Use ONLY the document content to answer. If the answer is not in the document, say so clearly. "
        "Be concise and accurate."
    )
    user_prompt = f"Document content:\n{context[:12000]}\n\nQuestion: {question}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def get_gemini_answer(question: str, context: str, api_key: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        "You are a helpful assistant that answers questions based on provided document content. "
        "Use ONLY the document content to answer. If the answer is not in the document, say so clearly.\n\n"
        f"Document content:\n{context[:12000]}\n\nQuestion: {question}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def get_openai_summary(context: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Provide a clear, concise summary of the following document.",
            },
            {"role": "user", "content": f"Summarize this document:\n{context[:10000]}"},
        ],
        max_tokens=600,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


def get_gemini_summary(context: str, api_key: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"Provide a clear, concise summary of the following document:\n{context[:10000]}"
    response = model.generate_content(prompt)
    return response.text.strip()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/process-pdf", methods=["POST"])
def process_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    try:
        text = extract_text_from_pdf(save_path)
        word_count = len(text.split())
        char_count = len(text)
        page_count = _count_pages(save_path)

        return jsonify({
            "success": True,
            "filename": file.filename,
            "text": text,
            "word_count": word_count,
            "char_count": char_count,
            "page_count": page_count,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _count_pages(file_path: str) -> int:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    question = data.get("question", "").strip()
    context = data.get("context", "").strip()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai").lower()

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if not context:
        return jsonify({"error": "No document context provided"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    try:
        if provider == "openai":
            answer = get_openai_answer(question, context, api_key)
        elif provider == "gemini":
            answer = get_gemini_answer(question, context, api_key)
        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400

        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    context = data.get("context", "").strip()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "openai").lower()

    if not context:
        return jsonify({"error": "No document context provided"}), 400
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    try:
        if provider == "openai":
            summary = get_openai_summary(context, api_key)
        elif provider == "gemini":
            summary = get_gemini_summary(context, api_key)
        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400

        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
