
import asyncio
from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select

NEW_STRATEGY_FINAL = """
---
Votre but est de convaincre l'utilisateur. Soyez proactif, transformez chaque info technique en bénéfice business (gain de temps, sécurité, croissance). Ne donnez jamais de prix 'sec'. Terminez toujours par une question pour engager. Utilisez le Markdown.
"""

async def update_prompts_final():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        
        for p in prompts:
            if "---" in p.content:
                p.content = p.content.split("---")[0]
            
            print(f"Updating prompt ID {p.id} ({p.language})...")
            p.content += NEW_STRATEGY_FINAL
            session.add(p)
        
        await session.commit()
        print("Update complete.")

if __name__ == "__main__":
    asyncio.run(update_prompts_final())
