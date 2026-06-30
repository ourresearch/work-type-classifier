"""Evaluate the classifier: held-out + CV metrics, per-type beta/alpha, hotspot confusion,
confidence/coverage curve, external validation, and human-set agreement.

    python -m typeclf.evaluate                 # both scopes, full report
    python -m typeclf.evaluate --features full
    python -m typeclf.evaluate --no-cv --report report.md

Per-type **precision = 1 - beta** (false-classification) and **recall = 1 - alpha**
(missing-assignment), in the language of Maisano et al. (2025).
"""
from __future__ import annotations

import argparse
import io
import sys
from collections import Counter

from .dataset import TRAIN_JSONL, VAL_JSONL, load_gold, load_human
from .train import build_pipeline

HOTSPOTS = ["article", "review", "conference-paper", "conference-abstract",
            "editorial", "letter", "paratext", "book-chapter"]


def _stratified_split(rows, labels, meta, test_frac=0.2, seed=42):
    """Stratified split that tolerates singleton classes (they go entirely to train)."""
    from sklearn.model_selection import train_test_split
    import numpy as np

    counts = Counter(labels)
    idx = list(range(len(labels)))
    strat_idx = [i for i in idx if counts[labels[i]] >= 2]
    solo_idx = [i for i in idx if counts[labels[i]] < 2]
    y_strat = [labels[i] for i in strat_idx]
    tr, te = train_test_split(strat_idx, test_size=test_frac, random_state=seed, stratify=y_strat)
    tr = tr + solo_idx  # singletons can't be split — keep them in train
    pick = lambda src, ids: [src[i] for i in ids]
    return (pick(rows, tr), pick(labels, tr), pick(meta, tr),
            pick(rows, te), pick(labels, te), pick(meta, te))


def _print(out, *a):
    print(*a)
    print(*a, file=out)


def evaluate_scope(scope, model, do_cv, out_md):
    import numpy as np
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    buf = io.StringIO()
    _print(buf, f"\n{'='*72}\n  SCOPE = {scope.upper()}   model = {model}\n{'='*72}")

    rows, labels, meta = load_gold(TRAIN_JSONL, scope=scope)
    _print(buf, f"gold works: {len(rows)} | types: {len(set(labels))}")

    Xtr, ytr, mtr, Xte, yte, mte = _stratified_split(rows, labels, meta)
    pipe = build_pipeline(scope, model, C=4.0)
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)

    acc = accuracy_score(yte, pred)
    macro = f1_score(yte, pred, average="macro", zero_division=0)
    # Baseline: keep OpenAlex's current type (the thing we audit). Measures lift.
    base_pred = [m["oa_type"] or "article" for m in mte]
    base_acc = accuracy_score(yte, base_pred)
    _print(buf, f"\nHELD-OUT (20% = {len(yte)} works)")
    _print(buf, f"  accuracy   : {acc:.3f}   (baseline 'keep oa_type': {base_acc:.3f})")
    _print(buf, f"  macro-F1   : {macro:.3f}")

    _print(buf, "\nPER-TYPE (precision = 1-beta, recall = 1-alpha; support from held-out):")
    rep = classification_report(yte, pred, zero_division=0, digits=3)
    _print(buf, rep)
    # Flag under-supported tail types
    sup = Counter(yte)
    thin = sorted([t for t, c in sup.items() if c < 10])
    if thin:
        _print(buf, f"  ⚠ thin support (<10 held-out): {', '.join(thin)} — metrics unstable, "
                    f"need targeted labeling.")

    # Hotspot confusion (rows=true, cols=pred)
    present = [t for t in HOTSPOTS if t in set(yte) | set(pred)]
    cm = confusion_matrix(yte, pred, labels=present)
    _print(buf, "\nHOTSPOT CONFUSION (row=true, col=pred):")
    head = "true\\pred".ljust(20) + "".join(t[:9].rjust(10) for t in present)
    _print(buf, head)
    for i, t in enumerate(present):
        _print(buf, t.ljust(20) + "".join(str(cm[i][j]).rjust(10) for j in range(len(present))))

    # Confidence / coverage curve (needs predict_proba)
    if hasattr(pipe, "predict_proba"):
        proba = pipe.predict_proba(Xte)
        conf = proba.max(axis=1)
        order = np.argsort(-conf)
        correct = (np.array(pred) == np.array(yte)).astype(int)
        _print(buf, "\nCONFIDENCE / COVERAGE (threshold on max class prob):")
        _print(buf, "  thresh   coverage   accuracy@covered")
        for th in (0.0, 0.5, 0.7, 0.8, 0.9, 0.95):
            keep = conf >= th
            cov = keep.mean()
            a = correct[keep].mean() if keep.any() else float("nan")
            _print(buf, f"  {th:>5.2f}   {cov:>7.1%}   {a:>10.3f}")

    # 5-fold CV macro-F1 on the full gold (heaviest step)
    if do_cv:
        from sklearn.model_selection import cross_val_score
        cv_pipe = build_pipeline(scope, model, C=4.0)
        scores = cross_val_score(cv_pipe, rows, labels, cv=5,
                                 scoring="f1_macro", n_jobs=1)
        _print(buf, f"\n5-FOLD CV macro-F1: {scores.mean():.3f} ± {scores.std():.3f}")

    # External validation on sample1000 (drop any DOI overlap with the training pool)
    val_rows, val_labels, val_meta = load_gold([VAL_JSONL], scope=scope)
    train_dois = {m["doi"] for m in meta if m["doi"]}
    keep = [i for i, m in enumerate(val_meta) if m["doi"] not in train_dois]
    if keep:
        full_pipe = build_pipeline(scope, model, C=4.0).fit(rows, labels)
        vr = [val_rows[i] for i in keep]; vy = [val_labels[i] for i in keep]
        vp = full_pipe.predict(vr)
        _print(buf, f"\nEXTERNAL VAL sample1000 ({len(vr)} non-overlapping works, model fit on all gold):")
        _print(buf, f"  accuracy : {accuracy_score(vy, vp):.3f} | macro-F1 : "
                    f"{f1_score(vy, vp, average='macro', zero_division=0):.3f}")
    else:
        full_pipe = build_pipeline(scope, model, C=4.0).fit(rows, labels)

    # Secondary human-set agreement: join the human labels to gold feature rows by DOI/OA id.
    by_doi, by_oaid = load_human()
    h_rows, h_true = [], []
    canon = set(labels)
    unmappable = 0
    matched = 0
    for r, m in zip(rows, meta):
        hl = by_doi.get(m["doi"]) or by_oaid.get(m["oa_id"])
        if not hl:
            continue
        matched += 1
        if hl not in canon:
            unmappable += 1
            continue
        h_rows.append(r); h_true.append(hl)
    if h_rows:
        hp = full_pipe.predict(h_rows)
        agree = accuracy_score(h_true, hp)
        _print(buf, f"\nHUMAN-SET AGREEMENT (secondary check; pre-#535 vocab mapped):")
        _print(buf, f"  joined {matched} human rows to gold features | {len(h_rows)} mappable "
                    f"| {unmappable} unmappable labels")
        _print(buf, f"  model-vs-human accuracy : {agree:.3f}")
    else:
        _print(buf, "\nHUMAN-SET AGREEMENT: no human rows joined to gold features "
                    "(human set may not overlap the gold sample).")

    if out_md is not None:
        out_md.write(buf.getvalue())
    return {"scope": scope, "heldout_acc": acc, "heldout_macro_f1": macro, "baseline_acc": base_acc}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="typeclf.evaluate", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", choices=["full", "metadata", "both"], default="both")
    ap.add_argument("--model", choices=["logreg", "linsvc"], default="logreg")
    ap.add_argument("--no-cv", action="store_true", help="skip 5-fold CV (faster)")
    ap.add_argument("--report", default=None, help="also write the full text report to this file")
    args = ap.parse_args(argv)

    scopes = ["full", "metadata"] if args.features == "both" else [args.features]
    out_md = open(args.report, "w") if args.report else None
    if out_md:
        out_md.write("# typeclf evaluation report\n\n```\n")
    summary = [evaluate_scope(s, args.model, not args.no_cv, out_md) for s in scopes]
    if out_md:
        out_md.write("\n```\n")
        out_md.close()

    print("\n" + "=" * 72)
    print("SUMMARY (held-out):")
    for s in summary:
        print(f"  {s['scope']:9s}  acc={s['heldout_acc']:.3f}  macro-F1={s['heldout_macro_f1']:.3f}  "
              f"(baseline keep-oa_type acc={s['baseline_acc']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
