import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath("."))

from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import SystemPrompt

async def export_prompt():
    async with AsyncSessionLocal() as session:
        stmt = select(SystemPrompt).where(SystemPrompt.is_active == True).order_by(SystemPrompt.id.desc())
        result = await session.execute(stmt)
        prompt = result.scalar_one_or_none()
        
        if prompt:
            with open("active_prompt.txt", "w", encoding="utf-8") as f:
                f.write(prompt.content)
            print("Active prompt exported to active_prompt.txt")
        else:
            print("No active system prompt found.")

if __name__ == "__main__":
    asyncio.run(export_prompt())
