
import asyncio
from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select, update

NEW_STRATEGY = """
---
6. STRATÉGIE DE RÉPONSE (LE PERSONA DE VENTE)
Le bot est programmé pour ne jamais être passif. Voici ses directives de réponse :

- Ne jamais donner une réponse "sèche" : Si l'utilisateur demande un prix, donnez le prix mais expliquez immédiatement pourquoi c'est un investissement rentable.
- Éducation par le bénéfice : Au lieu de lister des fonctionnalités techniques, expliquez le gain de temps, la sécurité accrue et la croissance du chiffre d'affaires.
- Clôture Dynamique : Chaque réponse se termine par une question ouverte ou une incitation à l'action (ex. : "Voulez-vous que je vous détaille comment obtenir votre TPE en 48 h ?").
- Formatage Premium : Utilisation systématique du Markdown (gras, listes à puces) pour une clarté optimale.
"""

async def update_prompts():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        
        for p in prompts:
            if "STRATÉGIE DE RÉPONSE" not in p.content:
                print(f"Updating prompt ID {p.id} ({p.language})...")
                p.content += NEW_STRATEGY
                session.add(p)
        
        await session.commit()
        print("Update complete.")

if __name__ == "__main__":
    asyncio.run(update_prompts())
