
import asyncio
from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select

NEW_STRATEGY_CLEAN = """
---
MISSION : Vendre et convaincre.
RÈGLES D'OR :
- NE SOYEZ JAMAIS PASSIF : Prenez les devants, engagez l'utilisateur.
- JAMAIS DE PRIX SEC : Donnez le prix, mais justifiez-le immédiatement par un ROI ou un bénéfice business.
- FOCUS BÉNÉFICES : Parlez gain de temps, sécurité et croissance (pas de technique pure).
- CLÔTURE DYNAMIQUE : Finissez TOUJOURS par une question ou une incitation à l'action.
- FORMATAGE : Utilisez le Markdown (gras, listes) pour un aspect premium.
"""

async def update_prompts_v2():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        
        for p in prompts:
            # Remove the old strategy if present
            if "STRATÉGIE DE RÉPONSE" in p.content:
                p.content = p.content.split("---")[0]
            
            if "RÈGLES D'OR" not in p.content:
                print(f"Updating prompt ID {p.id} ({p.language})...")
                p.content += NEW_STRATEGY_CLEAN
                session.add(p)
        
        await session.commit()
        print("Update complete.")

if __name__ == "__main__":
    asyncio.run(update_prompts_v2())
