import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.getcwd())

from cache.redis_client import get_redis, get_history

async def main():
    r = await get_redis()
    history = await get_history("ui-user", max_turns=10)
    print("--- HISTORY FOR ui-user ---")
    for idx, msg in enumerate(history):
        print(f"\nMessage {idx+1} ({msg['role']}):")
        print(msg['content'])
    print("---------------------------")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
