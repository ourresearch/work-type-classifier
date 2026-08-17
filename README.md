# OpenAlex work-type classifier

Development and evaluation workspace for OpenAlex's work-type classification — the system
described in [An Overhaul of Type Classification](https://blog.openalex.org/an-overhaul-of-type-classification/)
(July 2026).

## Where are the actual rules?

**The complete, deployed rule set is public, and lives in the
[openalex-walden](https://github.com/ourresearch/openalex-walden) pipeline repo:**

> [`notebooks/end2end/CreateLocationsWithTypes.ipynb`](https://github.com/ourresearch/openalex-walden/blob/main/notebooks/end2end/CreateLocationsWithTypes.ipynb)

That notebook holds the full SQL rule cascade that re-classifies the entire corpus every day.
It is the single source of truth: when we add or change a rule, that's the file that changes
(see its git history for every rule change since launch, each with measured evidence).

A few notes for readers of the blog post:

- The post described "an ordered cascade of ~160 rules" — that was the count at launch
  (July 2026). The cascade grows as we vet new rules (reader reports welcome!), so the live
  file is bigger; the ordering-and-first-match-wins design is unchanged.
- Every classification is attributable: alongside `type`, the warehouse records
  `classified_rule` — the name of the specific rule that fired for that work.
- Rules are precision-first: each rule was admitted only with measured precision on a
  gold-labeled evaluation set, and rule changes must pass a regression gate before deploy.

## What's in this repo, then?

The development history and evaluation tooling that produced the cascade:

| Path | What it is |
|------|-----------|
| `WORK-TYPES.md` | The 25-type taxonomy: definitions and annotation guidance. |
| `labeler/` | The gold-set annotation tool (LLM-assisted labeling pipeline). |
| `data/` | Gold-labeled evaluation shards (~52K works with human/LLM-adjudicated types). |
| `shubh-work-type-classifier/` | Historical: early classifier iterations and reports. |
| `sql/worktype_rules.sql` | **Historical**: an early ~13-rule distilled corrector experiment. *Not* the deployed rule set — see the walden notebook above. |
