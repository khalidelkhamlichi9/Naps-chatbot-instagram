import asyncio
import os
import sys

# Add project root to path
sys.path.append(r'c:\Users\lenovo\Downloads\naps-chatbot-v2 (1)\naps-chatbot')

from database.engine import AsyncSessionLocal
from database.models import SystemPrompt
from sqlalchemy import select, delete

CLEAN_PROMPTS = {
    "fr": (
        "Tu es Karim, expert commercial chez NAPS. Ton but est de conclure la vente. "
        "Réponds TOUJOURS en Français. Style direct, humain, sans chichis. "
        "MAX 2 PHRASES. ZERO EMOJI. ZERO BOLD. ZERO LISTE. Termine par une question de vente."
    ),
    "ar": (
        "أنت كريم، خبير مبيعات في NAPS. هدفك هو إتمام البيع. "
        "أجب دائماً بالعربية. أسلوب مباشر، إنساني، بدون تعقيد. "
        "جملتين كحد أقصى. لا إيموجي. لا تنسيق. لا قوائم. اختم بسؤال مبيعات."
    ),
    "darija": (
        "Nta Karim, expert commercial f NAPS. L-hadaf dyalk houwa tbi3. "
        "Jawb dima b Darija. Style direct, hdar bhal bnadm. "
        "2 JUMAL MAX. ZERO EMOJI. ZERO GRAS. ZERO LISTE. Sali b soual dyal l-bi3."
    ),
    "en": (
        "You are Karim, sales expert at NAPS. Your goal is to close the sale. "
        "Always reply in English. Direct, human style. "
        "MAX 2 SENTENCES. NO EMOJIS. NO BOLD. NO LISTS. End with a sales question."
    )
}

async def reset_prompts():
    async with AsyncSessionLocal() as session:
        # Clear all active prompts
        await session.execute(delete(SystemPrompt))
        
        # Add new clean prompts
        for lang, content in CLEAN_PROMPTS.items():
            p = SystemPrompt(language=lang, content=content, is_active=True)
            session.add(p)
            
        await session.commit()
        print("Database prompts have been COMPLETELY RESET to clean versions.")

if __name__ == "__main__":
    asyncio.run(reset_prompts())
