import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath("."))

from sqlalchemy import delete
from database.engine import AsyncSessionLocal
from database.models import RagChunk, UploadedDocument

async def forceful_delete():
    async with AsyncSessionLocal() as session:
        filename = "cahier_des_charges_chatbot_naps.pdf"
        
        # 1. Delete by source string (most reliable for what's visible in UI)
        stmt1 = delete(RagChunk).where(RagChunk.source == filename)
        result1 = await session.execute(stmt1)
        print(f"Deleted {result1.rowcount} chunks using source column match.")

        # 2. Delete by partial match just in case
        stmt2 = delete(RagChunk).where(RagChunk.source.like(f"%{filename}%"))
        result2 = await session.execute(stmt2)
        print(f"Deleted {result2.rowcount} additional chunks using partial source match.")
        
        # 3. Clean up the document entry if it exists
        stmt3 = delete(UploadedDocument).where(UploadedDocument.filename == filename)
        result3 = await session.execute(stmt3)
        print(f"Deleted {result3.rowcount} document entries.")

        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(forceful_delete())
