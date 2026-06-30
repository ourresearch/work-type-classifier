"""Feature discovery (oxjob #909, iteration I2): which 3-4 factors separate each type from
`article`? Uses an unpenalized multinomial logit (statsmodels MNLogit) for honest coefficients/
p-values + a shallow tree for global importance. DISCOVERY ONLY — not the production model.

De-leaked: features exclude oa_type/oa_is_paratext by construction (see features.py).
"""
from __future__ import annotations

import warnings

import numpy as np

from .features import record_to_features, to_matrix

# separation guard: |coef| above this is a quasi-separated dummy (uninterpretable SE) -> hide
_SEP = 6.0

# Curated, well-identified subset for the HONEST logit. Excludes the near-deterministic crt_*
# dummies (cr_subtype_preprint, crt_proceedings, crt_dataset, crt_peer_review, ...): they cause
# quasi-separation (singular covariance) and are better expressed as cascade rules. Continuous
# features (n_refs, title_len) are standardized so odds are per-SD and comparable.
DISCOVERY_FEATURES = [
    "single_page", "n_refs", "has_abstract", "has_isbn", "container_present",
    "venue_proceedings", "venue_preprint", "refs_ge_150", "title_len", "src_repository",
    "ti_editorial", "ti_letter", "ti_book_review", "ti_review_word",
]
_CONTINUOUS = {"n_refs", "title_len"}


def _discovery_matrix(records):
    rows = [record_to_features(r) for r in records]
    X = np.asarray([[row[n] for n in DISCOVERY_FEATURES] for row in rows], dtype=float)
    # standardize the continuous columns (z-score) for conditioning + per-SD odds
    for j, name in enumerate(DISCOVERY_FEATURES):
        if name in _CONTINUOUS:
            mu, sd = X[:, j].mean(), X[:, j].std() or 1.0
            X[:, j] = (X[:, j] - mu) / sd
    return X, list(DISCOVERY_FEATURES)


def mnlogit_signals(records, labels, base="article", top_k=4,
                    focus=("paratext", "review", "editorial", "conference-paper", "preprint", "letter")):
    """Per-class BINARY logit (class vs article). One-vs-article is far more stable than a joint
    23-class MNLogit (which won't converge with rare classes) and is exactly the team's framing.
    Drops near-constant columns within each pair and skips separation artifacts (|coef|>=_SEP)."""
    import statsmodels.api as sm

    Xall, names = _discovery_matrix(records)
    labels = list(labels)
    out, pseudo_r2 = {}, {}
    for cls in focus:
        idx = [i for i, l in enumerate(labels) if l in (base, cls)]
        if len(idx) < 30 or sum(labels[i] == cls for i in idx) < 10:
            continue
        Xp = Xall[idx]
        y = np.array([1.0 if labels[i] == cls else 0.0 for i in idx])
        # keep only columns with variance in this pair (avoids perfect separation / singularity)
        keep = [j for j in range(Xp.shape[1]) if Xp[:, j].std() > 1e-9]
        Xk, kn = Xp[:, keep], [names[j] for j in keep]
        Xc = sm.add_constant(Xk, has_constant="add")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = sm.Logit(y, Xc).fit(method="newton", maxiter=100, disp=0)
            params, tvals, pvals = res.params, res.tvalues, res.pvalues
            llf, llnull = res.llf, res.llnull
        except Exception:
            continue
        rows = []
        for k, fname in enumerate(["const"] + kn):
            if fname == "const":
                continue
            coef, z, p = params[k], tvals[k], pvals[k]
            if not np.isfinite(coef) or abs(coef) >= _SEP:
                continue
            rows.append((fname, float(coef), float(z), float(p), float(np.exp(coef))))
        rows.sort(key=lambda r: -abs(r[2]))
        out[cls] = rows[:top_k]
        pseudo_r2[cls] = (1 - llf / llnull) if llnull else None
    return out, pseudo_r2, None


def format_signals(sig: dict, pseudo_r2=None,
                   focus=("paratext", "review", "editorial", "conference-paper", "preprint", "letter")):
    lines = []
    pseudo_r2 = pseudo_r2 or {}
    for cls in focus:
        if cls not in sig:
            continue
        r2 = pseudo_r2.get(cls)
        r2s = f"  [McFadden pseudo-R²={r2:.2f}]" if r2 is not None else ""
        lines.append(f"\n{cls} vs article (top factors by |z|, separation-stable):{r2s}")
        lines.append(f"  {'factor':22s} {'coef':>7s} {'z':>7s} {'p':>10s} {'odds':>8s}")
        for fname, coef, z, p, odds in sig[cls]:
            lines.append(f"  {fname:22s} {coef:7.2f} {z:7.2f} {p:10.1e} {odds:8.2f}")
    return "\n".join(lines)


def tree_importances(records, labels, max_depth=5, top=15):
    from sklearn.tree import DecisionTreeClassifier
    X, names = to_matrix(records)
    clf = DecisionTreeClassifier(max_depth=max_depth, class_weight="balanced", random_state=909)
    clf.fit(X, labels)
    imp = sorted(zip(names, clf.feature_importances_), key=lambda t: -t[1])
    return imp[:top], clf
