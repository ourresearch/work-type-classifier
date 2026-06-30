# worktype-cli

Standalone, parallel **work-type classifier** for OpenAlex / Crossref works. It reproduces the
enrich → annotate pipeline from oxjob #534/#535 as a repeatable CLI:

1. **Enrich** each DOI with the signals that actually decide type — OpenAlex (`title`, biblio,
   `source_type`, current `type`), Crossref (`type`/`subtype`), taxicab harvested-HTML meta
   (`dc.type`, `citation_title`, `article-type`) + page title, and a **live landing-page health
   check** (for the `broken` flag).
2. **Annotate** with Claude (Opus 4.8), constrained by structured outputs to the **canonical 25-type
   taxonomy** (#535). Returns `type`, `is_broken`, `confidence`, and a one-sentence evidence reason.

Runs the whole thing concurrently (default 50, comfortable up to ~100 threads), is **resumable**, and
writes both JSONL (full signals + annotation) and a tidy CSV.

## Install

```bash
cd worktype-cli
pip install -e .            # or: pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or: ant auth login
```

## Use

```bash
# 100 random Crossref works, 100 threads (the headline use case)
worktype --sample 100 --seed 42 --workers 100 -o sample100

# A specific list of DOIs
worktype --dois my_dois.txt -o mybatch

# A CSV with a `doi` column (e.g. the contested adjudication set)
worktype --csv contested_for_adjudication.csv --doi-col doi --workers 100 -o contested

# Every OpenAlex 'editorial' work (capped), to audit one type
worktype --filter 'type:editorial' --limit 2000 -o editorial_audit

# Enrich only, no LLM (no API key needed)
worktype --sample 200 --no-annotate -o enriched_only
```

Re-running the same `-o` prefix **resumes** — already-classified DOIs are skipped (use `--no-resume`
to force a full re-run).

### Building a large training set (~100k, last 20 years)

`--sample` defaults to Crossref works from the last ~20 years (`from_publication_date:2006-01-01`).
OpenAlex caps a single `sample` query at **10,000**, so build 100k as ten seeded shards into the same
output (resume/dedup is automatic):

```bash
for s in 1 2 3 4 5 6 7 8 9 10; do
  worktype --sample 10000 --seed $s --workers 100 -o gold100k
done
```

This yields ~100k labeled rows (`opus_type` + reason + signals) — the gold to train/validate a cheaper
deployable classifier downstream.

## Output

`<prefix>.jsonl` — one full record per work (every signal + the annotation, with `_request_id`).
`<prefix>.csv` — columns: `doi, openalex_id, title, current_oa_type, crossref_raw_type,
predicted_type, is_broken, confidence, reason, source_type, lp_status, tx_page_title, error`.

## Key flags

| Flag | Default | Notes |
|---|---|---|
| `--workers` | 50 | Concurrent threads. ~100 is fine — the Anthropic SDK backs off on 429/5xx. |
| `--effort` | medium | `low`→`max`. Raise for harder boundary calls (review↔article), lower for speed/cost. |
| `--model` | claude-opus-4-8 | Any current Claude model id. |
| `--no-landing-check` | off | Skip the live page probe (faster; disables the page-based `broken` signal). |
| `--no-annotate` | off | Enrichment only. |
| `--mailto` | — | OpenAlex/Crossref polite-pool email. |

## How `broken` is decided

`is_broken` is a **page-health** flag, independent of `type`: true only when the live landing page is
genuinely dead — HTTP 5xx, 404/410, unreachable, or a taxicab page title of "Page not found" /
"DOI Not Found". A 403/401 bot-block or any 200/202 page is **not** broken. The work still gets its
best `type` from metadata even when the page is broken.

## Notes on scale & rate limits

Enrichment is I/O-bound (4 HTTP calls/work) and parallelizes freely. The Claude calls share one
thread-safe client with `max_retries=8`; at 100 concurrent annotations you may briefly hit Opus
RPM/ITPM limits, which the SDK rides out with exponential backoff. For very large jobs (tens of
thousands), consider the Message Batches API (50% cheaper) as a future mode — this CLI is tuned for
interactive, resumable runs up to a few thousand works.
