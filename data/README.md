# Gold datasets — LLM-labeled work types

Produced by the `labeler/` CLI (Opus 4.8 over OpenAlex+Crossref+taxicab signals, #535 taxonomy).
Labels are blind (no human/vendor label fed in). `is_changed` = `opus_type` differs from current OpenAlex `current_type`.

| File | Rows | What |
|---|---|---|
| `gold_shard01.csv` / `.jsonl` | 10,000 | random Crossref, last 20 yrs (seed=1). CSV = labels; JSONL = full enrichment features + labels. |
| `sample1000.csv` / `.jsonl` | 1,000 | earlier validated run (seed=42). |
| `gold_strat.csv` / `.jsonl` | ~1,360 | **stratified** oversample of under-represented/leaking types (editorial, letter, review, other, retraction, standard, erratum, peer-review, libguides) for training the deployable classifier. |

CSV columns: `openalex_id, doi, landing_page_url, current_type, opus_type, opus_confidence, opus_reason, opus_is_broken, lp_status, error` (+ `is_changed` in regenerated outputs). `error=refusal` = safety-classifier refusal (hand-label).

## Human-annotated reference
`human_annotated.csv` — 200 works hand-labeled by the OpenAlex team (jason/casey/kyle/rohan; 166 with a label), combined with an `annotator` column. Original hand-annotation gold; pairs with the LLM gold for cross-checking. Note: some rows use pre-#535 vocabulary/typos.
