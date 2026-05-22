import asyncio
import aiosqlite

async def migrate():
    async with aiosqlite.connect("naps_chatbot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url VARCHAR(500) NOT NULL UNIQUE,
                name VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                last_scrape TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("[OK] Created knowledge_sources table")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(migrate())
