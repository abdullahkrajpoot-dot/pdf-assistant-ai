import streamlit as st
import requests

FLASK_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    [data-testid="stSidebar"] { background-color: #1A1D27; border-right: 1px solid #2D3142; }

    .app-header {
        background: linear-gradient(135deg, #6C63FF 0%, #3F3D99 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .app-header h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .app-header p { color: rgba(255,255,255,0.8); margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    .metric-card {
        background: #1A1D27;
        border: 1px solid #2D3142;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
        height: 100%;
    }
    .metric-card .metric-value { font-size: 1.8rem; font-weight: 700; color: #6C63FF; }
    .metric-card .metric-label { font-size: 0.78rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; }

    .chat-user {
        background: #2D3142;
        border-left: 3px solid #6C63FF;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.6rem 0;
    }
    .chat-assistant {
        background: #1A1D27;
        border-left: 3px solid #10B981;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin: 0.6rem 0;
    }
    .chat-role { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.35rem; }
    .chat-user .chat-role { color: #6C63FF; }
    .chat-assistant .chat-role { color: #10B981; }
    .chat-answer { line-height: 1.65; color: #E5E7EB; }

    .source-block {
        background: #0E1117;
        border: 1px solid #2D3142;
        border-radius: 6px;
        padding: 0.6rem 0.8rem;
        margin-top: 0.5rem;
        font-size: 0.78rem;
        color: #9CA3AF;
        font-family: monospace;
        line-height: 1.5;
    }
    .source-header {
        font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.08em; color: #4B5563; margin-bottom: 0.4rem;
    }

    .rag-badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: rgba(245, 158, 11, 0.12); color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 20px; padding: 0.2rem 0.65rem; font-size: 0.75rem; font-weight: 700;
    }
    .status-ok {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(16, 185, 129, 0.15); color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px; padding: 0.25rem 0.75rem; font-size: 0.8rem; font-weight: 600;
    }
    .status-idle {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(156, 163, 175, 0.15); color: #9CA3AF;
        border: 1px solid rgba(156, 163, 175, 0.3);
        border-radius: 20px; padding: 0.25rem 0.75rem; font-size: 0.8rem; font-weight: 600;
    }
    .provider-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(108, 99, 255, 0.15); color: #6C63FF;
        border: 1px solid rgba(108, 99, 255, 0.3);
        border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600;
    }
    .section-title {
        font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #6C63FF; margin-bottom: 0.6rem;
    }
    .custom-divider { border: none; border-top: 1px solid #2D3142; margin: 1.2rem 0; }
    .summary-box {
        background: #1A1D27; border: 1px solid #2D3142; border-radius: 10px;
        padding: 1.2rem; line-height: 1.7; color: #E5E7EB; font-size: 0.93rem;
    }
    .pipeline-info {
        background: rgba(245,158,11,0.07);
        border: 1px solid rgba(245,158,11,0.2);
        border-radius: 8px;
        padding: 0.7rem 1rem;
        font-size: 0.82rem;
        color: #D97706;
        margin: 0.8rem 0;
    }
    .empty-state {
        text-align: center; padding: 3rem 1rem; color: #4B5563;
    }
    .empty-state .empty-icon { font-size: 3.5rem; margin-bottom: 0.8rem; }
    .empty-state h3 { color: #6B7280; font-weight: 600; margin-bottom: 0.4rem; }
    .empty-state p { font-size: 0.88rem; }
    .stButton > button { border-radius: 8px !important; font-weight: 600 !important; transition: all 0.2s !important; }
    .sidebar-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #6B7280; margin-bottom: 0.4rem; }
</style>
""", unsafe_allow_html=True)


def check_backend():
    try:
        r = requests.get(f"{FLASK_URL}/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def process_pdf(file_bytes, filename):
    files = {"file": (filename, file_bytes, "application/pdf")}
    r = requests.post(f"{FLASK_URL}/api/process-pdf", files=files, timeout=60)
    return r.json()


def ask_question(doc_id, question, api_key, provider):
    payload = {"doc_id": doc_id, "question": question, "api_key": api_key, "provider": provider}
    r = requests.post(f"{FLASK_URL}/api/chat", json=payload, timeout=90)
    return r.json()


def get_summary(doc_id, api_key, provider):
    payload = {"doc_id": doc_id, "api_key": api_key, "provider": provider}
    r = requests.post(f"{FLASK_URL}/api/summarize", json=payload, timeout=120)
    return r.json()


def init_session():
    defaults = {
        "chat_history": [],
        "doc_meta": None,
        "doc_id": None,
        "summary": None,
        "api_key": "",
        "provider": "OpenAI",
        "show_sources": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()

# ─────────────────────── SIDEBAR ────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem;'>
        <span style='font-size:2.2rem;'>📄</span>
        <div style='font-size:1.1rem; font-weight:700; color:#FAFAFA; margin-top:0.3rem;'>DocuMind AI</div>
        <div style='font-size:0.75rem; color:#6B7280;'>RAG-Powered PDF Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>🤖 AI Provider</div>", unsafe_allow_html=True)
    provider = st.selectbox(
        "Select Provider",
        ["OpenAI", "Gemini"],
        index=0 if st.session_state.provider == "OpenAI" else 1,
        label_visibility="collapsed",
    )
    if provider != st.session_state.provider:
        st.session_state.provider = provider

    st.markdown("<div class='sidebar-label' style='margin-top:1rem;'>🔑 API Key</div>", unsafe_allow_html=True)
    key_placeholder = "sk-..." if provider == "OpenAI" else "AIza..."
    api_key_input = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder=key_placeholder,
        label_visibility="collapsed",
    )
    st.session_state.api_key = api_key_input

    if api_key_input:
        st.markdown("<span class='status-ok'>● Key configured</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-idle'>○ No key set</span>", unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>📂 Upload Document</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        if st.button("⚙️  Process & Index Document", use_container_width=True, type="primary"):
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
                st.success(f"Ready! Split into {result['chunk_count']} chunks.")
            else:
                st.error(result.get("error", "Processing failed"))

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>📊 Document Status</div>", unsafe_allow_html=True)
    if st.session_state.doc_meta:
        m = st.session_state.doc_meta
        st.markdown(f"""
        <div style='font-size:0.82rem; color:#E5E7EB; line-height:2.1;'>
            📄 <b>{m['filename']}</b><br>
            📑 {m['pages']} pages &nbsp;·&nbsp; 📝 {m['words']:,} words<br>
            🧩 <b style='color:#F59E0B;'>{m['chunks']} RAG chunks</b> indexed
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️  Clear Document", use_container_width=True):
            st.session_state.doc_id = None
            st.session_state.doc_meta = None
            st.session_state.chat_history = []
            st.session_state.summary = None
            st.rerun()
    else:
        st.markdown("<span class='status-idle'>○ No document loaded</span>", unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>⚙️ Settings</div>", unsafe_allow_html=True)
    show_sources = st.toggle("Show source excerpts", value=st.session_state.show_sources)
    st.session_state.show_sources = show_sources

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    backend_ok = check_backend()
    if backend_ok:
        st.markdown("<span class='status-ok'>● Backend online</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-idle'>○ Backend offline</span>", unsafe_allow_html=True)


# ─────────────────────── MAIN AREA ──────────────────────
st.markdown("""
<div class='app-header'>
    <h1>📄 DocuMind AI</h1>
    <p>RAG-powered PDF chat &mdash; answers grounded <i>exclusively</i> in your document</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_summary, tab_pipeline, tab_guide = st.tabs(["💬  Chat", "📋  Summary", "🔬  RAG Pipeline", "📖  Guide"])

# ── Chat tab ──────────────────────────────────────────────
with tab_chat:
    if not st.session_state.doc_id:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📂</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF from the sidebar and click <b>Process &amp; Index Document</b> to get started.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        meta = st.session_state.doc_meta
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{meta['pages']}</div><div class='metric-label'>Pages</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{meta['words']:,}</div><div class='metric-label'>Words</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{meta['chunks']}</div><div class='metric-label'>RAG Chunks</div></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><div class='metric-value'><span class='provider-badge'>{st.session_state.provider}</span></div><div class='metric-label'>AI Provider</div></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.8rem;'><span class='rag-badge'>⚡ RAG Active</span></div>", unsafe_allow_html=True)

        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

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
                    indexed_note = ""
                    if msg.get("chunks_built"):
                        indexed_note = "<span style='color:#F59E0B; font-size:0.75rem;'>(vector index built on first query)</span> "
                    st.markdown(f"""
                    <div class='chat-assistant'>
                        <div class='chat-role'>AI · {st.session_state.provider} {indexed_note}</div>
                        <div class='chat-answer'>{msg['content']}</div>
                    </div>""", unsafe_allow_html=True)

                    if st.session_state.show_sources and msg.get("sources"):
                        with st.expander(f"📎 {len(msg['sources'])} source excerpt(s) used", expanded=False):
                            for i, src in enumerate(msg["sources"]):
                                relevance_pct = max(0, round((1 - src['relevance_score'] / 2) * 100))
                                st.markdown(f"""
                                <div class='source-block'>
                                    <div class='source-header'>Excerpt {i+1} &nbsp;·&nbsp; Relevance ~{relevance_pct}%</div>
                                    {src['excerpt']}
                                </div>
                                """, unsafe_allow_html=True)

            if st.button("🗑️  Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.markdown("""
            <div class='empty-state' style='padding:2rem 1rem;'>
                <div class='empty-icon'>💬</div>
                <h3>Start the conversation</h3>
                <p>Your first question will build the vector index — subsequent queries are instant.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            user_q = st.text_input(
                "Your question",
                placeholder="What is this document about? List key recommendations. Who wrote this?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send ➤", use_container_width=True, type="primary")

        if submitted and user_q.strip():
            if not st.session_state.api_key:
                st.error("Please enter your API key in the sidebar.")
            else:
                is_first = not any(m["role"] == "assistant" for m in st.session_state.chat_history)
                spin_msg = "Building vector index and searching…" if is_first else f"Searching {meta['chunks']} chunks with {st.session_state.provider}…"
                with st.spinner(spin_msg):
                    resp = ask_question(
                        st.session_state.doc_id,
                        user_q,
                        st.session_state.api_key,
                        st.session_state.provider.lower(),
                    )
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

# ── Summary tab ───────────────────────────────────────────
with tab_summary:
    if not st.session_state.doc_id:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📋</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF first to generate a summary.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state.summary:
            st.markdown("<div class='section-title'>AI-Generated Summary</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='summary-box'>{st.session_state.summary}</div>", unsafe_allow_html=True)
            if st.button("🔄  Regenerate Summary"):
                st.session_state.summary = None
                st.rerun()
        else:
            meta = st.session_state.doc_meta
            st.markdown(f"""
            <div class='pipeline-info'>
                📋 <b>Map-Reduce Summarization:</b> The backend will process all {meta['chunks']} chunks
                using {"a map-reduce" if meta['chunks'] > 6 else "a single-pass"} strategy with {st.session_state.provider}.
            </div>
            """, unsafe_allow_html=True)

            col_btn, _ = st.columns([2, 3])
            with col_btn:
                if st.button("✨  Generate Summary", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("Please enter your API key in the sidebar.")
                    else:
                        with st.spinner("Summarizing all document chunks…"):
                            resp = get_summary(
                                st.session_state.doc_id,
                                st.session_state.api_key,
                                st.session_state.provider.lower(),
                            )
                        if "summary" in resp:
                            st.session_state.summary = resp["summary"]
                            st.rerun()
                        else:
                            st.error(f"Error: {resp.get('error', 'Unknown error')}")

# ── RAG Pipeline tab ───────────────────────────────────────
with tab_pipeline:
    st.markdown("<div class='section-title'>How the RAG Pipeline Works</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B; font-size:1rem;'>① Ingestion &amp; Chunking</b><br><br>
            When you upload a PDF, <b>pdfplumber</b> extracts all raw text. LangChain's
            <code>RecursiveCharacterTextSplitter</code> then breaks it into <b>overlapping chunks</b>
            (1,000 chars each, 150-char overlap).<br><br>
            Overlapping ensures sentences aren't cut mid-thought — context bleeds between chunks
            so no information is lost at boundaries.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B; font-size:1rem;'>② Embedding &amp; Vector Storage (FAISS)</b><br><br>
            On your first question, each chunk is converted to a dense vector using:<br>
            • <b>OpenAI:</b> <code>text-embedding-ada-002</code><br>
            • <b>Gemini:</b> <code>models/embedding-001</code><br><br>
            These vectors are stored in a <b>FAISS</b> in-memory index — an ultra-fast similarity
            search engine. The index is cached so subsequent queries are instant.
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B; font-size:1rem;'>③ Retrieval (Semantic Search)</b><br><br>
            Your question is embedded with the same model. FAISS performs a
            <b>cosine similarity search</b> to find the 5 most relevant chunks — not by keyword,
            but by <em>meaning</em>.<br><br>
            Only these top chunks are sent to the LLM as context, keeping the prompt focused
            and grounded in the actual document.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#F59E0B; font-size:1rem;'>④ Grounded Generation</b><br><br>
            The LLM receives a strict prompt:<br>
            <em>"Answer ONLY using the provided excerpts. If the answer is not there, say so."</em><br><br>
            This eliminates hallucinations — the model <b>cannot</b> answer from general knowledge.
            Every claim is traceable back to a specific document chunk, visible in the
            <b>source excerpts</b> shown under each answer.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class='summary-box' style='border-color:#6C63FF55; text-align:center;'>
        <span style='font-size:1rem; letter-spacing:0.05em; color:#9CA3AF;'>
            📄 PDF &nbsp;→&nbsp; 🧩 Chunks &nbsp;→&nbsp; 🔢 Embeddings &nbsp;→&nbsp;
            🗃️ FAISS Index &nbsp;→&nbsp; 🔍 Similarity Search &nbsp;→&nbsp; 🤖 LLM &nbsp;→&nbsp; ✅ Grounded Answer
        </span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.doc_meta:
        st.markdown("<br>", unsafe_allow_html=True)
        m = st.session_state.doc_meta
        st.markdown(f"""
        <div class='pipeline-info'>
            <b>Current document stats:</b> &nbsp;
            {m['filename']} &nbsp;·&nbsp;
            {m['pages']} pages &nbsp;·&nbsp;
            {m['words']:,} words &nbsp;·&nbsp;
            <b>{m['chunks']} indexed chunks</b>
        </div>
        """, unsafe_allow_html=True)

# ── Guide tab ─────────────────────────────────────────────
with tab_guide:
    st.markdown("<div class='section-title'>Getting Started</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 1 — Choose your AI Provider</b><br><br>
            Select <b>OpenAI</b> (GPT-3.5) or <b>Gemini</b> (Gemini 1.5 Flash) from the sidebar.<br><br>
            <b>OpenAI key:</b> <a href='https://platform.openai.com/api-keys' style='color:#6C63FF;' target='_blank'>platform.openai.com</a><br>
            <b>Gemini key:</b> <a href='https://aistudio.google.com/app/apikey' style='color:#6C63FF;' target='_blank'>aistudio.google.com</a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 2 — Upload &amp; Index</b><br><br>
            Upload your PDF and click <b>Process &amp; Index Document</b>. The backend extracts
            text and splits it into overlapping chunks for the RAG pipeline.
            No embeddings are created yet — that happens lazily on your first question.
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 3 — Chat with your Document</b><br><br>
            Your first question builds the FAISS vector index (takes a few seconds).
            All subsequent questions are instant semantic searches across your document.<br><br>
            Toggle <b>Show source excerpts</b> in the sidebar to see exactly which parts of the
            document were used to generate each answer.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 4 — Generate a Summary</b><br><br>
            The <b>Summary</b> tab uses a map-reduce strategy for long documents —
            each chunk is individually summarized, then combined into a final overview.
            Check the <b>RAG Pipeline</b> tab to understand how it all works under the hood.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class='summary-box' style='border-color:#6C63FF55;'>
        <b style='color:#6C63FF;'>🔐 Privacy note:</b>
        Your API key is never stored on disk — session only.
        Uploaded PDFs are temporarily saved for extraction and can be cleared anytime.
        The FAISS vector index lives in server memory and is lost on restart.
    </div>
    """, unsafe_allow_html=True)
