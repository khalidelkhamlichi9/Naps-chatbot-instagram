import asyncio
from database.engine import init_db, get_session
from database.models import RagChunk
from rag.embedder import embed, load_embedder
from sqlalchemy import select

async def populate_detailed():
    load_embedder()
    await init_db()
    
    knowledge = [
        # --- TPE SECTION ---
        {
            "content": (
                "NAPS propose trois formules principales pour les TPE :\n"
                "1. Formule GO : Idéale pour un flux jusqu'à 20 000 Dhs/mois. Frais mensuels : 290 Dhs HT. Commission nationale : 0%. Commission internationale : 2.9%.\n"
                "2. Formule GO+ : Idéale pour un flux jusqu'à 40 000 Dhs/mois. Frais mensuels : 470 Dhs HT. Commission nationale : 0%. Commission internationale : 2.9%.\n"
                "3. Formule CONFORT : Idéale pour un flux jusqu'à 250 000 Dhs/mois. Frais mensuels : 0 Dhs. Commission nationale : 1.75%. Commission internationale : 3%.\n"
                "Le prix de vente unitaire du TPE est de 3 000 Dhs HT pour toutes les formules."
            ),
            "category": "tpe",
            "source": "https://naps.ma/tpe/"
        },
        {
            "content": (
                "Les avantages des TPE NAPS incluent : Mise en service sous 48h, suivi de l'activité en temps réel via des reportings intelligents, "
                "et un accompagnement PRO disponible 7j/7. NAPS propose aussi des services à valeur ajoutée comme la personnalisation du ticket avec votre logo, "
                "la gestion dématérialisée des pourboires, et le versement des fonds le jour même (Règlement Express)."
            ),
            "category": "tpe",
            "source": "https://naps.ma/tpe/"
        },
        {
            "content": (
                "Le paiement en plusieurs fois (N-fois) sur TPE NAPS permet aux clients de régler leurs achats en plusieurs échéances. "
                "La carte bancaire est débitée automatiquement aux dates fixées. NAPS propose aussi le paiement récurrent pour les abonnements."
            ),
            "category": "tpe",
            "source": "https://naps.ma/tpe/"
        },
        # --- CARTE SECTION ---
        {
            "content": (
                "La Carte NAPS est disponible au prix de 99 Dhs TTC. Elle est valable pendant 2 ans. "
                "Il n'y a aucun frais de souscription ni frais de gestion mensuels. "
                "La carte est sans compte bancaire, sans engagement et sans contact."
            ),
            "category": "carte",
            "source": "https://naps.ma/carte-naps/"
        },
        {
            "content": (
                "Les fonctionnalités de la Carte NAPS incluent : Retrait sur tous les GAB au Maroc, paiement sur tous les TPE et sites e-commerce, "
                "dotation e-commerce pour achats internationaux, et un RIB pour recevoir des virements. "
                "Le solde est instantanément plafonné à 5 000 Dhs (extensible à 20 000 Dhs avec justificatif d'adresse)."
            ),
            "category": "carte",
            "source": "https://naps.ma/carte-naps/"
        },
        {
            "content": (
                "Pour obtenir une Carte NAPS, il suffit de souscrire en ligne sur naps.ma, appeler le 05 22 91 74 74 pour une livraison à domicile, "
                "ou se rendre dans une agence NAPS avec une pièce d'identité et un numéro de téléphone mobile."
            ),
            "category": "carte",
            "source": "https://naps.ma/carte-naps/"
        },
        # --- GENERAL SECTION ---
        {
            "content": (
                "NAPS est le premier opérateur financier indépendant agréé par Bank Al-Maghrib au Maroc. "
                "Le service client est joignable au 05 22 91 74 74 ou par email à Info@Naps.ma."
            ),
            "category": "support",
            "source": "https://naps.ma/"
        }
    ]

    async for session in get_session():
        for item in knowledge:
            # Avoid duplicates
            exists = await session.execute(select(RagChunk).where(RagChunk.content == item["content"]))
            if exists.scalar():
                continue
                
            chunk = RagChunk(
                content=item["content"],
                embedding=embed(item["content"]),
                category=item["category"],
                source=item["source"],
                language="fr"
            )
            session.add(chunk)
        await session.commit()
        print(f"Successfully added {len(knowledge)} detailed chunks.")
        break

if __name__ == "__main__":
    asyncio.run(populate_detailed())
