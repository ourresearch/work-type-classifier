"""Canonical work-type taxonomy (#535) + the Claude annotation system prompt and output schema."""
from pathlib import Path

# The 25 canonical OpenAlex work types (oxjob #535).
CANONICAL_TYPES = [
    "article", "book", "book-chapter", "book-review", "conference-abstract",
    "conference-paper", "data-paper", "dataset", "dissertation", "editorial",
    "erratum", "letter", "libguides", "other", "paratext", "peer-review",
    "preprint", "reference-entry", "report", "retraction", "review",
    "software-paper", "software", "standard", "supplementary-materials",
]

_DATA = Path(__file__).resolve().parent.parent / "data"


def load_descriptions() -> str:
    """Full annotator-grade definitions for the 25 types (DESCRIPTIONS.md from #535)."""
    return (_DATA / "taxonomy_descriptions.md").read_text()


SYSTEM_PROMPT = """You are a work-type classification council member for OpenAlex's classifier-improvement project. \
You assign each scholarly work the single best `type` from OpenAlex's canonical 25-type taxonomy, plus an \
independent landing-page-health flag, with a one-sentence evidence-grounded reason.

AUTHORITATIVE TAXONOMY (use these exact definitions; Includes / Goes elsewhere / Boundary rules are binding):

{descriptions}

CLASSIFICATION RULES
- `type` MUST be exactly one of the 25 canonical types above. Never output "broken"/"unknown"/"ambiguous" as a type.
- Type is the work's intrinsic genre, judged from all signals — NOT a copy of the current OpenAlex `oa_type`, which is \
Crossref-inherited and is exactly what we are auditing. Treat `oa_type` as a weak prior only.
- Near-deterministic routes when present: Crossref `proceedings-article` -> conference-paper; `posted-content`+subtype \
`preprint` (or an SSRN/arXiv/bioRxiv/Research Square/`*discussions` venue) -> preprint; `book-chapter` -> book-chapter; \
`monograph`/`edited-book`/`reference-book` -> book; `dataset` -> dataset; `dissertation` -> dissertation; \
`reference-entry` -> reference-entry; `peer-review` -> peer-review.
- Content boundaries (apply the taxonomy precisely): review = survey of MANY works / explicitly "review article" \
(OpenAlex under- and over-tags this because its current rule is venue-derived, so trust `dc.type`/article-type/title \
over `oa_type`); conference-abstract = abstract-only (0 refs + a supplement/`A47`/`s420`-style page + a meeting venue); \
editorial = opinion/"From the Editor"/introduction; letter = reader correspondence; book-review = appraisal of one book \
(taxicab `citation_title` is a book title + "Edited by..."/publisher, or a JSTOR "Review:" page); reference-entry = one \
entry in an encyclopedia/dictionary; paratext = covers/TOC/index/front-matter/whole-issue records. Case reports presented \
as full papers -> article. News/obituaries/full journal issues -> other.
- SEPARATELY set `is_broken` (boolean): TRUE only when the live landing page is genuinely inaccessible/dead — `lp_status` \
5xx, 404/410, `lp_reachable=false`, or a taxicab `tx_page_title` of "Page not found"/"DOI Not Found". A 403/401 bot-block \
or a 200/202 page is NOT broken. `is_broken` is about page health, not type — still assign the best `type` from metadata \
even when the page is broken.

The signals you receive are HIGH VALUE in this order for the hard cases: the taxicab harvested-HTML meta tags \
(`dc.type`, `DC.Type.articleType`, `article-type`, `citation_title`) and page title, then Crossref type/subtype, then \
biblio (pages / single-page / reference count), then the venue. These reveal the true genre that OpenAlex got wrong.

Output ONLY the structured object: type, is_broken, confidence (high|medium|low), reason (one sentence naming the \
DECISIVE signal). Be decisive and consistent."""


def system_prompt() -> str:
    return SYSTEM_PROMPT.format(descriptions=load_descriptions())


# JSON-schema for structured outputs (output_config.format). additionalProperties:false + required are mandatory;
# no minLength/maxLength (unsupported by structured outputs).
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": CANONICAL_TYPES,
                 "description": "the single best canonical work type"},
        "is_broken": {"type": "boolean",
                      "description": "true only if the live landing page is dead/inaccessible (5xx/404/unreachable)"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string", "description": "one sentence naming the decisive signal"},
    },
    "required": ["type", "is_broken", "confidence", "reason"],
    "additionalProperties": False,
}
