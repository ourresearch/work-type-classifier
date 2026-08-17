-- ============================================================================
-- ⚠️ HISTORICAL ARTIFACT (June 2026) — NOT the deployed OpenAlex type classifier.
-- This was an early ~13-rule distilled-corrector experiment. The complete,
-- production rule cascade (the "~160 rules" from the July 2026 blog post, since
-- grown) is public in the openalex-walden repo:
--   https://github.com/ourresearch/openalex-walden/blob/main/notebooks/end2end/CreateLocationsWithTypes.ipynb
-- ============================================================================
-- worktype_rules.sql  —  Deterministic work-type CORRECTOR for Databricks (Spark SQL)
-- ============================================================================
-- WHAT THIS IS
--   A small, fully deterministic rule set that OVERRIDES OpenAlex's `type` only when
--   a high-precision signal fires, and otherwise KEEPS the existing label. It is NOT a
--   from-scratch classifier — ML (logistic regression + a shallow decision tree) was used
--   only to DISCOVER which 3-4 facts separate the types; this SQL is the distilled result.
--
-- DESIGN GUARDRAILS (every choice below has a reason, measured on 12,123 LLM-gold works)
--   1. NO CIRCULAR FEATURES. OpenAlex's own type-opinion (oa_type, oa_raw_type,
--      oa_is_paratext) is NEVER a rule input — using "OpenAlex says article" to predict
--      "article" is circular. The current type is used ONLY as the fallback when no rule
--      fires (i.e. "don't change what we can't improve").
--   2. INDEPENDENT SIGNALS ONLY. Rules key on Crossref's type (a different database),
--      ISBN, source/venue type, and reference count — facts, not opinions.
--   3. PRECISION-FIRST. Rules ordered most-specific -> broadest. Each rule's measured
--      precision & coverage is in its comment. We DROPPED every low-precision idea.
--   4. MISSING != ZERO. We do NOT use "few references" as a signal: 44% of works have
--      n_refs = 0 because references were never parsed, not because none exist. Only the
--      HIGH-reference direction (>=120 -> review) is used, since a high count can't be a
--      data artifact. (Threshold validated: refs>=120 on journal-articles = ~80% precision;
--      refs>=40 was only ~22% — the old 40 gate was far too low.)
--
-- MEASURED RESULT (full 12,123-work gold set)
--   Baseline (keep oa_type everywhere) ....... 67.4% accuracy
--   This corrector ........................... 73.6% accuracy  (+6.2 pp)
--   Overrides fire on 31% of works at 79.6% precision; of overridden works it FIXED 888 and
--   BROKE 143 (net +745). Each rule corrects far more than it breaks.
--
-- COLUMN MAPPING — adjust these to your actual OpenAlex/warehouse schema:
--   work_id        : work identifier
--   current_type   : OpenAlex's existing `type`          (fallback only)
--   crossref_type  : raw Crossref type  (NOT OpenAlex's type_crossref, which is null)
--   source_type    : OpenAlex source/venue type (journal | repository | conference | ...)
--   isbn           : ISBN string, NULL when absent
--   n_refs         : referenced_works_count
-- ============================================================================

WITH features AS (
    SELECT
        work_id,
        current_type,
        crossref_type,
        crossref_subtype,            -- Crossref `subtype` (e.g. 'preprint' for posted-content)
        source_type,
        isbn,
        n_refs
    FROM openalex.works              -- <-- point at your table
),

-- Apply the cascade. First matching WHEN wins (top = highest precision).
ruled AS (
    SELECT
        work_id,
        current_type,
        CASE
            -- ---- HIGH confidence (>=85% precision) ----
            WHEN crossref_type = 'peer-review'           THEN 'peer-review'        -- 100.0% (n=235)
            WHEN crossref_type = 'standard'              THEN 'standard'           --  99.4% (n=172)
            WHEN crossref_type = 'dissertation'          THEN 'dissertation'       --  98.7% (n=78)
            WHEN crossref_type = 'reference-entry'       THEN 'reference-entry'    --  98.2% (n=57)
            WHEN crossref_type = 'journal-issue'         THEN 'paratext'           --  91.7% (n=84)
            WHEN crossref_type = 'proceedings-article'   THEN 'conference-paper'   --  86.5% (n=706)
            WHEN crossref_type IN ('monograph','edited-book') THEN 'book'          --  86.7% (n=83)
            WHEN source_type   = 'conference'            THEN 'conference-paper'   --  92.6% (n=27)
            -- preprint requires subtype='preprint': raw posted-content is only 71% (the rest
            -- is supplementary-materials/abstracts); with the subtype gate it is 99%.
            WHEN crossref_type = 'posted-content'
                 AND crossref_subtype = 'preprint'       THEN 'preprint'           --  99.0% (n=196)
            -- ---- MEDIUM confidence (65-80% precision) ----
            WHEN isbn IS NOT NULL                        THEN 'book-chapter'       --  69.1% (n=1654) book family
            WHEN crossref_type = 'book-chapter'          THEN 'book-chapter'       --  66.0% (n=259)
            WHEN crossref_type = 'journal-article'
                 AND n_refs >= 120                       THEN 'review'             --  79.1% (n=129)
            WHEN crossref_type = 'report'                THEN 'report'             --  68.4% (n=38)
            ELSE NULL                                                              -- no rule fires
        END AS rule_type,
        CASE
            WHEN crossref_type IN ('peer-review','standard','dissertation','reference-entry',
                                   'journal-issue','proceedings-article','monograph','edited-book')
                 OR source_type = 'conference'
                 OR (crossref_type = 'posted-content' AND crossref_subtype = 'preprint') THEN 'high'
            WHEN crossref_type IN ('book-chapter','report')
                 OR isbn IS NOT NULL
                 OR (crossref_type = 'journal-article' AND n_refs >= 120)     THEN 'medium'
            ELSE NULL
        END AS rule_confidence
    FROM features
)

SELECT
    work_id,
    current_type,
    rule_type,
    rule_confidence,
    -- CORRECTOR output: override when a rule fired, else keep the existing label.
    COALESCE(rule_type, current_type) AS predicted_type,
    -- convenience flag for the review queue / audit
    (rule_type IS NOT NULL AND rule_type <> current_type) AS is_override
FROM ruled;

-- ----------------------------------------------------------------------------
-- DEPLOYMENT NOTES
--   * For a CONSERVATIVE rollout, apply only high-confidence overrides:
--       COALESCE(CASE WHEN rule_confidence = 'high' THEN rule_type END, current_type)
--   * `is_override = TRUE` rows are the ones to spot-check / route to human review.
--   * KNOWN GAPS (left as current_type on purpose — no clean deterministic signal yet):
--       conference-abstract, editorial, letter, erratum, retraction, book-review,
--       data-paper / software-paper, supplementary-materials. These need text/venue
--       signals; chasing them with reference/abstract heuristics scored 13-42% precision
--       and was deliberately excluded.
-- ----------------------------------------------------------------------------
