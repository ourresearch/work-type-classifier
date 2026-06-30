"""Train the work-type classifier and save it with joblib.

    python -m typeclf.train --features full     -o models/full.joblib
    python -m typeclf.train --features metadata  -o models/meta.joblib
    python -m typeclf.train --features full --model linsvc -o models/full_svm.joblib

Multinomial logistic regression over the WorkTypeFeaturizer, class_weight="balanced"
(the gold is severely imbalanced). `--model linsvc` swaps in a calibrated LinearSVC A/B.
"""
from __future__ import annotations

import argparse
import os
import sys

from .dataset import TRAIN_JSONL, load_gold
from .features import build_featurizer


def build_pipeline(scope: str, model: str, C: float):
    from sklearn.pipeline import Pipeline

    feat = build_featurizer(scope)
    if model == "logreg":
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression(
            C=C, class_weight="balanced", max_iter=2000, n_jobs=-1,
        )  # sklearn>=1.5 picks multinomial softmax automatically for multiclass
    elif model == "linsvc":
        # Plain LinearSVC A/B. No predict_proba (so no confidence/abstain curve) — calibrating
        # it would require ≥3 examples/class, which the tail types (e.g. software-paper=1) lack
        # without silently dropping classes. logreg is the primary precisely for that reason.
        from sklearn.svm import LinearSVC
        clf = LinearSVC(C=C, class_weight="balanced", max_iter=5000)
    else:
        raise ValueError(f"unknown model {model!r}")
    return Pipeline([("feat", feat), ("clf", clf)])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="typeclf.train", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", choices=["full", "metadata"], default="full",
                    help="feature scope (default: full)")
    ap.add_argument("--model", choices=["logreg", "linsvc"], default="logreg")
    ap.add_argument("-C", type=float, default=4.0, help="inverse regularization strength (default 4.0)")
    ap.add_argument("--train", nargs="+", default=TRAIN_JSONL,
                    help="gold JSONL files (default: gold_shard01 + gold_strat)")
    ap.add_argument("-o", "--out", default=None, help="output model path (default: models/<scope>.joblib)")
    args = ap.parse_args(argv)

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                                   f"{args.features}.joblib")
    out = os.path.normpath(out)

    rows, labels, _ = load_gold(args.train, scope=args.features)
    if not rows:
        print("[typeclf] no labeled training rows found — check data/ paths", file=sys.stderr)
        return 1
    print(f"[typeclf] training {args.model}/{args.features} on {len(rows)} works "
          f"({len(set(labels))} types)", file=sys.stderr)

    pipe = build_pipeline(args.features, args.model, args.C)
    pipe.fit(rows, labels)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    import joblib
    joblib.dump({"pipeline": pipe, "scope": args.features, "model": args.model,
                 "classes": list(pipe.classes_)}, out, compress=3)
    size_mb = os.path.getsize(out) / 1e6
    print(f"[typeclf] saved {out} ({size_mb:.1f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
