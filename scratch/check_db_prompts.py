
import asyncio
from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select

async def check_prompts():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        if not prompts:
            print("No active system prompts in database.")
        for p in prompts:
            print(f"ID: {p.id}, Lang: {p.language}, Active: {p.is_active}")
            print(f"Content: {p.content[:100]}...")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_prompts())
