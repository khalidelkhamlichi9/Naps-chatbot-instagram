import asyncio
import os
import sys

# Add project root to path so we can import modules
sys.path.append(r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot')

from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select

async def clean_prompts():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        
        for p in prompts:
            print(f"Cleaning prompt ID {p.id} ({p.language})...")
            
            # Remove the "Formatage Premium" line if it exists
            content = p.content
            content = content.replace("Formatage Premium : Utilisation systématique du Markdown (gras, listes à puces) pour une clarté optimale.", "")
            content = content.replace("- JAMAIS d'emojis numerotes comme 1️⃣ 2️⃣ 3️⃣ ou 🔹 ✅ en debut de ligne.", "- ZERO emojis, ZERO symboles (pas de 👉, 🚀, ✅, 🔹, etc.).")
            
            # Add strict human instructions if not already there
            human_instr = (
                "\n\nDIRECTIVES HUMAINES CRITIQUES :\n"
                "- ZERO emojis, ZERO symboles, ZERO Markdown (pas de **, pas de *, pas de #).\n"
                "- ZERO listes ou tirets.\n"
                "- Réponses ultra-courtes (2 phrases max).\n"
                "- Pas de politesse robotique ('Voici', 'Bien sûr', 'En tant que')."
            )
            
            if "DIRECTIVES HUMAINES CRITIQUES" not in content:
                content += human_instr
            
            p.content = content.strip()
            session.add(p)
        
        await session.commit()
        print("Database prompts cleaned and humanized.")

if __name__ == "__main__":
    asyncio.run(clean_prompts())
