"""Run the pipeline stages in order, each as its own process.

Run from the backend folder:
  python run_pipeline.py                 # all stages: ingest, embed, cluster
  python run_pipeline.py ingest cluster  # only these, in this order
If a stage fails, the remaining stages are skipped and the exit code is 1.
"""

import subprocess
import sys
import time
from pathlib import Path

# The folder this file lives in (backend/), so it works from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent

# Stage name -> the script that does it. The order here is the default order.
STAGES = {
    "ingest": "ingest.py",
    "embed": "embed_articles.py",
    "cluster": "cluster_stories.py",
}


def run_stage(name):
    """Run one stage's script and return (ok, seconds)."""
    print(f"===== {name} ({STAGES[name]}) =====", flush=True)
    start = time.monotonic()
    # sys.executable is the Python running this file (the venv's Python).
    # A separate process means a crash there can't break this script.
    result = subprocess.run([sys.executable, STAGES[name]], cwd=BACKEND_DIR)
    seconds = time.monotonic() - start
    return result.returncode == 0, seconds


def main():
    # Stage names from the command line, or all of them.
    chosen = sys.argv[1:] or list(STAGES)

    # Check every name BEFORE running anything.
    unknown = [name for name in chosen if name not in STAGES]
    if unknown:
        print(f"unknown stage(s): {', '.join(unknown)}")
        print(f"valid stages: {', '.join(STAGES)}")
        sys.exit(2)

    results = []  # (name, status, seconds)
    failed = None
    for name in chosen:
        if failed:
            results.append((name, "skipped", 0.0))
            continue
        ok, seconds = run_stage(name)
        results.append((name, "ok" if ok else "FAILED", seconds))
        print(flush=True)
        if not ok:
            failed = name
            print(f"stage '{name}' failed, skipping the rest", flush=True)

    print("===== summary =====")
    for name, status, seconds in results:
        print(f"  {name:<8} {status:<8} {seconds:6.1f}s")
    print(f"  total             {sum(r[2] for r in results):6.1f}s")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
