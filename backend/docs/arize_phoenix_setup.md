# Arize Phoenix Production Observability Setup Guide

This guide details how to integrate **Arize Phoenix** using standard **OpenTelemetry** instrumentation in the FastAPI backend of the `mro-tts` system. This allows full visibility, latency tracing, and input/output tracing of our RAG retrievals and LLM compliance validation completions.

---

## 1. Required Dependencies

Install the following OpenTelemetry and OpenInference dependencies inside the Python environment:

```bash
uv pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-exporter-otlp \
  openinference-instrumentation-dspy \
  arize-phoenix
```

---

## 2. OpenTelemetry Configuration & Initialization

Create a configuration module `backend/app/core/observability.py` to initialize the Tracer Provider at application startup:

```python
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger("observability")

def init_observability(app: FastAPI, service_name: str = "mro-tts-backend") -> None:
    """Initializes OpenTelemetry Tracer Provider and registers FastAPI instrumentation."""
    
    # Configure Resource metadata
    resource = Resource.create(attributes={
        "service.name": service_name,
        "environment": "production"
    })
    
    provider = TracerProvider(resource=resource)
    
    # Arize Phoenix accepts traces via OTLP/HTTP at /v1/traces (default port 6006)
    phoenix_endpoint = "http://localhost:6006/v1/traces"
    
    try:
        exporter = OTLPSpanExporter(endpoint=phoenix_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry Tracer Provider initialized targeting Arize Phoenix at {phoenix_endpoint}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry exporter: {e}")
        return
        
    # Instrument the FastAPI app for incoming HTTP request spans
    FastAPIInstrumentor.instrument_app(app)
```

Integrate this into `backend/app/main.py`:

```python
from app.core.observability import init_observability

# At the end of the FastAPI application definition:
init_observability(app)
```

---

## 3. Instrumenting the RAG & LLM Pipeline

Since our RAG logic and OpenRouter calls in [process_pipeline.py](file:///c:/Coding/mro-tts/backend/app/pipelines/process_pipeline.py) use raw HTTP clients (`httpx`), we can instrument these blocks using custom OpenTelemetry spans. This gives granular breakdowns of each stage (Transcription, Pinecone Query, Cohere Rerank, DeepSeek LLM execution).

### Step-by-Step Pipeline Spans

Here is how you can update `process_pipeline.py` to trace spans and record metadata (like token counts, models, and latency):

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("mro-tts-pipeline")

# Inside RAGPipelineCoordinator:
async def execute(
    self,
    connection_id: str,
    audio_bytes: bytes | None = None,
    transcript: str | None = None,
) -> None:
    # 1. Start parent span for the overall execution pipeline
    with tracer.start_as_current_span("mro_tts_pipeline_execute") as parent_span:
        parent_span.set_attribute("connection_id", connection_id)
        
        # --- Stage 1: Transcription ---
        with tracer.start_as_current_span("transcription_stage") as span:
            # transcription logic...
            span.set_attribute("audio.size_bytes", len(audio_bytes) if audio_bytes else 0)
            # ...
            span.set_attribute("transcript.result", transcript)

        # --- Stage 2: RAG Retrieval & Rerank ---
        with tracer.start_as_current_span("rag_retrieval_stage") as span:
            # 2.1 Get Embedding
            with tracer.start_as_current_span("embedding_generation") as emb_span:
                vector = await self.openrouter.get_embedding(transcript)
                emb_span.set_attribute("embedding.model", "openai/text-embedding-3-small")
            
            # 2.2 Query Pinecone
            with tracer.start_as_current_span("pinecone_query") as pc_span:
                matches = await self.pinecone.query_vectors(vector, top_k=15)
                pc_span.set_attribute("pinecone.top_k", 15)
                pc_span.set_attribute("pinecone.matches_count", len(matches))
            
            # 2.3 Rerank via Cohere
            with tracer.start_as_current_span("cohere_rerank") as cohere_span:
                doc_texts = [m["text"] for m in matches if m["text"]]
                if doc_texts:
                    reranked = await self.cohere.rerank(transcript, doc_texts, top_n=3)
                    cohere_span.set_attribute("cohere.top_n", 3)
                    cohere_span.set_attribute("cohere.reranked_count", len(reranked))
                
        # --- Stage 3: LLM Extraction and Compliance Analysis ---
        with tracer.start_as_current_span("llm_extraction_stage") as span:
            span.set_attribute("llm.model", "deepseek/deepseek-v4-flash")
            span.set_attribute("llm.temperature", 0.0)
            
            context_snippets = [ref["snippet"] for ref in references]
            prompt = self._build_validation_prompt(transcript, context_snippets)
            span.set_attribute("llm.prompt", prompt)
            
            completion = await self.openrouter.generate_completion(
                model="deepseek/deepseek-v4-flash",
                prompt=prompt,
                temperature=0.0,
            )
            
            span.set_attribute("llm.completion", completion)
            
            # Record structured output parameters to spans
            try:
                data = json.loads(cleaned_completion)
                span.set_attribute("validation.status", data["validation"]["status"])
                span.set_attribute("validation.issues_count", len(data["validation"]["details"]["issues"]))
            except Exception:
                pass
```

---

## 4. Launching the Arize Phoenix Local Server

For local development or testing, launch the Phoenix UI server:

```bash
python -m phoenix.server.main serve
```

Go to **`http://localhost:6006`** in your browser to inspect:
- **Trace Spans**: Full tree tracing for HTTP requests, retrievals, and completions.
- **Latency Breakdown**: Pinpoint bottlenecks (e.g., Pinecone vs. OpenRouter).
- **Evaluations**: Analyze outputs, token usage, and hallucination scores.
