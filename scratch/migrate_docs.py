import asyncio
import aiosqlite

async def migrate():
    async with aiosqlite.connect("naps_chatbot.db") as db:
        # Add document_id to rag_chunks if not exists
        try:
            await db.execute("ALTER TABLE rag_chunks ADD COLUMN document_id INTEGER;")
            print("[OK] Added document_id to rag_chunks")
        except Exception as e:
            print(f"[*] document_id already exists or error: {e}")
            
        # Create uploaded_documents table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("[OK] Created uploaded_documents table")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(migrate())
