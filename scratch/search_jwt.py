import sqlite3
import os

def search_jwt(root_dir):
    for root, dirs, files in os.walk(root_dir):
        if 'venv' in root or '.git' in root or '__pycache__' in root: continue
        for file in files:
            if file.endswith('.db'):
                db_path = os.path.join(root, file)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_chunks';")
                    if cursor.fetchone():
                        cursor.execute("SELECT id, source, content FROM rag_chunks WHERE content LIKE '%JWT%';")
                        rows = cursor.fetchall()
                        if rows:
                            print(f"--- Found {len(rows)} JWT chunks in {db_path} ---")
                            for r in rows[:5]:
                                print(f"ID: {r[0]} | Source: '{r[1]}' | Content: {r[2][:50]}...")
                    conn.close()
                except Exception: pass

if __name__ == "__main__":
    search_jwt(".")
    search_jwt("..")
