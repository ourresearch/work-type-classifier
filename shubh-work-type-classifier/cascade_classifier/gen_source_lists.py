"""Generate cascade_classifier/source_lists.py from the #547 catalog + preprint_servers.csv.
Kept signals (I8, measured on gold_master): NAME match for all 5 types; DOI-PREFIX for preprint only."""
import csv, json, re
from collections import defaultdict

import os
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OX = "/Users/shubhankar/Documents/oxjobs/working/single-type-source-catalog"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_lists.py")
TARGETS = ["conference-paper", "conference-abstract", "data-paper", "dataset", "preprint"]
DATASET_MIXED = {"zenodo", "figshare", "harvard dataverse", "mendeley data", "osf", "open science framework"}
# catalog "canonical" rows include descriptive labels, not real oa_source_name strings; these
# generic tokens would over-fire at corpus scale (gold_master happened not to hit them).
GENERIC = {"report", "reports", "proceedings", "conference proceedings", "preprint", "preprints"}

norm = lambda s: (s or "").strip().lower()
def keep(n):  # reject dataset-mixed, generic labels, and wildcard/note entries
    return n not in DATASET_MIXED and n not in GENERIC and not n.startswith("*") and "..." not in n
def doi_prefix(d):
    m = re.search(r"10\.\d{3,9}", norm(d)); return m.group(0) if m else None

names = defaultdict(set); pre_prefixes = set()

with open(f"{OX}/evidence/single-type-sources.csv") as f:
    for r in csv.DictReader(f):
        t = r["type"]
        if t in TARGETS and keep(norm(r["source"])):
            names[t].add(norm(r["source"]))

for e in json.load(open(f"{OX}/work/candidates.json")):
    t = e.get("type")
    if t not in TARGETS or e.get("frac", 0) < 0.90 or not keep(norm(e["name"])):
        continue
    names[t].add(norm(e["name"]))
    if t == "preprint":
        for d in e.get("sample_dois", []):
            p = doi_prefix(d)
            if p: pre_prefixes.add(p)

# preprint_servers.csv: ONLY genuine preprint servers (service_type), NOT general repositories
# (Zenodo/Figshare are "general repository" there and dataset-mixed in #547 — must not be hard preprint).
with open(f"{ROOT}/data/preprint_servers.csv") as f:
    for r in csv.DictReader(f):
        if norm(r.get("is_active")) != "true" or norm(r.get("service_type")) != "preprint server":
            continue
        names["preprint"].add(norm(r["source_name"]))
        for a in (r.get("aliases") or "").split(";"):
            if a.strip() and keep(norm(a)): names["preprint"].add(norm(a))

def fmt(s):
    return "{\n" + "".join(f"    {v!r},\n" for v in sorted(s)) + "}"

VAR = {"conference-paper": "CONFPAPER_NAMES", "conference-abstract": "CONFABS_NAMES",
       "data-paper": "DATAPAPER_NAMES", "dataset": "DATASET_NAMES", "preprint": "PREPRINT_NAMES"}

with open(OUT, "w") as f:
    f.write('"""Single-type source allowlists (oxjob #544 / I8).\n\n'
            "Generated from oxjob #547 single-type-source-catalog (evidence/single-type-sources.csv +\n"
            "work/candidates.json, gold-frac >= 0.90) and data/preprint_servers.csv. Kept signals are\n"
            "name-match for all 5 types (measured >= 0.95 precision on gold_master) and DOI-prefix for\n"
            "preprint only (0.985; other types' prefixes were too broad and dropped at the 0.86 bar).\n"
            "The 5 dataset-mixed repos (Zenodo/Figshare/Dataverse/Mendeley/OSF) are excluded.\n"
            "Regenerate with cascade_classifier.gen_source_lists (python -m).\n\"\"\"\n\n")
    for t in TARGETS:
        f.write(f"{VAR[t]} = frozenset({fmt(names[t])})\n\n")
    f.write(f"PREPRINT_PREFIXES = frozenset({fmt(pre_prefixes)})\n")

print("wrote", OUT)
for t in TARGETS:
    print(f"  {VAR[t]:18s} {len(names[t])}")
print(f"  PREPRINT_PREFIXES  {len(pre_prefixes)}: {sorted(pre_prefixes)}")
