import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, distinct

# Add project root
sys.path.append(os.path.abspath("."))
from database.models import RagChunk

async def inspect_sources():
    db_paths = ["./naps_chatbot.db", "./data/naps_chatbot.db"]
    
    for path in db_paths:
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path): continue
            
        print(f"--- Sources in {path} ---")
        url = f"sqlite+aiosqlite:///{full_path}"
        engine = create_async_engine(url)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            stmt = select(distinct(RagChunk.source))
            sources = (await session.execute(stmt)).scalars().all()
            for s in sources:
                print(f"'{s}' (len: {len(str(s))})")
                
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_sources())
