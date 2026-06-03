# API Catalog

Prefer `scripts/omics_api.py` for supported repositories. It uses only Python standard-library modules and returns JSON so results are easy to inspect, filter with `jq`, and cite in final answers.

Run from the skill directory:

```bash
python3 scripts/omics_api.py --help
```

In Claude Code, use the absolute skill path when needed:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" ena-runs --accession PRJNA185544 --limit 5
```

## Supported Commands

| Command | Repository | Best For | Notes |
|---|---|---|---|
| `resolve-accession` | Multi-repository router | Guess likely repositories for GSE/SRP/PRJNA/SRR/PXD/MTBLS/MGYS/S-BSST/ENCFF/DOI/UUID inputs | Add `--fetch` for exact detail lookups where supported |
| `probe-url` | Direct HTTP(S) URL | Proving whether a candidate file URL is directly downloadable | Uses `HEAD` and, by default, `Range: bytes=0-0`; reports status, content length, content type, and range support |
| `make-download-plan` | Direct HTTP(S) URL | Generating resumable `aria2c`/`wget`/`curl` commands and validation commands | Add repository-provided `--expected-size`, `--md5`, or `--sha256` when available |
| `probe-china-access` | Globalping public probes | Point-in-time China-mainland HTTP reachability checks | Use only when mainland/no-VPN access matters; use `--dry-run` in tests or CI |
| `ncbi-search` | NCBI E-utilities | GEO/SRA/PubMed/BioProject/BioSample discovery | Set `NCBI_API_KEY` if doing many requests |
| `ncbi-summary` | NCBI E-utilities | Fetching summaries for Entrez UIDs | Use after `ncbi-search` |
| `ena-runs` | ENA Portal API | Resolving study/run/sample accessions to FASTQ URLs and MD5s | Converts ENA FTP paths to HTTPS mirrors |
| `cellxgene-collection` | CELLxGENE Discover curation API | Resolving collection UUIDs to H5AD/other assets | Use `assets[].url`; never guess h5ad paths |
| `gdc-files` | GDC API | TCGA/TARGET file discovery and open/controlled status | Download with GDC manifest/client for large batches |
| `encode-search` | ENCODE REST API | ENCODE File/Experiment searches | Pass portal filters as `--param key=value` |
| `encode-object` | ENCODE REST API | Exact ENCODE object lookups, especially `ENCFF...` file accessions | Adds direct download URL when present |
| `pride-project` | PRIDE Archive API | Proteomics project metadata by PXD accession | Exact accession path |
| `pride-files` | PRIDE Archive API | Proteomics file lists and public locations | Adds HTTPS equivalents for PRIDE FTP locations |
| `mgnify-study` | MGnify API | Microbiome/metagenomics study metadata | Use ENA for raw reads |
| `mgnify-downloads` | MGnify API | Processed MGnify study outputs | Returns pipeline download records |
| `metabolights-study` | MetaboLights API | Metabolomics study metadata and public FTP/HTTP/Globus URLs | Good for direct public study folders |
| `crossref-search` / `crossref-work` | Crossref API | Paper DOI metadata before hunting data availability | Use DOI/title to discover related dataset records |
| `datacite-doi` | DataCite API | Dataset DOI metadata for Zenodo, Dryad, Figshare, BioStudies, and other repositories | Prefer this for data DOIs that Crossref does not index |
| `biostudies-search` / `biostudies-study` | BioStudies API | BioStudies/ArrayExpress records and public file directories | Useful for `S-*`, `E-MTAB-*`, and Europe PMC-linked supplements |
| `zenodo-search` / `zenodo-record` | Zenodo REST API | Processed matrices, h5ad/Seurat objects, reference models, supplemental archives | Search can be rate-limited; prefer exact record IDs when known |
| `figshare-search` / `figshare-article` | Figshare API | Supplemental figures/files and article-hosted datasets | `figshare-article` exposes file download URLs and MD5s |
| `dryad-search` / `dryad-dataset` | Dryad API | Dataset DOI metadata and packaged downloads | Use for `10.5061/dryad...` identifiers |
| `hca-catalogs` / `hca-projects` | HCA Azul Data Browser API | Human Cell Atlas project discovery by organ/disease/project UUID | Uses current default catalog unless specified |
| `supplement-search` | BioStudies + Zenodo + Figshare + Dryad | Broad supplemental data search for a paper title, DOI, accession, or biological phrase | Follow with exact detail command and URL validation |

## Examples

Search GEO DataSets:

```bash
python3 scripts/omics_api.py ncbi-search \
  --db gds \
  --term '("Homo sapiens"[Organism]) AND liver AND single-cell' \
  --retmax 10
```

Route and fetch exact accessions:

```bash
python3 scripts/omics_api.py resolve-accession --accession PXD000001 --fetch
python3 scripts/omics_api.py resolve-accession --accession 10.5281/zenodo.7599104 --fetch
```

Resolve raw read FASTQ paths through ENA:

```bash
python3 scripts/omics_api.py ena-runs \
  --accession PRJNA185544 \
  --limit 5
```

Resolve CELLxGENE collection assets:

```bash
python3 scripts/omics_api.py cellxgene-collection \
  --collection-id 6f6d381a-7701-4781-935c-db10d30de293
```

Search GDC open transcriptome files:

```bash
python3 scripts/omics_api.py gdc-files \
  --project TCGA-LUAD \
  --data-category 'Transcriptome Profiling' \
  --access open \
  --size 10
```

Search ENCODE files with portal-style filters:

```bash
python3 scripts/omics_api.py encode-search \
  --param type=File \
  --param assay_term_name=RNA-seq \
  --param file_format=fastq \
  --limit 5
```

Fetch PRIDE project files:

```bash
python3 scripts/omics_api.py pride-files \
  --accession PXD000001 \
  --limit 5
```

Fetch MGnify processed downloads:

```bash
python3 scripts/omics_api.py mgnify-downloads \
  --accession ERP009004 \
  --page-size 10
```

Fetch MetaboLights public study URLs:

```bash
python3 scripts/omics_api.py metabolights-study \
  --accession MTBLS1
```

Search paper supplements across common general repositories:

```bash
python3 scripts/omics_api.py supplement-search \
  --query 'Human Lung Cell Atlas Sikkema h5ad' \
  --limit 3
```

Validate a direct file URL before recommending it:

```bash
python3 scripts/omics_api.py probe-url \
  --url 'https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1' \
  --range
```

Generate resumable download commands:

```bash
python3 scripts/omics_api.py make-download-plan \
  --url 'https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1' \
  --output HLCA_full_v1.1_emb.h5ad
```

Prepare or run China-mainland probes:

```bash
python3 scripts/omics_api.py probe-china-access \
  --url 'https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1' \
  --method RANGE \
  --limit 3
```

Search HCA liver projects:

```bash
python3 scripts/omics_api.py hca-projects \
  --organ liver \
  --size 5
```

## MCP Tools

When this repository is loaded as a Claude Code plugin, `.mcp.json` starts `servers/omics_mcp.py` as a stdio MCP server. The server wraps `scripts/omics_api.py`, so CLI and MCP behavior share the same API logic.

MCP tool names use underscores:

- `resolve_accession`
- `ncbi_search`
- `probe_url`
- `make_download_plan`
- `probe_china_access`
- `ena_runs`
- `cellxgene_collection`
- `gdc_files`
- `encode_search`
- `encode_object`
- `pride_files`
- `mgnify_downloads`
- `metabolights_study`
- `datacite_doi`
- `supplement_search`
- `biostudies_search`
- `zenodo_record`
- `figshare_article`
- `dryad_dataset`
- `hca_projects`

Keep future MCP additions thin: validate inputs, call the same adapter logic, and return JSON plus provenance.
