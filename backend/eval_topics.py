"""Step 7b: compare three ways of scoring articles against topic descriptions.

Run from the backend folder:  python eval_topics.py
Read-only: it only SELECTs and writes no files. Titles are printed to the
console only, never saved.

Variants:
  A: single description per topic, tag every topic with score >= t.
  B: single description per topic, relative rule (see predict_relative).
  C: like B, but a topic's score is the best of its 3 descriptions.
"""

import csv
import sys

import numpy as np
from pgvector.psycopg import register_vector
from sklearn.model_selection import KFold

from db import BACKEND_DIR, get_connection
from embed_articles import load_model
from topics import TOPIC_DESCRIPTIONS, TOPIC_VARIANTS

# Print non-English letters correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

GOLD_PATH = BACKEND_DIR.parent / "data" / "labels" / "gold_labels.csv"

# BBC programme pages: the title is a show name, not a story.
PROGRAMME_TITLES = {"Tech Now", "Tech Life", "Inside Health", "BBC Inside Science"}

MAX_TAGS = 3          # an article gets at most this many topics
MIN_GOLD = 5          # fewer gold examples than this: "too few to judge"
MAX_MISMATCHES = 15
TITLE_MAX_CHARS = 70
N_FOLDS = 5
SEED = 42             # fixed, so the folds are the same every run

# Parameter grids. A uses (t,), B and C use (f, m).
GRID_ABSOLUTE = [(round(i * 0.025, 3),) for i in range(13)]            # 0.00 ... 0.30
GRID_RELATIVE = [(f, m) for f in (0.05, 0.10, 0.15, 0.20, 0.25)
                 for m in (0.7, 0.8, 0.9)]


# ---------- loading ----------

def load_gold():
    """Return {url: set of gold topics} from the gold labels file."""
    with open(GOLD_PATH, encoding="utf-8", newline="") as f:
        return {row["url"]: {t for t in row["topics"].split(",") if t}
                for row in csv.DictReader(f)}


def load_articles(urls):
    """Return a list of (url, title, embedding) for the gold urls in the database."""
    with get_connection() as conn:
        conn.read_only = True   # safety: the database refuses any write
        register_vector(conn)   # read pgvector columns as Vector objects
        return conn.execute(
            "SELECT url, title, embedding FROM articles "
            "WHERE url = ANY(%s) AND embedding IS NOT NULL ORDER BY id",
            (list(urls),),
        ).fetchall()


# ---------- the two prediction rules ----------

def predict_absolute(scores, names, params):
    """Every topic with score >= t, highest first, at most MAX_TAGS."""
    (t,) = params
    order = np.argsort(-scores)  # topic indexes, best match first
    return [names[i] for i in order if scores[i] >= t][:MAX_TAGS]


def predict_relative(scores, names, params):
    """Tag the best topic if its score >= f, plus up to 2 more topics whose
    score is >= f and >= m times the best score."""
    f, m = params
    order = np.argsort(-scores)
    best = scores[order[0]]
    if best < f:
        return []
    tags = [names[order[0]]]
    for i in order[1:MAX_TAGS]:
        if scores[i] >= f and scores[i] >= m * best:
            tags.append(names[i])
    return tags


# ---------- scoring ----------

def micro_counts(preds, golds):
    """Sum true positives, false positives and false negatives over all rows."""
    tp = fp = fn = 0
    for p, g in zip(preds, golds):
        p = set(p)
        tp += len(p & g)   # predicted and in gold
        fp += len(p - g)   # predicted but not in gold
        fn += len(g - p)   # in gold but missed
    return tp, fp, fn


def prf(tp, fp, fn):
    """Precision, recall and F1 from the counts."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def f1_on(rows, sims, golds, names, rule, params):
    """Micro-F1 of one rule and parameter setting on the chosen row indexes."""
    preds = [rule(sims[i], names, params) for i in rows]
    return prf(*micro_counts(preds, [golds[i] for i in rows]))[2]


def best_params(rows, sims, golds, names, rule, grid):
    """The parameters with the highest micro-F1 on these rows (first one wins ties)."""
    scored = [(f1_on(rows, sims, golds, names, rule, p), p) for p in grid]
    best_f1 = max(s for s, _ in scored)
    return next(p for s, p in scored if s == best_f1), best_f1


def format_params(params):
    if len(params) == 1:
        return f"t={params[0]:.3f}"
    return f"f={params[0]:.2f}, m={params[1]:.1f}"


# ---------- main ----------

def main():
    gold = load_gold()
    articles = load_articles(gold)
    print(f"gold rows: {len(gold)}, matched in database: {len(articles)}")

    # Drop programme pages, whose titles say nothing about the story.
    kept = [a for a in articles if a[1].strip() not in PROGRAMME_TITLES]
    print(f"excluded programme labels: {len(articles) - len(kept)}, rows remaining: {len(kept)}")
    articles = kept

    names = list(TOPIC_DESCRIPTIONS)
    golds = [gold[url] for url, _title, _emb in articles]
    model = load_model()

    # Article vectors, one row per article. All vectors are length 1, so a
    # dot product is the cosine similarity.
    article_vectors = np.array([emb.to_numpy() for _url, _title, emb in articles])

    # Single-description scores (variants A and B): shape (articles, 13).
    single = model.encode([TOPIC_DESCRIPTIONS[n] for n in names], normalize_embeddings=True)
    sims_single = article_vectors @ single.T

    # Multi-description scores (variant C): for each topic, the best of its 3.
    sims_multi = np.zeros_like(sims_single)
    for j, name in enumerate(names):
        vectors = model.encode(TOPIC_VARIANTS[name], normalize_embeddings=True)
        sims_multi[:, j] = (article_vectors @ vectors.T).max(axis=1)

    variants = {
        "A (single, absolute)": (sims_single, predict_absolute, GRID_ABSOLUTE),
        "B (single, relative)": (sims_single, predict_relative, GRID_RELATIVE),
        "C (multi, relative)":  (sims_multi, predict_relative, GRID_RELATIVE),
    }

    # The same 5 folds for every variant.
    all_rows = list(range(len(articles)))
    folds = list(KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(all_rows))

    results = {}
    for label, (sims, rule, grid) in variants.items():
        # In-sample: best parameters on all rows (optimistic).
        params, in_f1 = best_params(all_rows, sims, golds, names, rule, grid)
        in_preds = [rule(sims[i], names, params) for i in all_rows]

        # Cross-validation: pick parameters on 4 folds, score on the 5th.
        fold_f1s = []
        held_out_preds = [None] * len(articles)
        chosen = []
        for train, test in folds:
            fold_params, _ = best_params(train, sims, golds, names, rule, grid)
            chosen.append(fold_params)
            fold_f1s.append(f1_on(test, sims, golds, names, rule, fold_params))
            for i in test:
                held_out_preds[i] = rule(sims[i], names, fold_params)
        cv_f1 = float(np.mean(fold_f1s))
        results[label] = (cv_f1, held_out_preds)

        print(f"\n=== {label}")
        print(f"  in-sample best micro-F1: {in_f1:.3f} at {format_params(params)}"
              f"  (no-tag rows: {sum(not p for p in in_preds) / len(articles):.0%})")
        print(f"  5-fold CV micro-F1:      {cv_f1:.3f} "
              f"(folds: {', '.join(f'{x:.2f}' for x in fold_f1s)})"
              f"  (held-out no-tag rows: {sum(not p for p in held_out_preds) / len(articles):.0%})")
        print(f"  parameters chosen per fold: {'; '.join(format_params(p) for p in chosen)}")

    # --- Details for the variant with the best cross-validated F1 ---
    best_label = max(results, key=lambda k: results[k][0])
    preds = results[best_label][1]
    print(f"\nbest cross-validated variant: {best_label}")
    print("per-topic table (held-out predictions, each row predicted by a fold that did not see it):")
    print(f"\n{'topic':14} {'gold':>4} {'pred':>4}  {'prec':>5}  {'recall':>6}  F1")
    for name in names:
        tp = sum(name in p and name in g for p, g in zip(preds, golds))
        n_gold = sum(name in g for g in golds)
        n_pred = sum(name in p for p in preds)
        precision, recall, f1 = prf(tp, n_pred - tp, n_gold - tp)
        prec_s = f"{precision:.2f}" if n_pred else "  -"
        rec_s = f"{recall:.2f}" if n_gold else "  -"
        f1_s = "too few to judge" if n_gold < MIN_GOLD else f"{f1:.2f}"
        print(f"{name:14} {n_gold:>4} {n_pred:>4}  {prec_s:>5}  {rec_s:>6}  {f1_s}")

    print(f"\nrows where prediction differs from gold (up to {MAX_MISMATCHES}):")
    shown = 0
    for (_url, title, _emb), p, g in zip(articles, preds, golds):
        if set(p) != g and shown < MAX_MISMATCHES:
            gold_s = ",".join(sorted(g)) or "(none)"
            pred_s = ",".join(p) or "(none)"
            print(f"  gold={gold_s:22} pred={pred_s:28} {title[:TITLE_MAX_CHARS]}")
            shown += 1
    total_diff = sum(set(p) != g for p, g in zip(preds, golds))
    print(f"  ({total_diff} of {len(articles)} rows differ in total)")

    print("\nLabels are LLM-drafted and unreviewed. Parameters were chosen inside "
          "cross-validation; the held-out scores are the honest estimate.")


if __name__ == "__main__":
    main()
