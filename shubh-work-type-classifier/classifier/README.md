# typeclf — lightweight deployable work-type classifier

A tiny, **no-LLM, no-neural-net** classifier that reproduces the Opus 4.8 gold labels (from
[`../labeler`](../labeler)) at full-corpus scale. Multinomial **logistic regression over
TF-IDF** + a few structured signals — the literature's top pick for scholarly text
classification and the cheapest thing to deploy (a few-MB model scoring millions of works
with just numpy/scipy).

It is the cheap counterpart to the labeler: the labeler makes gold with Opus-per-work;
`typeclf` distills that gold into a model you can run offline over all of OpenAlex.

## Two feature scopes

| Scope | Uses | Runs where | Held-out acc | Notes |
|---|---|---|---|---|
| **metadata** | OpenAlex-native fields only (title, current type, venue, biblio, ISBN, has-abstract) | offline, full ~250M-work corpus | ~0.87 | no external fetch — the real at-scale model |
| **full** | + taxicab `dc.type`/page-title + landing-page health | needs the enrich step (4 HTTP/work) | ~0.89 | accuracy ceiling; a drop-in cheaper-than-Opus pass |

Both clear the "keep OpenAlex's current type" baseline (~0.71) by a wide margin. See
[`APPROACH.md`](./APPROACH.md) for the full results, per-type β/α, and limitations.

## Install

```bash
cd shubh-work-type-classifier/classifier
pip install -r requirements.txt        # scikit-learn, scipy, numpy, joblib
```

## Train

```bash
python -m typeclf.train --features full     -o models/full.joblib
python -m typeclf.train --features metadata  -o models/meta.joblib
# A/B the model family (LinearSVC instead of logreg; no confidence scores):
python -m typeclf.train --features full --model linsvc -o models/full_svm.joblib
```

Trains on `../data/gold_shard01.jsonl` (10k) + `../data/gold_strat.jsonl` (~1.36k, props up
the rare/leaking types) in ~15s. `class_weight="balanced"` handles the heavy imbalance.

## Evaluate

```bash
python -m typeclf.evaluate                       # both scopes; held-out + CV + external val
python -m typeclf.evaluate --features full --no-cv --report report.md
```

Reports overall accuracy + macro-F1, **per-type precision/recall (= 1−β / 1−α** in the
Maisano et al. 2025 sense), hotspot confusion (`article↔review`/`conference-paper`/
`editorial`), a confidence/coverage curve, and external validation on `sample1000`.

Independent human check (enriches the 166 human-labeled DOIs, then scores them):

```bash
python -m typeclf.eval_human --model models/full.joblib      # enrich (network) + score; caches
python -m typeclf.eval_human --model models/meta.joblib --no-fetch   # offline, from cache
```

## Predict (the deployable path — no LLM, no network)

```bash
python -m typeclf.predict --in works.jsonl --model models/full.joblib --out preds.csv
```

Input is enrichment JSONL — either the labeler's output, or generated fresh with
`worktype --sample N --no-annotate -o works` (enrich only, no API key). For the
**metadata** model the records only need the OpenAlex-native `oa_*` fields, so you can feed
a plain OpenAlex works dump mapped to those names — no enrich step at all.

Output columns: `doi, openalex_id, current_type, predicted_type, confidence, changed`.
`confidence` is the max class probability — threshold it to auto-route low-confidence works
to the LLM labeler (at conf ≥ 0.7 the full model covers ~84% of works at ~95% accuracy).

## Layout

```
classifier/
  typeclf/
    features.py     # enrichment record -> features; FULL vs METADATA scopes; WorkTypeFeaturizer
    dataset.py      # load gold JSONL + human CSV; normalize DOI/OA-id join keys
    train.py        # fit the pipeline, save with joblib
    evaluate.py     # held-out/CV metrics, per-type β/α, hotspots, coverage curve
    eval_human.py   # independent check vs the human reference set (enriches its DOIs)
    predict.py      # batch scoring — the deployable inference path
  models/           # saved .joblib models (gitignored)
  requirements.txt
```
