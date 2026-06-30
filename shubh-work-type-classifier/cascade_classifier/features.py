"""Engineered, NON-circular features for oxjob #544.

Deliberately excludes OpenAlex's own labels (`oa_type`, `oa_is_paratext`) — those are
circular (predicting the thing we audit). Raw Crossref `cr_type`/`cr_subtype` are KEPT: they
are the upstream signal OpenAlex flattens, and recovering types from them is the goal.

Every feature is numeric/boolean so the same matrix feeds statsmodels MNLogit (discovery) and
a sklearn DecisionTree (deployable). All are OpenAlex/Crossref-native — no landing-page fetch.
"""
from __future__ import annotations

import re

# --- regex vocab (anchored where possible to keep precision high) ---
_VENUE_PROC = re.compile(r"\b(proceedings|symposium|workshop|conference|congress|colloqui)", re.I)
_VENUE_PRE = re.compile(r"\b(ssrn|arxiv|biorxiv|medrxiv|chemrxiv|osf|research square|preprints?|zenodo|repository|hal-)\b", re.I)

_TI_EDITORIAL = re.compile(r"^(editorial|from the editor|in this issue|introduction\b|preface|foreword|guest editor)", re.I)
_TI_ERRATUM = re.compile(r"\b(erratum|corrigend(um|a)|publisher correction|correction to|author correction)\b", re.I)
_TI_RETRACTION = re.compile(r"\b(retraction|retracted article|notice of retraction|withdrawn|expression of concern)\b", re.I)
_TI_BOOK_REVIEW = re.compile(r"(^book review\b|^review of\b|\breviewed work\b|^reviews of books)", re.I)
# paratext = front/back matter, mastheads, whole-issue records. Tokens chosen by precision×support
# (info-gain, I6) and UNIONED with the OpenAlex production detective's paratext patterns (I7:
# ourresearch/openalex-guts detective/work_type_detective.py:looks_like_paratext), filtered to the
# #535 taxonomy (their obituary / notes-and-news -> `other`, excluded). 0.99 precision / 0.42 recall.
_TI_PARATEXT = re.compile(r"""(?ix)
    ^\s*( contents | table\ of\ contents | (front|back)\ ?matter | frontmatter |
      cover(\ (and|&)\ back\ matter)? | masthead | editorial\ board |
      contributors? | list\ of\ (contributors|abbreviations|contents|tables|figures|plates) |
      abbreviations | title\ page | issue\ (information|publication\ information|editorial\ masthead) |
      author\ guidelines | author\ index | (back|front|inside\ back|inside\ front|inside)\ cover |
      cover\ (image|picture) | frontispiece | graphical\ contents\ list | inhalt |
      calendar\ of\ events | short(er)?\ notices | pages\ de\ d[ée]but | editor'?s\ preface |
      call\ for\ papers | expediente | sumario | (í|i)ndice | impressum )\b
  | \bcover\ and\ back\ matter\b | \[(front\ cover|inside\ back\ cover[^\]]*|masthead)\]
  | ^\s*(subject\ |author\ |name\ )?index(es)?\s*$
  | ^\s*(volume|vol\.?|volumen)\s*\d+\b.*\b(issue|number|n(u|ú)mero|no\.?)\b
""")
_TI_LETTER = re.compile(r"\b(reply to|comment on|response to|letter to the editor|author'?s? reply|in response to|correspondence)\b", re.I)
_TI_REVIEW_WORD = re.compile(r"\breview\b", re.I)

# source_type values we expand into indicators (others fold into src_other)
_SRC_LEVELS = ["journal", "repository", "conference", "book series", "ebook platform"]

# Ordered numeric feature names — the design matrix columns (discovery + tree share these).
FEATURE_NAMES = [
    # structural
    "single_page", "n_refs", "refs_40_99", "refs_100_149", "refs_ge_150",
    "has_abstract", "title_len",
    # container
    "has_isbn", "container_present", "venue_proceedings", "venue_preprint",
    "src_journal", "src_repository", "src_conference", "src_book_series", "src_ebook", "src_other",
    # upstream Crossref votes (non-circular)
    "crt_proceedings", "crt_posted_content", "crt_book_chapter", "crt_reference_entry",
    "crt_dataset", "crt_peer_review", "crt_journal_article", "crt_book", "crt_issue",
    "cr_subtype_preprint",
    # title keyword flags
    "ti_editorial", "ti_erratum", "ti_retraction", "ti_book_review", "ti_letter", "ti_review_word",
    "ti_paratext",
]


def _b(x):
    return 1.0 if x else 0.0


def record_to_features(rec: dict) -> dict:
    """Flatten one raw enrichment record into the engineered numeric feature dict."""
    title = (rec.get("oa_title") or rec.get("cr_title") or "")
    venue = (rec.get("oa_source_name") or rec.get("cr_container") or "")
    src = (rec.get("oa_source_type") or "").lower()
    crt = (rec.get("cr_type") or "").lower()
    n_refs = rec.get("oa_n_refs")
    n_refs = n_refs if isinstance(n_refs, int) else 0
    container_present = bool(rec.get("cr_container") or rec.get("oa_source_name"))

    f = {
        # structural
        "single_page": _b(rec.get("oa_single_page")),
        "n_refs": float(n_refs),
        "refs_40_99": _b(40 <= n_refs < 100),
        "refs_100_149": _b(100 <= n_refs < 150),
        "refs_ge_150": _b(n_refs >= 150),
        "has_abstract": _b(rec.get("oa_has_abstract")),
        "title_len": float(len(title.split())),
        # container
        "has_isbn": _b(rec.get("cr_isbn")),
        "container_present": _b(container_present),
        "venue_proceedings": _b(_VENUE_PROC.search(venue)),
        "venue_preprint": _b(_VENUE_PRE.search(venue)),
        "src_journal": _b(src == "journal"),
        "src_repository": _b(src == "repository"),
        "src_conference": _b(src == "conference"),
        "src_book_series": _b(src == "book series"),
        "src_ebook": _b(src == "ebook platform"),
        "src_other": _b(src not in _SRC_LEVELS and src != ""),
        # upstream Crossref votes
        "crt_proceedings": _b(crt == "proceedings-article"),
        "crt_posted_content": _b(crt == "posted-content"),
        "crt_book_chapter": _b(crt == "book-chapter"),
        "crt_reference_entry": _b(crt == "reference-entry"),
        "crt_dataset": _b(crt == "dataset"),
        "crt_peer_review": _b(crt == "peer-review"),
        "crt_journal_article": _b(crt == "journal-article"),
        "crt_book": _b(crt in ("book", "monograph", "edited-book", "reference-book")),
        # container-level Crossref types = whole-issue/volume records = paratext (gold: journal-issue
        # 65/66, journal-volume 2/2). From the openalex-guts detective lookup. The structured signal
        # that lifts paratext recall past title-vocabulary coverage.
        "crt_issue": _b(crt in ("journal-issue", "journal-volume")),
        "cr_subtype_preprint": _b((rec.get("cr_subtype") or "").lower() == "preprint"),
        # title keyword flags
        "ti_editorial": _b(_TI_EDITORIAL.search(title)),
        "ti_erratum": _b(_TI_ERRATUM.search(title)),
        "ti_retraction": _b(_TI_RETRACTION.search(title)),
        "ti_book_review": _b(_TI_BOOK_REVIEW.search(title)),
        "ti_letter": _b(_TI_LETTER.search(title)),
        "ti_review_word": _b(_TI_REVIEW_WORD.search(title)),
        "ti_paratext": _b(_TI_PARATEXT.search(title)),
    }
    return f


def to_matrix(records):
    """List of raw records -> (X ndarray [n, len(FEATURE_NAMES)], FEATURE_NAMES)."""
    import numpy as np
    rows = [record_to_features(r) for r in records]
    X = np.asarray([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    return X, FEATURE_NAMES
