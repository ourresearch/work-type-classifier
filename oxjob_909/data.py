"""Load the gold enrichment records (raw, for our own feature engineering) + labels + ids.

Reuses the labeler/typeclf DOI normalization but keeps the *raw* enrichment record (unlike
typeclf.dataset.load_gold, which pre-flattens to typeclf features). Dedup by DOI, last wins.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(_HERE, ".."))
DATA_DIR = os.path.join(REPO, "data")
GOLD = ["gold_shard01.jsonl", "gold_strat.jsonl"]

# reuse typeclf's normalizers (sibling package under classifier/)
sys.path.insert(0, os.path.join(REPO, "classifier"))
from typeclf.dataset import _clean_doi, _norm_oaid  # type: ignore  # noqa: E402


def load_gold(paths=GOLD):
    """Return (records, labels, ids). One record per labeled work, deduped by DOI."""
    by_key = {}
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
        if not os.path.exists(full):
            continue
        with open(full) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                label = (rec.get("annotation") or {}).get("type")
                if not label:
                    continue
                key = _clean_doi(rec.get("doi")) or _norm_oaid(rec.get("oa_id"))
                if key:
                    by_key[key] = (rec, label)
    records, labels, ids = [], [], []
    for key, (rec, label) in by_key.items():
        records.append(rec)
        labels.append(label)
        ids.append(key)
    return records, labels, ids
