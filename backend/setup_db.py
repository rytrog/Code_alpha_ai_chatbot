"""
Setup script — creates the 'university_ai' database in PostgreSQL.
Run this ONCE before starting the app:
    python setup_db.py

It uses psycopg (sync driver) to connect to the default 'postgres'
database and issue CREATE DATABASE.
"""
import sys

# ── Read password from .env file ──
def _read_password():
    """Read the PostgreSQL password from the DATABASE_URL in .env."""
    from pathlib import Path
    from urllib.parse import unquote
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("ERROR: .env file not found. Copy .env.example to .env first.")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                # Format: postgresql+asyncpg://user:password@host:port/dbname
                url = line.split("=", 1)[1]
                # Extract password between first : and last @
                after_scheme = url.split("://", 1)[1]  # user:pass@host:port/db
                # Split from the RIGHT on @ to handle @ in passwords
                at_idx = after_scheme.rfind("@")
                user_pass = after_scheme[:at_idx]  # user:pass (may contain @)
                parts = user_pass.split(":", 1)
                password = unquote(parts[1]) if len(parts) > 1 else ""
                return parts[0], password
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)


def main():
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed. Install it with:")
        print("  pip install psycopg[binary]")
        sys.exit(1)

    user, password = _read_password()
    db_name = "university_ai"

    print(f"Connecting to PostgreSQL as '{user}'...")

    try:
        # Connect to default 'postgres' database with autocommit
        # (CREATE DATABASE cannot run inside a transaction)
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            user=user,
            password=password,
            dbname="postgres",
            autocommit=True,
        )

        cursor = conn.cursor()

        # Check if database already exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,),
        )
        exists = cursor.fetchone()

        if exists:
            print(f"Database '{db_name}' already exists. [OK]")
        else:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully! [OK]")

        cursor.close()
        conn.close()
        print("\nSetup complete. You can now run the app:")
        print("  python app.py")

    except Exception as e:
        print(f"\nERROR: Could not connect to PostgreSQL: {e}")
        print("\nPlease make sure:")
        print("  1. PostgreSQL is running")
        print("  2. The password in .env is correct")
        print("  3. The user 'postgres' exists")
        sys.exit(1)


if __name__ == "__main__":
    main()
