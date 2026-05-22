import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Add project root
sys.path.append(os.path.abspath("."))
from database.models import RagChunk

async def search_content():
    db_paths = ["./naps_chatbot.db", "./data/naps_chatbot.db"]
    search_text = "Il ne gère pas ses propres utilisateurs."
    
    for path in db_paths:
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path): continue
            
        print(f"--- Searching in {path} ---")
        url = f"sqlite+aiosqlite:///{full_path}"
        engine = create_async_engine(url)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            stmt = select(RagChunk).where(RagChunk.content.like(f"%{search_text}%"))
            results = (await session.execute(stmt)).scalars().all()
            print(f"Found {len(results)} chunks.")
            for r in results:
                print(f"ID: {r.id}, Source: '{r.source}', Content: {r.content[:50]}...")
                
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(search_content())
