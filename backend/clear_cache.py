import asyncio
import sys
from database import db

async def clear():
    try:
        await db.init_pool()
        async with db.db_pool.connection() as conn:
            await conn.execute("TRUNCATE TABLE answer_cache")
            await conn.commit()
        print("Answer cache successfully truncated.")
        await db.close_pool()
    except Exception as e:
        print(f"Error clearing cache: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(clear())
