# Approach note — lightweight deployable type classifier (Shubhankar's ack job)

*Project note for the OpenAlex `type`-classification effort. Owner: Shubhankar. Date: 2026-06-30.*

## Ack job / task split

This is **one independent lane** in the type-classification effort — the *cheap, deployable*
counterpart to the Opus labeler. Overlap with other lanes is fine and expected.

- **This lane (here):** distill the Opus 4.8 gold labels into a tiny linear model that runs
  at full-corpus scale with **no LLM and no neural net**. Single concrete path: multinomial
  logistic regression over TF-IDF + a few structured signals.
- **Labeler lane (`../labeler`):** Opus-per-work gold generation (the training signal here).
- **Open for others:** rules/gates layer (ISBN/ISSN/container gates, `refs≥40→review`),
  cross-source concordance auditing, GBDT/embedding variants, active-learning to fix the
  thin tail types. Nothing here forecloses those.

## What & why

OpenAlex inherits coarse Crossref types and labels ~99.5% of journal items a generic
`article`, leaking reviews/editorials/conference-papers/paratext (confirmed by
[arxiv 2406.15154](https://arxiv.org/abs/2406.15154); our gold changes 29% of labels). Opus
fixes this per-work but doesn't scale to ~250M works. So: **train a model to reproduce the
Opus gold from cheap features.**

**Model = multinomial logistic regression + TF-IDF.** The literature consensus for scholarly
text classification is LogReg+TF-IDF on top (beats SVM/NB/RF/GBDT and embeddings in head-to-
heads; refs in the repo PR/notes). It is also the cheapest to deploy — a few-MB model that
scores millions of works with numpy/scipy — gives **calibrated probabilities** (a clean
confidence/abstain threshold to auto-route hard works back to the LLM), and is **interpretable**
(per-type coefficients). `LinearSVC` is wired up as a one-flag A/B (`--model linsvc`).

**Two feature scopes, both reported** (see `features.py`):
- **metadata** — only OpenAlex-native fields (title, current type, venue, biblio, ISBN,
  has-abstract). No external fetch → the genuinely full-corpus-deployable model.
- **full** — adds taxicab `dc.type`/page-title (78–94% coverage) + landing-page health.
  Accuracy ceiling; a drop-in cheaper-than-Opus pass that still needs the enrich step.

`class_weight="balanced"` is mandatory — the gold is severely imbalanced (`article` 48% …
`software-paper` 1 row in 10k). `gold_strat` (~1.36k stratified) props up the leaking/rare types.

## Results

Held-out = stratified 20% of `gold_shard01`+`gold_strat`. External val = `sample1000`
(seed=42, non-overlapping). Baseline = keep OpenAlex's current `type`. Per-type
precision/recall = **1−β / 1−α** in the Maisano et al. (2025) sense. Reproduce with
`python -m typeclf.evaluate --report report.md`.

| Metric | **full** | **metadata** | baseline |
|---|---|---|---|
| Held-out accuracy | **0.890** | **0.868** | 0.711 |
| Held-out macro-F1 | 0.777 | 0.743 | — |
| 5-fold CV macro-F1 | 0.788 ± 0.037 | 0.767 ± 0.039 | — |
| External val (sample1000) accuracy | 0.900 | 0.870 | — |
| External val macro-F1 | 0.840 | 0.788 | — |
| Human-set agreement (166 rows) | 0.613 | 0.607 | — |

**Takeaways**
- **+18 points over baseline** on held-out; **metadata-only is within ~2 points of full** —
  so the truly-deployable model captures almost all the lift without any external fetch.
- **Confidence routing works** (full model): at max-prob ≥ 0.70 the model covers **84%** of
  works at **95%** accuracy; ≥ 0.90 covers 57% at 98%. The remaining low-confidence tail is
  exactly what you'd send to the Opus labeler.
- **Hotspots improve but remain the hard cases.** Residual confusion is `article↔review`
  (recall ~0.67 on review), `editorial→article/letter` (editorial recall ~0.55), and
  `conference-abstract↔article` — the same boundaries the paper flags. Strong types
  (preprint, peer-review, dissertation, erratum, standard, paratext) are ≥0.94 F1.

## Limitations (read before trusting it)

1. **Gold is LLM labels, not ground truth.** The model is trained to reproduce Opus, so
   held-out/CV numbers measure *fidelity to Opus*, not correctness. The **human-set agreement
   (~0.61)** is the honest independent number — lower partly because the 166 human rows use
   pre-#535 vocabulary/typos (16 unmappable) and a different annotation convention, and the
   set is tiny and noisy. Closing the LLM-vs-human gap needs more human gold in #535 vocab.
2. **Thin tail types** (`data-paper`, `software`, `software-paper`, `supplementary-materials`,
   `retraction`) have ≤ a handful of examples — their metrics are unstable and they need
   targeted labeling. The evaluator flags these rather than hiding them.
3. **`cr_subtype` is only 3% populated** in the gold, so the model leans on title + page
   text + venue + `oa_type` prior, not Crossref subtype.
4. **No silent drops:** all 24 observed types are kept in training and reported.

## Files
`typeclf/{features,dataset,train,evaluate,eval_human,predict}.py` — see `README.md` for
usage. Models are gitignored (regenerate in ~15s). `data/human_enriched.jsonl` caches the
human-DOI enrichment so `eval_human --no-fetch` runs offline.

> The parent `type_classification/` research-notes folder is **outside this git repo**, so
> this pushable note lives here. Mirror it there manually if a copy alongside the other
> notes is wanted.
