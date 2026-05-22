import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "")
if "sqlite+aiosqlite:///" in db_url:
    db_path = db_url.split("sqlite+aiosqlite:///")[1]
    if db_path.startswith("./"):
        db_path = db_path[2:]
else:
    db_path = "data/naps_chatbot.db"

print(f"Connecting to database for rollback: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all prompts
    cursor.execute("SELECT id, is_active FROM system_prompts ORDER BY id DESC")
    prompts = cursor.fetchall()
    
    if len(prompts) >= 2:
        new_prompt_id = prompts[0][0]
        old_prompt_id = prompts[1][0]
        
        # Deactivate new, activate old
        cursor.execute("UPDATE system_prompts SET is_active = 0")
        cursor.execute("UPDATE system_prompts SET is_active = 1 WHERE id = ?", (old_prompt_id,))
        conn.commit()
        
        print(f"Rollback SUCCESS! Prompt {old_prompt_id} is now active (Prompt {new_prompt_id} deactivated).")
    else:
        print("Not enough prompts to rollback.")
        
    conn.close()
except Exception as e:
    print(f"Error rolling back DB: {e}")
