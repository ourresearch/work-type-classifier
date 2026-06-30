# oxjob #909 — feature-first, de-leaked, interpretable type classifier

Pivot from the `../classifier` LogReg+TF-IDF model after team review. The learnings driving #909:

1. **Overall accuracy isn't enough** — report the confusion matrix + per-type behavior, and prove
   paratext isn't won by sacrificing article.
2. **Overfit risk** — 30k TF-IDF tokens > 10.7k samples isn't trustworthy. Use few features.
3. **Find the 3–4 factors per type**, distill into a decision tree / simple rules.
4. **Remove circular features** — drop OpenAlex's own labels (`oa_type`, `oa_is_paratext`); keep raw
   Crossref (`cr_type`/`cr_subtype`) — the upstream signal OpenAlex flattens.
5. **Reference count is the discovered signal**, but at a high threshold: refs≥40→review is only 16%
   precise; **≥150 is 86%**.
6. **Deterministic wins**: proceedings→conference (92%), `cr_subtype=preprint`→preprint (99%),
   ISBN→book-family, repository→preprint/dataset.
7. **ML discovers signals; the deployable is rules + a shallow tree.**

`ML for discovery, not production.` The shipped artifact is a **hybrid**: a deterministic cascade
(`cascade.py` / `cascade.sql`) + a depth-6 decision tree on the residual (`tree.py`).

## Results (frozen 60/20/20 split, seed 909)

| Iter | What | split | acc | macro-F1 | article P / R |
|---|---|---|---|---|---|
| I0 | keep oa_type (baseline) | val | 0.716 | 0.526 | 0.711 / 0.986 |
| I1 | de-leaked LR (no oa_type) | val | 0.775 | 0.551 | 0.798 / 0.976 |
| I3 | deterministic cascade only | val | 0.699 | 0.344 | 0.661 / 0.994 |
| I4 | hybrid cascade→tree | val | 0.763 | 0.523 | 0.825 / 0.947 |
| **I5** | **final hybrid** | **TEST (locked)** | **0.763** | **0.527** | **0.820 / 0.929** |

The hybrid beats baseline on accuracy with **train/val gap ≈ 0** (not overfit), recovers the biggest
OpenAlex errors — **conference-paper recall 0→0.73, conference-abstract 0→0.49, paratext 0→0.37** —
while **article precision holds at 0.82** (the original question: article is *not* sacrificed for
paratext). Editorial (~0.19) is the remaining hard article-boundary cell. Full per-iteration history,
confusion matrices, and learnings are in [`JOURNAL.md`](./JOURNAL.md) + `iters/`.

## Run

Run these from the `shubh-work-type-classifier/` namespace dir (the parent of this package).

```bash
pip install -r requirements.txt          # scikit-learn, scipy, numpy, statsmodels
python -m oxjob_909.splits               # build the frozen split (once)
python -m oxjob_909.run --all            # I0..I4 on val (writes JOURNAL + iters/)
python -m oxjob_909.run --iter I5 --commit-test   # FINAL: locked test, touched once
```

## Layout

```
oxjob_909/
  program.md     # standing per-iteration protocol (invariants, metric, keep/discard loop)
  JOURNAL.md     # the experiment log + leaderboard (one entry per iteration)
  data.py        # load raw gold enrichment records + labels (reuses ../classifier dataset)
  features.py    # engineered NON-circular features (no oa_type/oa_is_paratext)
  splits.py      # frozen stratified 60/20/20; locked test set
  discover.py    # per-class logit (X vs article) + tree importances — signal discovery (I2)
  cascade.py     # deterministic rule cascade (I3)
  cascade.sql    # the cascade as Spark SQL — the Databricks deterministic layer
  tree.py        # depth-6 decision tree on the residual + hybrid predict (I4)
  evaluate.py    # confusion matrix, article-boundary scorecard, train/val gap, JOURNAL logger
  run.py         # driver for iterations I0..I5
  iters/         # per-iteration metrics.json + confusion/signal/tree artifacts
```

## Deploy in Databricks

Two-stage, both fetch-free and OpenAlex-native:
1. **`cascade.sql`** assigns the deterministic types in pure Spark SQL (no UDF, no model) — ~32% of
   works, high precision. Leaves the residual `NULL`.
2. For `NULL` rows, score the depth-6 tree (`iters/I4_tree.txt` is the human-readable export;
   ~12 features) — trivially portable to Spark MLlib or a handful of nested CASE statements.
