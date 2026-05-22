import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.getcwd())

from database.engine import get_db, init_db
from database.models import SystemPrompt
from sqlalchemy import select

async def main():
    await init_db()
    async for session in get_db():
        stmt = select(SystemPrompt).where(SystemPrompt.is_active == True)
        result = await session.execute(stmt)
        prompt = result.scalars().first()
        if prompt:
            print("--- ACTIVE PROMPT IN DB ---")
            print(prompt.content[:500])
            print("---------------------------")
            print(f"Length: {len(prompt.content)}")
        else:
            print("No active prompt found in database!")
        break

if __name__ == "__main__":
    asyncio.run(main())
