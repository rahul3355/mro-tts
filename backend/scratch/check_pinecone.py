import asyncio
import sys
import os
import httpx

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

async def main() -> None:
    host = "https://mro-tts-o133fy5.svc.aped-4627-b74a.pinecone.io"
    url = f"{host}/describe_index_stats"
    headers = {
        "Api-Key": settings.PINECONE_API_KEY,
        "Content-Type": "application/json",
    }
    
    print(f"Checking Pinecone index stats at: {host}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json={})
            response.raise_for_status()
            stats = response.json()
            print("\nPinecone Index Stats:")
            print("=" * 40)
            print(f"Total Vector Count: {stats.get('totalRecordCount', 0)}")
            print(f"Dimensions: {stats.get('dimension', 512)}")
            print(f"Namespaces: {stats.get('namespaces', {})}")
            print("=" * 40)
        except Exception as e:
            print("Failed to fetch Pinecone index stats:", e)

if __name__ == "__main__":
    asyncio.run(main())
