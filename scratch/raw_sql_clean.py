import sqlite3
import os

def clean_db(db_path):
    if not os.path.exists(db_path):
        print(f"File {db_path} not found.")
        return
    
    print(f"--- Cleaning {db_path} ---")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    for (table_name,) in tables:
        # Check if table has a 'content' column
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [c[1] for c in cursor.fetchall()]
        
        if 'content' in columns or 'source' in columns:
            print(f"Checking table {table_name}...")
            # Count chunks for the PDF
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE source LIKE '%cahier_des_charges_chatbot_naps.pdf%';")
            count = cursor.fetchone()[0]
            print(f"Found {count} rows in {table_name}")
            
            if count > 0:
                cursor.execute(f"DELETE FROM {table_name} WHERE source LIKE '%cahier_des_charges_chatbot_naps.pdf%';")
                print(f"Deleted {cursor.rowcount} rows from {table_name}")
                
            # Search by content snippet from screenshot
            snippet = "Authentification Le backend NAPS"
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE content LIKE '%{snippet}%';")
            count_snippet = cursor.fetchone()[0]
            print(f"Found {count_snippet} rows with snippet in {table_name}")
            
            if count_snippet > 0:
                cursor.execute(f"DELETE FROM {table_name} WHERE content LIKE '%{snippet}%';")
                print(f"Deleted {cursor.rowcount} rows with snippet from {table_name}")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    clean_db("./naps_chatbot.db")
    clean_db("./data/naps_chatbot.db")
