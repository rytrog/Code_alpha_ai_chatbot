# Troubleshooting & Optimization Walkthrough: Resolving System Errors
**Target Project:** University AI Chatbot (FastAPI + psycopg3 + ChromaDB)

This guide provides a step-by-step walkthrough to resolve the common runtime errors, deprecation warnings, database issues, and connection bottlenecks found in your log files (`logs/error.log`).

---

## 🛠️ Step 1: Fix the Windows Event Loop & Deprecation Warnings

### The Error in Your Logs:
> `Database startup error: Psycopg cannot use the 'ProactorEventLoop' to run in async mode...`
> &
> `DeprecationWarning: 'asyncio.WindowsSelectorEventLoopPolicy' is deprecated...`

### Why it happens:
On Windows, Python uses `ProactorEventLoop` by default. However, `psycopg` (the database connector) cannot use it for async operations on Windows and requires the older `SelectorEventLoop`. Setting `WindowsSelectorEventLoopPolicy` manually works, but Python 3.12+ prints deprecation warnings.

### Step-by-Step Resolution:
To fix both the event loop error AND remove the deprecation warnings, update the main entry point to use Python's modern loop factory.

1. Open [app.py](file:///l:/university-ai%20final%20product/backend/app.py)
2. Locate the `if __name__ == "__main__":` block at the bottom of the file.
3. Change the execution block to supply a custom event loop factory rather than setting a global policy:

```python
if __name__ == "__main__":
    import uvicorn
    import selectors
    
    if _is_windows():
        # Clean way to set SelectorEventLoop without triggering deprecation warnings
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
        
        config = uvicorn.Config(
            app=app,
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            workers=1,
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())
    else:
        uvicorn.run(
            "app:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            workers=1,
        )
```

---

## 🛠️ Step 2: Fix Database Connection Issues (Network Refused)

### The Error in Your Logs:
> `Database startup error: Multiple exceptions: Connect call failed ('127.0.0.1', 5432)`  
> `Health - PostgreSQL: [WinError 1225] The remote computer refused the network connection`

### Why it happens:
FastAPI is trying to connect to PostgreSQL on port 5432, but the PostgreSQL database service is either:
1. Not running on your computer.
2. Running, but listening on a different port.
3. Blocked by a local firewall.

### Step-by-Step Resolution:
1. **Verify if PostgreSQL is running on Windows:**
   * Open the **Start Menu**, search for **Services**, and press Enter.
   * Scroll down to locate `postgresql-x64-XX` (where `XX` is your version number).
   * Check if the **Status** is *Running*. If not, right-click it and select **Start**.
2. **Verify using the command line:**
   * Open a PowerShell terminal and run:
     ```powershell
     Get-Service -Name postgresql*
     ```
   * If it is stopped, start it:
     ```powershell
     Start-Service -Name postgresql*
     ```
3. **Confirm the Database Port:**
   * Ensure PostgreSQL is indeed configured to listen on port `5432`. Check the `postgresql.conf` file (typically found in `C:\Program Files\PostgreSQL\xx\data\`).

---

## 🛠️ Step 3: Fix Password Authentication Failures

### The Error in Your Logs:
> `Database startup error: password authentication failed for user "postgres"`

### Why it happens:
The connection password specified in your backend configurations does not match the actual password of the `postgres` user inside your database.

### Step-by-Step Resolution:
1. Open your backend environment configuration file [backend/.env](file:///l:/university-ai%20final%20product/backend/.env)
2. Locate the `DATABASE_URL` variable. It will look like this:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/university_ai
   ```
3. Update the credentials using the format: `postgresql+psycopg://[username]:[password]@[host]:[port]/[database_name]`
   * Replace the second `postgres` with your actual local PostgreSQL password.

---

## 🛠️ Step 4: Fix Gemini API 503 Errors (High Demand / Rate Limits)

### The Error in Your Logs:
> `Gemini API error: 503 UNAVAILABLE. This model is currently experiencing high demand...`

### Why it happens:
When using the free tier of the Gemini API, Google heavily restricts usage rates. High traffic spikes from students will result in HTTP 503 (Unavailable) errors, causing the bot to fail.

### Step-by-Step Resolution:
To handle temporary API spikes robustly, implement a retry mechanism with **Exponential Backoff** when calling the Gemini SDK.

1. Open [services/gemini_service.py](file:///l:/university-ai%20final%20product/backend/services/gemini_service.py)
2. Modify the Gemini API call inside the `generate_answer` function to catch rate limit exceptions and retry:

```python
import time
from google.genai.errors import APIError  # or appropriate SDK exception class

async def generate_answer(question: str, context_chunks: list[dict]) -> dict:
    # ... existing guards ...
    
    max_retries = 3
    base_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=user_prompt,
            )
            answer_text = response.text.strip() if response.text else NO_ANSWER_MSG
            
            # ... process sources and return ...
            return {"answer": answer_text, "source": source_str}
            
        except APIError as e:
            if e.code in [429, 503] and attempt < max_retries - 1:
                sleep_time = base_delay * (2 ** attempt)
                logger.warning(f"Gemini API rate limit/busy (status {e.code}). Retrying in {sleep_time}s...")
                await asyncio.sleep(sleep_time)
                continue
            logger.error(f"Gemini API error: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
            
    return {
        "answer": "I apologize, but the AI service is currently busy. Please try again in a few moments.",
        "source": ""
    }
```

---

## 🛠️ Step 5: Implement Database Connection Pooling

### The Bottleneck:
Connecting and disconnecting on every FastAPI request.

### Step-by-Step Resolution:
1. Open [database/db.py](file:///l:/university-ai%20final%20product/backend/database/db.py)
2. Replace your manual connection dependencies with a global `ConnectionPool`:

```python
import psycopg
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from config import settings

_conninfo = _parse_db_url(settings.DATABASE_URL)

# Initialize a global connection pool (minimum 5, maximum 20 connections)
db_pool = AsyncConnectionPool(
    conninfo=_conninfo,
    min_size=5,
    max_size=20,
    open=False, # Open pool on startup lifespan
    kwargs={"row_factory": dict_row}
)

async def init_db():
    # ... your existing table creation ...
    # Open the pool
    await db_pool.open()
    
async def get_conn():
    """Yields a connection from the pool and returns it automatically."""
    async with db_pool.connection() as conn:
        yield conn
```

3. Update the `lifespan` event handler inside [app.py](file:///l:/university-ai%20final%20product/backend/app.py) to shut down the pool cleanly when the server stops:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and open database pool
    await init_db()
    
    yield
    
    # Clean up pool on shutdown
    await db_pool.close()
```
