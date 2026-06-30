"""Standard reporting for oxjob #544: confusion matrix, the article-boundary scorecard,
train/val overfit gap, and an append-only JOURNAL logger.

The headline metric is NOT overall accuracy. It is macro-F1 + the article-boundary scorecard
(article precision/recall, and how much each neighbor type bleeds INTO article). Overall
accuracy is reported but secondary — per the team's "accuracy isn't enough" steer.
"""
from __future__ import annotations

import json
import os
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(_HERE, "JOURNAL.md")
ITERS = os.path.join(_HERE, "iters")

# the neighbors that historically leak into `article`
BLEED = ["editorial", "review", "letter", "paratext", "conference-paper", "conference-abstract"]


def scorecard(y_true, y_pred) -> dict:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    classes = sorted(set(y_true))
    acc = accuracy_score(y_true, y_pred)
    macro = f1_score(y_true, y_pred, average="macro", zero_division=0)

    art_p = precision_score(y_true, y_pred, labels=["article"], average="micro", zero_division=0)
    art_r = recall_score(y_true, y_pred, labels=["article"], average="micro", zero_division=0)

    # per-bleed-class: recall + how many true X were predicted `article`
    bleed = {}
    for c in BLEED:
        idx = [i for i, t in enumerate(y_true) if t == c]
        if not idx:
            continue
        rec = sum(1 for i in idx if y_pred[i] == c) / len(idx)
        to_article = sum(1 for i in idx if y_pred[i] == "article")
        bleed[c] = {"n": len(idx), "recall": round(rec, 3), "->article": to_article}
    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro, 4),
        "article_precision": round(float(art_p), 4),
        "article_recall": round(float(art_r), 4),
        "bleed": bleed,
    }


def format_scorecard(sc: dict, title: str = "") -> str:
    lines = []
    if title:
        lines.append(title)
    lines.append(f"  accuracy={sc['accuracy']:.3f}  macro-F1={sc['macro_f1']:.3f}  "
                 f"article P={sc['article_precision']:.3f} R={sc['article_recall']:.3f}")
    lines.append("  bleed INTO article (true type -> #predicted article | recall):")
    for c, d in sc["bleed"].items():
        lines.append(f"    {c:20s} n={d['n']:4d}  ->article={d['->article']:3d}  recall={d['recall']:.3f}")
    return "\n".join(lines)


def confusion_text(y_true, y_pred, classes=None, top=None) -> str:
    from sklearn.metrics import confusion_matrix
    if classes is None:
        classes = sorted(set(y_true) | set(y_pred), key=lambda c: -Counter(y_true)[c])
    if top:
        classes = classes[:top]
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    w = 9
    head = "true\\pred".ljust(20) + "".join(c[:w].rjust(w + 1) for c in classes)
    out = [head]
    for i, c in enumerate(classes):
        out.append(c.ljust(20) + "".join(str(cm[i][j]).rjust(w + 1) for j in range(len(classes))))
    return "\n".join(out)


def overfit_gap(model_predict, Xtr, ytr, Xva, yva) -> dict:
    """train vs val macro-F1 gap — a large positive gap flags overfitting."""
    from sklearn.metrics import f1_score
    tr = f1_score(ytr, model_predict(Xtr), average="macro", zero_division=0)
    va = f1_score(yva, model_predict(Xva), average="macro", zero_division=0)
    return {"train_macro_f1": round(tr, 4), "val_macro_f1": round(va, 4), "gap": round(tr - va, 4)}


def save_iter(iter_id: str, metrics: dict, artifacts: dict = None):
    os.makedirs(ITERS, exist_ok=True)
    with open(os.path.join(ITERS, f"{iter_id}_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    for name, text in (artifacts or {}).items():
        with open(os.path.join(ITERS, f"{iter_id}_{name}.txt"), "w") as f:
            f.write(text)


def log_journal(*, iter_id, date, hypothesis, change, split, scorecard_sc, gap=None,
                decision, learning, result_line=None):
    """Append one iteration entry to JOURNAL.md (autoresearch-style). `result_line` overrides
    the default scorecard line (used by discovery iterations that have no val score)."""
    gap_s = f" | train/val gap={gap['gap']:+.3f}" if gap else ""
    if result_line is None:
        result_line = (f"acc={scorecard_sc['accuracy']:.3f}, macro-F1={scorecard_sc['macro_f1']:.3f}, "
                       f"article P={scorecard_sc['article_precision']:.3f}/"
                       f"R={scorecard_sc['article_recall']:.3f}{gap_s}")
    entry = (
        f"### {iter_id} — {date}\n"
        f"- **Hypothesis:** {hypothesis}\n"
        f"- **Change:** {change}\n"
        f"- **Split:** {split}\n"
        f"- **Result:** {result_line}\n"
        f"- **Decision:** {decision}\n"
        f"- **Learning:** {learning}\n"
    )
    # Upsert by iter id: replace an existing "### <id> —" block so reruns stay idempotent
    # (the journal is append-only across DISTINCT iterations, not across reruns of the same one).
    text = ""
    if os.path.exists(JOURNAL):
        with open(JOURNAL) as f:
            text = f.read()
    marker = f"### {iter_id} — "
    if marker in text:
        head, rest = text.split(marker, 1)
        after = rest.split("\n### ", 1)
        tail = ("\n### " + after[1]) if len(after) > 1 else ""
        text = head + entry + tail
    else:
        text = text.rstrip() + "\n\n" + entry
    with open(JOURNAL, "w") as f:
        f.write(text)
    return entry
