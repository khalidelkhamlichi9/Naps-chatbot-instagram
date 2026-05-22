import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY", "")

async def main():
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        data = resp.json()
        
        free_models = []
        for model in data.get("data", []):
            if model.get("id", "").endswith(":free") or model.get("pricing", {}).get("prompt") == "0":
                free_models.append(model["id"])
                
        print("Active Free Models on OpenRouter:")
        for m in sorted(free_models):
            print(f"- {m}")

import asyncio
asyncio.run(main())
