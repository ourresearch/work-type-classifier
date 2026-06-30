"""Load gold JSONL (features + labels) and the human reference CSV; normalize join keys."""
from __future__ import annotations

import csv
import json
import os
import re

from .features import record_to_row

# repo layout: classifier/typeclf/dataset.py  ->  ../../data
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "data"))

# gold files were renamed upstream (2026-06-30): gold_shard01 -> gold_random_10k,
# gold_strat -> gold_stratified, sample1000 -> gold_random_1k.
TRAIN_JSONL = ["gold_random_10k.jsonl", "gold_stratified.jsonl"]
VAL_JSONL = "gold_random_1k.jsonl"
HUMAN_CSV = "human_annotated.csv"


def _clean_doi(doi: str) -> str:
    """Mirror of labeler/worktype/enrich.py:clean_doi — strip the doi.org prefix."""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip(), flags=re.I)


def _norm_oaid(oaid: str) -> str:
    """Bare OpenAlex id (W...), stripped of the URL prefix."""
    return re.sub(r"^https?://openalex\.org/", "", (oaid or "").strip(), flags=re.I)


def iter_jsonl(path: str):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_gold(paths, scope: str = "full"):
    """Read enrichment JSONL files -> (rows, labels, meta). Keeps only labeled rows.

    `label` is the Opus annotation type. `meta` carries doi/oa_id for joining/reporting.
    Deduplicates by DOI (last record wins), matching the labeler's own CSV-rewrite rule.
    """
    by_doi = {}
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(DATA_DIR, p)
        if not os.path.exists(full):
            continue
        for rec in iter_jsonl(full):
            ann = rec.get("annotation") or {}
            label = ann.get("type")
            if not label:
                continue  # unlabeled / refusal / error — not training material
            doi = _clean_doi(rec.get("doi"))
            by_doi[doi or rec.get("oa_id")] = (rec, label)

    rows, labels, meta = [], [], []
    for key, (rec, label) in by_doi.items():
        rows.append(record_to_row(rec, scope=scope))
        labels.append(label)
        meta.append({
            "doi": _clean_doi(rec.get("doi")),
            "oa_id": _norm_oaid(rec.get("oa_id")),
            "oa_type": rec.get("oa_type"),
        })
    return rows, labels, meta


def load_human(scope_irrelevant=None):
    """human_annotated.csv -> {join_key: human_label}. Keys are bare DOI and bare OA id.

    Maps a few obvious pre-#535 vocabulary differences/typos onto the canonical taxonomy;
    leaves anything unrecognized as-is (reported as 'unmappable' by the evaluator).
    """
    path = os.path.join(DATA_DIR, HUMAN_CSV)
    by_doi, by_oaid = {}, {}
    if not os.path.exists(path):
        return by_doi, by_oaid
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            label = (r.get("annotated_type") or r.get("predicted_new_type") or "").strip()
            if not label:
                continue
            label = _map_human_label(label)
            doi = _clean_doi(r.get("doi"))
            oaid = _norm_oaid(r.get("openalex_id"))
            if doi:
                by_doi[doi] = label
            if oaid:
                by_oaid[oaid] = label
    return by_doi, by_oaid


# pre-#535 vocab / common typos -> canonical type
_HUMAN_LABEL_MAP = {
    "article-commentary": "editorial",
    "research-article": "article",
    "research article": "article",
    "book chapter": "book-chapter",
    "bookchapter": "book-chapter",
    "conference paper": "conference-paper",
    "conference-proceedings": "conference-paper",
    "proceedings-article": "conference-paper",
    "conference abstract": "conference-abstract",
    "meeting-abstract": "conference-abstract",
    "abstract": "conference-abstract",
    "book review": "book-review",
    "bookreview": "book-review",
    "review-article": "review",
    "reference entry": "reference-entry",
    "reference-work-entry": "reference-entry",
    "encyclopedia-entry": "reference-entry",
    "peer review": "peer-review",
    "peer-review-report": "peer-review",
    "correction": "erratum",
    "corrigendum": "erratum",
    "preprints": "preprint",
    "data-set": "dataset",
    "supplementary-material": "supplementary-materials",
    "supplementary materials": "supplementary-materials",
    "front-matter": "paratext",
    "frontmatter": "paratext",
    "news": "other",
}


def _map_human_label(label: str) -> str:
    key = label.strip().lower()
    return _HUMAN_LABEL_MAP.get(key, key)
