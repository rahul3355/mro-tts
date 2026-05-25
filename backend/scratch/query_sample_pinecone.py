import asyncio
import sys
import os
import httpx

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings

async def main():
    host = "https://mro-tts-o133fy5.svc.aped-4627-b74a.pinecone.io"
    url = f"{host}/query"
    headers = {
        "Api-Key": settings.PINECONE_API_KEY,
        "Content-Type": "application/json",
    }
    
    # 512 dimensions
    dummy_vector = [0.1] * 512
    payload = {
        "vector": dummy_vector,
        "topK": 5,
        "includeMetadata": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res = response.json()
            print("Matches:")
            for m in res.get("matches", []):
                print(f"ID: {m['id']}")
                print(f"Score: {m['score']}")
                print(f"Doc Path: {m.get('metadata', {}).get('doc_path')}")
                print(f"Text preview: {m.get('metadata', {}).get('text')[:200]}")
                print("-" * 50)
        except Exception as e:
            print("Error querying Pinecone:", e)

if __name__ == "__main__":
    asyncio.run(main())
