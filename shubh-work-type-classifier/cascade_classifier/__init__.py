"""oxjob #544 — feature-first, de-leaked, interpretable work-type classifier.

ML is used here for *feature discovery*, not as the production model. The deployable artifact
is a hybrid: a deterministic rule cascade for the clean types + a depth-limited decision tree
for the fuzzy article<->editorial/review residual. Circular OpenAlex-own-label features
(oa_type, oa_is_paratext) are excluded by construction. Every iteration is logged in JOURNAL.md.
"""
__version__ = "0.1.0"
