"""Deterministic rule cascade (oxjob #544, iteration I3+).

Pure function over the engineered feature dict (features.record_to_features), so it is exactly
expressible in SQL CASE / PySpark. Ordered most-specific -> least. Returns (label, rule_name);
label is None when nothing fires (the article-boundary residual that the I4 tree handles).

Rule order & thresholds are grounded in measured purity on the gold set:
  cr_subtype=preprint -> preprint (99%)   proceedings-article -> conference (92%)
  ISBN -> book-family (65% chapter; split by crt)   repository -> preprint|dataset (needs crt)
  refs>=150 + abstract -> review (86% precision; 40 was far too low at 16%)
"""
from __future__ import annotations

from .features import record_to_features

# ordered list of (rule_name, predicate(f) -> label or None)
RULES = []


def rule(name):
    def deco(fn):
        RULES.append((name, fn))
        return fn
    return deco


@rule("preprint:cr_subtype")
def _r1(f):
    return "preprint" if f["cr_subtype_preprint"] else None


# NOTE: a `crt_posted_content -> preprint` rule (val precision 0.38) and a `crt_dataset -> dataset`
# rule (0.46) were tried and REMOVED — they locked in errors; demoting dataset/repo-preprint to the
# residual tree lifted macro-F1 0.498 -> 0.523 at no cost to accuracy or article precision (see I3).


@rule("conference:proceedings")
def _r4(f):
    if f["crt_proceedings"] or (f["venue_proceedings"] and f["src_conference"]):
        # split off abstract-only proceedings records
        if f["single_page"] and f["n_refs"] == 0 and not f["has_abstract"]:
            return "conference-abstract"
        return "conference-paper"
    return None


@rule("reference-entry:crt")
def _r5(f):
    return "reference-entry" if f["crt_reference_entry"] else None


@rule("book:whole")
def _r6(f):
    return "book" if f["crt_book"] else None


@rule("book-family:isbn")
def _r7(f):
    if f["crt_book_chapter"]:
        return "book-chapter"
    if f["has_isbn"]:
        # front/back matter inside a book: short, no abstract, no refs
        if f["single_page"] and not f["has_abstract"] and f["n_refs"] == 0:
            return "paratext"
        return "book-chapter"  # ISBN default is chapter (65% on gold)
    return None


@rule("peer-review:crt")
def _r8(f):
    return "peer-review" if f["crt_peer_review"] else None


@rule("paratext:title_or_issue")
def _r8b(f):
    # paratext = front/back matter, mastheads, whole-issue records. Two high-precision signals
    # (I6+I7, derived/validated vs the openalex-guts detective): the anchored title vocabulary
    # (ti_paratext) OR a container-level Crossref type (journal-issue/journal-volume). Combined:
    # 0.99 precision / 0.57 recall on gold — the cr_type signal breaks the title-vocabulary ceiling.
    return "paratext" if (f["ti_paratext"] or f["crt_issue"]) else None


@rule("title:retraction")
def _r9(f):
    return "retraction" if f["ti_retraction"] else None


@rule("title:erratum")
def _r10(f):
    return "erratum" if f["ti_erratum"] else None


@rule("title:book-review")
def _r11(f):
    return "book-review" if f["ti_book_review"] else None


@rule("title:editorial")
def _r12(f):
    return "editorial" if f["ti_editorial"] else None


@rule("title:letter")
def _r13(f):
    return "letter" if f["ti_letter"] else None


@rule("review:high-refs")
def _r14(f):
    # high-precision review gate: refs>=150 + has abstract + not a proceedings venue
    if f["refs_ge_150"] and f["has_abstract"] and not f["venue_proceedings"]:
        return "review"
    return None


def classify(f: dict):
    """Run the cascade over one feature dict. Returns (label_or_None, rule_name_or_None)."""
    for name, fn in RULES:
        out = fn(f)
        if out is not None:
            return out, name
    return None, None


def classify_record(rec: dict):
    return classify(record_to_features(rec))


def predict(records, default="article"):
    """Cascade-only prediction (residual -> `default`). Returns (labels, rules_fired)."""
    labels, rules = [], []
    for r in records:
        lab, name = classify_record(r)
        labels.append(lab if lab is not None else default)
        rules.append(name)
    return labels, rules
