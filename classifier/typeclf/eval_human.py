"""Independent check: enrich the 166 human-labeled DOIs (reusing ../labeler's enrich) and
compare a trained model's predictions against the human labels.

The human set doesn't overlap the gold sample and the CSV lacks enrichment features, so we
fetch features here (network). Results are cached to data/human_enriched.jsonl so re-runs
are offline and reproducible.

    python -m typeclf.eval_human --model models/full.joblib            # enrich + score
    python -m typeclf.eval_human --model models/meta.joblib --no-fetch # use cache only
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .dataset import DATA_DIR, HUMAN_CSV, _clean_doi, _map_human_label, _norm_oaid
from .features import record_to_row
from .predict import load_model

CACHE = os.path.join(DATA_DIR, "human_enriched.jsonl")


def _import_enrich():
    """Reuse the labeler's enrich() without installing it (sibling package on disk)."""
    labeler_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "labeler"))
    if labeler_dir not in sys.path:
        sys.path.insert(0, labeler_dir)
    from worktype.enrich import enrich  # type: ignore
    return enrich


def _read_human_rows():
    rows = []
    with open(os.path.join(DATA_DIR, HUMAN_CSV), newline="") as f:
        for r in csv.DictReader(f):
            label = (r.get("annotated_type") or r.get("predicted_new_type") or "").strip()
            doi = _clean_doi(r.get("doi"))
            if label and doi:
                rows.append({"doi": doi, "oa_id": _norm_oaid(r.get("openalex_id")),
                             "human": _map_human_label(label)})
    return rows


def _load_cache():
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    cache[_clean_doi(rec.get("doi"))] = rec
    return cache


def _fetch_missing(human, cache, mailto, workers, landing_check):
    enrich = _import_enrich()
    todo = [h["doi"] for h in human if h["doi"] not in cache]
    if not todo:
        return cache
    print(f"[eval_human] enriching {len(todo)} human DOIs ({workers} workers)…", file=sys.stderr)
    with open(CACHE, "a") as out, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(enrich, d, mailto, landing_check=landing_check): d for d in todo}
        done = 0
        for fut in as_completed(futs):
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"doi": futs[fut], "error": f"{type(e).__name__}:{e}"}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            cache[_clean_doi(rec.get("doi"))] = rec
            done += 1
            if done % 25 == 0:
                print(f"[eval_human]   {done}/{len(todo)}", file=sys.stderr)
    return cache


def main(argv=None):
    ap = argparse.ArgumentParser(prog="typeclf.eval_human", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--no-fetch", action="store_true", help="use only the cache, don't hit the network")
    ap.add_argument("--mailto", default="rohan.mantena@gmail.com")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--no-landing-check", action="store_true")
    args = ap.parse_args(argv)

    from sklearn.metrics import accuracy_score, f1_score

    pipe, scope = load_model(args.model)
    human = _read_human_rows()
    cache = _load_cache()
    if not args.no_fetch:
        cache = _fetch_missing(human, cache, args.mailto, args.workers, not args.no_landing_check)

    rows, y_true, missing = [], [], 0
    canon = set(getattr(pipe, "classes_", []))
    unmappable = 0
    for h in human:
        rec = cache.get(h["doi"])
        if not rec or rec.get("error"):
            missing += 1
            continue
        if h["human"] not in canon:
            unmappable += 1
            continue
        rows.append(record_to_row(rec, scope=scope))
        y_true.append(h["human"])

    if not rows:
        print("[eval_human] no scorable rows (run without --no-fetch first to populate the cache)",
              file=sys.stderr)
        return 1
    pred = pipe.predict(rows)
    acc = accuracy_score(y_true, pred)
    macro = f1_score(y_true, pred, average="macro", zero_division=0)
    print(f"\n[eval_human] model={os.path.basename(args.model)} scope={scope}")
    print(f"  human rows: {len(human)} | scored: {len(rows)} | "
          f"unenriched/failed: {missing} | unmappable label: {unmappable}")
    print(f"  model-vs-human accuracy : {acc:.3f}")
    print(f"  model-vs-human macro-F1 : {macro:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
