"""Enrichment: gather classification signals for a DOI from OpenAlex + Crossref + taxicab + a live landing-page check."""
import gzip
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

TAXICAB_BASE = "http://harvester-load-balancer-366186003.us-east-1.elb.amazonaws.com/taxicab/doi/"
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_META_RE = re.compile(
    r"citation_(title|journal|conference|inbook|book|dissertation)|dc\.type|og:type|article-type|prism\.aggregationType",
    re.I,
)


def _get(url, *, raw=False, timeout=30, ua=None, retries=3):
    headers = {"User-Agent": ua or "worktype-cli/1.0"}
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            time.sleep(0.6 * (attempt + 1))
        except Exception:
            time.sleep(0.6 * (attempt + 1))
    return None


def clean_doi(doi: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip(), flags=re.I)


def _openalex(doi, mailto):
    d = _get(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?mailto={mailto}")
    if not d:
        return {"oa_found": False}
    pl = d.get("primary_location") or {}
    src = pl.get("source") or {}
    b = d.get("biblio") or {}
    return {
        "oa_found": True,
        "oa_id": d.get("id"),
        "oa_title": d.get("title"),
        "oa_type": d.get("type"),
        "oa_type_crossref": d.get("type_crossref"),
        "oa_raw_type": pl.get("raw_type"),
        "oa_is_paratext": d.get("is_paratext"),
        "oa_is_retracted": d.get("is_retracted"),
        "oa_biblio": b,
        "oa_single_page": bool(b.get("first_page") and b.get("first_page") == b.get("last_page")),
        "pages": (f"{b.get('first_page')}-{b.get('last_page')}" if b.get("first_page") else None),
        "oa_has_abstract": bool(d.get("abstract_inverted_index")),
        "oa_n_refs": d.get("referenced_works_count"),
        "oa_source_type": src.get("type"),
        "oa_source_name": src.get("display_name"),
        "oa_landing": pl.get("landing_page_url"),
    }


def _crossref(doi, mailto):
    d = _get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={mailto}")
    if not d or "message" not in d:
        return {"cr_found": False}
    m = d["message"]
    return {
        "cr_found": True,
        "cr_type": m.get("type"),
        "cr_subtype": m.get("subtype"),
        "cr_title": (m.get("title") or [None])[0],
        "cr_container": (m.get("container-title") or [None])[0],
        "cr_isbn": bool(m.get("ISBN")),
        "cr_page": m.get("page"),
    }


def _taxicab(doi):
    d = _get(TAXICAB_BASE + urllib.parse.quote(doi, safe=""))
    if not d:
        return {"tx_found": False}
    html = d.get("html") or []
    out = {
        "tx_found": True,
        "tx_html": len(html),
        "tx_pdf": len(d.get("pdf") or []),
        "tx_resolved_url": (html[0].get("resolved_url") if html else None),
    }
    if html and html[0].get("download_url"):
        body = _get(html[0]["download_url"], raw=True, timeout=30)
        if body:
            try:
                if body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
                txt = body.decode("utf-8", "ignore")
                t = re.search(r"<title[^>]*>(.*?)</title>", txt, re.I | re.S)
                out["tx_page_title"] = re.sub(r"\s+", " ", t.group(1)).strip()[:160] if t else None
                out["tx_meta"] = [
                    re.sub(r"\s+", " ", mt).strip()[:200]
                    for mt in re.findall(r"<meta[^>]+>", txt, re.I)
                    if _META_RE.search(mt)
                ][:8]
            except Exception:
                pass
    return out


def _landing_health(doi):
    """Live DOI resolution. broken => 5xx / not-found / unreachable. 403/401 bot-block is NOT broken."""
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:")
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            head = r.read(4000).decode("utf-8", "ignore")
            nf = bool(re.search(r"not found|page not found|doi not found|error 404|410 gone", head, re.I))
            return {"lp_status": r.status, "lp_final_url": r.geturl(), "lp_reachable": True, "lp_notfound_text": nf}
    except urllib.error.HTTPError as e:
        return {"lp_status": e.code, "lp_final_url": url, "lp_reachable": True, "lp_notfound_text": e.code in (404, 410)}
    except Exception as e:
        return {"lp_status": None, "lp_final_url": url, "lp_reachable": False, "lp_error": type(e).__name__}


def enrich(doi: str, mailto: str, *, landing_check: bool = True) -> dict:
    """Return the full signal record for one DOI. Robust to partial-source failure."""
    doi = clean_doi(doi)
    rec = {"doi": doi}
    if not doi:
        rec["error"] = "empty-doi"
        return rec
    rec.update(_openalex(doi, mailto))
    rec.update(_crossref(doi, mailto))
    rec.update(_taxicab(doi))
    if landing_check:
        rec.update(_landing_health(doi))
    return rec


# fields handed to the annotator (keeps the prompt compact, hides nothing decisive)
SIGNAL_FIELDS = [
    "doi", "oa_title", "oa_type", "oa_type_crossref", "oa_raw_type",
    "oa_source_type", "oa_source_name", "oa_is_paratext", "oa_is_retracted",
    "oa_single_page", "pages", "oa_has_abstract", "oa_n_refs",
    "cr_type", "cr_subtype", "cr_container", "cr_isbn",
    "tx_html", "tx_pdf", "tx_resolved_url", "tx_page_title", "tx_meta",
    "lp_status", "lp_reachable", "lp_notfound_text", "lp_final_url",
]


def signals_for_annotation(rec: dict) -> dict:
    return {k: rec.get(k) for k in SIGNAL_FIELDS}
