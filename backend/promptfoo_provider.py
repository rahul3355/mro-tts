import asyncio
import os
import sys
import httpx

# Add the backend root directory to the python path
backend_dir = os.path.realpath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.integrations.openrouter import OpenRouterClient

def call_api(prompt, options, context):
    async def _call():
        # Instantiate HTTPX client matching main.py settings
        async with httpx.AsyncClient(
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(45.0, read=90.0),
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://mro-tts.vercel.app",
                "X-Title": "mro-tts-copilot-eval",
            },
        ) as http_client:
            client = OpenRouterClient(http_client)
            response_data = await client.generate_completion(
                model="deepseek/deepseek-v4-flash",
                prompt=prompt,
                temperature=0.0,
                provider_routing={
                    "order": ["Alibaba"],
                    "sort": "throughput",
                    "allow_fallbacks": True,
                },
            )
            return response_data["completion"]

    try:
        # Execute async method inside sync environment
        output = asyncio.run(_call())
        return {"output": output}
    except Exception as e:
        return {"error": str(e)}
