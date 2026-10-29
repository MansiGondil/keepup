"""Connect to the local Postgres database.

Run from the backend folder:  python db.py
It applies every file in sql/ (in name order) and prints each table's
columns and row count.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

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


TABLES = ["articles", "pipeline_runs"]


def main():
    # Apply 001_..., 002_..., and so on. Each file uses IF NOT EXISTS,
    # so running them again is safe.
    for sql_file in sorted((BACKEND_DIR / "sql").glob("*.sql")):
        run_sql_file(sql_file)
        print(f"Applied {sql_file.name}")

    print(f"Connected to database '{os.environ['POSTGRES_DB']}' as '{os.environ['POSTGRES_USER']}'")

    with get_connection() as conn:
        for table in TABLES:
            # Ask Postgres which columns the table has, in order.
            rows = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s ORDER BY ordinal_position",
                (table,),
            ).fetchall()
            columns = [row[0] for row in rows]

            # Count the rows. sql.Identifier safely quotes the table name.
            count_query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            count = conn.execute(count_query).fetchone()[0]

            print(f"{table} columns:", ", ".join(columns))
            print(f"{table} rows:", count)


if __name__ == "__main__":
    main()
