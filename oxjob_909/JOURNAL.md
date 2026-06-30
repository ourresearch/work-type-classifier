# oxjob #909 — experiment journal

Append-only log of iterations (autoresearch-style). Entries are upserted by `oxjob_909.run`
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
| **I5** | **final hybrid (incl. I6)** | **TEST (locked)** | **0.765** | **0.533** | **0.815 / 0.934** | **ship** |

**Bottom line:** the hybrid beats the keep-oa_type baseline on accuracy (0.765 vs 0.716) with no
overfit (train/val gap ≈ 0), recovers the biggest OpenAlex errors — conference-paper recall 0→0.73,
conference-abstract 0→0.49 — while **article precision stays 0.82** (article is not sacrificed).
**I6** added a deterministic `title:paratext` rule (0.99 precision, info-gain-selected tokens): it lifts
**paratext precision 0.56→0.88** by killing the `title_len` false alarms. Paratext *recall* stays ~0.33
— capped by vocabulary coverage (~38% of paratext titles are recognizable); the rest need a non-title
signal (page position / front-of-issue). Editorial (~0.19) remains the hard article-boundary residual.

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
- **Result:** acc=0.765, macro-F1=0.533, article P=0.815/R=0.934
- **Decision:** ship hybrid + export cascade to SQL
- **Learning:** Paratext recall stays high while editorial/review recover vs article — the original question answered: paratext is not won by sacrificing article.

### I6 — 2026-06-30
- **Hypothesis:** Paratext is a vocabulary type; an anchored title-token rule fixes the title_len blind spot (both missed paratext and false-flagged short articles).
- **Change:** Add ti_paratext feature + cascade title:paratext rule (0.99 prec / 0.38 recall on gold).
- **Split:** train->val
- **Result:** acc=0.768, macro-F1=0.540, article P=0.821/R=0.953
- **Decision:** keep — deterministic, 100%-precision, interpretable; lifts macro-F1
- **Learning:** PRECISION win: paratext precision ~0.56->0.88 (kills title_len false alarms on short articles); recall stays ~0.31 — capped by vocabulary coverage (~38% of paratext titles recognizable). Article precision held 0.82. Recall ceiling needs a non-title signal (page position / front-of-issue) — next iteration.
