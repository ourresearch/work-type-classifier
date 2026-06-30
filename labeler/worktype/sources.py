"""Input sources -> a list of DOIs to classify."""
import csv
import json
import urllib.parse
import urllib.request


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "worktype-cli/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _doi_of(work):
    doi = work.get("doi")
    return doi.replace("https://doi.org/", "") if doi else None


def from_sample(n, seed, mailto, extra_filter="indexed_in:crossref"):
    """Random OpenAlex sample of `n` works matching `extra_filter`. Pages by 200 (OpenAlex sample cap)."""
    dois, page, per = [], 1, min(200, n)
    while len(dois) < n:
        url = (f"https://api.openalex.org/works?filter={urllib.parse.quote(extra_filter)}"
               f"&sample={n}&seed={seed}&per_page={per}&page={page}"
               f"&select=id,doi&mailto={mailto}")
        results = _get(url).get("results", [])
        if not results:
            break
        dois += [d for w in results if (d := _doi_of(w))]
        page += 1
    return dois[:n]


def from_filter(openalex_filter, limit, mailto):
    """All works matching an OpenAlex filter (cursor-paged), capped at `limit`."""
    dois, cursor = [], "*"
    while cursor and len(dois) < limit:
        url = (f"https://api.openalex.org/works?filter={urllib.parse.quote(openalex_filter)}"
               f"&per_page=200&cursor={urllib.parse.quote(cursor)}&select=id,doi&mailto={mailto}")
        d = _get(url)
        dois += [x for w in d.get("results", []) if (x := _doi_of(w))]
        cursor = (d.get("meta") or {}).get("next_cursor")
    return dois[:limit]


def from_dois_file(path):
    with open(path) as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def from_csv(path, doi_col="doi"):
    with open(path, newline="") as f:
        return [row[doi_col].strip() for row in csv.DictReader(f) if row.get(doi_col, "").strip()]
