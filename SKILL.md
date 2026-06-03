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
4. Use query/API patterns from `references/query-recipes.md`.
5. For each candidate, collect accession, title, repository, organism, modality, sample/cell count, data types, publication, access status, and candidate download assets.
6. Validate download assets using `references/download-validation.md` or `scripts/probe_url.sh`.
7. Rank candidates by biological match, processed-data usefulness, metadata completeness, public accessibility, and download reliability.
8. Return a concise answer first, then a table and exact commands.

## When To Load References

- Load `references/database-map.md` when choosing where to search or explaining repository coverage.
- Load `references/query-recipes.md` when building repository/API queries or translating a paper/request into search terms.
- Load `references/download-validation.md` before declaring a link downloadable, mainland-accessible, or broken.

## Output Contract

For dataset-search results, include:

- Recommended dataset(s) and why they match.
- A table with accession, title, repository, organism, modality, size/counts, access status, verified URL/page, and verification date.
- Download commands for verified public assets.
- Caveats for controlled access, missing metadata, stale mirrors, or unverified links.

If no suitable public dataset is found, say so directly and list the exact searches/repositories checked plus the next best path.

