import asyncio
import httpx
from database.engine import init_db, get_session
from database.models import RagChunk
from rag.embedder import embed
from sqlalchemy import select

URLS = [
    "https://naps.ma/",
    "https://naps.ma/a-propos-de-nous/",
    "https://naps.ma/tpe/",
    "https://naps.ma/carte-naps/",
    "https://naps.ma/paiements-en-ligne/",
    "https://naps.ma/pack-family/",
]

async def populate():
    from rag.embedder import load_embedder
    load_embedder()
    await init_db()
    
    # Simple chunks based on the homepage content I just read
    # In a real scenario, we'd scrape each URL and chunk it.
    # For now, I'll add the core information to the DB manually to ensure quality.
    
    knowledge_base = [
        {
            "content": "NAPS est le 1er opérateur financier indépendant au Maroc, spécialiste des moyens et des services de paiement électronique sécurisé. NAPS est agréé par Bank Al-Maghrib.",
            "category": "general"
        },
        {
            "content": "NAPS propose des solutions pour les particuliers : Compte de paiement, cartes prépayées (Carte NAPS) et le pack Naps Family.",
            "category": "particuliers"
        },
        {
            "content": "Pour les commerçants, NAPS offre des terminaux de paiement électronique (TPE) et des solutions de paiement en ligne (e-commerce).",
            "category": "commerçants"
        },
        {
            "content": "Les entreprises et institutionnels peuvent bénéficier de solutions de gestion des frais professionnels, de cartes étudiant multiservices et de solutions de transport.",
            "category": "entreprises"
        },
        {
            "content": "Pourquoi choisir NAPS ? Contrat prêt en 24h, opérationnel en 48h, centre de relation client disponible 7j/7, tarification adaptée et programme de fidélité.",
            "category": "general"
        },
        {
            "content": "Le centre de relation client de NAPS est disponible au 05 22 91 74 74 ou par email à Info@Naps.ma.",
            "category": "support"
        },
        {
            "content": "La carte NAPS est une carte de paiement et de retrait prépayée, utilisable partout au Maroc et sur internet. Elle ne nécessite pas de compte bancaire classique.",
            "category": "carte"
        },
        {
            "content": "NAPS TPE : Une solution de terminal de paiement pour les commerçants permettant d'accepter toutes les cartes bancaires marocaines et internationales.",
            "category": "tpe"
        },
        {
            "content": "Paiement en ligne NAPS : Une plateforme sécurisée pour accepter les paiements sur votre site e-commerce avec une intégration simple et rapide.",
            "category": "ecommerce"
        }
    ]

    async for session in get_session():
        for item in knowledge_base:
            # Check if exists
            res = await session.execute(select(RagChunk).where(RagChunk.content == item["content"]))
            if res.scalar():
                continue
            
            chunk = RagChunk(
                content=item["content"],
                embedding=embed(item["content"]),
                category=item["category"],
                source="https://naps.ma/",
                language="fr"
            )
            session.add(chunk)
        await session.commit()
        print(f"Successfully added {len(knowledge_base)} chunks to the database.")
        break

if __name__ == "__main__":
    asyncio.run(populate())
