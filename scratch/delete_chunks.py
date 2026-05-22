import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath("."))

from sqlalchemy import select, delete
from database.engine import AsyncSessionLocal
from database.models import UploadedDocument, RagChunk

async def delete_file_chunks(filename):
    async with AsyncSessionLocal() as session:
        # Find the document
        stmt = select(UploadedDocument).where(UploadedDocument.filename == filename)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if doc:
            print(f"Found document: {doc.filename} (ID: {doc.id})")
            # Delete chunks
            chunk_stmt = delete(RagChunk).where(RagChunk.document_id == doc.id)
            chunk_result = await session.execute(chunk_stmt)
            print(f"Deleted {chunk_result.rowcount} chunks associated with document ID {doc.id}")
            
            # Delete document entry
            doc_stmt = delete(UploadedDocument).where(UploadedDocument.id == doc.id)
            await session.execute(doc_stmt)
            print(f"Deleted document entry for {filename}")
        else:
            print(f"Document {filename} not found in uploaded_documents table.")
            # Fallback: search by source in RagChunk
            chunk_stmt = delete(RagChunk).where(RagChunk.source == filename)
            chunk_result = await session.execute(chunk_stmt)
            print(f"Deleted {chunk_result.rowcount} chunks where source matches {filename}")
            
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    filename = "cahier_des_charges_chatbot_naps.pdf"
    asyncio.run(delete_file_chunks(filename))
