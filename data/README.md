# Gold datasets — LLM-labeled work types

Produced by the `labeler/` CLI (Opus 4.8 over OpenAlex+Crossref+taxicab signals, #535 taxonomy).
Labels are blind (no human/vendor label fed in). `is_changed` = `opus_type` differs from current OpenAlex `current_type`.

### ⭐ Use this: the full consolidated gold
| File | Rows | What |
|---|---|---|
| `gold_full_52k.csv` | **52,383** | **All shards below, deduped by DOI — the canonical full gold-standard label set.** 29.8% `is_changed` vs current OpenAlex. This is the single file to train/evaluate against. (Labels only; for the full per-work enrichment features, read the component `*.jsonl` shards — together they hold the same 52k.) |

### Component shards (provenance; concatenate the `.jsonl` for full features)
| File | Rows | What |
|---|---|---|
| `gold_random_10k.csv` / `.jsonl` | 10,000 | random Crossref, last 20 yrs (seed=1). CSV = labels; JSONL = full enrichment features + labels. |
| `gold_random_1k.csv` / `.jsonl` | 1,000 | earlier validated run (seed=42). |
| `gold_random_s7_10k.csv` / `.jsonl` | 10,000 | random Crossref, last 20 yrs (seed=7). |
| `gold_random_s8_10k.csv` / `.jsonl` | 10,000 | random Crossref, last 20 yrs (seed=8). |
| `gold_random_s9_10k.csv` / `.jsonl` | 10,000 | random Crossref, last 20 yrs (seed=9). |
| `gold_master.csv` / `.jsonl` | 10,000 | earlier master gather (random Crossref). |
| `gold_stratified.csv` / `.jsonl` | ~1,360 | **stratified** oversample of under-represented/leaking types (editorial, letter, review, other, retraction, standard, erratum, peer-review, libguides) for training the deployable classifier. |
| `gold_targeted.csv` / `.jsonl` | ~1,300 | **targeted** gather of rare/weak types (data-paper, software-paper, retraction, standard, conference-abstract, peer-review, erratum). |

The seed-1/7/8/9 + master shards are random draws (overlap is small but real); `gold_full_52k.csv`
is their dedup-by-DOI union, so use it as the eval set rather than summing the shards.

CSV columns: `openalex_id, doi, landing_page_url, current_type, opus_type, is_changed, opus_confidence, opus_reason, opus_is_broken, lp_status, error`. `error=refusal` = safety-classifier refusal (hand-label).

## Human-annotated reference
`human_annotated.csv` — 200 works hand-labeled by the OpenAlex team (jason/casey/kyle/rohan; 166 with a label), combined with an `annotator` column. Original hand-annotation gold; pairs with the LLM gold for cross-checking. Note: some rows use pre-#535 vocabulary/typos.
