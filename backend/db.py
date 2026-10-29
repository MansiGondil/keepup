"""Step 2b: connect to the local Postgres database.

Run from the backend folder:  python db.py
It creates the articles table (if missing) and prints its columns and row count.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# The folder this file lives in (backend/), so paths work from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent

# Read POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB from backend/.env.
load_dotenv(BACKEND_DIR / ".env")

DB_HOST = "127.0.0.1"
DB_PORT = 5432


def get_connection():
    """Open and return a new connection to the Keepup database."""
    # Pass each setting separately, so there is never a full connection
    # string (with the password inside) that could get printed by mistake.
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def run_sql_file(path):
    """Run every SQL statement in a .sql file and save the changes."""
    sql = Path(path).read_text(encoding="utf-8")
    # "with" closes the connection when done and commits if nothing failed.
    with get_connection() as conn:
        conn.execute(sql)


def main():
    sql_file = BACKEND_DIR / "sql" / "001_create_articles.sql"
    run_sql_file(sql_file)
    print(f"Applied {sql_file.name}")

    with get_connection() as conn:
        # Ask Postgres which columns the articles table has, in order.
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'articles' ORDER BY ordinal_position"
        ).fetchall()
        columns = [row[0] for row in rows]

        # Count how many articles are stored (0 for now).
        count = conn.execute("SELECT count(*) FROM articles").fetchone()[0]

    print(f"Connected to database '{os.environ['POSTGRES_DB']}' as '{os.environ['POSTGRES_USER']}'")
    print("articles columns:", ", ".join(columns))
    print("articles rows:", count)


if __name__ == "__main__":
    main()
