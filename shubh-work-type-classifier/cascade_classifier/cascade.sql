-- oxjob #544 — deterministic type cascade as a SQL CASE (Databricks / Spark SQL).
-- This is the rules layer (cascade.py, iteration I3) expressed in pure SQL — no model, no UDF,
-- no external fetch. It assigns the clean/deterministic types and leaves the fuzzy
-- article<->editorial/review residual as NULL (predicted_type IS NULL), which the deployed
-- hybrid hands to the depth-6 decision tree. On the gold set this layer covers ~32% of works
-- deterministically at high per-rule precision (proceedings 0.93, preprint/peer-review/erratum
-- /reference-entry 1.00, retraction 0.93). Rule order matters: most-specific first.
--
-- Expected input columns (map to your OpenAlex/Crossref source):
--   cr_type            -- raw Crossref type (NOT OpenAlex's oa_type — that is circular, excluded)
--   cr_subtype         -- Crossref subtype ('preprint' on posted-content)
--   has_isbn           -- ISBN present (boolean)
--   source_type        -- OpenAlex source type ('journal','repository','conference',...)
--   venue              -- source/container display name (lower-cased for matching)
--   title              -- work title
--   n_refs             -- referenced_works_count
--   single_page        -- first_page = last_page (boolean)
--   has_abstract       -- abstract present (boolean)
--   doi                -- DOI (lower-cased; for preprint DOI-registrant match)

WITH f AS (
  SELECT
    *,
    lower(coalesce(venue, ''))  AS venue_l,
    lower(coalesce(title, ''))  AS title_l,
    lower(coalesce(doi, ''))    AS doi_l,
    (lower(coalesce(venue, '')) RLIKE '(proceedings|symposium|workshop|conference|congress|colloqui)') AS venue_proceedings
  FROM works
)
SELECT
  *,
  CASE
    -- 1. preprint: Crossref subtype is definitive (99% pure on gold)
    WHEN lower(coalesce(cr_subtype,'')) = 'preprint' THEN 'preprint'

    -- I8. single-type source allowlists (oxjob #547 catalog + data/preprint_servers.csv).
    --     NON-circular: keys on venue NAME / DOI registrant, never oa_type. Name-match measured
    --     on held-out gold_master: preprint .939 / dataset 1.00 / conf-abstract .953 / conf-paper
    --     .958; preprint also DOI-registrant .985. Zenodo/Figshare/OSF excluded (dataset-mixed).
    WHEN venue_l IN (
         'african research repository', 'africarxiv', 'agri-archive', 'agrirxiv',
         'aijr preprint server', 'aijr preprints', 'alternative e-print archive', 'apsa preprints',
         'apsa preprints on cambridge open engage', 'arxiv', 'arxiv.org', 'authorea',
         'authorea preprints', 'beilstein archive', 'beilstein archives', 'biohackrxiv',
         'biohackrxiv preprints', 'biology preprint server', 'biorxiv', 'biorxiv (cold spring harbor laboratory)',
         'biorxiv.org', 'cambridge open engage', 'chemrxiv', 'chemrxiv preprints',
         'chinaxiv', 'chinaxiv.org', 'coe', 'criminology archive',
         'crimrxiv', 'cryptology eprint archive', 'e-print archive', 'earth and space science open archive',
         'earth archive', 'eartharxiv', 'easychair preprints', 'eccc',
         'ecoevo archive', 'ecoevorxiv', 'ecs archive', 'ecsarxiv',
         'ecsarxiv preprints', 'edarxiv', 'edarxiv preprints', 'education archive',
         'electronic colloquium on computational complexity', 'engineering archive', 'engrxiv', 'engrxiv preprints',
         'ess open archive', 'ess open archive (essoar)', 'essoar', 'health sciences preprint server',
         'iacr eprint archive', 'in review', 'india archive', 'indianrxiv',
         'indiarxiv', 'japan preprint server', 'jmir preprints', 'jxiv',
         'jxiv (jst, japan)', 'law archive', 'lawarxiv', 'lingbuzz',
         'lingbuzz archive', 'marxiv', 'media archive', 'mediarxiv',
         'mediarxiv preprints', 'medrxiv', 'medrxiv.org', 'metaarxiv',
         'metaarxiv preprints', 'nutrixiv', 'osf preprints', 'paleontology archive',
         'paleorxiv', 'philarchive', 'philosophy e-print archive', 'philosophy of science archive',
         'philpapers archive', 'philsci-archive', 'preprints.org', 'preprints.org (mdpi)',
         'preprints.ru', 'psyarxiv', 'psyarxiv preprints', 'psychology archive',
         'qeios', 'qeios preprints', 'repec working papers', 'research square',
         'research square (research square)', 'research square preprints', 'roa', 'russian preprint server',
         'rutgers optimality archive', 'scielo preprints', 'scielo preprints collection', 'scienceopen preprints',
         'socarxiv', 'socarxiv preprints', 'social science research network', 'socopen',
         'sportrxiv', 'sportrxiv preprints', 'ssrn', 'ssrn electronic journal',
         'ssrn first look', 'techrxiv', 'under review', 'vixra',
         'vixra.org', 'yale law archive'
      )
         OR doi_l LIKE '10.1101/%' OR doi_l LIKE '10.20944/%' OR doi_l LIKE '10.21203/%' OR doi_l LIKE '10.2139/%' OR doi_l LIKE '10.26434/%' OR doi_l LIKE '10.64898/%' THEN 'preprint'
    WHEN venue_l IN (
         '4tu.researchdata', 'addgene', 'aea randomized controlled trials', 'aea rct registry',
         'arrayexpress', 'biomodels', 'biostudies', 'cambridge structural database (csd)',
         'chemical effects in biological systems (cebs)', 'clinicaltrials.gov', 'clinvar', 'crystallography open database (cod)',
         'datasets - sistema salve - icmbio', 'dbgap', 'dbsnp', 'dryad',
         'earthchem', 'electron microscopy data bank (emdb)', 'encode', 'encode datasets',
         'european genome-phenome archive (ega)', 'european nucleotide archive (ena)', 'gabii project', 'gabii project reports database',
         'gbif (global biodiversity information facility)', 'genbank / ncbi nucleotide', 'gisaid', 'gwas catalog',
         'http://isrctn.com/', 'icpsr', 'igvf datasets', 'inorganic crystal structure database (icsd)',
         'isrctn registry', 'iucn red list of threatened species', 'materials project', 'metabolights',
         'morphosource', 'morphosource media', 'movebank', 'ncbi gene expression omnibus (geo)',
         'neuromorpho.org', 'openneuro', 'pangaea', 'proteomexchange / pride',
         'psyctests (apa)', 'psyctests dataset', 'salve — icmbio', 'sequence read archive (sra)',
         'treebase', 'uk data service', 'uniprot', 'worldwide protein data bank',
         'worldwide protein data bank (wwpdb)'
      ) THEN 'dataset'
    WHEN venue_l IN (
         'big earth data', 'biodiversity data journal', 'bmc genomic data', 'chemical data collections',
         'data (mdpi)', 'data in brief', 'data intelligence', 'data science journal',
         'earth system science data (essd)', 'genome announcements', 'geoscience data journal', 'gigascience / gigabyte',
         'journal of open humanities data', 'journal of open psychology data', 'microbiology resource announcements (genome/data announcements)', 'open data journal for agricultural research',
         'open health data', 'scientific data'
      ) THEN 'data-paper'
    WHEN venue_l IN (
         'abstracts', 'abstracts with programs - geological society of america', 'academy of management proceedings', 'acta crystallographica section a foundations and advances',
         'acta crystallographica section a — meeting abstracts', 'annals of oncology — esmo congress abstract supplements', 'archives of cardiovascular diseases supplements', 'atherosclerosis supplements',
         'blood — ash annual meeting abstract supplements', 'bone abstracts', 'cancer research — aacr meeting abstract supplements', 'circulation — aha scientific sessions abstract supplements',
         'diabetes — ada scientific sessions abstract supplements', 'ecs meeting abstracts', 'endocrine abstracts', 'european psychiatry',
         'european psychiatry — epa congress abstracts', 'european urology open science', 'european urology open science — abstracts', 'european urology supplements',
         'geological society of america abstracts with programs', 'goldschmidt abstracts', 'gsa abstracts with programs (geological society of america)', 'haematologica — eha congress abstract supplements',
         'innovation in aging', 'innovation in aging — gsa abstracts', 'isee conference abstracts', 'journal of clinical oncology — asco meeting abstract supplements',
         'journal of the endocrine society', 'journal of the endocrine society — abstract supplements', 'medicine & science in sports & exercise — acsm abstracts', 'medicine &amp; science in sports &amp; exercise',
         'microscopy and microanalysis', 'microscopy and microanalysis — meeting abstracts', 'neurology — aan annual meeting abstract supplements', 'proc. annual convention of the japanese psychological association',
         'the faseb journal', 'the faseb journal — meeting supplements', 'the journal of heart and lung transplantation', 'the journal of heart and lung transplantation — abstract suppl.',
         'the proceedings of the annual convention of the japanese psychological association', 'value in health', 'value in health — ispor abstracts'
      ) THEN 'conference-abstract'

    -- 2. conference: proceedings-article (92% pure); split abstract-only records
    WHEN lower(coalesce(cr_type,'')) = 'proceedings-article'
         OR (venue_proceedings AND lower(coalesce(source_type,'')) = 'conference') THEN
      CASE WHEN single_page AND n_refs = 0 AND NOT has_abstract
           THEN 'conference-abstract' ELSE 'conference-paper' END

    -- I8. named proceedings venues the regex misses (e.g. LNCS, CCIS); same abstract split.
    WHEN venue_l IN (
         'acl anthology', 'acta horticulturae', 'advances in economics, business and management research', 'advances in economics, business and management research (atlantis)',
         'advances in economics, business and management research/advances in economics, business and management research', 'advances in intelligent systems and computing (aisc)', 'advances in neural information processing systems (neurips)', 'advances in neural information processing systems 36',
         'advances in social science, education and humanities research', 'advances in social science, education and humanities research (atlantis)', 'advances in social science, education and humanities research/advances in social science, education and humanities research', 'aiaa papers (scitech / aviation / propulsion & energy)',
         'aip conference proceedings', 'anais do encontro nacional de engenharia de produção', 'asme international mechanical engineering congress proceedings', 'ceur workshop proceedings',
         'coastal engineering proceedings', 'communications in computer and information science', 'communications in computer and information science (ccis)', 'conference on lasers and electro-optics',
         'conference on lasers and electro-optics (cleo)', 'conference proceedings of the society for experimental mechanics', 'destech transactions', 'e3s web of conferences',
         'ecs transactions', 'edulearn proceedings', 'electronic proceedings in theoretical computer science (eptcs)', 'energy procedia',
         'epic series in computing', 'epj web of conferences', 'frontiers in artificial intelligence and applications (ios press)', 'hawaii international conf. on system sciences (hicss) proceedings',
         'iabse reports', 'iceri proceedings', 'iet conference proceedings', 'iet conference proceedings.',
         'ifac proceedings volumes', 'ifac-papersonline', 'ifip advances in information and communication technology', 'ifmbe proceedings',
         'inted proceedings', 'international petroleum technology conference (iptc)', 'iop conf. series: earth and environmental science', 'iop conf. series: materials science and engineering',
         'iop conference series earth and environmental science', 'iop conference series materials science and engineering', 'iop conference series: earth and environmental science', 'iop conference series: materials science and engineering',
         'isca interspeech archive', 'isprs annals of the photogrammetry, remote sensing & spatial info sci.', 'isprs annals of the photogrammetry, remote sensing and spatial information sciences', 'isprs archives of the photogrammetry, remote sensing & spatial info sci.',
         'itm web of conferences', 'journal of physics conference series', 'journal of physics: conference series', 'lecture notes in civil engineering',
         'lecture notes in computer science', 'lecture notes in computer science (lncs)', 'lecture notes in networks and systems', 'lecture notes of the inst. for computer sciences (lnicst)',
         'lecture notes of the institute for computer sciences, social informatics and telecommunications engineering', 'lecture notes on data engineering and communications technologies', 'lipics (leibniz int''l proceedings in informatics)', 'matec web of conferences',
         'materials research proceedings', 'materials today proceedings', 'materials today: proceedings', 'mrs proceedings',
         'mrs proceedings (materials research society)', 'nuclear physics b: proceedings supplements', 'proc. of the human factors and ergonomics society annual meeting', 'procedia - social and behavioral sciences',
         'procedia cirp / manufacturing / chemistry / structural integrity', 'procedia computer science', 'procedia engineering', 'proceedings of machine learning research (pmlr / icml, aistats)',
         'proceedings of spie, the international society for optical engineering/proceedings of spie', 'proceedings of the 2020 aera annual meeting', 'proceedings of the aaai conference on artificial intelligence', 'proceedings of the acm on programming languages (pacmpl)',
         'proceedings of the international astronomical union', 'proceedings of the language resources and evaluation conf. (lrec)', 'proceedings of the language resources and evaluation conference', 'proceedings of the vldb endowment (pvldb)',
         'proceedings of the water environment federation', 'sae technical paper series', 'sae technical papers on cd-rom/sae technical paper series', 'scitepress proceedings',
         'sgem international multidisciplinary scientific geoconference', 'sgem international multidisciplinary scientific geoconference expo proceedings', 'shs web of conferences', 'sid symposium digest of technical papers',
         'spe improved oil recovery conference', 'spie proceedings', 'springer proceedings in physics', 'the european proceedings of social & behavioural sciences',
         'the proceedings of the jsme annual meeting', 'usenix proceedings', 'vdi verlag ebooks', 'world congress on medical physics and biomedical engineering, september 7 - 12, 2009, munich, germany',
         'the european proceedings of social & behavioural sciences', 'the international archives of the photogrammetry, remote sensing and spatial information sciences/international archives of the photogrammetry, remote sensing and spatial information sciences'
      ) THEN
      CASE WHEN single_page AND n_refs = 0 AND NOT has_abstract
           THEN 'conference-abstract' ELSE 'conference-paper' END

    -- 3-4. reference / whole book
    WHEN lower(coalesce(cr_type,'')) = 'reference-entry' THEN 'reference-entry'
    WHEN lower(coalesce(cr_type,'')) IN ('book','monograph','edited-book','reference-book') THEN 'book'

    -- 5. book family via Crossref chapter type or ISBN (ISBN default is chapter, 65% on gold;
    --    short + no abstract + no refs inside a book => front/back matter = paratext)
    WHEN lower(coalesce(cr_type,'')) = 'book-chapter' THEN 'book-chapter'
    WHEN has_isbn THEN
      CASE WHEN single_page AND NOT has_abstract AND n_refs = 0
           THEN 'paratext' ELSE 'book-chapter' END

    -- 6. peer-review
    WHEN lower(coalesce(cr_type,'')) = 'peer-review' THEN 'peer-review'

    -- 7-11. title-prefix signals (high precision when the title states the genre)
    WHEN title_l RLIKE '(retraction|retracted article|notice of retraction|withdrawn|expression of concern)' THEN 'retraction'
    WHEN title_l RLIKE '(erratum|corrigend(um|a)|publisher correction|correction to|author correction)' THEN 'erratum'
    WHEN title_l RLIKE '(^book review|^review of|reviewed work|^reviews of books)' THEN 'book-review'
    WHEN title_l RLIKE '^(editorial|from the editor|in this issue|introduction|preface|foreword|guest editor)' THEN 'editorial'
    WHEN title_l RLIKE '(reply to|comment on|response to|letter to the editor|in response to|correspondence)' THEN 'letter'

    -- 12. high-precision review gate: refs >= 150 (NOT 40 — that was only 16% precise) + abstract + not proceedings
    WHEN n_refs >= 150 AND has_abstract AND NOT venue_proceedings THEN 'review'

    -- residual: fuzzy article-boundary -> NULL, handed to the decision tree (or kept as oa_type)
    ELSE NULL
  END AS cascade_type
FROM f;
