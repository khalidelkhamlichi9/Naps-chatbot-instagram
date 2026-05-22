import asyncio
import os
import sys

# Add project root to path
sys.path.append(r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot')

from database.engine import AsyncSessionLocal
from database.models import RagChunk
from sqlalchemy import select

async def check_chunks():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(RagChunk).limit(20))
        chunks = result.scalars().all()
        for c in chunks:
            print(f"ID: {c.id}, Category: {c.category}, Content: {c.content[:100]}...")

if __name__ == "__main__":
    asyncio.run(check_chunks())
