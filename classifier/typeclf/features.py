"""Turn an enrichment record (a ../labeler JSONL line) into model features.

Two feature scopes:
  FULL      — every signal, including taxicab harvested-HTML (`tx_*`) and the live
              landing-page health probe (`lp_*`). Highest accuracy, but producing these
              for a new work needs the enrich step (`worktype --no-annotate`).
  METADATA  — only fields OpenAlex already stores in its own DB (title, current type,
              venue, biblio, ISBN, has-abstract). No external fetch, so it scores the
              full ~250M-work corpus offline.

The transformer is a ColumnTransformer over three channels (text TF-IDF, one-hot
categoricals, numeric/boolean), built by `build_preprocessor()`. Records become a list of
plain dicts via `record_to_row()`; we lean on DictVectorizer/ColumnTransformer-friendly
shapes rather than pandas so the dependency stays minimal.
"""
from __future__ import annotations

import re

# Field-name vocabulary mirrors ../labeler/worktype/enrich.py.
TEXT_FIELDS_FULL = ["title", "tx_page_title", "tx_meta_text", "oa_source_name"]
TEXT_FIELDS_META = ["title", "oa_source_name"]

CATEGORICAL_FIELDS = ["oa_type", "cr_type", "oa_source_type"]

# numeric/boolean signals; metadata mode drops the landing-page status (external probe)
NUMERIC_FIELDS_FULL = [
    "cr_isbn", "oa_single_page", "oa_has_abstract", "oa_is_paratext",
    "n_refs", "n_refs_bucket", "refs_ge_40", "lp_status_bucket",
]
NUMERIC_FIELDS_META = [
    "cr_isbn", "oa_single_page", "oa_has_abstract", "oa_is_paratext",
    "n_refs", "n_refs_bucket", "refs_ge_40",
]


def _f(x):
    """coerce booleans/None to 0.0/1.0 floats; pass numbers through."""
    if x is None:
        return 0.0
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _refs_bucket(n):
    n = n or 0
    if n <= 0:
        return 0
    if n < 10:
        return 1
    if n < 40:
        return 2
    return 3  # >=40 — the validated review gate


def _lp_bucket(status):
    """Coarse landing-page health: 0 unknown, 2 ok(2xx), 3 redirect, 4 client-err, 5 server-err."""
    if not status:
        return 0
    try:
        return int(status) // 100
    except (TypeError, ValueError):
        return 0


def record_to_row(rec: dict, scope: str = "full") -> dict:
    """Flatten one enrichment record into a feature dict (text strings + numeric features).

    `scope` is "full" or "metadata". The returned dict always carries every key both scopes
    might use; the preprocessor selects the columns for the active scope, so a single
    flattening works for either model.
    """
    title = rec.get("oa_title") or rec.get("cr_title") or ""
    tx_meta = rec.get("tx_meta") or []
    tx_meta_text = " ".join(str(m) for m in tx_meta) if isinstance(tx_meta, list) else str(tx_meta or "")
    n_refs = rec.get("oa_n_refs") or 0

    row = {
        # text channels (always present as strings; metadata scope ignores tx_*)
        "title": _clean_text(title),
        "tx_page_title": _clean_text(rec.get("tx_page_title") or ""),
        "tx_meta_text": _clean_text(tx_meta_text),
        "oa_source_name": _clean_text(rec.get("oa_source_name") or ""),
        # categoricals (strings; "" => unknown bucket)
        "oa_type": rec.get("oa_type") or "",
        "cr_type": rec.get("cr_type") or "",
        "oa_source_type": rec.get("oa_source_type") or "",
        # numeric / boolean
        "cr_isbn": _f(rec.get("cr_isbn")),
        "oa_single_page": _f(rec.get("oa_single_page")),
        "oa_has_abstract": _f(rec.get("oa_has_abstract")),
        "oa_is_paratext": _f(rec.get("oa_is_paratext")),
        "n_refs": float(n_refs),
        "n_refs_bucket": float(_refs_bucket(n_refs)),
        "refs_ge_40": 1.0 if (n_refs or 0) >= 40 else 0.0,
        "lp_status_bucket": float(_lp_bucket(rec.get("lp_status"))),
    }
    return row


_WS = re.compile(r"\s+")


def _clean_text(s: str) -> str:
    return _WS.sub(" ", str(s)).strip()


def columns_for(scope: str):
    """Return (text_fields, categorical_fields, numeric_fields) for the given scope."""
    if scope == "metadata":
        return TEXT_FIELDS_META, CATEGORICAL_FIELDS, NUMERIC_FIELDS_META
    if scope == "full":
        return TEXT_FIELDS_FULL, CATEGORICAL_FIELDS, NUMERIC_FIELDS_FULL
    raise ValueError(f"unknown scope {scope!r} (use 'full' or 'metadata')")


def build_featurizer(scope: str = "full"):
    """Return an unfitted `WorkTypeFeaturizer` for the given scope (the Pipeline's first step)."""
    return WorkTypeFeaturizer(scope=scope)


# Imported lazily inside the class so `record_to_row`/`columns_for` stay importable without
# sklearn (e.g. a pure-stdlib caller that only flattens records).
class WorkTypeFeaturizer:
    """Transforms a list of feature dicts (from `record_to_row`) into one sparse matrix.

    Self-contained (no pandas / ColumnTransformer): per-text-field TF-IDF + a char-ngram
    channel on the title + one-hot categoricals + scaled numerics, hstacked. Implements the
    sklearn fit/transform protocol so it drops into a Pipeline and pickles with joblib.
    """

    def __init__(self, scope: str = "full"):
        self.scope = scope

    def get_params(self, deep=True):           # sklearn Pipeline/clone compatibility
        return {"scope": self.scope}

    def set_params(self, **p):
        for k, v in p.items():
            setattr(self, k, v)
        return self

    def fit(self, X, y=None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import MaxAbsScaler, OneHotEncoder
        import numpy as np

        text_fields, cat_fields, num_fields = columns_for(self.scope)
        self.text_fields_, self.cat_fields_, self.num_fields_ = text_fields, cat_fields, num_fields

        # word 1-2 grams per text field capture phrases ("book review", "proceedings of").
        self.text_vecs_ = {}
        for tf in text_fields:
            v = TfidfVectorizer(sublinear_tf=True, min_df=3, ngram_range=(1, 2),
                                lowercase=True, strip_accents="unicode")
            self.text_vecs_[tf] = v.fit([r.get(tf, "") for r in X])
        # extra char 3-5 gram channel on the title only — robust to typos/morphology and
        # short non-English venue strings; kept to one field so the matrix stays compact.
        from sklearn.feature_extraction.text import TfidfVectorizer as _TV
        self.char_vec_ = _TV(analyzer="char_wb", ngram_range=(3, 5), min_df=5,
                             sublinear_tf=True).fit([r.get("title", "") for r in X])

        self.ohe_ = OneHotEncoder(handle_unknown="ignore", min_frequency=5)
        self.ohe_.fit([[r.get(c, "") for c in cat_fields] for r in X])

        num = np.asarray([[float(r.get(n, 0.0)) for n in num_fields] for r in X], dtype=float)
        self.num_scaler_ = MaxAbsScaler().fit(num)  # bring n_refs onto the others' scale, sparse-safe
        return self

    def transform(self, X):
        from scipy import sparse
        import numpy as np

        mats = [self.text_vecs_[tf].transform([r.get(tf, "") for r in X]) for tf in self.text_fields_]
        mats.append(self.char_vec_.transform([r.get("title", "") for r in X]))
        mats.append(self.ohe_.transform([[r.get(c, "") for c in self.cat_fields_] for r in X]))
        num = np.asarray([[float(r.get(n, 0.0)) for n in self.num_fields_] for r in X], dtype=float)
        mats.append(sparse.csr_matrix(self.num_scaler_.transform(num)))
        return sparse.hstack(mats).tocsr()

    def fit_transform(self, X, y=None):
        return self.fit(X, y).transform(X)
