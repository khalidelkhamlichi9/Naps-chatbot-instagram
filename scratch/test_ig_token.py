"""Vérifie le token Instagram et l'accès API (lancer: python scratch/test_ig_token.py)."""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
IG_ID = os.getenv("INSTAGRAM_PAGE_ID", "")


def main():
    if not TOKEN or TOKEN.startswith("your_"):
        print("ERREUR: INSTAGRAM_ACCESS_TOKEN manquant dans .env")
        sys.exit(1)

    base = (
        "https://graph.instagram.com/v21.0"
        if TOKEN.startswith(("IGA", "IG"))
        else "https://graph.facebook.com/v21.0"
    )
    headers = {"Authorization": f"Bearer {TOKEN}"}

    print(f"Base API: {base}")
    print(f"IG account ID (.env): {IG_ID}\n")

    with httpx.Client(timeout=20.0) as client:
        r = client.get(f"{base}/me", params={"fields": "id,username"}, headers=headers)
        print("GET /me:", r.status_code)
        print(r.text[:500])
        if r.status_code != 200:
            print("\n=> Token invalide ou expiré. Regénérez-le dans Meta (Generate token).")
            sys.exit(1)

        if IG_ID:
            r2 = client.get(f"{base}/{IG_ID}", params={"fields": "id,username"}, headers=headers)
            print(f"\nGET /{IG_ID}:", r2.status_code)
            print(r2.text[:500])


if __name__ == "__main__":
    main()
