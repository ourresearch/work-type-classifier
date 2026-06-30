# oxjob #909 — program (standing per-iteration instructions)

This is the autoresearch-style "program" for #909: the fixed protocol every iteration follows.
Modeled on karpathy/autoresearch (a `program.md` + a keep/discard log on one metric), adapted
to keep an explicit `JOURNAL.md` so the experiment history survives.

## The job

Distill the Opus gold labels into a **small, interpretable, non-circular, Databricks-deployable**
type classifier. ML is used to **discover signals**, not as the production model. The deployable
is a **hybrid**: a deterministic rule cascade (clean types) + a depth-limited decision tree (the
fuzzy article↔editorial/review residual).

## Invariants (do not violate)

1. **No circular features.** Never feed OpenAlex's own labels (`oa_type`, `oa_is_paratext`) to a
   model or rule. Raw Crossref (`cr_type`, `cr_subtype`) is allowed — it is the upstream signal
   OpenAlex flattens. (See `features.py`; this is enforced by construction.)
2. **Frozen splits.** Iterate on `val`. The `test` set is **touched once**, at the final iteration.
   Never tune on test. (`splits/` is written once and reloaded.)
3. **Interpretable-size models only.** Deployable uses ≤~20 engineered features and a depth-≤6 tree
   — feature count must stay << samples. No raw TF-IDF tokens in the deployable.
4. **Headline metric = macro-F1 + the article-boundary scorecard**, never overall accuracy alone.
   Guardrail: **article precision must not fall** while neighbor-type recall rises.

## Each iteration

1. State a one-line **hypothesis**.
2. Make the **smallest change** that tests it (a feature, a rule, a threshold, a depth).
3. Evaluate on **val**: print the confusion matrix + article-boundary scorecard + train/val gap.
4. **Keep or discard** vs the current best, and **append the decision + learning** to `JOURNAL.md`
   (`evaluate.log_journal` upserts by iter id; `iters/` holds the artifacts).
5. Only at the end: run the **locked test** once (`run.py --iter I5 --commit-test`).

## Run

```bash
pip install -r requirements.txt
python -m oxjob_909.run --all                 # I0..I4 on val
python -m oxjob_909.run --iter I5 --commit-test   # FINAL: locked test, once
```

## Ideas backlog (next iterations)

- Editorial recall is the weak cell (~0.19). Try: publisher/venue editorial-section priors,
  `front-of-issue` page position, first-page≤2 signal.
- ISBN→book-family split (chapter vs reference-entry vs paratext) could use a sub-tree.
- Calibrate a confidence/abstain threshold on the tree leaf purity → route low-confidence to Opus.
- Replace the depth-6 tree with a 2–3 rule hand-authored extension if it matches the tree (more
  auditable for Jason).
