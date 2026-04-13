# Workspace

## Overview

pnpm workspace monorepo using TypeScript + Python full-stack application.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5 (Node) + Flask (Python)
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## DocuMind AI — Python App

A full-stack PDF intelligence app built with Streamlit (frontend) and Flask (backend).

### Files
- `streamlit_app.py` — Streamlit frontend (dark mode, sidebar, chat/summary UI)
- `flask_app.py` — Flask REST API backend (PDF processing, OpenAI/Gemini integration)
- `start.sh` — Startup script that runs both services
- `.streamlit/config.toml` — Streamlit server + dark theme config

### Ports
- **Streamlit**: port 5000 (main UI)
- **Flask API**: port 8000 (backend)

### Supported AI Providers
- **OpenAI** (GPT-3.5): requires an API key from platform.openai.com
- **Gemini** (Gemini 1.5 Flash): requires an API key from aistudio.google.com

### API Endpoints
- `GET /api/health` — Health check (reports loaded docs & cached stores)
- `POST /api/process-pdf` — Upload PDF, extract text, split into RAG chunks → returns `doc_id`
- `POST /api/chat` — RAG chat: FAISS similarity search → grounded LLM answer + source excerpts
- `POST /api/summarize` — Map-reduce or stuffing summarization of all document chunks
- `POST /api/translate` — Translate any text to Urdu (or other language) via the selected LLM

### Portfolio Features
- **Urdu Translation**: one-click AI translation of the summary with RTL rendering
- **Download Chat Highlights**: exports full Q&A conversation as a `.txt` file
- **Download Summary**: exports English-only or bilingual English + Urdu `.txt` file
- **RAG Pipeline tab**: visual explanation of the full retrieval-augmented generation flow
- **Responsive layout**: works on narrow screens via CSS media queries

## Key Commands

- `bash start.sh` — Start both Flask API and Streamlit app
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
