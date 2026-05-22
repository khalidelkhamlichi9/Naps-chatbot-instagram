import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY", "")

prompt = """
Tu es Yasmine, conseillère commerciale de NAPS.
### CRITICAL SYSTEM OVERRIDES
1. LANGUE : Réponds en Darija Marocain avec des lettres latines (Arabizi).
2. CONCISION : Réponds en 1 seule phrase courte (max 15 mots).
3. RÈGLE D'OR : Ne donne jamais de prix. Demande plutôt le type d'activité commerciale.

Utilisateur : salam bghit tpe, chhal taman dyalo f chhar ?
Yasmine :
"""

async def main():
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemma-4-31b-it:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 150
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print("SUCCESS:", data["choices"][0]["message"]["content"])
            else:
                print("FAILED:", resp.status_code, resp.text)
        except Exception as e:
            print("ERROR:", e)

import asyncio
asyncio.run(main())
