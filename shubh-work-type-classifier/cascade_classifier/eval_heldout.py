"""I10 validation harness: score the cascade on the de-leaked gold_full_52k held-out.

Eval set = the feature-enriched .jsonl union MINUS the #544 train/val/test split ids (so the
residual tree is not leaked). Reports per-type precision/recall/F1 + the article guardrail, for
the current cascade with the dc.type map toggled (baseline / full / no-article variant).

Run: python -m cascade_classifier.eval_heldout
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from .data import DATA_DIR
from .splits import SPLIT_DIR
from . import cascade, dctype_map
from . import tree as treemod
from .splits import split_data

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "classifier"))
from typeclf.dataset import _clean_doi, _norm_oaid  # noqa: E402

JSONLS = ["gold_master.jsonl", "gold_random_10k.jsonl", "gold_random_s7_10k.jsonl",
          "gold_random_s8_10k.jsonl", "gold_random_s9_10k.jsonl",
          "gold_stratified.jsonl", "gold_targeted.jsonl"]
WATCH = ["article", "editorial", "book-review", "review", "dissertation", "conference-abstract",
         "retraction", "erratum", "book-chapter", "conference-paper", "dataset", "preprint",
         "data-paper", "paratext"]


def _split_ids():
    out = set()
    for k in ("train", "val", "test"):
        p = os.path.join(SPLIT_DIR, f"{k}.txt")
        out |= set(l.strip() for l in open(p) if l.strip())
    return out


def load_heldout():
    split = _split_ids()
    seen, recs, labs = {}, [], []
    for j in JSONLS:
        fp = os.path.join(DATA_DIR, j)
        if not os.path.exists(fp):
            continue
        for line in open(fp):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            lab = (r.get("annotation") or {}).get("type")
            if not lab:
                continue
            k = _clean_doi(r.get("doi")) or _norm_oaid(r.get("oa_id"))
            if not k or k in split:
                continue
            seen[k] = (r, lab)
    for r, lab in seen.values():
        recs.append(r)
        labs.append(lab)
    return recs, labs


def score(labs, pred):
    from sklearn.metrics import precision_recall_fscore_support, accuracy_score
    acc = accuracy_score(labs, pred)
    P, R, F, S = precision_recall_fscore_support(labs, pred, labels=WATCH, zero_division=0)
    return acc, {t: (s, p, r, f) for t, s, p, r, f in zip(WATCH, S, P, R, F)}


def _row(name, acc, m, base=None):
    print(f"\n=== {name} === acc={acc:.4f}" + (f"  (Δ {acc-base:+.4f})" if base is not None else ""))
    print(f"  {'type':20s} {'n':>5} {'P':>6} {'R':>6} {'F1':>6}")
    for t in WATCH:
        s, p, r, f = m[t]
        print(f"  {t:20s} {s:5d} {p:6.3f} {r:6.3f} {f:6.3f}")


def main():
    recs, labs = load_heldout()
    print(f"held-out (de-leaked): {len(recs)} works")
    d = split_data(("train",))
    t = treemod.train_residual_tree(d["train"][0], d["train"][1])
    full = dict(dctype_map.DCTYPE_MAP)
    noart = {k: v for k, v in full.items() if v != "article"}

    results = {}
    for name, m in [("baseline (no dc.type)", {}), ("full dc.type map", full),
                    ("dc.type no-article", noart)]:
        dctype_map.DCTYPE_MAP = m
        pc, rules = cascade.predict(recs)
        ph, _ = treemod.hybrid_predict(recs, t)
        results[name] = (score(labs, pc), score(labs, ph), rules)

    base_c = results["baseline (no dc.type)"][0][0]
    base_h = results["baseline (no dc.type)"][1][0]
    for name in results:
        (ca, cm), (ha, hm), rules = results[name]
        _row(f"{name} — cascade-only", ca, cm, base_c)
        _row(f"{name} — hybrid", ha, hm, base_h)

    # dc.type rule precision on held-out (full map, cascade)
    dctype_map.DCTYPE_MAP = full
    pc, rules = cascade.predict(recs)
    idx = [i for i, rn in enumerate(rules) if rn == "dc.type:map"]
    prec = sum(1 for i in idx if pc[i] == labs[i]) / max(1, len(idx))
    print(f"\ndc.type:map rule — fires {len(idx)}, precision {prec:.3f}")


if __name__ == "__main__":
    main()
