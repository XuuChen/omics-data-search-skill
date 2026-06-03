---
name: omics-data-search
description: Find, verify, and document public omics datasets across genomics, transcriptomics, single-cell, spatial, epigenomics, proteomics, metabolomics, and microbiome repositories. Use when the user asks to locate accession IDs, papers' data availability, download links, processed matrices, raw FASTQ/BAM files, alternative mirrors, China-mainland/no-VPN accessibility, or to fix 404/broken omics data links.
argument-hint: "[organism/tissue/disease/modality/accession/access constraints]"
---

# Omics Data Search

Search for real datasets, prove access paths, and return reproducible download instructions. Treat omics links as unstable until verified by a repository page, official API, or file header check.

## Operating Rules

- Do not invent accession IDs, file names, bucket paths, or download URLs.
- Prefer official repository APIs, accession pages, and data availability statements over model memory or third-party summaries.
- Separate raw data, processed matrices, metadata, and reference/embedding/model files. Do not present one as another.
- State access status explicitly: public, login-required, controlled-access, embargoed, unavailable, or unverified.
- For large files, verify with `HEAD` and a byte-range request before proposing a full download.
- If the user asks for China-mainland/no-VPN accessibility, test from the target host first when available. If public CN probes are used, label them as probe results, not a guarantee for the user's institute/network.
- When working on remote/HPC systems, read project instructions first and preserve existing persistent shell/SSH policies.

## Workflow

1. Normalize the request into facets: organism, tissue/cell type, disease/condition, modality, platform, cohort size, raw vs processed, public vs controlled, and geography/access constraints.
2. If the user gave a paper, DOI, title, or accession, start exact. If the query is broad, search at least two likely repositories.
3. Select repositories from `references/database-map.md`.
4. Prefer `scripts/omics_api.py` for supported repositories; load `references/api-catalog.md` for command examples.
5. Use query/API patterns from `references/query-recipes.md` when a repository is not covered by the adapter or needs custom query construction.
6. For each candidate, collect accession, title, repository, organism, modality, sample/cell count, data types, publication, access status, and candidate download assets.
7. Validate download assets with `probe-url`; for mainland/no-VPN claims use `probe-china-access` or the user's target machine.
8. Rank candidates by biological match, processed-data usefulness, metadata completeness, public accessibility, and download reliability.
9. Return a concise answer first, then a table and exact commands.

## When To Load References

- Load `references/database-map.md` when choosing where to search or explaining repository coverage.
- Load `references/api-catalog.md` when using the bundled API adapter or deciding whether a future MCP wrapper would help.
- Load `references/query-recipes.md` when building repository/API queries or translating a paper/request into search terms.
- Load `references/download-validation.md` before declaring a link downloadable, mainland-accessible, or broken.

## API Adapter

For supported repositories, run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" --help
```

Use the adapter to get machine-readable JSON from NCBI, ENA, CELLxGENE, GDC, ENCODE, PRIDE, MGnify, MetaboLights, BioStudies, Zenodo, Figshare, Dryad, Crossref, DataCite, and HCA/Azul before writing manual curl commands. Continue to cite the live repository page/API response in the final answer.

If this repository is loaded as a Claude Code plugin, prefer the bundled MCP tools for supported API calls, URL probes, China-mainland probes, and download-plan generation. Use the CLI adapter as a fallback/debug surface.

Start exact identifiers with:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" resolve-accession --accession ACCESSION --fetch
```

For paper titles, data availability leads, or supplemental processed files, use `supplement-search` and then validate candidate download URLs.

Before recommending a direct public file URL:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" probe-url --url URL --range
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" make-download-plan --url URL --output FILE
```

For China-mainland/no-VPN checks, only run public probes when appropriate and label the result as point-in-time evidence:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" probe-china-access --url URL --method RANGE --limit 3
```

## Output Contract

For dataset-search results, include:

- Recommended dataset(s) and why they match.
- A table with accession, title, repository, organism, modality, size/counts, access status, verified URL/page, and verification date.
- Download commands for verified public assets.
- Evidence line for each direct URL, including verification date, HTTP status, byte-range result, size when known, and probe location when tested.
- Caveats for controlled access, missing metadata, stale mirrors, or unverified links.

If no suitable public dataset is found, say so directly and list the exact searches/repositories checked plus the next best path.
