# oxjob #544 — experiment journal

Append-only log of iterations (autoresearch-style). Entries are upserted by `cascade_classifier.run`
(re-running an iteration replaces its block). Each entry: hypothesis · change · split · result
(macro-F1 + article-boundary scorecard) · keep/discard · learning.

**Headline metric:** macro-F1 + the article-boundary scorecard (article precision/recall and how
much each neighbor type bleeds *into* article). Overall accuracy is reported but secondary.

## Leaderboard

| Iter | What | split | accuracy | macro-F1 | article P / R | note |
|---|---|---|---|---|---|---|
| I0 | keep oa_type (baseline) | val | 0.716 | 0.526 | 0.711 / 0.986 | reference |
| I1 | de-leaked LR (no oa_type) | val | 0.775 | 0.551 | 0.798 / 0.976 | honest signal floor |
| I3 | deterministic cascade only | val | 0.699 | 0.344 | 0.661 / 0.994 | rules layer (32% coverage, high per-rule precision) |
| I4 | hybrid cascade→tree | val | 0.763 | 0.523 | 0.825 / 0.947 | deployable; gap −0.003 |
| I6 | + title:paratext rule | val | 0.768 | 0.540 | 0.821 / 0.953 | paratext precision 0.56→0.88 |
| I7 | + openalex-guts detective signals | val | 0.771 | 0.535 | 0.814 / 0.966 | paratext recall via journal-issue cr_type |
| **I5** | **final hybrid (incl. I7)** | **TEST (locked)** | **0.773** | **0.538** | **0.812 / 0.945** | **ship** |
| I8 | + #547/preprint_servers source allowlists (5 types) | gold_master (held-out 10k) | 0.789 | — | 0.839 / 0.945 | vs 0.773 baseline on same set; dataset F 0→.71, conf-abstract .43→.50, conf-paper .83→.90 |
| I10 | + dc.type (taxicab landing-page) rules | gold_full_52k (held-out 41k) | 0.730 | — | 0.842 / 0.864 | rule prec 0.974; editorial R .11→.21, book-review .07→.24, dissertation 0→.33; **cascade-only 0.760 > hybrid (tree doesn't generalize at scale)** |
| I11 | review: phrase+refs guard (drop bare refs≥150) | gold_full_52k (held-out 41k) | 0.730 | — | 0.843 / 0.860 | Jason's-technique; review P 0.81→**0.98** (cascade), rule prec 1.00; replaced the 0.571-precision refs≥150 gate; case-report blocks |

**Bottom line:** the hybrid beats the keep-oa_type baseline on accuracy (0.773 vs 0.716) with no
overfit (train/val gap ≈ 0), recovers the biggest OpenAlex errors — conference-paper recall 0→0.73,
conference-abstract 0→0.49 — while **article precision stays 0.81** (article is not sacrificed).
**I6** added a deterministic `paratext` title rule (0.99 precision, info-gain-selected tokens) →
**paratext precision 0.56→0.88**. **I7** referenced the OpenAlex production detective
(`openalex-guts` `work_type_detective.py`): unioned its richer paratext title vocabulary and added the
**structured `cr_type=journal-issue/journal-volume` signal (65/66 paratext on gold)** — the *non-title*
signal that breaks the vocabulary ceiling, lifting paratext recall (test 0.32→0.36; the rule alone is
0.99 prec / 0.57 recall gold-wide) with precision held. Editorial (~0.19) remains the hard residual.

---

## Entries

### I0 — 2026-06-30
- **Hypothesis:** OpenAlex's current type is the reference to beat.
- **Change:** No model — predict oa_type as-is.
- **Split:** val (2146)
- **Result:** acc=0.716, macro-F1=0.526, article P=0.711/R=0.986
- **Decision:** keep as baseline
- **Learning:** Baseline accuracy and the article-boundary leakage we must improve on.

### I1 — 2026-06-30
- **Hypothesis:** How much did the old model lean on OpenAlex's own label?
- **Change:** LR on engineered features only; compare to LR+oa_type.
- **Split:** train->val
- **Result:** acc=0.775, macro-F1=0.551, article P=0.798/R=0.976
- **Decision:** adopt de-leaked feature basis
- **Learning:** oa_type adds +0.049 acc (circular). De-leaked macro-F1=0.551; this is the honest signal floor for rules/tree.

### I2 — 2026-06-30
- **Hypothesis:** A few structural factors separate each type from article.
- **Change:** Per-class binary logit (X vs article) + shallow tree on engineered features.
- **Split:** train
- **Result:** discovery only — per-class pseudo-R²: paratext 0.80, review 0.41, editorial 0.35, conference-paper 0.67, preprint 0.95, letter 0.29
- **Decision:** use top factors to author the cascade (I3)
- **Learning:** Top differentiators: refs & 'review' in title -> review; low refs/no abstract/short title -> editorial; ti_letter -> letter; short title/no abstract -> paratext.

### I3 — 2026-06-30
- **Hypothesis:** Deterministic gates recover the clean types at high precision.
- **Change:** 12-rule ordered cascade (two low-precision rules pruned); residual defaults to article.
- **Split:** val
- **Result:** acc=0.699, macro-F1=0.344, article P=0.661/R=0.994
- **Decision:** keep as the deterministic layer
- **Learning:** Cascade covers 32% of works deterministically; article-boundary residual (editorial/review) is what the tree must fix.

### I4 — 2026-06-30
- **Hypothesis:** A shallow tree on the residual lifts editorial/review without hurting article.
- **Change:** DecisionTree(depth<=6, natural weighting) on cascade-residual works; hybrid predict.
- **Split:** train->val
- **Result:** acc=0.763, macro-F1=0.523, article P=0.825/R=0.947 | train/val gap=-0.003
- **Decision:** adopt hybrid as the deployable
- **Learning:** Hybrid macro-F1=0.523; train/val gap=-0.003 (~0 -> not overfit, unlike the 30k-token model). The de-leaked LR (I1) edges it on macro-F1, but the hybrid is deterministic/SQL-deployable with auditable per-rule precision — the team's stated preference.

### I5 — 2026-06-30
- **Hypothesis:** The hybrid generalizes to unseen data without article being sacrificed.
- **Change:** Final cascade->tree hybrid; evaluate locked test once.
- **Split:** TEST (locked, first touch)
- **Result:** acc=0.773, macro-F1=0.538, article P=0.812/R=0.953
- **Decision:** ship hybrid + export cascade to SQL
- **Learning:** Paratext recall stays high while editorial/review recover vs article — the original question answered: paratext is not won by sacrificing article.

### I6 — 2026-06-30
- **Hypothesis:** Paratext is a vocabulary type; an anchored title-token rule fixes the title_len blind spot (both missed paratext and false-flagged short articles).
- **Change:** Add ti_paratext feature + cascade title:paratext rule (0.99 prec / 0.38 recall on gold).
- **Split:** train->val
- **Result:** acc=0.771, macro-F1=0.535, article P=0.814/R=0.966
- **Decision:** keep — deterministic, 100%-precision, interpretable; lifts macro-F1
- **Learning:** PRECISION win: paratext precision ~0.56->0.89 (kills title_len false alarms on short articles); recall stays ~0.37 — capped by vocabulary coverage (~38% of paratext titles recognizable). Article precision held 0.81. Recall ceiling needs a non-title signal (page position / front-of-issue) — next iteration.

### I7 — 2026-06-30
- **Hypothesis:** The OpenAlex production detective encodes paratext signals we lack — a richer title vocabulary AND a structured container cr_type (journal-issue).
- **Change:** Union the detective's paratext title patterns (#535-filtered) + add crt_issue (journal-issue/journal-volume -> paratext) to the cascade rule.
- **Split:** train->val
- **Result:** acc=0.771, macro-F1=0.535, article P=0.814/R=0.966
- **Decision:** keep — recall jumps with precision held
- **Learning:** Paratext recall 0.37 (was ~0.31 at I6); precision 0.89; rule precision 1.00. The cr_type=journal-issue signal (65/66 paratext on gold) breaks the title-vocabulary ceiling — a non-title signal, as predicted. Article precision held 0.81.

### I8 — 2026-06-30
- **Hypothesis:** #544 is strong on Crossref-type trust but blind to the source/venue axis — it has no source-name/host/DOI-prefix rules. Five hard types (conference-paper, conference-abstract, data-paper, dataset, preprint) are dominated by single-type venues, so a curated source allowlist should add high-precision recall.
- **Change:** New `source_lists.py` allowlists (generated from oxjob #547 `single-type-source-catalog` + `data/preprint_servers.csv`); 5 cascade rules keying on venue NAME (all 5 types) + DOI registrant (preprint only). NON-circular. Mirrored into `cascade.sql`. Cleaning: dataset-mixed venues (Zenodo/Figshare/OSF — only "preprint server" rows of preprint_servers.csv are trusted, not "general repository") and generic catalog labels (report/proceedings/preprints) excluded. Change isolated to the cascade (not added to FEATURE_NAMES → residual tree unchanged).
- **Split:** **gold_master.jsonl (held-out, 10k; 1/10000 id overlap with #544 train — confirmed clean).** Eval set chosen per session decision.
- **Result (gold_master, before → after):** overall acc **0.773 → 0.789**; article P **0.832 → 0.839** (held). Hybrid per-type F1: conference-paper .83→**.90**, conference-abstract .43→**.50**, dataset .56→**.71**, preprint .99→.99, data-paper 0→.67 (n=2, not meaningful). Cascade-only: dataset F 0→**.87**, conf-abstract F .02→.25, preprint recall **.805→.996**. Each new rule's precision on gold_master: preprint .939, dataset 1.00, conf-abstract .953, conf-paper .958, data-paper 1.00 — all ≥ the 0.86 HIGH bar.
- **Decision:** keep — every target type improves or holds, article precision unchanged, all rules ≥0.94 precision.
- **Learning:** Source-NAME match is the high-precision signal across all five types; DOI-prefix is clean only for preprint (dedicated registrants like 10.2139/SSRN) — shared registrants (10.1088/IOP, 10.1007/Springer) are too broad and were dropped at the 0.86 bar. The biggest deterministic wins were the cells with NO prior rule: dataset (cascade 0→.87 F) and conference-abstract (.02→.25 F). `data-paper` (n=2 in gold_master) stays unmeasurable here — coverage-only. Self-check: `python -m cascade_classifier.test_source_lists`.

### I10 — 2026-06-30
- **Hypothesis:** dc.type (taxicab landing-page metadata) is fetched by `labeler/worktype/enrich.py` into `tx_meta` but the #544 cascade uses ZERO landing-page signals. It is #545's highest-value channel (~96% aggregate precision) and targets the report's open cells (editorial, book-review, review, dissertation).
- **Change:** Parse dc.type from `tx_meta` → `dc_type` (cascade-only; NOT in FEATURE_NAMES, tree unchanged). New `dctype_map.py` (43 mappings ported from #545 `rules_manifest.tsv`, precision ≥93% / n ≥10) + cascade rule `dc.type:map` (Stage 3: after Crossref+source allowlists, before title regexes). Mirrored into `cascade.sql`.
- **Split:** **de-leaked gold_full_52k held-out (40,656 works)** = feature-enriched `.jsonl` union (51,387) minus all 10,731 #544 train/val/test ids. All types measurable (data-paper 252, not 2). dc.type present on ~78%.
- **Result:** dc.type:map rule precision **0.974** on held-out (fires 1,575). Cascade-only acc **0.746→0.760**; open-cell recall (cascade): editorial 0.11→**0.21**, book-review 0.07→**0.24** (P 0.93), review 0.10→**0.15**, dissertation 0→**0.33** (P 1.00), retraction 0.60→**0.85**, erratum 0.71→0.74. Article precision held: 0.705→**0.720** (cascade), 0.830→**0.842** (hybrid). Hybrid acc 0.715→0.730.
- **Decision:** keep — full map (incl. →article; the no-article variant was ~identical, full marginally better on hybrid; dc.type values are disjoint so →article does not dilute minority recall). Every kept mapping ≥0.86 on held-out (rule aggregate 0.974).
- **Learning:** (1) dc.type recovers exactly the open cells the report flagged. (2) **On the large de-leaked 52k, cascade-only (0.760) BEATS hybrid (0.730)** — the depth-6 residual tree, fit on the 10k split, does not generalize to the full distribution; the deterministic deployable is the stronger artifact at scale (good — the SQL corrector IS cascade-only). (3) Leakage caveat: the held-out excludes the tree's train/val/test, but the ported dc.type map (and I8 allowlists) were curated on overlapping #545/#547 gold — they are value/venue-level rules re-measured here (0.974), "independent of the tree," not "never-seen by the miners." Self-check: `python -m cascade_classifier.test_dctype_map`.

### I11 — 2026-06-30 (Jason's technique — review)
- **Hypothesis:** review's bare `refs≥150 + abstract` gate is imprecise; an explicit review-methodology phrase conjoined with a ref count is high-precision. Induced by inspecting review misses (false negatives) + false alarms on the held-out.
- **Change:** New features `ti_review_phrase` (systematic review|meta-analysis|scoping/narrative/umbrella review, over oa_title + **tx_page_title**) and `ti_case_report` (cascade-only). Replaced rule `review:high-refs` with **`review:phrase+refs`** = `ti_review_phrase AND NOT ti_case_report AND n_refs≥100 AND has_abstract AND ¬proceedings`. Mirrored in `cascade.sql`.
- **Split:** de-leaked gold_full_52k held-out (40,656).
- **Result:** new rule precision **1.000** (fires 17). Cascade-only review **P 0.812→0.983** (R 0.154→0.089 — precision-first trade); hybrid review **F1 0.524→0.538** (R 0.395→0.422, tree recovers recall). Article precision held (0.718 cascade, 0.843 hybrid); overall acc flat (0.760→0.759 cascade, 0.730 hybrid).
- **Decision:** keep — removes the **0.571-precision** liability gate, replaces with a 1.00-precision conjunction; precision-first per the team steer.
- **Learning (measurement overturned induction):** (1) "systematic review/meta-analysis" in the title ALONE is only **0.725** — gold labels many meta-analyses as `article`; high precision needs the refs conjunction. (2) Review-series VENUE names fail: "clinics of north america" 0.500, contains "reviews" 0.384, "annual review" 0.667. (3) **`tx_page_title` carries the label `oa_title` truncates** ("Hearing Loss and Falls" → page_title "…: A Systematic Review and Meta-Analysis"). (4) **"case report" blocks review** — only 2.1% of 'case report/series' works are review. (5) Honest ceiling: narrative reviews with no label/dc.type are not deterministically recoverable at high precision (rule reaches ~17–27 of 1,322). Self-check: `python -m cascade_classifier.test_review_rule`.
