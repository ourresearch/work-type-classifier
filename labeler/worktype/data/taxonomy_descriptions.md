# Work-type descriptions — DRAFT v5

Annotator-grade descriptions for the **25 canonical types** (the #534 list plus `book-review`, added 2026-06-29).
Each entry is laid out as: a **definition** paragraph, then bulleted fields — **Includes**, **Goes elsewhere**
(common misfiles), **Boundary** (rule vs. nearest neighbors), and **Signal** / **WoS** / **Note** where relevant.

**Source trust order** (Casey, 2026-06-29): (1) our **notes for annotators** — authoritative, we wrote them;
(2) WoS document-type descriptions; (3) Scopus; (4) the OpenAlex API's existing `type` text — **least
trusted**, being replaced. Where sources conflict, higher trust wins. See EXPLORE.md for the full table +
per-type grounding status. Where this draft **diverges** from WoS or revises #534 wording, it's flagged ⚠️.

> v2: rewrote in WoS style. v3: re-grounded ~10 types in WoS doc-type text. v4: reformatted to bulleted
> fields; `book-review`/`book-chapter`/`conference-abstract`/`peer-review` fixes.
> v5 (2026-06-29): shortened the definition paragraphs (content unchanged; bullets kept).

---

## article

Reports of new, original, citable research published in a journal — research papers, brief communications, technical notes, chronologies, full papers, and case reports presented as full papers. Usually includes an author, abstract, graphs, tables, and cited references.

- **Includes:** research papers, brief communications, technical notes, chronologies, case reports presented as full papers.
- **Goes elsewhere:** a critical survey of existing research → `review` (a review is its own type, **not** an article); a full paper presented at a conference → `conference-paper`; a conference abstract → `conference-abstract`; a pre-publication version → `preprint`.
- **Boundary:** original-research full text in a journal.
- **Note:** ✅ Confirmed (Casey 2026-06-29) — does NOT include reviews of existing research (→ `review`) or conference articles (→ `conference-paper`/`conference-abstract`). ⚠️ Diverges from WoS, which folds conference papers/abstracts (and reviews delivered at conferences) into article.

## book

A scholarly book published as a complete, standalone volume — monographs, authored/edited volumes as a whole, and reference works in their entirety. Typically has an ISBN and a publisher.

- **Includes:** monographs, authored and edited volumes (as a whole), scholarly reference books (as a whole).
- **Goes elsewhere:** a single chapter → `book-chapter`; a single entry in a reference work → `reference-entry`.
- **Boundary:** the whole book, not its parts.

## book-chapter

A single chapter or section within a book, sometimes presenting original research. Usually has its own title, authors, and cited references.

- **Includes:** contributed chapters in edited volumes, sections of authored books.
- **Goes elsewhere:** the book as a whole → `book`; an encyclopedia/dictionary entry → `reference-entry`.
- **Boundary:** a part of a book vs. the whole; vs. `reference-entry`, which is specifically an entry in a *reference* work.

## book-review

A critical appraisal of a single book — its organization, writing style, and significance — often reflecting the reviewer's opinion. Usually short, published in a journal's book-review section, with few or no cited references.

- **Includes:** book reviews, review essays centered on a specific book.
- **Goes elsewhere:** a report or comment about a non-book work (e.g. a referee report on a paper) → `peer-review`; a critical survey of *many* works → `review`.
- **Boundary:** about a **single book** specifically — distinct from `peer-review` (a report/comment on one work generally) and `review` (a survey of the literature). ✅ Per Casey (2026-06-29): its own type, separated from `peer-review`.
- **Signal:** the document typically says the words "book review," and the title of the review usually includes the title of the book being reviewed.
- **WoS:** Book Review. ⚠️ WoS processes the reviewed book as the source title and the reviewer as the author — that is WoS-specific and is **not** how OpenAlex handles it.

## conference-abstract

An abstract or extended abstract presented (or to be presented) at a symposium or conference, published without the full paper. Usually brief, grouped in a supplement, with few or no cited references.

- **Includes:** meeting abstracts, published abstracts, poster abstracts, abstract-only proceedings records.
- **Goes elsewhere:** the full proceedings paper → `conference-paper`; a journal article → `article`.
- **Boundary:** **abstract only, no full text.** ✅ Per Casey (2026-06-29): published/meeting abstracts belong here, deliberately *not* in `article`.
- **WoS:** Meeting Abstract / Meeting / Meeting Summary.

## conference-paper

A full paper presented at a conference, symposium, or meeting, generally published in proceedings. Reports original work much like a journal article.

- **Includes:** proceedings papers; review articles delivered at a conference (WoS processes conference reviews as proceedings papers, not as `review`).
- **Goes elsewhere:** an abstract-only record → `conference-abstract`; a journal article → `article`.
- **Boundary:** full text published in a conference/proceedings venue, vs. an abstract; venue distinguishes it from `article`.
- **WoS:** Proceedings Paper — WoS dual-types it as Article; Proceedings Paper, whereas OpenAlex keeps it distinct from `article`.

## data-paper

A peer-reviewed paper whose main purpose is to describe a dataset — its collection, access, and features (metadata) — rather than to analyze it.

- **Includes:** data descriptors, "data articles" (e.g. *Scientific Data*, *Data in Brief*).
- **Goes elsewhere:** the dataset itself → `dataset`; a normal research article that merely *uses* data → `article`.
- **Boundary:** the narrative paper *about* a dataset vs. the dataset.
- **WoS:** Data Paper — WoS dual-types it as Article; Data Paper.

## dataset

A record describing one or more data collections deposited in a repository — the data artifact itself, typically with its own DOI, not a paper.

- **Includes:** datasets and data collections deposited in a repository, database records.
- **Goes elsewhere:** the paper describing the data → `data-paper`; files attached to an article → `supplementary-materials`; software/code → `software`.
- **Boundary:** the data artifact itself, not the paper about it.

## dissertation

A document submitted in completion of an academic degree or professional qualification — doctoral and master's theses, dissertations, and habilitations.

- **Includes:** PhD and master's theses, dissertations, habilitations.
- **Goes elsewhere:** a journal article derived from a thesis → `article`; an institutional technical report → `report`.
- **Boundary:** a degree-/qualification-completion document.

## editorial

An article giving the opinions of a person, group, or organization on a broad topic (not about one specific work) — editorials, commentaries, interviews, discussions, research highlights, and introductions/prefaces/conclusions. Usually few cited references.

- **Includes:** editorials, editor's notes, commentaries, interviews, discussions, round-table symposia, conference summaries, research highlights, introductions/prefaces/conclusions.
- **Goes elsewhere:** correspondence from readers → `letter`; a formal referee report, reviewer report, or open peer-review report tied to a specific manuscript/work → `peer-review`; structural front/back matter (covers, TOC) → `paratext`.
- **Boundary:** **opinion on a broad topic** — opinion, commentary, discussion, or framing content. If it is a formal artifact of peer review rather than an editorial/commentary article, use `peer-review`.
- **WoS:** Editorial Material.

## erratum

A correction of errors in a previously published article. Includes errata, corrigenda, and additions; the title cites the corrected article.

- **Includes:** errata, corrigenda, corrections, publisher corrections, additions.
- **Goes elsewhere:** a full withdrawal of a work → `retraction`.
- **Boundary:** amends a work, rather than withdrawing it. (This is the *correction notice* record.)
- **WoS:** Correction — note WoS processed retractions as corrections prior to 2016.

## letter

Brief correspondence from readers to the journal editor about previously published material — letters to the editor, replies, and comments. Usually short. (In some fields a "Letter" is a short rapid-communication research article — those belong in `article`.)

- **Includes:** letters to the editor, replies and responses, "Readers Write," "Questions and Answers," reader comments.
- **Goes elsewhere:** opinion/commentary pieces → `editorial`; short original research labeled "Letter" → `article`.
- **Boundary:** reader/author correspondence about previously published material.
- **WoS:** Letter.

## libguides

A library research guide (LibGuides) curated by librarians to point users toward resources on a topic or course. A navigation aid, not scholarship.

- **Includes:** LibGuides platform pages.
- **Goes elsewhere:** an entry in a reference work → `reference-entry`; other miscellaneous web records → `other`.
- **Boundary:** a library-curated guide, not original or peer-reviewed scholarship.

## other

A work that fits no other type — news items, obituaries and biographies, full journal issues, and miscellaneous records. Catch-all only.

- **Includes:** news items, obituaries and biographies, full journal issues, other miscellaneous records.
- **Goes elsewhere:** anything that fits a specific type belongs there instead.
- **Boundary:** genuine catch-all.

## paratext

Covers, tables of contents, mastheads, and other records that package a publication rather than carry its content. Often auto-generated from issue/book structure.

- **Includes:** covers, title pages, tables of contents, mastheads, author/submission guidelines, index records.
- **Goes elsewhere:** substantive editor-written content → `editorial`; non-fitting miscellaneous works → `other`.
- **Boundary:** structural/packaging material *around* the content, not content itself.

## peer-review

A formal peer-review artifact about a single work — an open peer-review report, referee/reviewer report, review history, or author response in an open-review package. Part of a review process, not a standalone editorial or comment.

- **Includes:** open peer-review reports, referee reports, reviewer reports, review histories, author responses attached to formal open review.
- **Goes elsewhere:** a survey of *many* works → `review`; a review of a single book → `book-review`; a standalone published comment, reply, perspective, discussion, or editorial about a work → `editorial` or `letter`, depending on format.
- **Boundary:** a formal review-process artifact about one target work, not merely any commentary about one work.
- **Signal:** the document typically says the words "peer review" (also "referee report" / "reviewer report"); title, venue, relation type, or source metadata may also identify it as an open-review artifact.

## preprint

An article whose primary version precedes peer-reviewed publication, or is hosted in a preprint repository (arXiv, bioRxiv, medRxiv, SSRN).

- **Includes:** arXiv/bioRxiv/medRxiv/SSRN preprints, working versions preceding formal publication.
- **Goes elsewhere:** the published version → `article`; institutional working papers → `report`.
- **Boundary:** a pre-publication or repository-hosted version.
- **WoS:** no analog — WoS "Early Access" is the version-of-record before volume/issue assignment, **not** a preprint; do not crosswalk them.

## reference-entry

A self-contained entry within a reference work such as an encyclopedia, dictionary, or handbook — one of many entries in a larger volume.

- **Includes:** encyclopedia articles, dictionary entries, handbook/companion entries.
- **Goes elsewhere:** a chapter in a regular book → `book-chapter`; the reference work as a whole → `book`.
- **Boundary:** an entry specifically within a *reference* work.

## report

A technical report or working paper issued by an institution, agency, or company outside the journal system — technical reports, working papers, white papers, government reports.

- **Includes:** technical reports, working papers, white papers, government and agency reports.
- **Goes elsewhere:** a repository-hosted pre-publication article → `preprint`; a degree thesis → `dissertation`.
- **Boundary:** an institutional/technical report, vs. a journal article.

## retraction

A published statement announcing the retraction of a manuscript and the reason; it must state the item is retracted, and cites the original work.

- **Includes:** retraction notices, withdrawal notices.
- **Goes elsewhere:** a correction that amends rather than withdraws → `erratum`.
- **Boundary:** withdrawal vs. correction. (This is the *retraction notice* record; the retracted work itself keeps its own type.)
- **WoS:** Retraction — distinct from "Retracted Publication," which is the original article. Prior to 2016 WoS processed retractions as corrections.

## review

A journal article that critically surveys previously published research, summarizing prior studies without presenting new findings — review articles, literature reviews, mini-reviews, systematic reviews. Per WoS, it has cited references and the review claim should recur in the abstract or introduction.

- **Includes:** review articles, literature reviews, mini-reviews, systematic reviews.
- **Goes elsewhere:** a review of a *single* work → `peer-review`; a review of a single book → `book-review`; a review delivered at a conference → `conference-paper`.
- **Boundary:** about **multiple** works, no new original research, has references.
- **WoS:** Review.

## software-paper

A peer-reviewed paper whose main purpose is to describe research software — its design, functionality, and use — rather than report results (e.g. JOSS, *SoftwareX* articles).

- **Includes:** software articles/descriptors (e.g. JOSS papers, *SoftwareX* articles).
- **Goes elsewhere:** the software itself → `software`; a research article that merely *uses* software → `article`.
- **Boundary:** the narrative paper *about* software vs. the software artifact.
- **Note:** ⚠️ No WoS equivalent — proposed definition (modeled on `data-paper`).

## software

A research software package or code released as a citable artifact, typically with its own identifier (e.g. a Zenodo DOI). The software itself, not a paper about it.

- **Includes:** deposited code and tagged software releases with their own identifier (e.g. Zenodo software DOIs).
- **Goes elsewhere:** the paper describing it → `software-paper`; data → `dataset`.
- **Boundary:** the software artifact itself.
- **Note:** ⚠️ No WoS equivalent — proposed definition (modeled on `dataset`).

## standard

A formal standard from a Standards Development Organization (SDO) or consortium (ISO, IEEE, W3C, ANSI), specifying requirements or methods. Issued and versioned by the standards body.

- **Includes:** ISO/IEEE/W3C/ANSI standards, formal technical specifications.
- **Goes elsewhere:** an institutional technical report → `report`.
- **Boundary:** a formally issued standard.

## supplementary-materials

Supporting materials accompanying a primary work, usually a journal article — supporting-information files, figures, tables, appendices. Subordinate to the parent work; often labeled "Supporting Information."

- **Includes:** supporting-information files, supplementary figures/tables/appendices attached to a parent work.
- **Goes elsewhere:** a standalone dataset → `dataset`; a standalone work → its own type.
- **Boundary:** subordinate supplement *to a parent work*, not a standalone artifact.

---

## Decisions

### Resolved (Casey, 2026-06-29)

1. **`article` ⟷ `conference-paper`** — ✅ Conference articles are **not** within `article`; full conference papers route to `conference-paper`. Supersedes the #534 "journal and conference articles" wording (reconciled in #534's `PROPOSAL-taxonomy.md`).
2. **Published abstracts** — ✅ → `conference-abstract`, not `article`.
3. **Not-adopted neighbors:**
   - `book-review` → ✅ **its own type** (reversed 2026-06-29 — separated from `peer-review`; adds a 25th canonical type).
   - `news` → ✅ `other`.
   - `expression-of-concern` → ✅ **removed for now** — no mapping; revisit later. (Records keep whatever type they already have.)
4. **`article` no longer "a review of existing research"** — ✅ removed; reviews are their own type (`review`).
5. **`data-paper` definition** — ✅ now grounded in the WoS *Data Paper* text (no longer from scratch).
6. **Source trust** — ✅ WoS > OpenAlex API; annotator notes authoritative.
7. **`editorial` framing** — ✅ "opinion on a broad topic"; WoS Editorial Material breadth; standalone commentary/discussion/framing stays in `editorial` unless it is a formal peer-review artifact.
8. **`peer-review`** — ✅ a formal review-process artifact about one target work. **Signal:** the document says the words "peer review" (also referee/reviewer report); metadata may also identify it.
9. **`book-review` correction** — ✅ dropped the WoS "reviewed book = source title / reviewer = author" claim (WoS-specific, not how OpenAlex works). **Signal:** says "book review"; title usually includes the reviewed book's title.

### Still open

10. **`software-paper` / `software` definitions** — WoS has no equivalent doc type (only *Software Review*, an appraisal). Still modeled on `data-paper`/`dataset`. Confirm wording.
11. **`review` operational rule** — adopt WoS's "must have references + title-claim must recur in body" as the definition, or keep OpenAlex's venue-derived rule? (Definition implies the former; classifier is a #534 question.)
