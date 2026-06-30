"""Threaded enrich -> annotate pipeline with checkpoint/resume and incremental JSONL + CSV output."""
import csv
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .annotate import Annotator
from .enrich import clean_doi, enrich, signals_for_annotation

# Requested 7 columns + the three audit columns (broken flag, raw landing status, diagnostics).
# The remaining signals (title, taxicab meta, crossref subtype, ...) stay in the <prefix>.jsonl.
CSV_COLUMNS = [
    "openalex_id", "doi", "landing_page_url", "current_type",
    "opus_type", "is_changed", "opus_confidence", "opus_reason",
    "opus_is_broken", "lp_status", "error",
]


def _row_for_csv(rec):
    a = rec.get("annotation") or {}
    doi = rec.get("doi")
    opus_t = a.get("type")
    # blank when unlabeled (refusal/error); else True iff the predicted type differs from current OpenAlex type
    is_changed = "" if not opus_t else (opus_t != rec.get("oa_type"))
    return {
        "openalex_id": rec.get("oa_id"),
        "doi": ("https://doi.org/" + doi) if doi else "",
        "landing_page_url": rec.get("lp_final_url") or rec.get("oa_landing") or "",
        "current_type": rec.get("oa_type"),
        "opus_type": opus_t,
        "is_changed": is_changed,
        "opus_confidence": a.get("confidence"),
        "opus_reason": a.get("reason"),
        "opus_is_broken": a.get("is_broken"),
        "lp_status": rec.get("lp_status"),
        "error": rec.get("error") or a.get("_error"),
    }


def _load_done(jsonl_path, require_annotation):
    """A DOI counts as done only if it has a successful annotation (when labeling). This lets a
    key-less enrich pass run first, and makes failed/unlabeled rows retry on the next run."""
    done = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    d = clean_doi(r.get("doi"))
                    if not d:
                        continue
                    if require_annotation:
                        ann = r.get("annotation") or {}
                        # Done if labeled, OR terminally refused (safety classifier) — refusals
                        # never succeed on retry, so skip them; the user hand-labels those.
                        # Transient errors (rate-limit / network / bad-json) stay un-done -> retried.
                        if ann.get("type") or ann.get("_error") == "refusal":
                            done.add(d)
                    else:
                        done.add(d)
                except Exception:
                    pass
    return done


def run(dois, *, out_prefix, mailto, workers=50, model="claude-opus-4-8", effort="medium",
        landing_check=True, resume=True, annotate=True, progress=True):
    """Process every DOI through enrich (+ optional annotate) concurrently. Returns the output paths."""
    jsonl_path, csv_path = out_prefix + ".jsonl", out_prefix + ".csv"
    done = _load_done(jsonl_path, require_annotation=annotate) if resume else set()
    todo = [d for d in ({clean_doi(x) for x in dois}) if d and d not in done]
    if progress:
        print(f"[worktype] {len(dois)} input DOIs | {len(done)} already done | {len(todo)} to process "
              f"| {workers} workers | annotate={annotate}", file=sys.stderr)

    annotator = Annotator(make_client_for(model), model=model, effort=effort) if annotate else None
    write_lock = threading.Lock()
    jf = open(jsonl_path, "a")
    counter = {"n": 0, "broken": 0, "err": 0}
    usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}

    def process(doi):
        rec = enrich(doi, mailto, landing_check=landing_check)
        if annotate and not rec.get("error"):
            rec["annotation"] = annotator.annotate(signals_for_annotation(rec))
        return rec

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process, d): d for d in todo}
            for fut in as_completed(futs):
                doi = futs[fut]
                try:
                    rec = fut.result()
                except Exception as e:
                    rec = {"doi": doi, "error": f"pipeline:{type(e).__name__}:{e}"}
                with write_lock:
                    jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    jf.flush()
                    counter["n"] += 1
                    a = rec.get("annotation") or {}
                    if a.get("is_broken"):
                        counter["broken"] += 1
                    if rec.get("error") or a.get("_error"):
                        counter["err"] += 1
                    for k, v in (a.get("_usage") or {}).items():
                        usage[k] += v
                    if progress and counter["n"] % 25 == 0:
                        print(f"[worktype]   {counter['n']}/{len(todo)} done "
                              f"({counter['broken']} broken, {counter['err']} errors)", file=sys.stderr)
    finally:
        jf.close()

    _rewrite_csv(jsonl_path, csv_path)
    if progress:
        print(f"[worktype] wrote {jsonl_path} and {csv_path}", file=sys.stderr)
        if annotate and counter["n"]:
            _print_cost(usage, counter["n"], model)
    return jsonl_path, csv_path


# Opus 4.8 per-MTok rates ($): input, output, cache-read, cache-write(5m).
_RATES = {"claude-opus-4-8": (5.0, 25.0, 0.50, 6.25)}


def _print_cost(usage, n, model):
    ri, ro, rcr, rcw = _RATES.get(model, _RATES["claude-opus-4-8"])
    cost = (usage["in"] * ri + usage["out"] * ro + usage["cache_read"] * rcr + usage["cache_write"] * rcw) / 1e6
    print(f"[worktype] tokens: in={usage['in']:,} out={usage['out']:,} "
          f"cache_read={usage['cache_read']:,} cache_write={usage['cache_write']:,}", file=sys.stderr)
    print(f"[worktype] cost: ${cost:.2f} for {n} works  (${cost/n:.4f}/work  ->  "
          f"~${cost/n*100_000:,.0f} per 100k; ~${cost/n*50_000:,.0f} via Batches API)", file=sys.stderr)


def _rewrite_csv(jsonl_path, csv_path):
    # Dedup by DOI, last (most complete) record wins — handles enrich-then-label reruns.
    latest = {}
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                latest[clean_doi(r.get("doi"))] = r
    with open(csv_path, "w", newline="") as out:
        w = csv.DictWriter(out, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in latest.values():
            w.writerow(_row_for_csv(r))


def make_client_for(model):
    # Imported lazily so `--no-annotate` / enrichment-only runs don't require the anthropic package or a key.
    from .annotate import make_client
    return make_client()
