"""Generate cascade_classifier/dctype_map.py from oxjob #545's rules_manifest.tsv (channel=dc.type).

Ports the high-precision dc.type -> work-type mappings (precision >= 93%, n >= 10). dc.type is
landing-page metadata (taxicab tx_meta), independent of OpenAlex's own type — non-circular. The
mapping is re-measured on the held-out gold_full_52k before any rule is trusted (see I10 eval).

Run: python -m cascade_classifier.gen_dctype_map
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = "/Users/shubhankar/Documents/oxjobs/working/rule-based-worktype-classifier/evidence/rules_manifest.tsv"
OUT = os.path.join(HERE, "dctype_map.py")
MIN_PREC, MIN_N = 93.0, 10

# value -> (type, precision) keeping the highest-precision mapping per dc.type value
best = {}
with open(MANIFEST) as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r["channel"] != "dc.type":
            continue
        try:
            prec, n = float(r["precision"]), int(r["n"])
        except (ValueError, KeyError):
            continue
        if prec < MIN_PREC or n < MIN_N:
            continue
        val = r["signal"].strip().lower()
        if val not in best or prec > best[val][1]:
            best[val] = (r["type"], prec)

DCTYPE_MAP = {v: t for v, (t, _) in sorted(best.items())}

with open(OUT, "w") as f:
    f.write('"""dc.type -> work-type map (oxjob #544 / I10).\n\n'
            f"Generated from oxjob #545 rules_manifest.tsv (channel=dc.type, precision>={MIN_PREC}%,\n"
            f"n>={MIN_N}). dc.type is taxicab landing-page metadata (tx_meta), non-circular. Re-measured\n"
            "on held-out gold_full_52k in I10. Regenerate: python -m cascade_classifier.gen_dctype_map\n"
            '"""\n\n')
    f.write("DCTYPE_MAP = {\n")
    for v, t in DCTYPE_MAP.items():
        f.write(f"    {v!r}: {t!r},\n")
    f.write("}\n")

print("wrote", OUT, "—", len(DCTYPE_MAP), "mappings")
from collections import Counter
print("by target type:", dict(Counter(DCTYPE_MAP.values()).most_common()))
