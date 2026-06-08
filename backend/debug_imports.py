"""Debug script to find which import is hanging."""
import sys
import time

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

print("Step 1: importing config...", flush=True)
t = time.time()
from config import settings
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 2: importing database.db...", flush=True)
t = time.time()
from database.db import init_db, get_conn, _conninfo
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 3: importing utils.logger...", flush=True)
t = time.time()
from utils.logger import logger
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 4: importing utils.rate_limit...", flush=True)
t = time.time()
from utils.rate_limit import RateLimitMiddleware
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 5: importing api.chat...", flush=True)
t = time.time()
from api.chat import router as chat_router
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 6: importing api.upload...", flush=True)
t = time.time()
from api.upload import router as upload_router
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 7: importing api.analytics...", flush=True)
t = time.time()
from api.analytics import router as analytics_router
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("Step 8: importing api.health...", flush=True)
t = time.time()
from api.health import router as health_router
print(f"  OK ({time.time()-t:.1f}s)", flush=True)

print("\nAll imports successful!", flush=True)
