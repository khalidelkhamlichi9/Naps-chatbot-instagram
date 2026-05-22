import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

# Determine DB path
db_url = os.getenv("DATABASE_URL", "")
if "sqlite+aiosqlite:///" in db_url:
    db_path = db_url.split("sqlite+aiosqlite:///")[1]
    # Handle absolute paths vs relative paths correctly
    if db_path.startswith("./"):
        db_path = db_path[2:]
else:
    db_path = "data/naps_chatbot.db"

print(f"Connecting to database: {db_path}")

sql_file = "scratch/04_SQL_Migration_Prompt.sql"

try:
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_script = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(sql_script)
    conn.commit()
    
    # Verify
    cursor.execute("SELECT LENGTH(content) FROM system_prompts WHERE is_active = 1")
    length = cursor.fetchone()
    if length:
        print(f"Migration SUCCESS! Active prompt length: {length[0]} characters.")
    else:
        print("Migration failed: no active prompt found.")
    
    conn.close()
except Exception as e:
    print(f"Error executing SQL: {e}")
