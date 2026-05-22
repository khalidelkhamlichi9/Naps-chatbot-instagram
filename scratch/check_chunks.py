import asyncio
from database.engine import init_db, get_session
from database.models import RagChunk
from sqlalchemy import select, func

async def main():
    await init_db()
    async for session in get_session():
        count = await session.scalar(select(func.count()).select_from(RagChunk))
        print(f"Chunks count: {count}")
        break

if __name__ == "__main__":
    asyncio.run(main())
