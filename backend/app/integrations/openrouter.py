import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("openrouter-client")


class OpenRouterClient:
    """Wrapper integration for accessing OpenRouter AI models asynchronously."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        # Use shared client or construct a local transient one
        self.client = client or httpx.AsyncClient(
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(30.0, read=60.0),
            headers={
                "HTTP-Referer": "https://mro-tts.vercel.app",
                "X-Title": "mro-tts-copilot",
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            },
        )

    async def transcribe_audio(self, audio_bytes: bytes, _filename: str = "audio.wav") -> str:
        """Sends audio bytes to openai/gpt-audio-mini for speech-to-text transcription."""
        import base64

        url = "/chat/completions"
        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "model": "openai/gpt-audio-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": base64_audio, "format": "wav"},
                        },
                        {
                            "type": "text",
                            "text": "Transcribe this audio exactly. Do not add any conversational remarks, introductions, or metadata. Output ONLY the raw transcribed text. If there is no speech or only silence, output an empty string.",
                        },
                    ],
                }
            ],
            "modalities": ["text"],
        }

        try:
            logger.info("Submitting STT transcription request to OpenRouter chat completions")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Expected string content in transcription response")
            transcript = content.strip()
            logger.info("STT transcription complete")
            return transcript
        except Exception as e:
            logger.error(f"OpenRouter STT transcription exception: {e}")
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """Generates 512-dimension vector embedding via openai/text-embedding-3-small."""
        url = "/embeddings"
        payload = {
            "model": "openai/text-embedding-3-small",
            "input": text,
            "dimensions": settings.PINECONE_DIMENSION,
        }

        try:
            logger.info("Generating text vector embedding from OpenRouter")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            embedding = result["data"][0]["embedding"]

            # Verify dimensions
            if len(embedding) != settings.PINECONE_DIMENSION:
                raise ValueError(f"Expected {settings.PINECONE_DIMENSION} dimensions, received {len(embedding)}")

            return embedding  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"OpenRouter Embedding generation exception: {e}")
            raise

    async def generate_completion(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        response_format: dict[str, Any] | None = None,
        provider_routing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Runs chat completion against reasoning or structured completion models.

        Args:
            model: OpenRouter model identifier.
            prompt: The user prompt to send.
            temperature: Sampling temperature (0.0 = deterministic).
            response_format: Optional structured output format dict.
            provider_routing: Optional OpenRouter provider preferences, e.g.
                {"order": ["Alibaba"], "sort": "throughput", "allow_fallbacks": False}
        """
        url = "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        if provider_routing:
            payload["provider"] = provider_routing

        try:
            logger.info(f"Submitting chat completion request to model: {model}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Expected string content in completion response")
            completion_text = content.strip()
            logger.info("Chat completion request complete")
            return {
                "completion": completion_text,
                "usage": result.get("usage", {})
            }
        except Exception as e:
            logger.error(f"OpenRouter completion request exception ({model}): {e}")
            raise

