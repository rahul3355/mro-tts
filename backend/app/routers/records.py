import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.integrations.cohere import CohereClient
from app.integrations.openrouter import OpenRouterClient
from app.integrations.pinecone import PineconeClient
from app.pipelines.process_pipeline import RAGPipelineCoordinator
from app.services.stream_manager import SSEStreamManager, get_stream_manager

logger = logging.getLogger("records-router")
router: APIRouter = APIRouter()


# Dependency injection providers for client wrappers mapping to shared HTTP sessions
def get_openrouter_client(request: Request) -> OpenRouterClient:
    return OpenRouterClient(request.app.state.http_client)


def get_cohere_client(request: Request) -> CohereClient:
    return CohereClient(request.app.state.http_client)


def get_pinecone_client(request: Request) -> PineconeClient:
    return PineconeClient(request.app.state.http_client)


@router.get("/stream")
async def stream_events(
    connection_id: str, stream_manager: SSEStreamManager = Depends(get_stream_manager)
) -> StreamingResponse:
    """Subscribes client to Server-Sent Events (SSE) progress broadcast by connection ID."""
    logger.info(f"SSE Subscription request received for connection ID: {connection_id}")

    # Establish connection buffer queue
    await stream_manager.register_connection(connection_id)

    # Send welcome handshake event immediately
    await stream_manager.publish_event(
        connection_id, "connection_established", {"connection_id": connection_id, "heartbeat_interval_ms": 30000}
    )

    return StreamingResponse(
        stream_manager.subscribe(connection_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy caching/buffering
        },
    )


@router.get("/status")
async def get_connection_status(
    connection_id: str, stream_manager: SSEStreamManager = Depends(get_stream_manager)
) -> list[dict]:
    """Retrieves all accumulated events in history for the given connection ID (polling fallback)."""
    return await stream_manager.get_history(connection_id)


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
async def process_audio(
    connection_id: str = Form(...),
    audio: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    openrouter: OpenRouterClient = Depends(get_openrouter_client),
    cohere: CohereClient = Depends(get_cohere_client),
    pinecone: PineconeClient = Depends(get_pinecone_client),
    stream_manager: SSEStreamManager = Depends(get_stream_manager),
) -> dict[str, str]:
    """Receives voice record files, starting the RAG compliance evaluation pipeline asynchronously."""
    logger.info(f"Audio upload payload received for connection ID: {connection_id}")

    audio_bytes = await audio.read()

    # Build the pipeline runner coordinator
    coordinator = RAGPipelineCoordinator(
        db=None,
        openrouter=openrouter,
        cohere=cohere,
        pinecone=pinecone,
        stream_manager=stream_manager,
    )

    # Delegate execution to background worker pool
    background_tasks.add_task(coordinator.execute, connection_id, audio_bytes)

    return {"status": "processing", "connection_id": connection_id, "message": "Audio processing pipeline initiated"}


@router.post("/process-text", status_code=status.HTTP_202_ACCEPTED)
async def process_text(
    connection_id: str = Form(...),
    text: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    openrouter: OpenRouterClient = Depends(get_openrouter_client),
    cohere: CohereClient = Depends(get_cohere_client),
    pinecone: PineconeClient = Depends(get_pinecone_client),
    stream_manager: SSEStreamManager = Depends(get_stream_manager),
) -> dict[str, str]:
    """Receives edited text transcript, starting the RAG compliance evaluation pipeline asynchronously from Stage 2."""
    logger.info(f"Text process payload received for connection ID: {connection_id}")

    # Build the pipeline runner coordinator
    coordinator = RAGPipelineCoordinator(
        db=None,
        openrouter=openrouter,
        cohere=cohere,
        pinecone=pinecone,
        stream_manager=stream_manager,
    )

    # Delegate execution to background worker pool
    background_tasks.add_task(coordinator.execute, connection_id, audio_bytes=None, transcript=text)

    return {"status": "processing", "connection_id": connection_id, "message": "Text processing pipeline initiated"}


@router.get("/pdf/{filename}")
async def get_pdf(filename: str) -> FileResponse:
    """Serves a PDF manual inline in the browser."""
    # Try resolving relative to backend directory (works in container as /app/data, and locally)
    data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    filepath = os.path.join(data_dir, filename)

    # Fallback to project root level data directory (works in local dev)
    if not os.path.exists(filepath):
        alt_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
        filepath = os.path.join(alt_data_dir, filename)
        data_dir = alt_data_dir

    if not os.path.exists(filepath):
        logger.error(f"Requested PDF file not found: {filename} (searched in {data_dir})")
        raise HTTPException(status_code=404, detail="PDF manual not found")
        
    return FileResponse(
        filepath,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
