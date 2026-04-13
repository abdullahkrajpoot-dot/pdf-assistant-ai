import streamlit as st
import requests
import json
import time

FLASK_URL = "http://localhost:8000"

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Main layout */
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* Sidebar styling */
    [data-testid="stSidebar"] { background-color: #1A1D27; border-right: 1px solid #2D3142; }

    /* Header */
    .app-header {
        background: linear-gradient(135deg, #6C63FF 0%, #3F3D99 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .app-header h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .app-header p { color: rgba(255,255,255,0.8); margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* Metric cards */
    .metric-card {
        background: #1A1D27;
        border: 1px solid #2D3142;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .metric-card .metric-value { font-size: 1.8rem; font-weight: 700; color: #6C63FF; }
    .metric-card .metric-label { font-size: 0.78rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Chat messages */
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

    /* Status badges */
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

    /* Provider badge */
    .provider-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(108, 99, 255, 0.15); color: #6C63FF;
        border: 1px solid rgba(108, 99, 255, 0.3);
        border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600;
    }

    /* Section headings */
    .section-title {
        font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #6C63FF; margin-bottom: 0.6rem;
    }

    /* Divider */
    .custom-divider { border: none; border-top: 1px solid #2D3142; margin: 1.2rem 0; }

    /* Summary box */
    .summary-box {
        background: #1A1D27; border: 1px solid #2D3142; border-radius: 10px;
        padding: 1.2rem; line-height: 1.7; color: #E5E7EB; font-size: 0.93rem;
    }

    /* Empty state */
    .empty-state {
        text-align: center; padding: 3rem 1rem; color: #4B5563;
    }
    .empty-state .empty-icon { font-size: 3.5rem; margin-bottom: 0.8rem; }
    .empty-state h3 { color: #6B7280; font-weight: 600; margin-bottom: 0.4rem; }
    .empty-state p { font-size: 0.88rem; }

    /* Button overrides */
    .stButton > button {
        border-radius: 8px !important; font-weight: 600 !important;
        transition: all 0.2s !important;
    }

    /* Sidebar section label */
    .sidebar-label {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #6B7280; margin-bottom: 0.4rem;
    }
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


def ask_question(question, context, api_key, provider):
    payload = {"question": question, "context": context, "api_key": api_key, "provider": provider}
    r = requests.post(f"{FLASK_URL}/api/chat", json=payload, timeout=60)
    return r.json()


def get_summary(context, api_key, provider):
    payload = {"context": context, "api_key": api_key, "provider": provider}
    r = requests.post(f"{FLASK_URL}/api/summarize", json=payload, timeout=90)
    return r.json()


def init_session():
    defaults = {
        "chat_history": [],
        "doc_text": None,
        "doc_meta": None,
        "summary": None,
        "api_key": "",
        "provider": "OpenAI",
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
        <div style='font-size:0.75rem; color:#6B7280;'>PDF Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # — AI Provider ——
    st.markdown("<div class='sidebar-label'>🤖 AI Provider</div>", unsafe_allow_html=True)
    provider = st.selectbox(
        "Select Provider",
        ["OpenAI", "Gemini"],
        index=0 if st.session_state.provider == "OpenAI" else 1,
        label_visibility="collapsed",
    )
    st.session_state.provider = provider

    # — API Key ——
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

    # — Upload ——
    st.markdown("<div class='sidebar-label'>📂 Upload Document</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        if st.button("⚙️  Process Document", use_container_width=True, type="primary"):
            with st.spinner("Extracting text…"):
                result = process_pdf(uploaded_file.read(), uploaded_file.name)
            if result.get("success"):
                st.session_state.doc_text = result["text"]
                st.session_state.doc_meta = {
                    "filename": result["filename"],
                    "pages": result["page_count"],
                    "words": result["word_count"],
                    "chars": result["char_count"],
                }
                st.session_state.chat_history = []
                st.session_state.summary = None
                st.success("Document ready!")
            else:
                st.error(result.get("error", "Processing failed"))

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # — Document status ——
    st.markdown("<div class='sidebar-label'>📊 Document Status</div>", unsafe_allow_html=True)
    if st.session_state.doc_meta:
        m = st.session_state.doc_meta
        st.markdown(f"""
        <div style='font-size:0.82rem; color:#E5E7EB; line-height:2;'>
            📄 <b>{m['filename']}</b><br>
            📑 {m['pages']} pages<br>
            📝 {m['words']:,} words<br>
            🔤 {m['chars']:,} characters
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️  Clear Document", use_container_width=True):
            st.session_state.doc_text = None
            st.session_state.doc_meta = None
            st.session_state.chat_history = []
            st.session_state.summary = None
            st.rerun()
    else:
        st.markdown("<span class='status-idle'>○ No document loaded</span>", unsafe_allow_html=True)

    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

    # — Backend status ——
    backend_ok = check_backend()
    if backend_ok:
        st.markdown("<span class='status-ok'>● Backend online</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-idle'>○ Backend offline</span>", unsafe_allow_html=True)


# ─────────────────────── MAIN AREA ──────────────────────
st.markdown("""
<div class='app-header'>
    <h1>📄 DocuMind AI</h1>
    <p>Upload a PDF and ask questions — powered by OpenAI or Google Gemini</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_summary, tab_guide = st.tabs(["💬  Chat", "📋  Summary", "📖  Guide"])

# ── Chat tab ──────────────────────────────────────────────
with tab_chat:
    if not st.session_state.doc_text:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📂</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF from the sidebar and click <b>Process Document</b> to get started.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        meta = st.session_state.doc_meta

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{meta['pages']}</div>
                <div class='metric-label'>Pages</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{meta['words']:,}</div>
                <div class='metric-label'>Words</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'><span class='provider-badge'>{st.session_state.provider}</span></div>
                <div class='metric-label'>AI Provider</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Chat history
        if st.session_state.chat_history:
            st.markdown("<div class='section-title'>Conversation</div>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class='chat-user'>
                        <div class='chat-role'>You</div>
                        {msg['content']}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='chat-assistant'>
                        <div class='chat-role'>AI ({st.session_state.provider})</div>
                        {msg['content']}
                    </div>""", unsafe_allow_html=True)

            if st.button("🗑️  Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.markdown("""
            <div class='empty-state' style='padding:2rem 1rem;'>
                <div class='empty-icon'>💬</div>
                <h3>Start the conversation</h3>
                <p>Ask anything about your document below.</p>
            </div>
            """, unsafe_allow_html=True)

        # Input
        st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            user_q = st.text_input(
                "Your question",
                placeholder="What is this document about? Who is the author? Summarize section 3…",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send ➤", use_container_width=True, type="primary")

        if submitted and user_q.strip():
            if not st.session_state.api_key:
                st.error("Please enter your API key in the sidebar.")
            else:
                with st.spinner(f"Thinking with {st.session_state.provider}…"):
                    resp = ask_question(
                        user_q,
                        st.session_state.doc_text,
                        st.session_state.api_key,
                        st.session_state.provider.lower(),
                    )
                if "answer" in resp:
                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    st.session_state.chat_history.append({"role": "assistant", "content": resp["answer"]})
                    st.rerun()
                else:
                    st.error(f"Error: {resp.get('error', 'Unknown error')}")

# ── Summary tab ───────────────────────────────────────────
with tab_summary:
    if not st.session_state.doc_text:
        st.markdown("""
        <div class='empty-state'>
            <div class='empty-icon'>📋</div>
            <h3>No document loaded</h3>
            <p>Upload a PDF first to generate a summary.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state.summary:
            st.markdown("<div class='section-title'>AI Summary</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='summary-box'>{st.session_state.summary}</div>", unsafe_allow_html=True)
            if st.button("🔄  Regenerate Summary"):
                st.session_state.summary = None
                st.rerun()
        else:
            st.markdown("""
            <div class='empty-state' style='padding:2.5rem 1rem;'>
                <div class='empty-icon'>🪄</div>
                <h3>Ready to summarize</h3>
                <p>Click below to generate an AI-powered summary of your document.</p>
            </div>
            """, unsafe_allow_html=True)

            col_btn, _ = st.columns([2, 3])
            with col_btn:
                if st.button("✨  Generate Summary", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("Please enter your API key in the sidebar.")
                    else:
                        with st.spinner("Generating summary…"):
                            resp = get_summary(
                                st.session_state.doc_text,
                                st.session_state.api_key,
                                st.session_state.provider.lower(),
                            )
                        if "summary" in resp:
                            st.session_state.summary = resp["summary"]
                            st.rerun()
                        else:
                            st.error(f"Error: {resp.get('error', 'Unknown error')}")

# ── Guide tab ─────────────────────────────────────────────
with tab_guide:
    st.markdown("""
    <div class='section-title'>Getting Started</div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 1 — Choose your AI Provider</b><br><br>
            In the sidebar, select <b>OpenAI</b> (GPT-3.5 / GPT-4) or <b>Gemini</b> (Google's Gemini 1.5 Flash).<br><br>
            <b>OpenAI key:</b> Get from <a href='https://platform.openai.com/api-keys' style='color:#6C63FF;' target='_blank'>platform.openai.com</a><br>
            <b>Gemini key:</b> Get from <a href='https://aistudio.google.com/app/apikey' style='color:#6C63FF;' target='_blank'>aistudio.google.com</a><br><br>
            Enter your key in the <b>API Key</b> field (it's stored only in your session).
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 2 — Upload & Process a PDF</b><br><br>
            Use the <b>Upload Document</b> panel in the sidebar to select a PDF file.<br><br>
            Click <b>Process Document</b> — the backend will extract all text from your PDF and make it available for AI queries.
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 3 — Chat with your Document</b><br><br>
            Switch to the <b>Chat</b> tab and type any question about your document.<br><br>
            Examples:<br>
            • "What is the main topic of this document?"<br>
            • "Who are the authors?"<br>
            • "What are the key findings in section 2?"<br>
            • "List all the recommendations mentioned."
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class='summary-box'>
            <b style='color:#6C63FF; font-size:1rem;'>Step 4 — Generate a Summary</b><br><br>
            Go to the <b>Summary</b> tab and click <b>Generate Summary</b>.<br><br>
            The AI will produce a concise, accurate summary of your entire document — great for quick overviews of long reports, research papers, or contracts.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class='summary-box' style='border-color:#6C63FF55;'>
        <b style='color:#6C63FF;'>🔐 Privacy note:</b>
        Your API key is never stored on disk — it lives only in your browser session.
        Uploaded PDFs are temporarily stored on the server for processing and can be cleared at any time.
    </div>
    """, unsafe_allow_html=True)
