"""
Seed the NAPS knowledge base into SQLite.
Run once: python scripts/seed_kb.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database.engine import init_db, AsyncSessionLocal
from database.models import RagChunk
from rag.embedder import load_embedder, embed_batch
from rag.knowledge_base import NAPS_KNOWLEDGE
from sqlalchemy import select, delete


async def seed():
    print("⏳ Loading embedding model...")
    load_embedder()

    print("⏳ Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Clear existing chunks
        await session.execute(delete(RagChunk))
        await session.commit()
        print("🗑️  Cleared existing chunks")

        # Embed all content in batch
        texts = [item["content"] for item in NAPS_KNOWLEDGE]
        print(f"⏳ Embedding {len(texts)} chunks...")
        embeddings = embed_batch(texts)

        # Insert chunks
        chunks = []
        for item, emb in zip(NAPS_KNOWLEDGE, embeddings):
            chunks.append(RagChunk(
                content=item["content"],
                embedding=emb,
                category=item.get("category", "general"),
                source="naps_kb_v1",
                language="fr",
            ))

        session.add_all(chunks)
        await session.commit()

    print(f"[OK] Seeded {len(chunks)} chunks into the knowledge base.")


if __name__ == "__main__":
    asyncio.run(seed())
