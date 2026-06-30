"""worktype — classify OpenAlex/Crossref works into the canonical 25-type taxonomy, in parallel."""
import argparse
import sys

from . import sources
from .pipeline import run


def build_parser():
    p = argparse.ArgumentParser(
        prog="worktype",
        description="Enrich (OpenAlex + Crossref + taxicab + live landing-page) and annotate work types "
                    "with Claude, in parallel. Repeatable and resumable.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sample", type=int, metavar="N", help="random sample of N Crossref works from OpenAlex")
    src.add_argument("--dois", metavar="FILE", help="file with one DOI per line")
    src.add_argument("--csv", metavar="FILE", help="CSV file with a DOI column (see --doi-col)")
    src.add_argument("--filter", metavar="OPENALEX_FILTER",
                     help="classify all works matching an OpenAlex filter (e.g. 'type:editorial'), capped by --limit")

    p.add_argument("--seed", type=int, default=42, help="random seed for --sample (default 42, reproducible)")
    p.add_argument("--doi-col", default="doi", help="DOI column name for --csv (default: doi)")
    p.add_argument("--limit", type=int, default=1000, help="cap for --filter (default 1000)")
    p.add_argument("--sample-filter", default="indexed_in:crossref,from_publication_date:2006-01-01",
                   help="OpenAlex filter applied to --sample. Default restricts to Crossref works from the "
                        "last ~20 years (from_publication_date:2006-01-01); override to widen/narrow the window.")

    p.add_argument("-o", "--out", default="worktype_out",
                   help="output prefix; writes <prefix>.jsonl and <prefix>.csv (default: worktype_out)")
    p.add_argument("-w", "--workers", type=int, default=50,
                   help="concurrent worker threads (default 50; ~100 is fine — the SDK backs off on 429)")
    p.add_argument("--model", default="claude-opus-4-8", help="Claude model id (default: claude-opus-4-8)")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                   help="reasoning effort (default: medium)")
    p.add_argument("--mailto", default="rohan.mantena@gmail.com",
                   help="email for the OpenAlex/Crossref polite pool")
    p.add_argument("--no-landing-check", action="store_true",
                   help="skip the live landing-page health probe (faster; disables the broken-by-page signal)")
    p.add_argument("--no-annotate", action="store_true",
                   help="enrich only; skip the Claude annotation step (no API key needed)")
    p.add_argument("--no-resume", action="store_true",
                   help="ignore any existing <prefix>.jsonl and reprocess everything")
    return p


def collect_dois(args):
    if args.sample is not None:
        return sources.from_sample(args.sample, args.seed, args.mailto, args.sample_filter)
    if args.dois:
        return sources.from_dois_file(args.dois)
    if args.csv:
        return sources.from_csv(args.csv, args.doi_col)
    return sources.from_filter(args.filter, args.limit, args.mailto)


def main(argv=None):
    args = build_parser().parse_args(argv)
    dois = collect_dois(args)
    if not dois:
        print("[worktype] no DOIs collected from the chosen source", file=sys.stderr)
        return 1
    run(
        dois,
        out_prefix=args.out,
        mailto=args.mailto,
        workers=args.workers,
        model=args.model,
        effort=args.effort,
        landing_check=not args.no_landing_check,
        resume=not args.no_resume,
        annotate=not args.no_annotate,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
