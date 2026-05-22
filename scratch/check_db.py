import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath("."))

from sqlalchemy import select, func
from database.engine import AsyncSessionLocal
from database.models import RagChunk

async def check_chunks():
    async with AsyncSessionLocal() as session:
        filename = "cahier_des_charges_chatbot_naps.pdf"
        
        # Count total chunks
        total = await session.scalar(select(func.count(RagChunk.id)))
        print(f"Total chunks in DB: {total}")
        
        # Count chunks for this file
        stmt = select(func.count(RagChunk.id)).where(RagChunk.source == filename)
        count = await session.scalar(stmt)
        print(f"Chunks for {filename}: {count}")
        
        # List first 5 sources to see if there's a typo
        stmt_sources = select(RagChunk.source).distinct().limit(20)
        sources = (await session.execute(stmt_sources)).scalars().all()
        print(f"Unique sources (first 20): {sources}")

if __name__ == "__main__":
    asyncio.run(check_chunks())
