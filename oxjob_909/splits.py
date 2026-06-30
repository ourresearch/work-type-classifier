"""Frozen, stratified 60/20/20 train/val/test split. The TEST set is locked — touched once.

Writes id lists to splits/{train,val,test}.txt the first time, then always reloads them so the
split never drifts across iterations. Iterate on val; only evaluate on test at the very end.
"""
from __future__ import annotations

import os
from collections import Counter

from .data import load_gold

_HERE = os.path.dirname(os.path.abspath(__file__))
SPLIT_DIR = os.path.join(_HERE, "splits")
SEED = 909


def _stratified_3way(ids, labels, seed=SEED):
    """60/20/20 stratified by label. Singleton classes go to train (can't be split)."""
    import random
    rng = random.Random(seed)
    by_label = {}
    for i, lab in zip(ids, labels):
        by_label.setdefault(lab, []).append(i)
    train, val, test = [], [], []
    for lab, members in by_label.items():
        members = sorted(members)
        rng.shuffle(members)
        n = len(members)
        if n < 3:
            train.extend(members)  # too few to split — keep in train
            continue
        n_test = max(1, round(n * 0.2))
        n_val = max(1, round(n * 0.2))
        test.extend(members[:n_test])
        val.extend(members[n_test:n_test + n_val])
        train.extend(members[n_test + n_val:])
    return set(train), set(val), set(test)


def _write(path, ids):
    with open(path, "w") as f:
        for i in sorted(ids):
            f.write(i + "\n")


def _read(path):
    with open(path) as f:
        return set(ln.strip() for ln in f if ln.strip())


def ensure_splits():
    """Create the frozen split files if missing; return (train, val, test) id sets."""
    paths = {k: os.path.join(SPLIT_DIR, f"{k}.txt") for k in ("train", "val", "test")}
    if all(os.path.exists(p) for p in paths.values()):
        return _read(paths["train"]), _read(paths["val"]), _read(paths["test"])
    os.makedirs(SPLIT_DIR, exist_ok=True)
    _, labels, ids = load_gold()
    train, val, test = _stratified_3way(ids, labels)
    for k, s in (("train", train), ("val", val), ("test", test)):
        _write(paths[k], s)
    return train, val, test


def split_data(which=("train", "val")):
    """Return dict {split: (records, labels, ids)} for the requested splits."""
    train, val, test = ensure_splits()
    members = {"train": train, "val": val, "test": test}
    records, labels, ids = load_gold()
    out = {}
    for w in which:
        want = members[w]
        idx = [i for i, _id in enumerate(ids) if _id in want]
        out[w] = ([records[i] for i in idx], [labels[i] for i in idx], [ids[i] for i in idx])
    return out


if __name__ == "__main__":
    tr, va, te = ensure_splits()
    print(f"train={len(tr)} val={len(va)} test={len(te)}  (seed={SEED})")
    d = split_data(("train", "val", "test"))
    for w in ("train", "val", "test"):
        print(f"  {w}: {len(d[w][1])} works, {len(set(d[w][1]))} types")
