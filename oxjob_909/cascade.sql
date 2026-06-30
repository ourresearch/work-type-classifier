-- oxjob #909 — deterministic type cascade as a SQL CASE (Databricks / Spark SQL).
-- This is the rules layer (cascade.py, iteration I3) expressed in pure SQL — no model, no UDF,
-- no external fetch. It assigns the clean/deterministic types and leaves the fuzzy
-- article<->editorial/review residual as NULL (predicted_type IS NULL), which the deployed
-- hybrid hands to the depth-6 decision tree. On the gold set this layer covers ~32% of works
-- deterministically at high per-rule precision (proceedings 0.93, preprint/peer-review/erratum
-- /reference-entry 1.00, retraction 0.93). Rule order matters: most-specific first.
--
-- Expected input columns (map to your OpenAlex/Crossref source):
--   cr_type            -- raw Crossref type (NOT OpenAlex's oa_type — that is circular, excluded)
--   cr_subtype         -- Crossref subtype ('preprint' on posted-content)
--   has_isbn           -- ISBN present (boolean)
--   source_type        -- OpenAlex source type ('journal','repository','conference',...)
--   venue              -- source/container display name (lower-cased for matching)
--   title              -- work title
--   n_refs             -- referenced_works_count
--   single_page        -- first_page = last_page (boolean)
--   has_abstract       -- abstract present (boolean)

WITH f AS (
  SELECT
    *,
    lower(coalesce(venue, ''))  AS venue_l,
    lower(coalesce(title, ''))  AS title_l,
    (lower(coalesce(venue, '')) RLIKE '(proceedings|symposium|workshop|conference|congress|colloqui)') AS venue_proceedings
  FROM works
)
SELECT
  *,
  CASE
    -- 1. preprint: Crossref subtype is definitive (99% pure on gold)
    WHEN lower(coalesce(cr_subtype,'')) = 'preprint' THEN 'preprint'

    -- 2. conference: proceedings-article (92% pure); split abstract-only records
    WHEN lower(coalesce(cr_type,'')) = 'proceedings-article'
         OR (venue_proceedings AND lower(coalesce(source_type,'')) = 'conference') THEN
      CASE WHEN single_page AND n_refs = 0 AND NOT has_abstract
           THEN 'conference-abstract' ELSE 'conference-paper' END

    -- 3-4. reference / whole book
    WHEN lower(coalesce(cr_type,'')) = 'reference-entry' THEN 'reference-entry'
    WHEN lower(coalesce(cr_type,'')) IN ('book','monograph','edited-book','reference-book') THEN 'book'

    -- 5. book family via Crossref chapter type or ISBN (ISBN default is chapter, 65% on gold;
    --    short + no abstract + no refs inside a book => front/back matter = paratext)
    WHEN lower(coalesce(cr_type,'')) = 'book-chapter' THEN 'book-chapter'
    WHEN has_isbn THEN
      CASE WHEN single_page AND NOT has_abstract AND n_refs = 0
           THEN 'paratext' ELSE 'book-chapter' END

    -- 6. peer-review
    WHEN lower(coalesce(cr_type,'')) = 'peer-review' THEN 'peer-review'

    -- 7-11. title-prefix signals (high precision when the title states the genre)
    WHEN title_l RLIKE '(retraction|retracted article|notice of retraction|withdrawn|expression of concern)' THEN 'retraction'
    WHEN title_l RLIKE '(erratum|corrigend(um|a)|publisher correction|correction to|author correction)' THEN 'erratum'
    WHEN title_l RLIKE '(^book review|^review of|reviewed work|^reviews of books)' THEN 'book-review'
    WHEN title_l RLIKE '^(editorial|from the editor|in this issue|introduction|preface|foreword|guest editor)' THEN 'editorial'
    WHEN title_l RLIKE '(reply to|comment on|response to|letter to the editor|in response to|correspondence)' THEN 'letter'

    -- 12. high-precision review gate: refs >= 150 (NOT 40 — that was only 16% precise) + abstract + not proceedings
    WHEN n_refs >= 150 AND has_abstract AND NOT venue_proceedings THEN 'review'

    -- residual: fuzzy article-boundary -> NULL, handed to the decision tree (or kept as oa_type)
    ELSE NULL
  END AS cascade_type
FROM f;
