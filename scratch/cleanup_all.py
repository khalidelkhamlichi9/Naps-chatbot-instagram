import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func, delete

# Add project root
sys.path.append(os.path.abspath("."))
from database.models import RagChunk, UploadedDocument

async def cleanup_all_dbs():
    db_paths = ["./naps_chatbot.db", "./data/naps_chatbot.db"]
    filename = "cahier_des_charges_chatbot_naps.pdf"
    
    for path in db_paths:
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            print(f"Skipping {path} (not found)")
            continue
            
        print(f"--- Processing {path} ---")
        url = f"sqlite+aiosqlite:///{full_path}"
        engine = create_async_engine(url)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            # Check counts
            count = await session.scalar(select(func.count(RagChunk.id)).where(RagChunk.source == filename))
            print(f"Found {count} chunks for {filename}")
            
            if count > 0:
                # Delete chunks
                res = await session.execute(delete(RagChunk).where(RagChunk.source == filename))
                print(f"Deleted {res.rowcount} chunks.")
                
                # Delete document
                res_doc = await session.execute(delete(UploadedDocument).where(UploadedDocument.filename == filename))
                print(f"Deleted {res_doc.rowcount} document entries.")
                
                await session.commit()
            
            # Check other possible matches
            res_like = await session.execute(delete(RagChunk).where(RagChunk.source.like(f"%{filename}%")))
            if res_like.rowcount > 0:
                print(f"Deleted {res_like.rowcount} chunks with LIKE match.")
                await session.commit()
                
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_all_dbs())
