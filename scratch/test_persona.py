
import asyncio
import os
from database.engine import AsyncSessionLocal, init_db
from core.pipeline import process_message
from core.language import detect_language

async def test_persona():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Ensure DB is ready
    await init_db()
    
    test_messages = [
        ("Bonjour", "user_123"),
        ("C'est quoi le prix d'un TPE ?", "user_123"),
        ("Chhal taman dyal TPE?", "user_456"),
    ]
    
    async with AsyncSessionLocal() as session:
        for msg, uid in test_messages:
            lang = detect_language(msg)
            print(f"\n[USER] ({lang}): {msg}")
            try:
                response = await process_message(msg, uid, session)
                print(f"[BOT]: {response}")
            except Exception as e:
                print(f"[ERROR]: {e}")
            print("-" * 50)

if __name__ == "__main__":
    # We need the API KEY for this to work
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Warning: OPENROUTER_API_KEY not set. Test might fail if it hits LLM.")
    
    from llm.deepseek import init_http_client
    init_http_client()
    
    asyncio.run(test_persona())
