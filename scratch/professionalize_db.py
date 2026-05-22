import asyncio
import os
import sys

# Add project root to path so we can import modules
sys.path.append(r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot')

from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select

async def professionalize_prompts():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemPrompt).where(SystemPrompt.is_active == True))
        prompts = result.scalars().all()
        
        for p in prompts:
            print(f"Professionalizing prompt ID {p.id} ({p.language})...")
            
            # New Professional Salesman Strategy
            pro_strategy = (
                "\n\nDIRECTIVES DE VENTE PROFESSIONNELLE :\n"
                "- Tu es un expert commercial d'élite chez NAPS. Ton but est de conclure la vente.\n"
                "- Réponds TOUJOURS dans la langue de l'utilisateur (Darija, FR, EN, etc.).\n"
                "- Sois persuasif, direct, et professionnel.\n"
                "- RÈGLES D'OR : 2 phrases max, ZERO emojis, ZERO markdown, ZERO listes.\n"
                "- Termine par une question d'engagement pour clore l'affaire."
            )
            
            # Replace old human instructions if they exist, or just append
            if "DIRECTIVES HUMAINES CRITIQUES" in p.content:
                p.content = p.content.replace("DIRECTIVES HUMAINES CRITIQUES", "DIRECTIVES DE VENTE PROFESSIONNELLE")
            elif "DIRECTIVES DE VENTE PROFESSIONNELLE" not in p.content:
                p.content += pro_strategy
            
            p.content = p.content.strip()
            session.add(p)
        
        await session.commit()
        print("Database prompts professionalized.")

if __name__ == "__main__":
    asyncio.run(professionalize_prompts())
