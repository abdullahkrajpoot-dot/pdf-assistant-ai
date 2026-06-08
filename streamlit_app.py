"""Streamlit Cloud-ready PDF Summarizer Agent.

This single-file app parses uploaded PDFs with pypdf and uses Gemini through
google-generativeai for executive summaries and contextual chat.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import google.generativeai as genai
import streamlit as st
from pypdf import PdfReader


APP_TITLE = "PDF Summarizer Agent"
GEMINI_MODEL = "gemini-1.5-flash"
MAX_CONTEXT_CHARS = 140_000


@dataclass(frozen=True)
class PdfDocument:
    """Structured representation of an uploaded PDF."""

    file_id: str
    filename: str
    text: str
    page_count: int
    word_count: int
    char_count: int
    pages_with_text: int


def init_state() -> None:
    """Create all session keys used by the application."""

    defaults: dict[str, Any] = {
        "document": None,
        "summary": "",
        "summary_error": "",
        "messages": [],
        "last_file_id": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css() -> None:
    """Add a restrained production UI layer over native Streamlit widgets."""

    st.markdown(
        """
        <style>
            :root {
                --ink: #111827;
                --muted: #6B7280;
                --line: #E5E7EB;
                --panel: #F8FAFC;
                --indigo: #4F46E5;
                --blue: #2563EB;
                --success-bg: #ECFDF5;
                --success-fg: #047857;
                --warn-bg: #FFFBEB;
                --warn-fg: #92400E;
            }

            .main .block-container {
                max-width: 1180px;
                padding-top: 1.25rem;
                padding-bottom: 2.5rem;
            }

            [data-testid="stSidebar"] {
                background: #F8FAFC;
                border-right: 1px solid var(--line);
            }

            h1, h2, h3 {
                color: var(--ink);
                letter-spacing: 0;
            }

            .app-shell {
                border-bottom: 1px solid var(--line);
                padding-bottom: 1rem;
                margin-bottom: 1rem;
            }

            .app-kicker {
                color: var(--blue);
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }

            .app-title {
                color: var(--ink);
                font-size: 2.1rem;
                font-weight: 800;
                line-height: 1.15;
                margin: 0;
            }

            .app-subtitle {
                color: var(--muted);
                font-size: 1rem;
                line-height: 1.65;
                margin-top: 0.5rem;
                max-width: 820px;
            }

            .status-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 700;
                padding: 0.28rem 0.7rem;
                margin-top: 0.4rem;
            }

            .status-ready {
                background: var(--success-bg);
                color: var(--success-fg);
                border: 1px solid #A7F3D0;
            }

            .status-idle {
                background: #EFF6FF;
                color: #1D4ED8;
                border: 1px solid #BFDBFE;
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.75rem;
                margin: 1rem 0 1.2rem;
            }

            .metric-card {
                background: white;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 0.85rem 1rem;
            }

            .metric-value {
                color: var(--indigo);
                font-size: 1.35rem;
                font-weight: 800;
                line-height: 1.2;
            }

            .metric-label {
                color: var(--muted);
                font-size: 0.73rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                margin-top: 0.25rem;
                text-transform: uppercase;
            }

            .empty-panel {
                background: var(--panel);
                border: 1px dashed #CBD5E1;
                border-radius: 8px;
                padding: 2.25rem;
                text-align: center;
                color: var(--muted);
            }

            .empty-panel strong {
                color: var(--ink);
                display: block;
                font-size: 1.1rem;
                margin-bottom: 0.35rem;
            }

            .summary-panel {
                background: white;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 1.1rem 1.2rem;
                line-height: 1.75;
            }

            .summary-panel h2,
            .summary-panel h3 {
                margin-top: 0.8rem;
            }

            .quick-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin: 0.7rem 0 0.2rem;
            }

            .sidebar-note {
                color: var(--muted);
                font-size: 0.88rem;
                line-height: 1.55;
            }

            @media (max-width: 760px) {
                .metric-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .app-title {
                    font-size: 1.55rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_gemini_api_key() -> str | None:
    """Read the Gemini key from Streamlit secrets without exposing it."""

    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None
    return str(key).strip() or None


def configure_gemini(api_key: str) -> genai.GenerativeModel:
    """Configure and return the Gemini model used by the app."""

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={
            "temperature": 0.2,
            "top_p": 0.9,
            "max_output_tokens": 4096,
        },
    )


def fingerprint_file(filename: str, file_bytes: bytes) -> str:
    """Create a stable id for the current upload."""

    digest = hashlib.sha256()
    digest.update(filename.encode("utf-8", errors="ignore"))
    digest.update(str(len(file_bytes)).encode())
    digest.update(file_bytes[:2048])
    digest.update(file_bytes[-2048:])
    return digest.hexdigest()[:16]


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(uploaded_file: Any) -> PdfDocument:
    """Read a PDF upload and extract text with pypdf."""

    file_bytes = uploaded_file.getvalue()
    file_id = fingerprint_file(uploaded_file.name, file_bytes)

    try:
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("This PDF is encrypted and could not be opened.") from exc

        pages: list[str] = []
        pages_with_text = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            page_text = clean_text(page_text)
            if page_text:
                pages_with_text += 1
                pages.append(f"[Page {page_number}]\n{page_text}")

        full_text = clean_text("\n\n".join(pages))
        if not full_text:
            raise ValueError(
                "No selectable text was found. The PDF may be scanned images or password protected."
            )

        return PdfDocument(
            file_id=file_id,
            filename=uploaded_file.name,
            text=full_text,
            page_count=len(reader.pages),
            word_count=len(full_text.split()),
            char_count=len(full_text),
            pages_with_text=pages_with_text,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Unable to read this PDF: {exc}") from exc


def trim_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Keep prompts inside a practical context budget for Streamlit requests."""

    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2 :]
    return f"{head}\n\n[Middle of document omitted for length]\n\n{tail}"


def response_text(response: Any) -> str:
    """Safely unwrap Gemini response text."""

    text = getattr(response, "text", None)
    if text:
        return str(text).strip()

    parts: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", "")
            if part_text:
                parts.append(part_text)

    if parts:
        return "\n".join(parts).strip()
    raise RuntimeError("Gemini returned an empty response. Try again with a smaller PDF or simpler question.")


def call_gemini(model: genai.GenerativeModel, prompt: str) -> str:
    """Call Gemini and return text while hiding implementation errors from users."""

    try:
        response = model.generate_content(prompt)
        return response_text(response)
    except Exception as exc:
        raise RuntimeError(f"Gemini request failed: {exc}") from exc


def build_summary_prompt(document: PdfDocument) -> str:
    """Create the structured executive-summary prompt."""

    context = trim_context(document.text)
    return f"""
You are an expert executive analyst. Read the PDF text below and produce a concise,
decision-ready executive summary using polished Markdown.

Required structure:

## Overview
Write one clear paragraph explaining what the document is about and why it matters.

## Key Metrics / Findings
Extract concrete numbers, dates, facts, decisions, names, risks, or conclusions.
Use bullets. If the document has no metrics, list the strongest findings instead.

## Target Audience / Context
Identify who this document appears to be for and the operating context.

## Action Items
Create a practical bulleted list of next steps. If the document does not state
actions explicitly, infer reasonable actions and label them as inferred.

Rules:
- Use only the uploaded document text.
- Do not invent exact numbers, dates, people, or claims.
- Keep the answer skimmable and professional.

PDF filename: {document.filename}
Pages: {document.page_count}
Words: {document.word_count}

PDF text:
---
{context}
---
"""


def build_chat_prompt(document: PdfDocument, messages: list[dict[str, str]], question: str) -> str:
    """Create a grounded conversational prompt for PDF Q&A."""

    context = trim_context(document.text)
    recent_turns = messages[-8:]
    chat_context = "\n".join(
        f"{turn['role'].title()}: {turn['content']}" for turn in recent_turns if turn.get("content")
    )
    return f"""
You are a careful PDF analysis agent. Answer the user's question using only the PDF
text below. You may use the recent conversation for continuity, but the source of
truth is always the PDF.

If the answer is not present in the PDF, say: "I could not find that in the uploaded PDF."
Be specific, concise, and cite page labels like [Page 2] when the evidence is available.

Recent conversation:
{chat_context or "No previous conversation."}

User question:
{question}

PDF text:
---
{context}
---
"""


def reset_document_state(document: PdfDocument) -> None:
    """Store a new PDF and clear outputs tied to the previous file."""

    st.session_state.document = document
    st.session_state.summary = ""
    st.session_state.summary_error = ""
    st.session_state.messages = []
    st.session_state.last_file_id = document.file_id


def render_header() -> None:
    """Render the main app header."""

    st.markdown(
        """
        <div class="app-shell">
            <div class="app-kicker">Gemini PDF Intelligence</div>
            <h1 class="app-title">PDF Summarizer Agent</h1>
            <div class="app-subtitle">
                Upload a PDF, get a structured executive summary, then ask follow-up
                questions in a grounded chat workspace.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(document: PdfDocument) -> None:
    """Render compact document metrics."""

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{document.page_count:,}</div>
                <div class="metric-label">Pages</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{document.word_count:,}</div>
                <div class="metric-label">Words</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{document.pages_with_text:,}</div>
                <div class="metric-label">Text Pages</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{document.char_count:,}</div>
                <div class="metric-label">Characters</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """Render the main empty state."""

    st.markdown(
        """
        <div class="empty-panel">
            <strong>Please upload a PDF file from the sidebar to begin analysis</strong>
            The executive summary and chat agent will appear here after the document is parsed.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(api_key: str | None) -> None:
    """Render configuration and upload controls."""

    with st.sidebar:
        st.markdown("## PDF Agent")
        st.markdown(
            """
            <div class="sidebar-note">
                Generate boardroom-ready summaries and ask contextual questions about
                contracts, reports, research papers, proposals, and policy documents.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        if api_key:
            st.markdown('<span class="status-badge status-ready">Gemini key loaded</span>', unsafe_allow_html=True)
        else:
            st.warning(
                "Missing `GEMINI_API_KEY`. Add it in Streamlit Cloud: "
                "Manage app -> Settings -> Secrets."
            )

        st.divider()
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], accept_multiple_files=False)

        if uploaded_file is not None:
            try:
                file_bytes = uploaded_file.getvalue()
                file_id = fingerprint_file(uploaded_file.name, file_bytes)

                if file_id != st.session_state.last_file_id:
                    with st.spinner("Reading PDF..."):
                        document = extract_pdf_text(uploaded_file)
                    reset_document_state(document)
                    st.success("Ready for Analysis")
                else:
                    st.markdown(
                        '<span class="status-badge status-ready">Ready for Analysis</span>',
                        unsafe_allow_html=True,
                    )
            except Exception as exc:
                st.session_state.document = None
                st.session_state.summary = ""
                st.session_state.messages = []
                st.error(str(exc))
        else:
            st.markdown('<span class="status-badge status-idle">Waiting for PDF</span>', unsafe_allow_html=True)


def render_summary_tab(model: genai.GenerativeModel | None, document: PdfDocument | None) -> None:
    """Render the executive summary tab."""

    if document is None:
        render_empty_state()
        return

    render_metrics(document)

    if model is None:
        st.warning("Add `GEMINI_API_KEY` in Streamlit secrets to generate the executive summary.")
        return

    if not st.session_state.summary and not st.session_state.summary_error:
        with st.spinner("Generating executive summary with Gemini..."):
            try:
                st.session_state.summary = call_gemini(model, build_summary_prompt(document))
            except Exception as exc:
                st.session_state.summary_error = str(exc)

    if st.session_state.summary_error:
        st.error(st.session_state.summary_error)
        if st.button("Retry summary", type="primary"):
            st.session_state.summary_error = ""
            st.rerun()
        return

    st.markdown('<div class="summary-panel">', unsafe_allow_html=True)
    st.markdown(st.session_state.summary)
    st.markdown("</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Regenerate summary", use_container_width=True):
            st.session_state.summary = ""
            st.session_state.summary_error = ""
            st.rerun()
    with col_b:
        st.download_button(
            "Download summary",
            data=st.session_state.summary.encode("utf-8"),
            file_name=f"{document.filename.rsplit('.', 1)[0]}_executive_summary.md",
            mime="text/markdown",
            use_container_width=True,
        )


def handle_chat_question(model: genai.GenerativeModel, document: PdfDocument, question: str) -> None:
    """Append a user question and Gemini answer to chat history."""

    clean_question = question.strip()
    if not clean_question:
        return

    st.session_state.messages.append({"role": "user", "content": clean_question})
    with st.spinner("Thinking through the PDF..."):
        try:
            answer = call_gemini(model, build_chat_prompt(document, st.session_state.messages, clean_question))
        except Exception as exc:
            answer = f"I could not complete that request. {exc}"
    st.session_state.messages.append({"role": "assistant", "content": answer})


def render_quick_actions(model: genai.GenerativeModel | None, document: PdfDocument | None) -> None:
    """Render quick prompt buttons for common analysis tasks."""

    actions = [
        "Extract all dates",
        "Summarize in 3 lines",
        "List key risks",
        "Find action items",
    ]
    st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
    columns = st.columns(len(actions))
    for column, action in zip(columns, actions):
        with column:
            if st.button(action, use_container_width=True, disabled=model is None or document is None):
                assert model is not None and document is not None
                handle_chat_question(model, document, action)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_tab(model: genai.GenerativeModel | None, document: PdfDocument | None) -> None:
    """Render the conversational PDF agent tab."""

    if document is None:
        render_empty_state()
        return

    if model is None:
        st.warning("Add `GEMINI_API_KEY` in Streamlit secrets to chat with the PDF.")
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown(
                "I have read the PDF. Ask me for decisions, dates, risks, obligations, "
                "financial figures, or a simpler explanation of any section."
            )

    render_quick_actions(model, document)

    question = st.chat_input("Ask a question about this PDF...")
    if question:
        handle_chat_question(model, document, question)
        st.rerun()


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_css()

    api_key = get_gemini_api_key()
    model = configure_gemini(api_key) if api_key else None

    render_sidebar(api_key)
    render_header()

    document: PdfDocument | None = st.session_state.document
    tab_summary, tab_chat = st.tabs(["📊 Executive Summary", "💬 Chat with PDF Agent"])
    with tab_summary:
        render_summary_tab(model, document)
    with tab_chat:
        render_chat_tab(model, document)


if __name__ == "__main__":
    main()
