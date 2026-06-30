"""Self-check for the I11 guarded review rule. Run: python -m cascade_classifier.test_review_rule"""
from .cascade import classify_record


def _rec(title="", page_title="", n_refs=120, has_abstract=True, venue=""):
    return {"oa_title": title, "tx_page_title": page_title, "oa_n_refs": n_refs,
            "oa_has_abstract": has_abstract, "oa_source_name": venue}


def demo():
    # phrase + refs>=100 + abstract -> review
    got, rule = classify_record(_rec("Hearing loss and falls",
                                     page_title="Hearing Loss and Falls: A Systematic Review and Meta-Analysis"))
    assert got == "review" and rule == "review:phrase+refs", (got, rule)

    # case report blocks review even with 'review of the literature' + high refs
    got, rule = classify_record(_rec("Squamoid Eccrine Ductal Carcinoma: A Case Report and Review of the Literature",
                                     n_refs=180))
    assert got != "review", f"case report wrongly classified review ({rule})"

    # high refs but NO review phrase -> NOT review (the old 0.571 gate's false positives)
    got, rule = classify_record(_rec("Visual form perception and arithmetic computation", n_refs=200))
    assert got != "review", f"high-refs non-review wrongly classified review ({rule})"

    # review phrase but too few refs -> NOT review (needs the refs guard)
    got, rule = classify_record(_rec("A systematic review of X", n_refs=10))
    assert got != "review", f"low-ref phrase wrongly classified review ({rule})"
    print("ok: review phrase+refs fires; case-report blocks; bare high-refs & low-ref-phrase rejected")


if __name__ == "__main__":
    demo()
