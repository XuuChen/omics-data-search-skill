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

Search HCA liver projects:

```bash
python3 scripts/omics_api.py hca-projects \
  --organ liver \
  --size 5
```

## MCP Direction

Do not build an MCP server until the CLI command names and normalized JSON fields have survived real searches. When ready, wrap these same functions as MCP tools:

- `omics_ncbi_search`
- `omics_resolve_accession`
- `omics_datacite_doi`
- `omics_ena_runs`
- `omics_cellxgene_collection`
- `omics_gdc_files`
- `omics_encode_search`
- `omics_pride_files`
- `omics_mgnify_downloads`
- `omics_metabolights_study`
- `omics_supplement_search`
- `omics_hca_projects`
- `omics_probe_url`

Keep MCP tools thin: validate inputs, call the same adapter logic, and return JSON plus provenance.
