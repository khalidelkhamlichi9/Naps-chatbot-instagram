import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.getcwd())

from database.engine import get_db, init_db
from rag.retriever import retrieve
from core.pipeline import build_context

async def main():
    await init_db()
    async for session in get_db():
        message = "bghit tpe l mahal dyali"
        chunks = await retrieve(message, session)
        print(f"Retrieved {len(chunks)} chunks:")
        for idx, chunk in enumerate(chunks):
            print(f"\nChunk {idx+1} (Score: {chunk[1]}):")
            print(chunk[0].content[:200])
        
        context = build_context(chunks)
        print("\n--- BUILT CONTEXT ---")
        print(context[:500])
        break

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
