"""Depth-limited decision tree for the article-boundary residual (oxjob #909, iteration I4).

The cascade resolves the clean types; whatever it leaves (label None — mostly article vs
editorial/review/letter/conference-abstract) goes to a shallow, interpretable tree over the
same engineered features. Hybrid = cascade -> tree. Kept shallow (depth<=6, min_samples_leaf)
so feature_count << samples and the tree is human-readable (export_text).
"""
from __future__ import annotations

import numpy as np

from .cascade import classify_record
from .features import FEATURE_NAMES, record_to_features


def _residual_mask(records):
    """True where the cascade does NOT fire (the tree's responsibility)."""
    return np.array([classify_record(r)[0] is None for r in records])


def _matrix(records):
    rows = [record_to_features(r) for r in records]
    return np.asarray([[row[n] for n in FEATURE_NAMES] for row in rows], dtype=float)


def train_residual_tree(records, labels, max_depth=6, min_samples_leaf=20, seed=909):
    from sklearn.tree import DecisionTreeClassifier
    mask = _residual_mask(records)
    Xr = _matrix([r for r, m in zip(records, mask) if m])
    yr = [l for l, m in zip(labels, mask) if m]
    # NO class_weight: the residual is ~70% genuine article, so balancing would shred the
    # majority class (article recall collapses, accuracy tanks). Natural weighting keeps
    # article precision high while still picking off the clear editorial/review/paratext cases.
    clf = DecisionTreeClassifier(max_depth=max_depth, min_samples_leaf=min_samples_leaf,
                                 random_state=seed)
    clf.fit(Xr, yr)
    return clf


def hybrid_predict(records, tree, default="article"):
    """Cascade first; residual -> tree. Returns (labels, source) where source in {rule,tree}."""
    labels, source = [], []
    residual_recs, residual_idx = [], []
    for i, r in enumerate(records):
        lab, _ = classify_record(r)
        if lab is not None:
            labels.append(lab); source.append("rule")
        else:
            labels.append(None); source.append("tree")
            residual_recs.append(r); residual_idx.append(i)
    if residual_recs:
        Xr = _matrix(residual_recs)
        preds = tree.predict(Xr)
        for i, p in zip(residual_idx, preds):
            labels[i] = p
    # safety: any leftover None -> default
    labels = [l if l is not None else default for l in labels]
    return labels, source


def export_tree_text(tree):
    from sklearn.tree import export_text
    return export_text(tree, feature_names=list(FEATURE_NAMES), max_depth=6)
