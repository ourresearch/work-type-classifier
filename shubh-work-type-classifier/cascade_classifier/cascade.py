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
from . import dctype_map

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


# --- I8: single-type source allowlists (oxjob #547 + preprint_servers). Each measured on the
# held-out gold_master: name-match precision preprint .995 / dataset 1.00 / conf-paper .965 /
# conf-abstract .953 (+ preprint DOI-prefix .985). These venues publish essentially one type. ---


@rule("preprint:source_list")
def _r1b(f):
    return "preprint" if f["src_preprint_list"] else None


@rule("dataset:source_list")
def _r1c(f):
    return "dataset" if f["src_dataset_list"] else None


@rule("data-paper:source_list")
def _r1d(f):
    return "data-paper" if f["src_datapaper_list"] else None


@rule("conference-abstract:source_list")
def _r1e(f):
    return "conference-abstract" if f["src_confabs_list"] else None


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


@rule("conference-paper:source_list")
def _r4b(f):
    # named proceedings venues the `proceedings` regex misses (e.g. LNCS, CCIS). Same abstract
    # split as the proceedings rule: a single-page, ref-less, abstract-only record is an abstract.
    if f["src_confpaper_list"]:
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


@rule("dc.type:map")
def _r8c(f):
    # I10: landing-page dc.type (taxicab tx_meta) -> type, ported from #545 (>=93% precision).
    # Stage 3: after trusted Crossref + source allowlists, before the weaker title regexes
    # (dc.type=retraction 99% beats the title 'retraction' regex). Fires only when dc.type present.
    return dctype_map.DCTYPE_MAP.get(f["dc_type"]) if f["dc_type"] else None


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


@rule("review:phrase+refs")
def _r14(f):
    # I11: the bare refs>=150 gate measured only 0.571 precision on the 40.6k held-out (long
    # original-research articles have 150+ refs too). Replaced with a guarded conjunction: an
    # explicit review-methodology phrase (title or landing-page title) + a substantial ref count
    # + abstract, with a case-report block. Measured 1.00 precision (n=27) on the held-out.
    if (f["ti_review_phrase"] and not f["ti_case_report"]
            and f["n_refs"] >= 100 and f["has_abstract"] and not f["venue_proceedings"]):
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
