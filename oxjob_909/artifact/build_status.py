"""Generate the self-contained oxjob #909 status artifact (status.html).

Recomputes the per-type hit-rates from the locked test split so the chart is accurate; the
leaderboard, info-gain table, and confusion examples are stable results pasted as narrative.
Output is a single CSP-safe HTML page (inline CSS, no external requests). Run:

    python -m oxjob_909.artifact.build_status
"""
from __future__ import annotations

import os
from collections import Counter

from ..splits import split_data
from .. import tree as treemod

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "status.html")


def per_type_hitrates():
    d = split_data(("train", "test"))
    tr, te = d["train"], d["test"]
    t = treemod.train_residual_tree(tr[0], tr[1])
    pred, _ = treemod.hybrid_predict(te[0], t)
    yt = te[1]
    types = sorted(set(yt), key=lambda c: -Counter(yt)[c])
    rows = []
    for ty in types:
        idx = [i for i, x in enumerate(yt) if x == ty]
        n = len(idx)
        if n < 10:
            continue
        c = sum(1 for i in idx if pred[i] == ty)
        rows.append((ty, n, c, c / n))
    return rows


LEADERBOARD = [
    ("I0", "keep oa_type (baseline)", "val", "0.716", "0.526", "0.711 / 0.986", "reference"),
    ("I1", "de-leaked LR (no oa_type)", "val", "0.775", "0.551", "0.798 / 0.976", "honest signal floor"),
    ("I3", "deterministic cascade only", "val", "0.699", "0.344", "0.661 / 0.994", "rules, 32% coverage"),
    ("I4", "hybrid cascade→tree", "val", "0.763", "0.523", "0.825 / 0.947", "deployable, gap −0.003"),
    ("I6", "+ paratext title rule", "val", "0.768", "0.540", "0.821 / 0.953", "paratext P 0.56→0.88"),
    ("I7", "+ openalex-guts detective", "val", "0.771", "0.535", "0.814 / 0.966", "journal-issue cr_type signal"),
    ("I5", "final hybrid (locked test)", "TEST", "0.773", "0.538", "0.812 / 0.945", "ship"),
]

INFOGAIN = [
    ("frontmatter", "0.0051", 12, 12, "1.00"),
    ("abbreviations", "0.0039", 9, 9, "1.00"),
    ("contents", "0.0150", 37, 36, "0.97"),
    ("front (matter)", "0.0060", 24, 18, "0.75"),
    ("editorial board", "0.0102", 42, 31, "0.74"),
    ("cover", "0.0052", 25, 17, "0.68"),
    ("index", "0.0095", 72, 37, "0.51"),
]

CONFUSIONS = [
    ("paratext → article", "BIM volume 13 issue 1 Cover and Back matter", "“explicitly says Cover and Back matter”",
     "model had no title-token feature — only title_len"),
    ("paratext → article", "Contributors", "“front/back-matter packaging record”", "title_len(1) ≈ a short article"),
    ("paratext → article", "Expediente", "“journal masthead / front-matter”", "non-English masthead, invisible to title_len"),
    ("article → paratext", "pina bausch", "(real article in a dance magazine)", "title_len(2) wrongly flagged paratext"),
]


def bar(label, pct, highlight=False):
    color = "#16a34a" if pct >= 0.75 else "#f59e0b" if pct >= 0.45 else "#dc2626"
    cls = " hl" if highlight else ""
    return (f'<div class="row{cls}"><div class="lab">{label}</div>'
            f'<div class="track"><div class="fill" style="width:{pct*100:.0f}%;background:{color}"></div></div>'
            f'<div class="val">{pct*100:.0f}%</div></div>')


def build():
    rows = per_type_hitrates()
    hl = {"article", "paratext", "editorial"}
    bars = "\n".join(bar(f"{ty} (n={n})", r, ty in hl) for ty, n, c, r in rows)

    lb = "\n".join(
        f"<tr class='{'ship' if it=='I5' else ''}'><td>{it}</td><td>{what}</td><td>{sp}</td>"
        f"<td>{a}</td><td>{m}</td><td>{ap}</td><td class='muted'>{nt}</td></tr>"
        for it, what, sp, a, m, ap, nt in LEADERBOARD)

    ig = "\n".join(f"<tr><td><code>{tk}</code></td><td>{ig}</td><td>{nt}</td><td>{npos}</td>"
                   f"<td class='{'good' if float(pr)>=0.7 else ''}'>{pr}</td></tr>"
                   for tk, ig, nt, npos, pr in INFOGAIN)

    conf = "\n".join(f"<tr><td><span class='tag'>{d}</span></td><td><code>{t}</code></td>"
                     f"<td class='muted'>{r}</td><td>{w}</td></tr>"
                     for d, t, r, w in CONFUSIONS)

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>oxjob #909 — work-type classifier</title>
<style>
  :root {{ --bg:#f8fafc; --card:#fff; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --accent:#4f46e5; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 24px 64px; }}
  header h1 {{ margin:0 0 4px; font-size:26px; letter-spacing:-.02em; }}
  header p {{ margin:0; color:var(--muted); }}
  .badges {{ display:flex; gap:10px; flex-wrap:wrap; margin:18px 0 8px; }}
  .badge {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; }}
  .badge b {{ display:block; font-size:20px; color:var(--accent); }}
  .badge span {{ font-size:12px; color:var(--muted); }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:20px 22px; margin:18px 0; }}
  h2 {{ font-size:16px; margin:0 0 14px; letter-spacing:.01em; }}
  h2 .n {{ color:var(--accent); font-weight:700; margin-right:8px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th,td {{ text-align:left; padding:7px 9px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
  tr.ship td {{ background:#eef2ff; font-weight:600; }}
  .muted {{ color:var(--muted); }} .good {{ color:#16a34a; font-weight:600; }}
  code {{ background:#f1f5f9; padding:1px 6px; border-radius:5px; font-size:12.5px; }}
  .tag {{ font-size:11px; font-weight:600; color:#fff; background:var(--accent); padding:2px 8px; border-radius:999px; white-space:nowrap; }}
  .row {{ display:grid; grid-template-columns:170px 1fr 44px; align-items:center; gap:10px; margin:5px 0; }}
  .row.hl .lab {{ font-weight:700; }}
  .lab {{ font-size:12.5px; }} .val {{ font-size:12.5px; text-align:right; color:var(--muted); }}
  .track {{ background:#f1f5f9; border-radius:5px; height:14px; overflow:hidden; }}
  .fill {{ height:100%; border-radius:5px; }}
  .note {{ font-size:12.5px; color:var(--muted); margin-top:10px; }}
  .key {{ font-size:12px; color:var(--muted); margin-top:8px; }}
  .lead {{ color:#334155; }}
</style></head>
<body><div class="wrap">
<header>
  <h1>oxjob #909 — work-type classifier</h1>
  <p>De-leaked, interpretable, Databricks-deployable. ML discovers signals; the deployable is a
     deterministic cascade + a shallow decision tree.</p>
</header>

<div class="badges">
  <div class="badge"><b>0.773</b><span>test accuracy (vs 0.716 baseline)</span></div>
  <div class="badge"><b>0.812</b><span>article precision (not sacrificed)</span></div>
  <div class="badge"><b>≈0</b><span>train/val gap (not overfit)</span></div>
  <div class="badge"><b>~15</b><span>features (no TF-IDF tokens)</span></div>
</div>

<section>
  <h2><span class="n">What</span>this is</h2>
  <p class="lead">A small, auditable classifier that corrects OpenAlex's <code>type</code> field. We
  removed the <b>circular</b> features (OpenAlex's own <code>oa_type</code>/<code>is_paratext</code>),
  kept raw Crossref signals, and engineered ~15 interpretable features. The deployable is a
  <b>deterministic rule cascade</b> (clean types, exported to Spark SQL) feeding a <b>depth-6 decision
  tree</b> for the fuzzy article↔editorial/review residual. Headline metric is the article-boundary
  scorecard, not overall accuracy.</p>
</section>

<section>
  <h2><span class="n">Progress</span>iteration leaderboard</h2>
  <table>
    <tr><th>iter</th><th>what</th><th>split</th><th>acc</th><th>macro-F1</th><th>article P / R</th><th>note</th></tr>
    {lb}
  </table>
  <p class="note">Every iteration is logged append-only in <code>JOURNAL.md</code> (autoresearch-style).
  The de-leaked LR (I1) edges the hybrid on macro-F1 but isn't SQL-deployable; the hybrid is.</p>
</section>

<section>
  <h2><span class="n">Per-type</span>prediction success (locked test, n=2,146)</h2>
  {bars}
  <p class="key">● green ≥75% · ● amber 45–74% · ● red &lt;45%. Bold = the types the team watches.
  <b>Article is not sacrificed</b> (93%) while the big OpenAlex errors are recovered (conference-paper
  0→73%, conference-abstract 0→49%). Editorial, book-review, reference-entry are the open cells.</p>
</section>

<section>
  <h2><span class="n">Deep-dive</span>paratext — a vocabulary type (iteration I6)</h2>
  <p class="lead">Paratext errors are decided by <b>title words</b> the de-leaked model couldn't see (it
  had only <code>title_len</code>). Examples from the held-out set:</p>
  <table>
    <tr><th>direction</th><th>title</th><th>opus reason</th><th>why the model missed</th></tr>
    {conf}
  </table>
  <p class="lead" style="margin-top:16px">We ranked title tokens by <b>precision×support</b> (raw
  information gain just surfaces stopwords) and turned the winners into one anchored, deterministic
  <code>title:paratext</code> rule — <b>0.99 precision</b>, info-gain-selected:</p>
  <table>
    <tr><th>token</th><th>info-gain</th><th>titles</th><th>#paratext</th><th>precision</th></tr>
    {ig}
  </table>
  <p class="note"><b>I6 result:</b> paratext precision <b>0.56 → 0.88</b> (the rule kills the
  <code>title_len</code> false alarms on short real articles). Gini/info-gain are already the tree's
  split criterion — the fix was giving them the right binary feature, not changing the criterion.<br>
  <b>I7 result:</b> referencing the OpenAlex production detective (<code>openalex-guts
  work_type_detective.py</code>) added a richer title vocabulary <i>and</i> the structured
  <code>cr_type=journal-issue</code> signal (<b>65/66 paratext</b> on gold) — the non-title signal that
  breaks the vocabulary ceiling. Paratext recall rises (test 0.32→0.36; the rule alone is 0.99 precision
  / 0.57 recall gold-wide) with precision held at 0.91.</p>
</section>

<section>
  <h2><span class="n">Next</span>roadmap</h2>
  <ul class="lead">
    <li><b>Editorial (~0.19 recall)</b> — the hard article-boundary cell; try venue/section priors and first-page position.</li>
    <li><b>Paratext recall</b> — I7 added the <code>journal-issue</code> cr_type signal (recall 0.32→0.36); next, page-position / front-of-issue for the long tail.</li>
    <li><b>book-review / reference-entry</b> — dedicated sub-trees under the ISBN/book family.</li>
    <li><b>Confidence routing</b> — threshold on tree-leaf purity; send low-confidence works to the Opus labeler.</li>
    <li><b>Fold in <code>gold_master</code> / <code>gold_targeted</code></b> — the newer growing gold for the tail types.</li>
  </ul>
</section>

<p class="key">Repo: <code>oxjob_909/</code> · deterministic layer: <code>cascade.sql</code> ·
experiment log: <code>JOURNAL.md</code> · generated from the locked-test split.</p>
</div></body></html>
"""
    os.makedirs(HERE, exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    return OUT


if __name__ == "__main__":
    p = build()
    print("wrote", p, f"({os.path.getsize(p)//1024} KB)")
