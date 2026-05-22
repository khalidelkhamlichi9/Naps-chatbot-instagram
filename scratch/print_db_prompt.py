import asyncio
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

from database.engine import AsyncSessionLocal, init_db
from core.pipeline import _get_active_system_prompt

async def main():
    await init_db()
    async with AsyncSessionLocal() as session:
        prompt = await _get_active_system_prompt(session)
        with open("scratch/active_prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)
        print("Prompt written to scratch/active_prompt.txt successfully")

if __name__ == "__main__":
    asyncio.run(main())
