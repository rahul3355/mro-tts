import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("cohere-client")


class CohereClient:
    """Wrapper integration for accessing Cohere Rerank models via OpenRouter API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(30.0, read=60.0),
            headers={
                "HTTP-Referer": "https://mro-tts.vercel.app",
                "X-Title": "mro-tts-copilot",
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            },
        )

    async def rerank(self, query: str, documents: list[str], top_n: int = 3) -> list[dict[str, Any]]:
        """Reranks document texts relative to search query using cohere/rerank-4-fast."""
        if not documents:
            return []

        url = "/rerank"
        payload = {
            "model": "cohere/rerank-4-fast",
            "query": query,
            "documents": documents,
            "top_n": top_n,
        }

        try:
            logger.info("Submitting Rerank request to OpenRouter Cohere endpoint")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            raw_results = result.get("results", [])
            ranked_docs = []

            for item in raw_results:
                index = item["index"]
                score = item["relevance_score"]
                ranked_docs.append({"index": index, "score": score, "text": documents[index]})

            logger.info(f"Rerank complete. Returned {len(ranked_docs)} sorted documents")
            return ranked_docs

        except Exception as e:
            logger.error(f"OpenRouter Cohere Rerank exception: {e}")
            raise
