# MRO-TTS // Aviation Maintenance QA Copilot

[![FastAPI Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React Frontend](https://img.shields.io/badge/Frontend-React%20%2F%20Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Promptfoo Eval](https://img.shields.io/badge/Evaluations-Promptfoo%20100%25-green?style=flat-square&logo=testcafe&logoColor=white)](https://promptfoo.dev)
[![Observability](https://img.shields.io/badge/Observability-Arize%20Phoenix-orange?style=flat-square&logo=opentelemetry&logoColor=white)](https://phoenix.arize.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

**MRO-TTS** is a real-time, voice-driven Quality Assurance (QA) compliance copilot for Aircraft Maintenance, Repair, and Overhaul (MRO) technicians. 

Technicians record spoken logs describing maintenance actions (e.g., torquing ground stud nuts, measuring wire harness clearance, installing hydraulic lines). MRO-TTS transcribes the audio, queries the specific structural specifications using **RAG (Pinecone + Cohere Rerank)**, and uses reasoning LLMs (**DeepSeek**) to validate parameters against ground-truth Aircraft Maintenance Manual (AMM) reference documents.

---

## ✈️ Real-World Business Impact & Use Cases

Aviation maintenance demands absolute precision; a single misplaced wire harness, incorrect ground stud torque, or missing lock-wire can lead to catastrophic component failure or grounding. Traditionally, technicians must stop work, wipe down their hands, open static PDFs or binder-bound manuals, and manually verify parameters. 

**MRO-TTS digitizes and automates this workflow directly at the aircraft:**
*   **Eyes-on-the-Job Verification**: Technicians remain hands-free. They speak their log, and the console immediately checks the values, sounding pleasant audit-pass cues or warning buzzers.
*   **Eliminate Manual Lookups**: Automates search through thousands of pages of structural specs, returning the exact manual page reference (e.g. *Avionics Wiring Handbook page 37*) within seconds.
*   **Instant Compliance Catch**: Automatically extracts parameter labels, measured values, and specifications, highlighting and logging out-of-spec failures (FAIL) before the aircraft is signed off.
*   **Audit-Ready Digital History**: Automatically archives every validated log with references into Neon PostgreSQL, creating a tamper-proof digital compliance checklist.

---

## Key Features

*   🎙️ **Real-Time Speech-to-Text**: Low-latency voice log processing via the multimodal `openai/gpt-audio-mini` model on OpenRouter.
*   🔍 **High-Density RAG Pipeline**: Combines Pinecone vector query (Top 15 Chunks) with Cohere's Reranker (`cohere/rerank-4-fast` via OpenRouter) to extract ground-truth manual specifications.
*   🧠 **Automated Compliance Engine**: DeepSeek extraction (`deepseek/deepseek-v4-flash`) validating parameters (PASS/FAIL) and logging deviations.
*   📡 **Server-Sent Events (SSE)**: Streaming execution updates and step progress dynamically to the technician console.
*   🧪 **CI/CD Prompt Evaluations**: 100% test coverage and validation checks utilizing **Promptfoo**.
*   📊 **APM & GenAI Tracing**: Full OpenTelemetry instrumentation reporting to **Arize Phoenix** for granular execution latency, costs, and token auditing.

---

## Core Pipeline Architecture

```mermaid
graph TD
    A[Technician Speech / WebM Audio] -->|POST /api/v1/records/process| B(FastAPI Endpoint)
    B -->|gpt-audio-mini| C[Spoken Transcript text]
    C -->|openai/text-embedding-3-small| D[Pinecone Vector Search]
    D -->|Top 15 Chunks| E[Cohere Rerank via OpenRouter]
    E -->|Top 3 AMM Contexts| F[DeepSeek validation prompt]
    F -->|Validation JSON| G[Pydantic compliance check]
    G -->|Write| H[Neon PostgreSQL database]
    G -->|SSE Stream event| I[React Technician UI]
```

---

## Technician Console Layout

The application features a single-page reactive console matching the physical workspace:
*   **Header status bar**: Shows active connection session IDs, connection heartbeat status, and light/dark theme toggles.
*   **Left Column (Input Control)**: Contains the voice recording trigger and the editable text transcript card for manual adjustments.
*   **Right Column (Validation & Intel)**: 
    *   **AMM Reference Card**: Displays the retrieved manual source document page, relevance score, and source snippets.
    *   **Validation Panel**: Renders extracted compliance parameters (values, specs, and status) with visual pass/fail indicator blocks.
*   **Footer**: Holds the persistent, historical session checklist tracker archiving all processed logs.

---

## Getting Started

### Prerequisites
*   Node.js `v22.18.0+`
*   Python `3.11+`

### 1. Setup Backend API
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables template and configure your secrets:
   ```bash
   cp .env.example .env
   ```
5. Run the dev server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Setup Frontend UI
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the development build:
   ```bash
   npm run dev
   ```

---

## Configuration (`.env`)

Configure the following secrets in `backend/.env`. 

> [!NOTE]
> Since the Cohere rerank model runs via OpenRouter's API endpoint, you **do not** need a separate Cohere API key. Only the OpenRouter key is required.

```ini
# OpenRouter API Credentials
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Pinecone Index Config
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=mro-tts-manuals
PINECONE_INDEX_HOST=https://your-pinecone-host.io

# Neon PostgreSQL Database Connection
DATABASE_URL=postgresql://user:password@neon-host/db?sslmode=require

# OpenTelemetry Exporter Endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces
```

---

## Testing & Observability

### Promptfoo Regression Evaluations
To ensure prompts output valid JSON structures and catch regression bugs during development:
```bash
cd backend
npx -y promptfoo eval
```

### Arize Phoenix Telemetry Tracing
1. Start the local Arize Phoenix trace collector:
   ```bash
   python -m phoenix.server.main serve
   ```
2. Open **`http://localhost:6006`** in your browser to inspect spans, latency, prompt trees, and token costs.

---

## Cloud Deployment

*   **Frontend (React/Vite)**: Deployed to **Vercel** (Free Tier). Set the environment variable `VITE_API_URL` to point to your hosted backend.
*   **Backend (FastAPI)**: Deployed to **Koyeb** (Free Tier) using the production [Dockerfile](backend/Dockerfile). Expose container port `8000` and map your environment secrets.

---

## License

This project is licensed under the MIT License.
