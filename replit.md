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
- `GET /api/health` — Health check
- `POST /api/process-pdf` — Upload and extract text from PDF
- `POST /api/chat` — Ask a question about the document
- `POST /api/summarize` — Generate a document summary

## Key Commands

- `bash start.sh` — Start both Flask API and Streamlit app
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
