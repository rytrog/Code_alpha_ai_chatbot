import sys
import os
import psycopg

# Parse DATABASE_URL from .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
db_url = None
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            db_url = line.split("=", 1)[1]

if not db_url:
    print("DATABASE_URL not found in .env")
    sys.exit(1)

# Convert url to conninfo
from urllib.parse import unquote, urlparse
clean_url = db_url.replace("+psycopg", "").replace("+asyncpg", "")
parsed = urlparse(clean_url)
password = unquote(parsed.password) if parsed.password else ""
host = parsed.hostname or "localhost"
port = parsed.port or 5432
dbname = parsed.path.lstrip("/") if parsed.path else ""
user = parsed.username or "postgres"
conninfo = f"host={host} port={port} dbname={dbname} user={user} password={password}"

try:
    conn = psycopg.connect(conninfo)
    cur = conn.cursor()
    
    # Update HOD of CSE row
    new_answer = (
        "Prof. Shree Nath Dwivedi is the Head of Department (HOD) for both "
        "Computer Science & Engineering (CSE) and Computer Science & Engineering (AI & ML) "
        "at AITD Kanpur. He is highly hardworking, a best faculty member, exceptionally "
        "supportive of students, and serves as the Project Head supervising innovative AI "
        "and computer science research at the institute."
    )
    
    cur.execute(
        "UPDATE faq SET answer = %s WHERE normalized_key = 'hod cse'",
        (new_answer,)
    )
    
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"Successfully updated HOD details in FAQ database (affected rows: {deleted}).")
except Exception as e:
    print(f"Error updating FAQ: {e}")
