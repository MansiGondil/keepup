"""Run the pipeline stages in order, each as its own process.

Run from the backend folder:
  python run_pipeline.py                 # all stages: ingest, embed, cluster, classify
  python run_pipeline.py ingest cluster  # only these, in this order
If a stage fails, the remaining stages are skipped and the exit code is 1.
Each execution is logged as one row in pipeline_executions.
"""

import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from db import get_connection

# The folder this file lives in (backend/), so it works from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent

# Stage name -> the script that does it. The order here is the default order.
STAGES = {
    "ingest": "ingest.py",
    "embed": "embed_articles.py",
    "cluster": "cluster_stories.py",
    "classify": "classify_stories.py",
}

# Keep in sync with LOOKBACK_DAYS in cluster_stories.py.
STORY_WINDOW_DAYS = 30
ERROR_MAX_CHARS = 500

START_SQL = "INSERT INTO pipeline_executions (started_at) VALUES (%s) RETURNING id"

FINISH_SQL = """
    UPDATE pipeline_executions
    SET finished_at = %(finished_at)s, ok = %(ok)s, total_seconds = %(total_seconds)s,
        stages = %(stages)s, funnel = %(funnel)s, error_message = %(error_message)s
    WHERE id = %(id)s
"""

# Used when the start row couldn't be written (e.g. the database was down then).
INSERT_FULL_SQL = """
    INSERT INTO pipeline_executions (started_at, finished_at, ok, total_seconds,
                                     stages, funnel, error_message)
    VALUES (%(started_at)s, %(finished_at)s, %(ok)s, %(total_seconds)s,
            %(stages)s, %(funnel)s, %(error_message)s)
"""

STORY_COUNTS_SQL = """
    SELECT count(*), count(*) FILTER (WHERE article_count >= 2)
    FROM stories
    WHERE last_published_at >= now() - make_interval(days => %s)
"""


def safe_text(text):
    """Hide passwords and connection strings, then cut to ERROR_MAX_CHARS."""
    password = os.environ.get("POSTGRES_PASSWORD")
    if password:
        text = text.replace(password, "***")
    text = re.sub(r"postgres(ql)?://\S+", "postgresql://***", text)  # URL form
    text = re.sub(r"password=\S+", "password=***", text)              # key=value form
    return text[:ERROR_MAX_CHARS]


def run_stage(name):
    """Run one stage's script. Return (ok, seconds, last error line)."""
    print(f"===== {name} ({STAGES[name]}) =====", flush=True)
    start = time.monotonic()
    # sys.executable is the Python running this file (the venv's Python).
    # A separate process means a crash there can't break this script.
    # Normal output goes straight to the screen. Error output (stderr) is
    # copied to the screen AND kept, so we can log its last line.
    process = subprocess.Popen([sys.executable, STAGES[name]], cwd=BACKEND_DIR,
                               stderr=subprocess.PIPE)
    captured = bytearray()
    while chunk := process.stderr.read1(4096):
        sys.stderr.buffer.write(chunk)
        sys.stderr.buffer.flush()
        captured.extend(chunk)
    process.wait()
    seconds = time.monotonic() - start

    lines = captured.decode("utf-8", errors="replace").replace("\r", "\n").splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    last_error_line = lines[-1] if lines else "(no error output)"
    return process.returncode == 0, seconds, last_error_line


def newest_ingest_run_id():
    """Highest id in pipeline_runs right now (0 if empty), or None if unreachable."""
    try:
        with get_connection() as conn:
            return conn.execute("SELECT coalesce(max(id), 0) FROM pipeline_runs").fetchone()[0]
    except Exception:
        return None


def collect_funnel(conn, ingest_ran, run_id_before):
    """Numbers that show how much flowed through the pipeline."""
    funnel = {"items_fetched": None, "new_articles": None,
              "stories_in_window": None, "multi_article_stories": None}
    if ingest_ran and run_id_before is not None:
        # The newest pipeline_runs row created during this execution.
        row = conn.execute(
            "SELECT items_fetched, new_rows FROM pipeline_runs WHERE id > %s "
            "ORDER BY id DESC LIMIT 1", (run_id_before,)).fetchone()
        if row:
            funnel["items_fetched"], funnel["new_articles"] = row
    total, multi = conn.execute(STORY_COUNTS_SQL, (STORY_WINDOW_DAYS,)).fetchone()
    funnel["stories_in_window"], funnel["multi_article_stories"] = total, multi
    return funnel


def log_start(started_at):
    """Write the first row (finished_at empty). Return its id, or None."""
    try:
        with get_connection() as conn:
            return conn.execute(START_SQL, (started_at,)).fetchone()[0]
    except Exception:
        print("could not log execution (start)", flush=True)
        return None


def log_finish(execution_id, row, ingest_ran, run_id_before):
    """Fill in the rest of the row. Never crashes the runner."""
    try:
        with get_connection() as conn:
            row["funnel"] = Jsonb(collect_funnel(conn, ingest_ran, run_id_before))
            if execution_id is None:
                conn.execute(INSERT_FULL_SQL, row)
            else:
                conn.execute(FINISH_SQL, {**row, "id": execution_id})
    except Exception:
        print("could not log execution", flush=True)


def main():
    # Stage names from the command line, or all of them.
    chosen = sys.argv[1:] or list(STAGES)

    # Check every name BEFORE running anything.
    unknown = [name for name in chosen if name not in STAGES]
    if unknown:
        print(f"unknown stage(s): {', '.join(unknown)}")
        print(f"valid stages: {', '.join(STAGES)}")
        sys.exit(2)

    started_at = datetime.now(timezone.utc)
    execution_id = log_start(started_at)
    run_id_before = None  # max pipeline_runs id just before ingest

    results = []  # (name, status, seconds)
    failed = None
    error_message = None
    for name in chosen:
        if failed:
            results.append((name, "skipped", 0.0))
            continue
        if name == "ingest":
            run_id_before = newest_ingest_run_id()
        ok, seconds, last_error_line = run_stage(name)
        results.append((name, "ok" if ok else "failed", seconds))
        print(flush=True)
        if not ok:
            failed = name
            error_message = safe_text(f"{name}: {last_error_line}")
            print(f"stage '{name}' failed, skipping the rest", flush=True)

    total_seconds = sum(r[2] for r in results)
    print("===== summary =====")
    for name, status, seconds in results:
        print(f"  {name:<8} {status.upper() if status == 'failed' else status:<8} {seconds:6.1f}s")
    print(f"  total             {total_seconds:6.1f}s", flush=True)

    log_finish(execution_id, {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc),
        "ok": failed is None,
        "total_seconds": round(total_seconds, 3),
        "stages": Jsonb([{"name": n, "status": s, "seconds": round(sec, 3)}
                         for n, s, sec in results]),
        "error_message": error_message,
    }, ingest_ran=any(n == "ingest" and s != "skipped" for n, s, _ in results),
       run_id_before=run_id_before)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
