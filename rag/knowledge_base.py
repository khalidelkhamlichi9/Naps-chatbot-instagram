"""
NAPS Knowledge Base — seed data.
Run: python scripts/seed_kb.py
"""

NAPS_KNOWLEDGE: list[dict] = [

    # ── TPE ───────────────────────────────────────────────────────────────────
    {
        "category": "tpe",
        "content": (
            "Le TPE NAPS (Terminal de Paiement Électronique) permet aux commerçants "
            "d'accepter les paiements par carte bancaire. La mise en service se fait "
            "sous 48h après validation du dossier. NAPS propose des TPE fixes, mobiles "
            "et Android selon les besoins du commerçant."
        ),
    },
    {
        "category": "tpe",
        "content": (
            "Les frais du TPE NAPS comprennent une commission par transaction (variable "
            "selon le secteur) et une redevance mensuelle de location du terminal. "
            "Pour connaître les tarifs exacts, contactez le service commercial NAPS "
            "au +212 5XX-XXXXXX ou via naps.ma."
        ),
    },
    {
        "category": "tpe",
        "content": (
            "Le TPE NAPS offre des fonctionnalités avancées : portabilité (accepter "
            "les paiements partout), tableau de bord analytique en temps réel, "
            "rapports de ventes quotidiens, et support technique 24/7."
        ),
    },
    {
        "category": "tpe",
        "content": (
            "Pour souscrire à un TPE NAPS, il faut fournir : registre de commerce, "
            "pièce d'identité du gérant, RIB bancaire, et formulaire de demande. "
            "Le dossier peut être déposé en ligne sur naps.ma ou dans une agence partenaire."
        ),
    },

    # ── E-Commerce / Paiement en ligne ────────────────────────────────────────
    {
        "category": "ecommerce",
        "content": (
            "La solution e-commerce NAPS permet aux boutiques en ligne d'accepter "
            "les paiements par carte bancaire. Elle s'intègre facilement via une API "
            "REST ou des plugins pour WooCommerce, PrestaShop et Shopify."
        ),
    },
    {
        "category": "ecommerce",
        "content": (
            "Le paiement en ligne NAPS est sécurisé par le protocole 3D Secure. "
            "Les fonds sont virés sur le compte du marchand sous 24 à 48h ouvrables. "
            "Un tableau de bord permet de suivre toutes les transactions en temps réel."
        ),
    },
    {
        "category": "ecommerce",
        "content": (
            "Pour intégrer le paiement NAPS sur votre site, vous recevez : "
            "une clé API, une documentation technique complète, et un environnement "
            "de test (sandbox) pour valider l'intégration avant la mise en production."
        ),
    },

    # ── Carte Prépayée ────────────────────────────────────────────────────────
    {
        "category": "carte",
        "content": (
            "La carte prépayée NAPS est disponible pour tous les résidents marocains. "
            "Elle s'ouvre sans compte bancaire, avec une pièce d'identité uniquement. "
            "Plafond de rechargement : 20 000 MAD par mois."
        ),
    },
    {
        "category": "carte",
        "content": (
            "La carte NAPS se recharge via virement bancaire, dépôt en agence, "
            "ou via l'application mobile NAPS. Elle permet les achats en ligne, "
            "les paiements en magasin et les retraits aux DAB Maroc."
        ),
    },
    {
        "category": "carte",
        "content": (
            "Le programme de fidélité NAPS récompense chaque achat avec des points "
            "échangeables contre des réductions. Les porteurs de carte bénéficient "
            "aussi d'assurances et d'offres partenaires exclusives."
        ),
    },

    # ── Naps Family ───────────────────────────────────────────────────────────
    {
        "category": "famille",
        "content": (
            "Naps Family est un pack familial qui permet d'associer jusqu'à 4 cartes "
            "supplémentaires à un compte principal. Le titulaire peut fixer des plafonds "
            "individuels et suivre les dépenses de chaque membre en temps réel."
        ),
    },

    # ── Solutions Entreprises ─────────────────────────────────────────────────
    {
        "category": "entreprise",
        "content": (
            "NAPS propose des cartes de notes de frais pour les entreprises : "
            "chaque employé reçoit une carte prépayée rechargeable par le service "
            "comptabilité. Les dépenses sont catégorisées automatiquement et "
            "exportables en CSV/Excel pour la comptabilité."
        ),
    },
    {
        "category": "entreprise",
        "content": (
            "La carte étudiante NAPS est destinée aux universités et grandes écoles. "
            "Elle combine paiement du restaurant universitaire, accès aux services "
            "campus et porte-monnaie électronique rechargeable par les parents."
        ),
    },
    {
        "category": "entreprise",
        "content": (
            "La carte de transport NAPS est une carte NFC multiservices utilisable "
            "dans les transports publics (bus, tramway) et les parkings partenaires. "
            "Elle est disponible pour les collectivités et entreprises de transport."
        ),
    },

    # ── Support ───────────────────────────────────────────────────────────────
    {
        "category": "support",
        "content": (
            "Pour tout problème technique avec votre TPE ou carte NAPS, contactez "
            "le support disponible 24h/24 et 7j/7 : numéro sur naps.ma, "
            "ou via l'espace client en ligne. Un technicien peut intervenir sur site "
            "sous 4h en cas de panne critique."
        ),
    },
    {
        "category": "support",
        "content": (
            "En cas de carte bloquée ou de transaction refusée : vérifiez le solde, "
            "assurez-vous que le plafond n'est pas atteint, et contactez le support "
            "NAPS si le problème persiste. La carte peut être débloquée en ligne "
            "ou en appelant le service client."
        ),
    },

    # ── Souscription ─────────────────────────────────────────────────────────
    {
        "category": "souscription",
        "content": (
            "Le processus de souscription NAPS se fait en 3 étapes : "
            "1) Remplir le formulaire en ligne sur naps.ma, "
            "2) Soumettre les documents requis (scannés ou en agence), "
            "3) Validation sous 48h et mise en service. "
            "Un conseiller NAPS vous accompagne à chaque étape."
        ),
    },
]
