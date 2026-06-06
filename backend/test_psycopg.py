"""Quick test: does psycopg async work on Python 3.14?"""
import asyncio
import psycopg

async def test():
    print("Connecting...", flush=True)
    conn = await psycopg.AsyncConnection.connect(
        host="localhost",
        dbname="university_ai",
        user="postgres",
        password="admin@123",
    )
    cur = conn.cursor()
    await cur.execute("SELECT 1")
    row = await cur.fetchone()
    print(f"DB OK: {row}", flush=True)
    await cur.close()
    await conn.close()

asyncio.run(test())
