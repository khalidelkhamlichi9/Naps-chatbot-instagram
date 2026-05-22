import sqlite3
import os

def clean_all_dbs(root_dir):
    for root, dirs, files in os.walk(root_dir):
        # Skip venv and .git
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.db'):
                db_path = os.path.join(root, file)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Check if rag_chunks exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_chunks';")
                    if cursor.fetchone():
                        print(f"--- Cleaning table rag_chunks in {db_path} ---")
                        
                        # Count before
                        cursor.execute("SELECT COUNT(*) FROM rag_chunks WHERE source LIKE '%cahier_des_charges_chatbot_naps.pdf%';")
                        count = cursor.fetchone()[0]
                        
                        snippet = "Authentification Le backend NAPS"
                        cursor.execute("SELECT COUNT(*) FROM rag_chunks WHERE content LIKE ?", (f"%{snippet}%",))
                        count_snippet = cursor.fetchone()[0]
                        
                        if count > 0 or count_snippet > 0:
                            print(f"Found {count} rows by source and {count_snippet} by content.")
                            cursor.execute("DELETE FROM rag_chunks WHERE source LIKE '%cahier_des_charges_chatbot_naps.pdf%';")
                            cursor.execute("DELETE FROM rag_chunks WHERE content LIKE ?", (f"%{snippet}%",))
                            conn.commit()
                            print(f"Deleted rows in {db_path}.")
                        else:
                            print(f"No matching rows in {db_path}.")
                    conn.close()
                except Exception as e:
                    print(f"Could not process {db_path}: {e}")

if __name__ == "__main__":
    # Clean the current workspace and one level up
    clean_all_dbs(".")
    clean_all_dbs("..")
