"""Self-check for the I8 source-allowlist cascade rules. Run: python -m cascade_classifier.test_source_lists"""
from .cascade import classify_record


def _rec(venue="", doi="", single_page=False, n_refs=10, has_abstract=True):
    return {"oa_source_name": venue, "doi": doi, "oa_single_page": single_page,
            "oa_n_refs": n_refs, "oa_has_abstract": has_abstract}


def demo():
    cases = [
        (_rec(venue="bioRxiv"),                              "preprint"),
        (_rec(doi="10.2139/ssrn.4123456"),                  "preprint"),   # SSRN registrant, no venue
        (_rec(venue="ENCODE datasets"),                     "dataset"),
        (_rec(venue="Data in Brief"),                       "data-paper"),
        (_rec(venue="ECS Meeting Abstracts"),               "conference-abstract"),
        (_rec(venue="Lecture Notes in Computer Science"),   "conference-paper"),
        # LNCS record that is structurally an abstract -> split to conference-abstract
        (_rec(venue="Lecture Notes in Computer Science",
              single_page=True, n_refs=0, has_abstract=False), "conference-abstract"),
    ]
    for rec, want in cases:
        got, rule = classify_record(rec)
        assert got == want, f"{rec.get('oa_source_name') or rec['doi']}: got {got!r} ({rule}), want {want!r}"

    # dataset-mixed must NOT be a hard preprint (Zenodo excluded) -> no source rule fires
    got, rule = classify_record(_rec(venue="Zenodo"))
    assert got != "preprint", f"Zenodo wrongly classified preprint via {rule}"
    print(f"ok: {len(cases)} venue mappings + Zenodo-exclusion pass")


if __name__ == "__main__":
    demo()
