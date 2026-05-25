# Project Folder Structure — mro-tts

This document outlines the recommended folder layout and separation of concerns for both backend (FastAPI) and frontend (React + Vite + TypeScript) applications.

---

## 1. Directory Tree Overview

```text
mro-tts/
├── .claude/
│   └── skills/
│       ├── backend-architecture.md
│       ├── frontend-system-design.md
│       ├── rag-pipeline.md
│       └── streaming-ui.md
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── exceptions.py
│   │   ├── routers/
│   │   │   ├── health.py
│   │   │   └── records.py
│   │   ├── schemas/
│   │   │   └── records.py
│   │   ├── services/
│   │   │   ├── audio.py
│   │   │   ├── stream_manager.py
│   │   │   └── validation.py
│   │   ├── repositories/
│   │   │   └── records.py
│   │   ├── pipelines/
│   │   │   └── process_pipeline.py
│   │   ├── integrations/
│   │   │   ├── cohere.py
│   │   │   ├── gemini_tts.py
│   │   │   ├── openrouter.py
│   │   │   └── pinecone.py
│   │   └── main.py
│   ├── migrations/
│   │   └── env.py
│   ├── tests/
│   ├── alembic.ini
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── client.ts
    │   ├── assets/
    │   ├── components/
    │   │   └── ui/
    │   │       ├── Button.tsx
    │   │       ├── Card.tsx
    │   │       └── StatusBadge.tsx
    │   ├── features/
    │   │   └── terminal/
    │   │       ├── components/
    │   │       │   ├── AMMReferences.tsx
    │   │       │   ├── RecordButton.tsx
    │   │       │   ├── TranscriptView.tsx
    │   │       │   ├── ValidationPanel.tsx
    │   │       │   └── WarningOverlay.tsx
    │   │       └── hooks/
    │   │           ├── useAudioRecorder.ts
    │   │           └── useSSEStream.ts
    │   ├── hooks/
    │   ├── store/
    │   │   └── terminalStore.ts
    │   ├── types/
    │   │   └── contracts.ts
    │   ├── App.tsx
    │   ├── index.css
    │   └── main.tsx
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

---

## 2. Backend Module Responsibilities

*   `app/core/`: Application settings and database setup.
    *   `config.py`: Loads and validates settings (database URLs, OpenRouter API keys, model parameters) using `pydantic-settings`.
    *   `database.py`: Initializes the SQLAlchemy asynchronous engine and async session factories.
*   `app/routers/`: Request validation and HTTP response routing.
    *   `records.py`: Exposes HTTP POST `/process` endpoint for audio upload, and GET `/stream` endpoint for SSE broadcast.
*   `app/schemas/`: Pydantic V2 definitions specifying request payloads, responses, and SSE event DTOs.
*   `app/services/`: Application business logic.
    *   `audio.py`: Processes and validates uploaded audio files.
    *   `validation.py`: Conducts structural logic comparison (extracted mechanic torque value vs. manual torque values).
    *   `stream_manager.py`: Manages SSE memory channels, reconnection queues, and thread-safe publishing.
*   `app/repositories/`: Raw database reads/writes.
    *   `records.py`: Implements async SQLAlchemy CRUD operations for storing the structured QA report to Neon PostgreSQL.
*   `app/pipelines/`: Orchestrates the processing flows.
    *   `process_pipeline.py`: Runs the async RAG & reasoning pipeline (STT -> Embeddings -> Vector Search -> Rerank -> Reasoning -> Structuring -> Validation).
*   `app/integrations/`: Interfaces with external service APIs.
    *   `openrouter.py`: Handles SDK calls to `openai/gpt-audio-mini` and `deepseek/deepseek-v4-flash`.
    *   `cohere.py`: Integrates `cohere/rerank-4-fast` reranking.
    *   `pinecone.py`: Standardizes Pinecone querying with exact vector dimensions = 512.
    *   `gemini_tts.py`: Connects to `google/gemini-3.1-flash-tts-preview` for safety warning audio synthesis.

---

## 3. Frontend Module Responsibilities

*   `src/api/`: Outlines API clients, client timeout protocols, and raw endpoint calls.
*   `src/components/ui/`: Contains atomic, reusable, visual styling primitives (buttons, layout panels, status indicators) adhering to the dark aviation operational aesthetic.
*   `src/features/terminal/`: Implements the central dashboard view.
    *   `components/`: Sub-components specific to the terminal layout, including the custom waveform visualizer, the torque parameter dashboard, and the manual checklist panel.
    *   `hooks/`: Hook logic managing hardware constraints.
        *   `useAudioRecorder.ts`: Interfaces with the Web Audio API to record audio, capture PCM bytes, and handle microphone authorization.
        *   `useSSEStream.ts`: Integrates the browser's EventSource to stream server events, handling automatic reconnect and buffer syncing.
*   `src/store/`: Zustand state container (`terminalStore.ts`) orchestrating the state of active recording, transcripts, retrieved reference pages, extracted compliance indicators, and active warning audio playbacks.
*   `src/types/`: Centralized typescript schemas matched explicitly against Backend Pydantic structures.
