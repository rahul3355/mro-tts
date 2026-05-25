import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace

from app.core.models import MaintenanceRecord
from app.integrations.cohere import CohereClient
from app.integrations.openrouter import OpenRouterClient
from app.integrations.pinecone import PineconeClient
from app.services.stream_manager import SSEStreamManager

logger = logging.getLogger("process-pipeline")

# Initialize OpenTelemetry Tracer
tracer = trace.get_tracer("mro-tts-pipeline")

# Load the validation prompt template from the dedicated prompts directory on startup
PROMPT_FILE_PATH = Path(__file__).parent / "prompts" / "validation_prompt.txt"
try:
    if not PROMPT_FILE_PATH.exists():
        raise FileNotFoundError(f"Validation prompt file not found at {PROMPT_FILE_PATH}")
    VALIDATION_PROMPT_TEMPLATE = PROMPT_FILE_PATH.read_text(encoding="utf-8")
    logger.info("Successfully loaded validation prompt template on startup")
except Exception as e:
    logger.critical(f"Failed to load validation prompt template on startup: {e}")
    raise


class RAGPipelineCoordinator:
    """Orchestrates the entire realtime audio verification pipeline asynchronously."""

    def __init__(
        self,
        db: AsyncSession | None,
        openrouter: OpenRouterClient,
        cohere: CohereClient,
        pinecone: PineconeClient,
        stream_manager: SSEStreamManager,
    ) -> None:
        self.db = db
        self.openrouter = openrouter
        self.cohere = cohere
        self.pinecone = pinecone
        self.stream_manager = stream_manager

    def _build_validation_prompt(self, transcript: str, contexts: list[str]) -> str:
        formatted_context = "\n---\n".join(contexts)
        return VALIDATION_PROMPT_TEMPLATE.replace("{{context}}", formatted_context).replace("{{transcript}}", transcript)

    async def execute(
        self,
        connection_id: str,
        audio_bytes: bytes | None = None,
        transcript: str | None = None,
    ) -> None:
        """Executes the pipeline stages sequentially, streaming updates to the client."""
        with tracer.start_as_current_span("mro_tts_pipeline_execute") as parent_span:
            parent_span.set_attribute("openinference.span.kind", "CHAIN")
            parent_span.set_attribute("connection_id", connection_id)
            if transcript:
                parent_span.set_attribute("input.value", transcript)
                parent_span.set_attribute("input.transcript", transcript)

            # Stage 1: Transcription
            if transcript is None:
                if audio_bytes is None:
                    logger.error("No audio bytes or transcript provided for processing")
                    await self.stream_manager.publish_event(
                        connection_id,
                        "error",
                        {
                            "stage": "stt",
                            "error_code": "STT_FAILURE",
                            "message": "Speech-to-text processing failed: No audio bytes provided.",
                        },
                    )
                    return
                try:
                    with tracer.start_as_current_span("transcription_stage") as stt_span:
                        stt_span.set_attribute("openinference.span.kind", "CHAIN")
                        await self.stream_manager.publish_event(connection_id, "transcribing", {"status": "started"})
                        transcript = await self.openrouter.transcribe_audio(audio_bytes)
                        stt_span.set_attribute("stt.transcript", transcript)
                        stt_span.set_attribute("output.value", transcript)
                        parent_span.set_attribute("input.value", transcript)
                        parent_span.set_attribute("input.transcript", transcript)
                        await self.stream_manager.publish_event(connection_id, "transcript", {"text": transcript})
                        await self.stream_manager.publish_event(connection_id, "transcribing", {"status": "completed"})
                except Exception as e:
                    logger.error(f"STT Stage failed: {e}")
                    await self.stream_manager.publish_event(
                        connection_id,
                        "error",
                        {
                            "stage": "stt",
                            "error_code": "STT_FAILURE",
                            "message": f"Speech-to-text processing failed: {str(e)}",
                        },
                    )
                    return
            else:
                # If transcript is provided directly (from manual text insertion/edit)
                # Publish transcript text to client so they receive the starting state
                await self.stream_manager.publish_event(connection_id, "transcript", {"text": transcript})

            # Stage 2: RAG Retrieval & Rerank
            try:
                with tracer.start_as_current_span("rag_retrieval_stage") as rag_span:
                    rag_span.set_attribute("openinference.span.kind", "CHAIN")
                    rag_span.set_attribute("input.value", transcript)
                    await self.stream_manager.publish_event(connection_id, "retrieving", {"status": "started"})

                    # 2.1 Get Embedding (dimensions = 512)
                    with tracer.start_as_current_span("embedding_generation") as emb_span:
                        emb_span.set_attribute("openinference.span.kind", "EMBEDDING")
                        emb_span.set_attribute("embedding.model_name", "openai/text-embedding-3-small")
                        emb_span.set_attribute("input.value", transcript)
                        vector = await self.openrouter.get_embedding(transcript)

                    # 2.2 Query Pinecone (Top 15 Chunks)
                    with tracer.start_as_current_span("pinecone_query") as pc_span:
                        pc_span.set_attribute("openinference.span.kind", "RETRIEVER")
                        pc_span.set_attribute("input.value", transcript)
                        pc_span.set_attribute("pinecone.top_k", 15)
                        matches = await self.pinecone.query_vectors(vector, top_k=15)
                        pc_span.set_attribute("pinecone.matches_count", len(matches))

                    # 2.3 Rerank via Cohere (Filter down to Top 3)
                    with tracer.start_as_current_span("cohere_rerank") as cohere_span:
                        cohere_span.set_attribute("openinference.span.kind", "RERANKER")
                        cohere_span.set_attribute("input.value", transcript)
                        doc_texts = [m["text"] for m in matches if m["text"]]

                        if doc_texts:
                            reranked = await self.cohere.rerank(transcript, doc_texts, top_n=3)
                            cohere_span.set_attribute("cohere.top_n", 3)
                            cohere_span.set_attribute("cohere.reranked_count", len(reranked))

                            # Re-map matched details containing doc_paths and IDs
                            references = []
                            for item in reranked:
                                # Find original match metadata matching this text block
                                orig = next((m for m in matches if m["text"] == item["text"]), None)
                                references.append(
                                    {
                                        "id": orig["id"] if orig else "unknown",
                                        "doc_path": orig["doc_path"] if orig else "AMM_Reference.pdf",
                                        "score": item["score"],
                                        "snippet": item["text"],
                                    }
                                )
                        else:
                            references = []

                    rag_span.set_attribute("output.value", json.dumps(references))
                    await self.stream_manager.publish_event(connection_id, "references", {"references": references})
                    await self.stream_manager.publish_event(connection_id, "retrieving", {"status": "completed"})
            except Exception as e:
                logger.error(f"RAG Stage failed: {e}")
                await self.stream_manager.publish_event(
                    connection_id,
                    "error",
                    {
                        "stage": "rag",
                        "error_code": "RAG_FAILURE",
                        "message": f"RAG context retrieval failed: {str(e)}",
                    },
                )
                return

            # Stage 3: Extraction and Compliance Analysis
            try:
                with tracer.start_as_current_span("llm_extraction_stage") as llm_span:
                    llm_span.set_attribute("openinference.span.kind", "LLM")
                    await self.stream_manager.publish_event(connection_id, "extracting", {"status": "started"})

                    context_snippets = [ref["snippet"] for ref in references]
                    prompt = self._build_validation_prompt(transcript, context_snippets)

                    llm_span.set_attribute("llm.model", "deepseek/deepseek-v4-flash")
                    llm_span.set_attribute("llm.model_name", "deepseek/deepseek-v4-flash")
                    llm_span.set_attribute("llm.provider", "deepseek")
                    llm_span.set_attribute("llm.temperature", 0.0)
                    llm_span.set_attribute("llm.prompt", prompt)
                    llm_span.set_attribute("input.value", prompt)

                    response_data = await self.openrouter.generate_completion(
                        model="deepseek/deepseek-v4-flash",
                        prompt=prompt,
                        temperature=0.0,
                        provider_routing={
                            "order": ["Alibaba"],
                            "sort": "throughput",
                            "allow_fallbacks": False,
                        },
                    )

                    completion = response_data["completion"]
                    usage = response_data.get("usage") or {}

                    llm_span.set_attribute("llm.completion", completion)
                    llm_span.set_attribute("output.value", completion)

                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                        llm_span.set_attribute("llm.token_count.prompt", prompt_tokens)
                        llm_span.set_attribute("llm.token_count.completion", completion_tokens)
                        llm_span.set_attribute("llm.token_count.total", total_tokens)

                    # Parse response block
                    cleaned_completion = completion.strip()
                    if cleaned_completion.startswith("```json"):
                        cleaned_completion = cleaned_completion[7:]
                    if cleaned_completion.endswith("```"):
                        cleaned_completion = cleaned_completion[:-3]
                    cleaned_completion = cleaned_completion.strip()
                    data = json.loads(cleaned_completion)
                    record_data = data["record"]
                    validation_data = data["validation"]

                    llm_span.set_attribute("validation.status", validation_data["status"])
                    llm_span.set_attribute("validation.issues_count", len(validation_data["details"]["issues"]))

                    await self.stream_manager.publish_event(connection_id, "extracted_record", {"record": record_data})
                    await self.stream_manager.publish_event(connection_id, "extracting", {"status": "completed"})
            except Exception as e:
                logger.error(f"Extraction Stage failed: {e}")
                await self.stream_manager.publish_event(
                    connection_id,
                    "error",
                    {
                        "stage": "extraction",
                        "error_code": "EXTRACTION_FAILURE",
                        "message": f"Structured records extraction failed: {str(e)}",
                    },
                )
                return

            # Stage 4: Safety Validation
            try:
                await self.stream_manager.publish_event(connection_id, "validating", {"status": "started"})

                status = validation_data["status"]
                issues = validation_data["details"]["issues"]
                parent_span.set_attribute("output.value", json.dumps(validation_data))

                await self.stream_manager.publish_event(
                    connection_id,
                    "validation_result",
                    {"status": status, "details": validation_data["details"]},
                )
                await self.stream_manager.publish_event(connection_id, "validating", {"status": "completed"})
            except Exception as e:
                logger.error(f"Validation Stage failed: {e}")
                await self.stream_manager.publish_event(
                    connection_id,
                    "error",
                    {
                        "stage": "validation",
                        "error_code": "VALIDATION_FAILURE",
                        "message": f"Compliance checks validation failed: {str(e)}",
                    },
                )
                return

            # Stage 5: warning voice alert (Bypassed in favor of client-side audio cues)
            pass

            # Stage 6: Persistent database write (Neon PG)
            try:
                with tracer.start_as_current_span("db_persistence_stage") as db_span:
                    db_span.set_attribute("openinference.span.kind", "CHAIN")
                    db_record = MaintenanceRecord(
                        transcript=transcript,
                        part_name=record_data.get("part_name") or "UNKNOWN",
                        part_number=record_data.get("part_number"),
                        ata_chapter=record_data.get("ata_chapter"),
                        action_performed=record_data.get("action_performed") or "UNKNOWN",
                        validation_status=status,
                        validation_issues=issues,
                        references_used=references,
                        compliance_parameters=record_data.get("compliance_parameters"),
                    )

                    if self.db is not None:
                        self.db.add(db_record)
                        await self.db.flush()
                        record_id = str(db_record.id)
                    else:
                        from app.core.database import AsyncSessionLocal
                        async with AsyncSessionLocal() as session:
                            session.add(db_record)
                            await session.commit()
                            record_id = str(db_record.id)

                    db_span.set_attribute("db.record_id", record_id)
                    logger.info(f"QA record persisted to PostgreSQL with ID: {record_id}")

                    # Emit complete flag containing references
                    await self.stream_manager.publish_event(
                        connection_id,
                        "complete",
                        {"record_id": record_id, "persisted_at": datetime.now(UTC).isoformat()},
                    )

            except Exception as e:
                logger.error(f"Database Persistence Stage failed: {e}")
                await self.stream_manager.publish_event(
                    connection_id,
                    "error",
                    {
                        "stage": "db",
                        "error_code": "PERSISTENCE_FAILURE",
                        "message": f"Failed to persist compliance QA log: {str(e)}",
                    },
                )
                return
