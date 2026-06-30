"""Self-check for the I10 dc.type cascade rule. Run: python -m cascade_classifier.test_dctype_map"""
from .cascade import classify_record


def _rec(dctype=None, **kw):
    r = {"oa_n_refs": 10, "oa_has_abstract": True}
    if dctype is not None:
        r["tx_meta"] = [f'<meta name="dc.type" content="{dctype}">']
    r.update(kw)
    return r


def demo():
    cases = [
        (_rec("Editorial"), "editorial"),
        (_rec("Book-Review"), "book-review"),     # case-insensitive parse
        (_rec("thesis"), "dissertation"),
        (_rec("Retraction"), "retraction"),
    ]
    for rec, want in cases:
        got, rule = classify_record(rec)
        assert got == want, f"dc.type={rec['tx_meta']}: got {got!r} ({rule}), want {want!r}"
        assert rule == "dc.type:map", f"expected dc.type:map to fire, got {rule!r}"

    # no dc.type meta -> dc.type rule must NOT fire (record falls through the cascade)
    got, rule = classify_record(_rec())
    assert rule != "dc.type:map", f"dc.type rule fired with no dc.type meta (rule={rule})"
    # an unmapped dc.type value -> no fire
    got, rule = classify_record(_rec("some-unknown-genre"))
    assert rule != "dc.type:map", f"unmapped dc.type fired (got {got!r})"
    print(f"ok: {len(cases)} dc.type mappings + no-meta + unmapped-value pass")


if __name__ == "__main__":
    demo()
