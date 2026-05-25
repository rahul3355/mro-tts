import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("pinecone-client")


class PineconeClient:
    """Wrapper integration for accessing Pinecone vector database index asynchronously via HTTP REST API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(15.0, read=30.0))
        # Ensure host is correctly configured and stripped of trailing slashes
        self.host = settings.PINECONE_INDEX_HOST.rstrip("/")

    async def query_vectors(self, vector: list[float], top_k: int = 15) -> list[dict[str, Any]]:
        """Queries Pinecone index for top_k nearest neighbors matching target vector."""
        url = f"{self.host}/query"
        headers = {
            "Api-Key": settings.PINECONE_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"vector": vector, "topK": top_k, "includeMetadata": True}

        try:
            logger.info("Submitting query vector request to Pinecone index REST endpoint")
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            matches = result.get("matches", [])
            logger.info(f"Pinecone query success. Found {len(matches)} vector matches")

            formatted_matches = []
            for m in matches:
                metadata = m.get("metadata", {})
                formatted_matches.append(
                    {
                        "id": m["id"],
                        "score": m.get("score", 0.0),
                        "text": metadata.get("text", ""),
                        "doc_path": metadata.get("doc_path", "AMM_Reference.pdf"),
                    }
                )
            return formatted_matches

        except Exception as e:
            logger.error(f"Pinecone query vector transaction exception: {e}")
            raise
