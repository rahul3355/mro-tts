import asyncio
import io
import os
import sys
import wave
import base64
import json

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.integrations.openrouter import OpenRouterClient
from app.integrations.cohere import CohereClient
from app.integrations.pinecone import PineconeClient
from app.services.stream_manager import SSEStreamManager
from app.pipelines.process_pipeline import RAGPipelineCoordinator


def generate_silence_wav() -> bytes:
    """Generates a 1-second valid WAV format byte array containing silence."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        # 16000 frames * 2 bytes/frame (16-bit) = 32000 bytes
        wav.writeframes(b"\x00" * 32000)
    return wav_io.getvalue()


async def listen_to_sse_events(connection_id: str, manager: SSEStreamManager) -> None:
    """Listens and logs SSE stream events in the background."""
    print(f"\n--- SSE Stream Listener Active (conn_id: {connection_id}) ---")
    try:
        async for event in manager.subscribe(connection_id):
            # Print cleanly formatted events
            lines = event.strip().split("\n")
            print("SSE Message received:")
            for line in lines:
                if line.startswith("data:"):
                    # Print json payload
                    try:
                        data = line.replace("data:", "").strip()
                        payload = json.loads(data)
                        if "audio_base64" in payload:
                            # Truncate base64 strings to keep log clean
                            payload["audio_base64"] = payload["audio_base64"][:30] + "... [TRUNCATED]"
                        print("  data:", payload)
                    except Exception:
                        print("  line:", line)
                else:
                    print("  line:", line)
    except Exception as e:
        print(f"SSE Listener encountered exception: {e}")
    print("--- SSE Stream Listener Inactive ---\n")


async def main() -> None:
    connection_id = "test-session-uuid-12345"
    audio_bytes = generate_silence_wav()

    # Setup async clients
    async with httpx.AsyncClient(
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=httpx.Timeout(45.0, read=90.0),
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://mro-tts.vercel.app",
            "X-Title": "mro-tts-copilot",
        },
    ) as http_client:
        # Instantiate clients
        openrouter = OpenRouterClient(http_client)
        cohere = CohereClient(http_client)
        pinecone = PineconeClient()
        stream_manager = SSEStreamManager()

        # Connect to DB session
        async with AsyncSessionLocal() as db_session:
            coordinator = RAGPipelineCoordinator(
                db=db_session,
                openrouter=openrouter,
                cohere=cohere,
                pinecone=pinecone,
                stream_manager=stream_manager,
            )

            # Start SSE background reader task
            sse_task = asyncio.create_task(listen_to_sse_events(connection_id, stream_manager))
            # Wait briefly to let queue instantiate
            await asyncio.sleep(0.5)

            print("\n1. Running STT endpoint check with generated WAV...")
            try:
                raw_transcript = await openrouter.transcribe_audio(audio_bytes)
                print(f"STT Output (Silence): '{raw_transcript}'")
            except Exception as e:
                print("STT Endpoint check failed:", e)

            print("\n2. Executing FULL validation pipeline with forced realistic transcript...")
            test_transcript = "Performed Class R structural bonding measurement on the ground stud. Measured resistance is 1.2 milliohms."
            print(f"Injecting mock transcript: '{test_transcript}'")

            from typing import Any

            # Since the pipeline execute method runs STT itself, let's temporarily mock transcribe_audio
            # to return our test_transcript instead of transcribing silence
            original_transcribe = openrouter.transcribe_audio

            async def mock_transcribe(*args: Any, **kwargs: Any) -> str:
                return test_transcript

            openrouter.transcribe_audio = mock_transcribe  # type: ignore[method-assign]

            try:
                await coordinator.execute(connection_id, audio_bytes)
                # Commit transactions
                await db_session.commit()
                print("\nSUCCESS: Full E2E pipeline run completed successfully!")
            except Exception as e:
                print("\nFAILURE: E2E pipeline check crashed:", e)
                import traceback

                traceback.print_exc()
            finally:
                # Restore original
                openrouter.transcribe_audio = original_transcribe  # type: ignore[method-assign]

            # Cancel SSE task after pipeline is complete
            await asyncio.sleep(2.0)
            sse_task.cancel()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
