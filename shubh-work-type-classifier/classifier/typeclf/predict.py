"""Score works with a trained model — no LLM, no network. The deployable inference path.

    python -m typeclf.predict --in works.jsonl --model models/full.joblib --out preds.csv

Input is enrichment JSONL (../labeler output, or `worktype --no-annotate`). For the
metadata-only model the records only need the OpenAlex-native fields, so you can feed a
plain OpenAlex works dump mapped to the `oa_*` field names. Output CSV columns:
`doi, openalex_id, current_type, predicted_type, confidence, changed`.
"""
from __future__ import annotations

import argparse
import csv
import sys

from .dataset import _clean_doi, _norm_oaid, iter_jsonl
from .features import record_to_row


def load_model(path):
    import joblib
    bundle = joblib.load(path)
    return bundle["pipeline"], bundle.get("scope", "full")


def predict_records(records, model_path, batch=2000):
    pipe, scope = load_model(model_path)
    has_proba = hasattr(pipe, "predict_proba")
    batch_rows, batch_meta = [], []

    def flush():
        if not batch_rows:
            return
        preds = pipe.predict(batch_rows)
        if has_proba:
            confs = pipe.predict_proba(batch_rows).max(axis=1)
        else:
            confs = [None] * len(batch_rows)
        for meta, p, c in zip(batch_meta, preds, confs):
            yield {
                "doi": meta["doi"],
                "openalex_id": meta["oa_id"],
                "current_type": meta["oa_type"] or "",
                "predicted_type": p,
                "confidence": (round(float(c), 4) if c is not None else ""),
                "changed": (p != meta["oa_type"]),
            }
        batch_rows.clear(); batch_meta.clear()

    for rec in records:
        batch_rows.append(record_to_row(rec, scope=scope))
        batch_meta.append({
            "doi": _clean_doi(rec.get("doi")),
            "oa_id": _norm_oaid(rec.get("oa_id")),
            "oa_type": rec.get("oa_type"),
        })
        if len(batch_rows) >= batch:
            yield from flush()
    yield from flush()


COLUMNS = ["doi", "openalex_id", "current_type", "predicted_type", "confidence", "changed"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="typeclf.predict", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, help="enrichment JSONL to score")
    ap.add_argument("--model", required=True, help="trained .joblib model")
    ap.add_argument("--out", required=True, help="output CSV path")
    args = ap.parse_args(argv)

    n = changed = 0
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in predict_records(iter_jsonl(args.inp), args.model):
            w.writerow(row)
            n += 1
            changed += bool(row["changed"])
    print(f"[typeclf] scored {n} works -> {args.out} ({changed} changed vs current type)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
