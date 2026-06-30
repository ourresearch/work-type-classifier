# Work-type descriptions — DRAFT v8

Annotator-grade descriptions for the **25 canonical types** (the #534 list plus `book-review`, added 2026-06-29).
Each entry is laid out as: a **definition** paragraph (concept only — no example list), then bulleted fields —
**Includes** (the examples) and **Goes elsewhere** (common misfiles).

**Source trust order:** (1) our **notes for annotators** — authoritative, we wrote them; (2) WoS document-type
descriptions; (3) Scopus; (4) the OpenAlex API's existing `type` text — **least trusted**, being replaced.
Where sources conflict, higher trust wins. See EXPLORE.md for the full table + per-type grounding status.

> v4: reformatted to bulleted fields. v5: shortened definitions. v6: `Goes elsewhere` → sub-bullets, removed
> `Boundary` bullets, WoS confined to its bullet.
> v7 (2026-06-29): definitions no longer duplicate the `Includes` examples (examples live only in `Includes`).
> v8 (2026-06-30): removed all `WoS` bullets (the WoS↔OpenAlex crosswalk lives in EXPLORE.md); dropped the
> remaining `Signal`/`Note` bullets.

## Order of precedence

When a work could match more than one of these overlapping types, assign the **first** that applies, in this order:

1. `retraction`
2. `preprint`
3. `conference-paper` / `conference-abstract`
4. `review`
5. `article`
6. `other`

(Types outside this list — `book`, `book-chapter`, `dataset`, `dissertation`, etc. — are assigned from their own clear signals and don't need tie-breaking.) This ordering is classifier logic and also belongs in the #534 classification spec.

---

## article

Reports of new, original, citable research, usually in a journal. Usually includes an author, abstract, graphs, tables, and cited references.

- **Includes:** research papers, brief communications, technical notes, chronologies, case reports presented as full papers.
- **Goes elsewhere:**
  - a critical survey of existing research → `review`
  - a full paper presented at a conference → `conference-paper`
  - a conference abstract → `conference-abstract`
  - a pre-publication version → `preprint`

## book

A scholarly book published as a complete, standalone volume. Typically has an ISBN and a publisher.

- **Includes:** monographs, authored and edited volumes (as a whole), scholarly reference books (as a whole).
- **Goes elsewhere:**
  - a single chapter → `book-chapter`
  - a single entry in a reference work → `reference-entry`

## book-chapter

A single chapter or section within a book, sometimes presenting original research. Usually has its own title, authors, and cited references.

- **Includes:** contributed chapters in edited volumes, sections of authored books.
- **Goes elsewhere:**
  - the book as a whole → `book`
  - an encyclopedia/dictionary entry → `reference-entry`

## book-review

A critical appraisal of a single book — its organization, writing style, and significance. Usually short, published in a journal's book-review section, with few or no cited references. Distinct from `peer-review`, which is always labelled "peer review."

- **Includes:** book reviews, review essays centered on a specific book.
- **Goes elsewhere:**
  - a report or comment about a non-book work (e.g. a referee report on a paper) → `peer-review`
  - a critical survey of *many* works → `review`

## conference-abstract

An abstract or extended abstract presented (or to be presented) at a symposium or conference, published without the full paper. Usually brief, grouped in a supplement, with few or no cited references.

- **Includes:** meeting abstracts, published abstracts, poster abstracts, abstract-only proceedings records.
- **Goes elsewhere:**
  - the full proceedings paper → `conference-paper`
  - a journal article → `article`

## conference-paper

A full paper presented at a conference, symposium, or meeting, generally published in proceedings. Reports original work much like a journal article.

- **Includes:** proceedings papers; review articles delivered at a conference.
- **Goes elsewhere:**
  - an abstract-only record → `conference-abstract`
  - a journal article → `article`

## data-paper

A peer-reviewed paper whose main purpose is to describe a dataset — its collection, access, and features (metadata) — rather than to analyze it.

- **Includes:** data descriptors, "data articles" (e.g. *Scientific Data*, *Data in Brief*).
- **Goes elsewhere:**
  - the dataset itself → `dataset`
  - a normal research article that merely *uses* data → `article`

## dataset

The data artifact itself, deposited in a repository and typically with its own DOI — not a paper about the data.

- **Includes:** deposited datasets, data collections, database records.
- **Goes elsewhere:**
  - the paper describing the data → `data-paper`
  - files attached to an article → `supplementary-materials`
  - software/code → `software`

## dissertation

A document submitted in completion of an academic degree or professional qualification.

- **Includes:** PhD and master's theses, dissertations, habilitations.
- **Goes elsewhere:**
  - a journal article derived from a thesis → `article`
  - an institutional technical report → `report`

## editorial

An article giving the opinions of a person, group, or organization on a broad topic (not about one specific work). Usually few cited references.

- **Includes:** editorials, editor's notes, commentaries, interviews, discussions, round-table symposia, conference summaries, research highlights, introductions/prefaces/conclusions.
- **Goes elsewhere:**
  - correspondence from readers → `letter`
  - a formal referee report, reviewer report, or open peer-review report tied to a specific manuscript/work → `peer-review`
  - structural front/back matter (covers, TOC) → `paratext`

## erratum

A correction of errors in a previously published article, issued by the journal; the title cites the corrected article.

- **Includes:** errata, corrigenda, corrections, publisher corrections, additions.
- **Goes elsewhere:**
  - a full withdrawal of a work → `retraction`
  - a complaint or criticism of the article from other authors → `letter`

## letter

Brief correspondence from readers to the journal editor about previously published material. Usually short. (In some fields a "Letter" is a short rapid-communication research article — those belong in `article`.)

- **Includes:** letters to the editor, replies and responses, "Readers Write," "Questions and Answers," reader comments.
- **Goes elsewhere:**
  - opinion/commentary pieces → `editorial`
  - short original research labeled "Letter" → `article`

## libguides

A library research guide (LibGuides) curated by librarians to point users toward resources on a topic or course. A navigation aid, not scholarship.

- **Includes:** LibGuides platform pages.
- **Goes elsewhere:**
  - an entry in a reference work → `reference-entry`
  - other miscellaneous web records → `other`

## other

A work that fits no other type. Catch-all only. Institutional repositories deposit lots of non-scholarly material here — photographs, video, audio, and the like — that is generally not of interest.

- **Includes:** news items, obituaries and biographies, full journal issues, non-scholarly repository items (photographs, video, audio, etc.), other miscellaneous records.
- **Goes elsewhere:**
  - anything that fits a specific type belongs there instead

## paratext

Records that package or frame a publication rather than carry its content. Often auto-generated from issue/book structure.

- **Includes:** covers, title pages, tables of contents, mastheads, author/submission guidelines, index records.
- **Goes elsewhere:**
  - substantive editor-written content → `editorial`
  - non-fitting miscellaneous works → `other`

## peer-review

A document that identifies itself as a peer review — its title or text says the words "peer review" (or "referee report" / "reviewer report"). A formal artifact of the review process for a single work, not a standalone editorial or comment.

- **Includes:** open peer-review reports, referee reports, reviewer reports, review histories, author responses attached to formal open review.
- **Goes elsewhere:**
  - a survey of *many* works → `review`
  - a review of a single book → `book-review`
  - a standalone published comment, reply, perspective, discussion, or editorial about a work → `editorial` or `letter`, depending on format

## preprint

An article whose primary location is a preprint repository — e.g. arXiv, bioRxiv, medRxiv, chemRxiv, SSRN, Research Square, Preprints.org, OSF Preprints, RePEc, SciELO Preprints, TechRxiv.

- **Goes elsewhere:**
  - the published version → `article`
  - institutional working papers → `report`

## reference-entry

A self-contained entry within a reference work — one of many entries in a larger volume.

- **Includes:** encyclopedia articles, dictionary entries, handbook/companion entries.
- **Goes elsewhere:**
  - a chapter in a regular book → `book-chapter`
  - the reference work as a whole → `book`

## report

A technical report or working paper issued by an institution, agency, or company outside the journal system.

- **Includes:** technical reports, working papers, white papers, government and agency reports.
- **Goes elsewhere:**
  - a repository-hosted pre-publication article → `preprint`
  - a degree thesis → `dissertation`

## retraction

A published statement announcing the retraction of a manuscript and the reason; it must state the item is retracted, and cites the original work.

- **Includes:** retraction notices, withdrawal notices.
- **Goes elsewhere:**
  - a correction that amends rather than withdraws → `erratum`
  - an article that has itself been retracted (the same article, its title changed to "Retracted: <original title>") → keeps its own type, e.g. `article`. This is an article that *has been* retracted, not a *retraction* notice.

## review

A journal article that critically surveys previously published research, summarizing prior studies without presenting new findings.

- **Includes:** review articles, literature reviews, mini-reviews, systematic reviews, meta-analyses.
- **Goes elsewhere:**
  - a review of a *single* work → `peer-review`
  - a review of a single book → `book-review`
  - a review delivered at a conference → `conference-paper`

## software-paper

A peer-reviewed paper whose main purpose is to describe research software — its design, functionality, and use — rather than report results.

- **Includes:** software articles/descriptors (e.g. JOSS papers, *SoftwareX* articles).
- **Goes elsewhere:**
  - the software itself → `software`
  - a research article that merely *uses* software → `article`

## software

A research software package or code released as a citable artifact, typically with its own identifier. The software itself, not a paper about it.

- **Includes:** deposited code and tagged software releases with their own identifier (e.g. Zenodo software DOIs).
- **Goes elsewhere:**
  - the paper describing it → `software-paper`
  - data → `dataset`

## standard

A formal standard from a Standards Development Organization (SDO) or consortium, specifying requirements or methods. Issued and versioned by the standards body.

- **Includes:** ISO/IEEE/W3C/ANSI standards, formal technical specifications.
- **Goes elsewhere:**
  - an institutional technical report → `report`

## supplementary-materials

Supporting materials accompanying a primary work, usually a journal article. Subordinate to the parent work; often labeled "Supporting Information."

- **Includes:** supporting-information files, supplementary figures/tables/appendices attached to a parent work.
- **Goes elsewhere:**
  - a standalone dataset → `dataset`
  - a standalone work → its own type

---

## Decisions

### Resolved

1. **`article` ⟷ `conference-paper`** — ✅ Conference articles are **not** within `article`; full conference papers route to `conference-paper`. Supersedes the #534 "journal and conference articles" wording (reconciled in #534's `PROPOSAL-taxonomy.md`).
2. **Published abstracts** — ✅ → `conference-abstract`, not `article`.
3. **Not-adopted neighbors:**
   - `book-review` → ✅ **its own type** (separated from `peer-review`; adds a 25th canonical type).
   - `news` → ✅ `other`.
   - `expression-of-concern` → ✅ **removed for now** — no mapping; revisit later. (Records keep whatever type they already have.)
4. **`article` no longer "a review of existing research"** — ✅ removed; reviews are their own type (`review`).
5. **`data-paper` definition** — ✅ grounded in the WoS *Data Paper* text.
6. **Source trust** — ✅ WoS > OpenAlex API; annotator notes authoritative.
7. **`editorial` framing** — ✅ "opinion on a broad topic"; WoS Editorial Material breadth; standalone commentary/discussion/framing stays in `editorial` unless it is a formal peer-review artifact.
8. **`peer-review`** — ✅ main feature: the document says the words "peer review" somewhere; it is a formal review-process artifact about one target work.
9. **`book-review`** — ✅ its own type; dropped the WoS "reviewed book = source title / reviewer = author" claim (WoS-specific, not how OpenAlex works); distinct from `peer-review` (which is always labelled "peer review").

### Still open

10. **`software-paper` / `software` definitions** — WoS has no equivalent doc type (only *Software Review*, an appraisal). Still modeled on `data-paper`/`dataset`. Confirm wording.
11. **`review` operational rule** — adopt WoS's "must have references + title-claim must recur in body" as the definition, or keep OpenAlex's venue-derived rule? (Classifier is a #534 question.)
