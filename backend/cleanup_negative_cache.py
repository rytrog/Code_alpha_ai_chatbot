"""Clean stale negative answers from the answer_cache table."""
import psycopg
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import _conninfo

conn = psycopg.connect(_conninfo)
cur = conn.cursor()
cur.execute("""
    DELETE FROM answer_cache 
    WHERE answer ILIKE '%not available%' 
       OR answer ILIKE '%could not generate%' 
       OR answer ILIKE '%try again later%' 
       OR answer ILIKE '%cannot find%' 
       OR answer ILIKE '%not found in%'
       OR answer ILIKE '%i don''t have%'
       OR answer ILIKE '%unable to%'
""")
deleted = cur.rowcount
conn.commit()
conn.close()
print(f"Cleaned {deleted} stale negative cache entries from answer_cache table.")
