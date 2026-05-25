# CLAUDE.md — Project Constitution & Guidelines

This document serves as the single source of truth for engineering standards, coding guidelines, development workflows, and architectural boundaries for the **mro-tts** project.

---

## 1. Development & Operations

### Build & Run Commands
- **Backend (FastAPI)**:
  - Install dependencies: `uv pip compile pyproject.toml -o requirements.txt && uv pip sync requirements.txt` (or `uv sync` if workspace-based)
  - Run development server: `uv run uvicorn app.main:app --reload --port 8000`
  - Run database migrations: `uv run alembic upgrade head`
  - Linting: `uv run ruff check .`
  - Formatting: `uv run ruff format .`
  - Type checking: `uv run mypy . --strict`
- **Frontend (Vite + React)**:
  - Install dependencies: `npm ci` or `npm install`
  - Run development server: `npm run dev`
  - Build production asset: `npm run build`
  - Linting & formatting: `npm run lint`
  - Type checking: `npm run type-check`

### Testing Command Conventions
- **Backend Unit/Integration**: `uv run pytest`
- **Frontend Unit/Component**: `npm run test`
- **End-to-End Testing**: `npm run test:e2e`

---

## 2. Architecture & Design Philosophy

### Modular Design & Composition
- **Composition Over Inheritance**: Avoid deep inheritance chains. Use dependency injection and abstract service components to inject behavior into pipelines.
- **Strict Separation of Concerns**: Keep components isolated:
  - Frontend components must strictly handle UI rendering and presentation logic.
  - Streaming, logic-heavy hooks, and API interactions must reside inside `src/features/` or `src/hooks/` and remain fully decoupled from views.
  - Backend controllers (`routers/`) only handle HTTP/SSE serialization and request parsing. They delegate all business logic to `services/` and `pipelines/`.
  - Database interactions must be encapsulated inside `repositories/` using clean async queries.

### Zero-Placeholder Policy
- No stub functions, mocked classes, or `TODO: implement later` blocks are allowed in production or main branches. Every file must be complete, correctly typed, and functional.
- When referencing files or external API outputs, every external field must be fully defined and validated using strict Pydantic schemas (backend) or TypeScript interfaces (frontend).

---

## 3. Tech Stack & Integration Rules

### Backend Stack (Python 3.11+)
- **Framework**: FastAPI (async-first, utilizing native lifespan handlers).
- **ORM & DB**: SQLAlchemy 2 (async session per request via `async_sessionmaker`) using the `asyncpg` driver connecting to Neon PostgreSQL.
- **Pydantic v2**: Strict model validations. All API request and response data must be serialized through schemas. No dictionary passing.
- **HTTP Client**: `httpx.AsyncClient` used inside a lifespan or dependency injection context to query OpenRouter and Cohere. Do not instantiate client connections per request.

### Frontend Stack (React + TS + Vite)
- **State Management**: Zustand (isolated stores for audio recordings, streaming SSE state, and active maintenance records).
- **Data Fetching**: TanStack Query (managing server-state cache, background query invalidation).
- **Styling & UI**: TailwindCSS + Framer Motion (operational, dark aviation-style, minimal layout, smooth transitions).
- **API Communication**: Native Web Audio API for recording, raw `EventSource` (or `fetch` with readable streams) for SSE events.

---

## 4. Aviation Domain & Safety Validation Rules

### Domain Terminology
- **AMM**: Aircraft Maintenance Manual (the source of truth for maintenance procedures, torque specifications, and limits).
- **QA Record**: Quality Assurance Record generated from a technician's recorded statement.
- **Safety Wire**: Critical locking mechanism used on aircraft fasteners to prevent backing out due to vibration. Must be parsed, validated, and explicitly logged.
- **Torque Limit**: Crucial validation check. Recorded torque values must fall within the AMM-specified ranges.

### Strict Validation Requirements
- All extracted records must run through a **Verification Pipeline**:
  1. Retrieve matching AMM page chunks using Pinecone (embeddings dimension = 512, cosine similarity) and Cohere Rerank.
  2. Perform model validation comparing extracted torque, safety wire, parts, and procedure details against retrieved AMM records.
  3. Set verification status to `PASS` or `FAIL`.
  4. If `FAIL` or anomaly detected (e.g., torque value mismatch or missing safety wire for key parts), trigger an immediate high-priority TTS warning using the Gemini 3.1 TTS model.

---

## 5. Anti-Patterns & Constraints

- **No Chatbots**: This is a realtime maintenance terminal. The interface must not contain "chat bubbles," agent greetings, or text inputs to "talk" to an assistant. Interaction is voice-driven, resulting in a structured QA record.
- **No Synchronous Database Access**: Do not block the async event loop. Avoid synchronous PostgreSQL drivers or querying without `await`.
- **No OpenRouter Model Swaps**: Stick strictly to the specified model roster:
  - **STT**: `openai/gpt-audio-mini`
  - **Embeddings**: `openai/text-embedding-3-small` (dimensions locked to **512**)
  - **Rerank**: `cohere/rerank-4-fast`
  - **Reasoning**: `deepseek/deepseek-v4-flash`
  - **TTS**: `google/gemini-3.1-flash-tts-preview`
- **No Inline Style Overrides**: Avoid arbitrary styled divs or inline style attributes. Rely purely on TailwindCSS utilities and CSS variables defined in the theme configuration.
