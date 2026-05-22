import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Add project root
sys.path.append(os.path.abspath("."))
from database.models import RagChunk

async def dump_all_chunks():
    db_paths = ["./naps_chatbot.db", "./data/naps_chatbot.db"]
    
    with open("all_chunks_dump.txt", "w", encoding="utf-8") as f:
        for path in db_paths:
            full_path = os.path.abspath(path)
            if not os.path.exists(full_path): continue
                
            f.write(f"--- DATABASE: {path} ---\n")
            url = f"sqlite+aiosqlite:///{full_path}"
            engine = create_async_engine(url)
            AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            
            async with AsyncSessionLocal() as session:
                stmt = select(RagChunk)
                results = (await session.execute(stmt)).scalars().all()
                f.write(f"Total chunks: {len(results)}\n")
                for r in results:
                    f.write(f"ID: {r.id} | Source: '{r.source}' | Category: '{r.category}' | Content: {r.content[:50]}...\n")
                    
            await engine.dispose()
            f.write("\n")

if __name__ == "__main__":
    asyncio.run(dump_all_chunks())
