import streamlit as st
import datetime
import hashlib
import os

from backend_core import (
    count_pages,
    doc_chunks,
    extract_text_from_pdf,
    get_llm,
    rag_answer,
    split_into_chunks,
    summarize_doc,
)

UPLOAD_FOLDER = "uploads"

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Layout ── */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #1A1D27;
        border-right: 1px solid #2D3142;
    }
    [data-testid="stSidebar"] .stFileUploader label { color: #9CA3AF !important; }

    /* ── Header ── */
    .app-header {
        background: linear-gradient(135deg, #6C63FF 0%, #3F3D99 100%);
        padding: 1.4rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.4rem;
        text-align: center;
    }
    .app-header h1 {
        color: white; font-size: 1.9rem; font-weight: 700;
        margin: 0; letter-spacing: -0.5px;
    }
    .app-header p { color: rgba(255,255,255,0.82); margin: 0.25rem 0 0; font-size: 0.9rem; }

    /* ── Metric cards ── */
    .metric-card {
        background: #1A1D27; border: 1px solid #2D3142;
        border-radius: 10px; padding: 0.85rem 1rem;
        text-align: center; height: 100%;
    }
    .metric-card .metric-value { font-size: 1.6rem; font-weight: 700; color: #6C63FF; }
    .metric-card .metric-label {
        font-size: 0.72rem; color: #9CA3AF;
        text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* ── Chat bubbles ── */
    .chat-user {
        background: #2D3142; border-left: 3px solid #6C63FF;
        border-radius: 8px; padding: 0.85rem 1.1rem; margin: 0.5rem 0;
    }
    .chat-assistant {
        background: #1A1D27; border-left: 3px solid #10B981;
        border-radius: 8px; padding: 0.85rem 1.1rem; margin: 0.5rem 0;
    }
    .chat-role {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.08em; margin-bottom: 0.3rem;
    }
    .chat-user .chat-role { color: #6C63FF; }
    .chat-assistant .chat-role { color: #10B981; }
    .chat-answer { line-height: 1.65; color: #E5E7EB; }

    /* ── Source excerpts ── */
    .source-block {
        background: #0E1117; border: 1px solid #2D3142;
        border-radius: 6px; padding: 0.55rem 0.8rem; margin-top: 0.4rem;
        font-size: 0.77rem; color: #9CA3AF; font-family: monospace; line-height: 1.5;
    }
    .source-header {
        font-size: 0.66rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.08em; color: #4B5563; margin-bottom: 0.35rem;
    }

    /* ── Summary / translation boxes ── */
    .summary-box {
        background: #1A1D27; border: 1px solid #2D3142; border-radius: 10px;
        padding: 1.2rem; line-height: 1.75; color: #E5E7EB; font-size: 0.93rem;
    }
    .urdu-box {
        background: #12151F;
        border: 1px solid #3B3960;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        line-height: 2.0;
        color: #C7D2FE;
        font-size: 1.05rem;
        direction: rtl;
        text-align: right;
        font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', serif;
    }
    .urdu-label {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #818CF8; margin-bottom: 0.5rem;
    }

    /* ── Badges ── */
    .rag-badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: rgba(245, 158, 11, 0.12); color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 20px; padding: 0.2rem 0.65rem;
        font-size: 0.75rem; font-weight: 700;
    }
    .status-ok {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(16, 185, 129, 0.15); color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px; padding: 0.25rem 0.75rem;
        font-size: 0.8rem; font-weight: 600;
    }
    .status-idle {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(156, 163, 175, 0.15); color: #9CA3AF;
        border: 1px solid rgba(156, 163, 175, 0.3);
        border-radius: 20px; padding: 0.25rem 0.75rem;
        font-size: 0.8rem; font-weight: 600;
    }
    .provider-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(108, 99, 255, 0.15); color: #6C63FF;
        border: 1px solid rgba(108, 99, 255, 0.3);
        border-radius: 6px; padding: 0.2rem 0.6rem;
        font-size: 0.78rem; font-weight: 600;
    }

    /* ── Misc ── */
    .section-title {
        font-size: 0.76rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #6C63FF; margin-bottom: 0.5rem;
    }
    .custom-divider { border: none; border-top: 1px solid #2D3142; margin: 1.1rem 0; }
    .pipeline-info {
        background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2);
        border-radius: 8px; padding: 0.65rem 1rem;
        font-size: 0.82rem; color: #D97706; margin: 0.7rem 0;
    }
    .empty-state { text-align: center; padding: 2.5rem 1rem; color: #4B5563; }
    .empty-state .empty-icon { font-size: 3rem; margin-bottom: 0.7rem; }
    .empty-state h3 { color: #6B7280; font-weight: 600; margin-bottom: 0.35rem; }
    .empty-state p { font-size: 0.87rem; }
    .stButton > button {
        border-radius: 8px !important; font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .sidebar-label {
        font-size: 0.69rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #6B7280; margin-bottom: 0.4rem;
    }

    /* ── Responsive: narrow screens ── */
    @media (max-width: 768px) {
        .app-header h1 { font-size: 1.4rem; }
        .metric-card .metric-value { font-size: 1.2rem; }
        .main .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
    }
</style>
""", unsafe_allow_html=True)


# ── API helpers ──────────────────────────────────────────────

def check_backend():
    return True


def process_pdf(file_bytes, filename):
    if not filename or not filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported"}

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    safe_filename = os.path.basename(filename)
    doc_id = hashlib.md5(safe_filename.encode() + file_bytes[:512]).hexdigest()[:16]
    save_path = os.path.join(UPLOAD_FOLDER, f"{doc_id}_{safe_filename}")

    try:
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        raw_text = extract_text_from_pdf(save_path)
        if not raw_text.strip():
            return {"error": "Could not extract text from this PDF. It may be image-based or password-protected."}

        chunks = split_into_chunks(raw_text)
        doc_chunks[doc_id] = chunks

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": safe_filename,
            "page_count": count_pages(save_path),
            "word_count": len(raw_text.split()),
            "char_count": len(raw_text),
            "chunk_count": len(chunks),
        }
    except Exception as e:
        return {"error": str(e)}


def ask_question(doc_id, question, api_key, provider):
    try:
        return rag_answer(doc_id, question.strip(), provider, api_key)
    except Exception as e:
        return {"error": str(e)}


def get_summary(doc_id, api_key, provider):
    try:
        return {"summary": summarize_doc(doc_id, provider, api_key)}
    except Exception as e:
        return {"error": str(e)}


def translate_text(text, api_key, provider, target_lang="Urdu"):
    try:
        prompt = (
            f"Translate the following text into {target_lang}. "
            "Produce only the translated text, no explanations, no notes, no original text.\n\n"
            f"{text}"
        )
        llm = get_llm(provider, api_key)
        from langchain_core.messages import HumanMessage

        response = llm.invoke([HumanMessage(content=prompt)])
        return {"translated": response.content.strip(), "target_lang": target_lang}
    except Exception as e:
        return {"error": str(e)}


# ── Export helpers ───────────────────────────────────────────

def build_summary_txt(doc_meta, summary_en, summary_ur=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 60,
        "  DocuMind AI — Document Summary Export",
        "=" * 60,
        f"Document : {doc_meta['filename']}",
        f"Pages    : {doc_meta['pages']}",
        f"Words    : {doc_meta['words']:,}",
        f"Exported : {now}",
        "=" * 60,
        "",
        "── ENGLISH SUMMARY ──",
        "",
        summary_en,
        "",
    ]
    if summary_ur:
        lines += [
            "── اردو خلاصہ ──",
            "",
            summary_ur,
            "",
        ]
    lines += ["=" * 60, "Generated by DocuMind AI (RAG-powered PDF Intelligence)", "=" * 60]
    return "\n".join(lines)


def build_chat_txt(doc_meta, chat_history, provider):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 60,
        "  DocuMind AI — Chat Highlights Export",
        "=" * 60,
        f"Document : {doc_meta['filename']}",
        f"Provider : {provider}",
        f"Messages : {len([m for m in chat_history if m['role'] == 'user'])} Q&A pairs",
        f"Exported : {now}",
        "=" * 60,
        "",
    ]
    for i, msg in enumerate(chat_history):
        if msg["role"] == "user":
            lines += [f"Q: {msg['content']}", ""]
        else:
            lines += [f"A: {msg['content']}", ""]
            if msg.get("sources"):
                lines.append(f"   [Sources used: {len(msg['sources'])} document excerpt(s)]")
                lines.append("")
            lines.append("-" * 50)
            lines.append("")
    lines += ["=" * 60, "Generated by DocuMind AI (RAG-powered PDF Intelligence)", "=" * 60]
    return "\n".join(lines)


# ── Session state ────────────────────────────────────────────

def init_session():
    defaults = {
        "chat_history": [],
        "doc_meta": None,
        "doc_id": None,
        "summary": None,
        "summary_urdu": None,
        "api_key": "",
        "provider": "OpenAI",
        "show_sources": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()

# ─────────────────────── SIDEBAR ────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem;'>
        <span style='font-size:2rem;'>📄</span>
        <div style='font-size:1.05rem; font-weight:700; color:#FAFAFA; margin-top:0.3rem;'>DocuMind AI</div>
        <div style='font-size:0.72rem; color:#6B7280;'>RAG-Powered PDF Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # Provider
    st.markdown("<div class='sidebar-label'>🤖 AI Provider</div>", unsafe_allow_html=True)
    provider = st.selectbox("Provider", ["OpenAI", "Gemini"], index=0 if st.session_state.provider == "OpenAI" else 1, label_visibility="collapsed")
    if provider != st.session_state.provider:
        st.session_state.provider = provider

    # API Key
    st.markdown("<div class='sidebar-label' style='margin-top:1rem;'>🔑 API Key</div>", unsafe_allow_html=True)
    api_key_input = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="sk-..." if provider == "OpenAI" else "AIza...",
        label_visibility="collapsed",
    )
    st.session_state.api_key = api_key_input
    if api_key_input:
        st.markdown("<span class='status-ok'>● Key configured</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-idle'>○ No key set</span>", unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # Upload
    st.markdown("<div class='sidebar-label'>📂 Upload Document</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_file:
        if st.button("⚙️  Process & Index", use_container_width=True, type="primary"):
            with st.spinner("Extracting text and splitting into chunks…"):
                result = process_pdf(uploaded_file.read(), uploaded_file.name)
            if result.get("success"):
                st.session_state.doc_id = result["doc_id"]
                st.session_state.doc_meta = {
                    "filename": result["filename"],
                    "pages": result["page_count"],
                    "words": result["word_count"],
                    "chars": result["char_count"],
                    "chunks": result["chunk_count"],
                }
                st.session_state.chat_history = []
                st.session_state.summary = None
                st.session_state.summary_urdu = None
                st.success(f"Ready — {result['chunk_count']} chunks indexed!")
            else:
                st.error(result.get("error", "Processing failed"))

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # Document status
    st.markdown("<div class='sidebar-label'>📊 Document</div>", unsafe_allow_html=True)
    if st.session_state.doc_meta:
        m = st.session_state.doc_meta
        st.markdown(f"""
        <div style='font-size:0.81rem; color:#E5E7EB; line-height:2.1;'>
            📄 <b>{m['filename']}</b><br>
            📑 {m['pages']} pages · 📝 {m['words']:,} words<br>
            🧩 <b style='color:#F59E0B;'>{m['chunks']} RAG chunks</b>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🗑️  Clear Document", use_container_width=True):
            for k in ("doc_id", "doc_meta", "chat_history", "summary", "summary_urdu"):
                st.session_state[k] = None if k != "chat_history" else []
            st.rerun()
    else:
        st.markdown("<span class='status-idle'>○ No document loaded</span>", unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # Settings
    st.markdown("<div class='sidebar-label'>⚙️ Settings</div>", unsafe_allow_html=True)
    st.session_state.show_sources = st.toggle("Show source excerpts", value=st.session_state.show_sources)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    if check_backend():
        st.markdown("<span class='status-ok'>● Backend online</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-idle'>○ Backend offline</span>", unsafe_allow_html=True)


# ─────────────────────── MAIN AREA ──────────────────────────
st.markdown("""
<div class='app-header'>
    <h1>📄 DocuMind AI</h1>
    <p>RAG-powered PDF chat &mdash; grounded answers · Urdu translation · one-click exports</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_summary, tab_pipeline, tab_guide = st.tabs([
    "💬  Chat", "📋  Summary & Export", "🔬  RAG Pipeline", "📖  Guide"
])


# ══════════════════════ CHAT TAB ════════════════════════════
with tab_chat:
    if not st.session_state.doc_id:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📂</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF from the sidebar and click <b>Process &amp; Index</b>.</p>
        </div>""", unsafe_allow_html=True)
    else:
        meta = st.session_state.doc_meta
        c1, c2, c3, c4 = st.columns(4)
        for col, val, label in [
            (c1, meta["pages"], "Pages"),
            (c2, f"{meta['words']:,}", "Words"),
            (c3, meta["chunks"], "RAG Chunks"),
            (c4, f"<span class='provider-badge'>{st.session_state.provider}</span>", "Provider"),
        ]:
            col.markdown(f"<div class='metric-card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.7rem;'><span class='rag-badge'>⚡ RAG Active — answers grounded in your document only</span></div>", unsafe_allow_html=True)
        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

        # ── Chat history ──
        if st.session_state.chat_history:
            st.markdown("<div class='section-title'>Conversation</div>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class='chat-user'>
                        <div class='chat-role'>You</div>
                        <div class='chat-answer'>{msg['content']}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    built_note = " <span style='color:#F59E0B;font-size:0.72rem;'>(index built)</span>" if msg.get("chunks_built") else ""
                    st.markdown(f"""
                    <div class='chat-assistant'>
                        <div class='chat-role'>AI · {st.session_state.provider}{built_note}</div>
                        <div class='chat-answer'>{msg['content']}</div>
                    </div>""", unsafe_allow_html=True)

                    if st.session_state.show_sources and msg.get("sources"):
                        with st.expander(f"📎 {len(msg['sources'])} source excerpt(s)", expanded=False):
                            for i, src in enumerate(msg["sources"]):
                                rel = max(0, round((1 - src["relevance_score"] / 2) * 100))
                                st.markdown(f"""
                                <div class='source-block'>
                                    <div class='source-header'>Excerpt {i+1} · Relevance ~{rel}%</div>
                                    {src['excerpt']}
                                </div>""", unsafe_allow_html=True)

            # ── Chat export button ──
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            col_clr, col_dl = st.columns([1, 2])
            with col_clr:
                if st.button("🗑️  Clear Chat", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()
            with col_dl:
                chat_txt = build_chat_txt(meta, st.session_state.chat_history, st.session_state.provider)
                safe_name = meta["filename"].replace(".pdf", "").replace(" ", "_")
                st.download_button(
                    label="⬇️  Download Chat Highlights (.txt)",
                    data=chat_txt.encode("utf-8"),
                    file_name=f"{safe_name}_chat_highlights.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        else:
            st.markdown("""
            <div class='empty-state' style='padding:2rem 1rem;'>
                <div class='empty-icon'>💬</div>
                <h3>Start the conversation</h3>
                <p>Your first question builds the FAISS vector index — subsequent queries are instant.</p>
            </div>""", unsafe_allow_html=True)

        # ── Chat input ──
        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            user_q = st.text_input(
                "Question",
                placeholder="What is this document about? List key findings. Who wrote this?",
                label_visibility="collapsed",
            )
            sent = st.form_submit_button("Send ➤", use_container_width=True, type="primary")

        if sent and user_q.strip():
            if not st.session_state.api_key:
                st.error("Please enter your API key in the sidebar.")
            else:
                first = not any(m["role"] == "assistant" for m in st.session_state.chat_history)
                spin = "Building vector index and searching…" if first else f"Searching {meta['chunks']} chunks with {st.session_state.provider}…"
                with st.spinner(spin):
                    resp = ask_question(st.session_state.doc_id, user_q, st.session_state.api_key, st.session_state.provider.lower())
                if "answer" in resp:
                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": resp["answer"],
                        "sources": resp.get("sources", []),
                        "chunks_built": resp.get("chunks_built", False),
                    })
                    st.rerun()
                else:
                    st.error(f"Error: {resp.get('error', 'Unknown error')}")


# ══════════════════════ SUMMARY & EXPORT TAB ════════════════
with tab_summary:
    if not st.session_state.doc_id:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📋</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF first to generate a summary.</p>
        </div>""", unsafe_allow_html=True)
    else:
        meta = st.session_state.doc_meta

        # ── Generate summary ──
        if not st.session_state.summary:
            st.markdown(f"""
            <div class='pipeline-info'>
                📋 Will use {"map-reduce" if meta["chunks"] > 6 else "single-pass"} summarization across {meta["chunks"]} chunks via {st.session_state.provider}.
            </div>""", unsafe_allow_html=True)
            col_g, _ = st.columns([2, 3])
            with col_g:
                if st.button("✨  Generate Summary", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("Enter your API key in the sidebar first.")
                    else:
                        with st.spinner("Summarizing all document chunks…"):
                            resp = get_summary(st.session_state.doc_id, st.session_state.api_key, st.session_state.provider.lower())
                        if "summary" in resp:
                            st.session_state.summary = resp["summary"]
                            st.session_state.summary_urdu = None
                            st.rerun()
                        else:
                            st.error(f"Error: {resp.get('error', 'Unknown error')}")
        else:
            # ── English summary ──
            st.markdown("<div class='section-title'>English Summary</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='summary-box'>{st.session_state.summary}</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

            # ── Action row: Translate + Download (English) ──
            col_tr, col_dl_en, col_regen = st.columns([2, 2, 1])

            with col_tr:
                translate_btn = st.button(
                    "🌐  Translate to Urdu",
                    use_container_width=True,
                    disabled=not st.session_state.api_key,
                )
            with col_dl_en:
                safe_name = meta["filename"].replace(".pdf", "").replace(" ", "_")
                en_txt = build_summary_txt(meta, st.session_state.summary)
                st.download_button(
                    label="⬇️  Download Summary (.txt)",
                    data=en_txt.encode("utf-8"),
                    file_name=f"{safe_name}_summary.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            with col_regen:
                if st.button("🔄", help="Regenerate summary", use_container_width=True):
                    st.session_state.summary = None
                    st.session_state.summary_urdu = None
                    st.rerun()

            if translate_btn:
                with st.spinner("Translating to Urdu…"):
                    tr = translate_text(st.session_state.summary, st.session_state.api_key, st.session_state.provider.lower())
                if "translated" in tr:
                    st.session_state.summary_urdu = tr["translated"]
                    st.rerun()
                else:
                    st.error(f"Translation error: {tr.get('error', 'Unknown error')}")

            # ── Urdu translation ──
            if st.session_state.summary_urdu:
                st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
                st.markdown("<div class='urdu-label'>اردو خلاصہ · Urdu Translation</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='urdu-box'>{st.session_state.summary_urdu}</div>", unsafe_allow_html=True)

                st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)

                # Download combined (English + Urdu)
                col_dl_both, _ = st.columns([2, 3])
                with col_dl_both:
                    both_txt = build_summary_txt(meta, st.session_state.summary, st.session_state.summary_urdu)
                    st.download_button(
                        label="⬇️  Download English + Urdu (.txt)",
                        data=both_txt.encode("utf-8"),
                        file_name=f"{safe_name}_summary_en_ur.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
            elif st.session_state.summary:
                st.markdown("""
                <div style='margin-top:0.6rem; font-size:0.82rem; color:#6B7280;'>
                    Click <b>Translate to Urdu</b> above to see the Urdu version and download the bilingual export.
                </div>""", unsafe_allow_html=True)


# ══════════════════════ RAG PIPELINE TAB ════════════════════
with tab_pipeline:
    st.markdown("<div class='section-title'>How the RAG Pipeline Works</div>", unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B;'>① Ingestion & Chunking</b><br><br>
            <b>pdfplumber</b> extracts raw text. LangChain's <code>RecursiveCharacterTextSplitter</code>
            creates <b>overlapping 1,000-char chunks</b> (150-char overlap) so no sentence is cut mid-thought.
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B;'>② Embedding & FAISS Index</b><br><br>
            On your first question, each chunk becomes a dense vector:<br>
            • <b>OpenAI:</b> <code>text-embedding-ada-002</code><br>
            • <b>Gemini:</b> <code>models/embedding-001</code><br><br>
            Stored in a <b>FAISS</b> in-memory index — cached for instant subsequent queries.
        </div>""", unsafe_allow_html=True)

    with cb:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B;'>③ Semantic Retrieval</b><br><br>
            Your question is embedded and compared against all chunk vectors via
            <b>cosine similarity</b>. The top 5 most relevant chunks are retrieved —
            by meaning, not keyword matching.
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B;'>④ Grounded Generation + Translation</b><br><br>
            The LLM receives a strict prompt: <em>"Answer ONLY from these excerpts."</em><br><br>
            Summaries use a <b>map-reduce</b> strategy (long docs) or <b>stuffing</b> (short docs).
            Translations are made by the same LLM — no third-party translation API needed.
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class='summary-box' style='border-color:#6C63FF55; text-align:center;'>
        <span style='color:#9CA3AF; letter-spacing:0.04em;'>
            📄 PDF &nbsp;→&nbsp; 🧩 Chunks &nbsp;→&nbsp; 🔢 Embeddings &nbsp;→&nbsp;
            🗃️ FAISS &nbsp;→&nbsp; 🔍 Similarity Search &nbsp;→&nbsp; 🤖 LLM
            &nbsp;→&nbsp; ✅ Grounded Answer / 🌐 Urdu Translation / ⬇️ .txt Export
        </span>
    </div>""", unsafe_allow_html=True)

    if st.session_state.doc_meta:
        m = st.session_state.doc_meta
        st.markdown(f"""
        <div class='pipeline-info' style='margin-top:1rem;'>
            <b>Loaded:</b> {m['filename']} · {m['pages']} pages · {m['words']:,} words · <b>{m['chunks']} chunks indexed</b>
        </div>""", unsafe_allow_html=True)


# ══════════════════════ GUIDE TAB ═══════════════════════════
with tab_guide:
    st.markdown("<div class='section-title'>Getting Started</div>", unsafe_allow_html=True)
    ga, gb = st.columns(2)

    with ga:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF;'>Step 1 — Choose AI Provider & Key</b><br><br>
            Select <b>OpenAI</b> (GPT-3.5) or <b>Gemini</b> (1.5 Flash) from the sidebar.<br><br>
            <b>OpenAI:</b> <a href='https://platform.openai.com/api-keys' style='color:#6C63FF;' target='_blank'>platform.openai.com</a><br>
            <b>Gemini:</b> <a href='https://aistudio.google.com/app/apikey' style='color:#6C63FF;' target='_blank'>aistudio.google.com</a>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF;'>Step 2 — Upload & Index Your PDF</b><br><br>
            Upload any PDF and click <b>Process &amp; Index</b>. The backend extracts text
            and splits it into overlapping RAG chunks — ready for semantic search.
        </div>""", unsafe_allow_html=True)

    with gb:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF;'>Step 3 — Chat & Download Highlights</b><br><br>
            Ask any question in the <b>Chat</b> tab. Each answer shows the exact document
            excerpts used. When done, click <b>Download Chat Highlights</b> to export a
            clean Q&amp;A text file.
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF;'>Step 4 — Summary, Urdu Translation & Export</b><br><br>
            In the <b>Summary &amp; Export</b> tab: generate a summary, then click
            <b>Translate to Urdu</b> for an instant RTL Urdu version. Download either the
            English-only or the bilingual English + اردو text file.
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class='summary-box' style='border-color:#6C63FF55;'>
        <b style='color:#6C63FF;'>🔐 Privacy note:</b>
        Your API key is session-only — never written to disk.
        Uploaded PDFs are temporarily saved for text extraction.
        The FAISS vector index lives in server memory and resets on restart.
    </div>""", unsafe_allow_html=True)
