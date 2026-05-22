import sys
import asyncio
sys.path.append('.')
from core.pipeline import _detect_intent

async def main():
    test_cases = [
        ("Vos services", "services"),
        ("Nous contacter", "contact"),
        ("Horaires", "horaires"),
        ("À propos de NAPS", "a_propos"),
        ("services", "services"),
        ("Quels sont vos horaires", "faq"),  # should go to FAQ/RAG because it's longer
        ("chkon naps", "a_propos"),
        ("wa9t", "horaires"),
    ]
    for msg, expected in test_cases:
        intent = await _detect_intent(msg, "fr")
        print(f"Msg: '{msg}' -> Intent: '{intent}' (Expected: '{expected}')")

asyncio.run(main())
