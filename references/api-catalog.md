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
| `ncbi-search` | NCBI E-utilities | GEO/SRA/PubMed/BioProject/BioSample discovery | Set `NCBI_API_KEY` if doing many requests |
| `ncbi-summary` | NCBI E-utilities | Fetching summaries for Entrez UIDs | Use after `ncbi-search` |
| `ena-runs` | ENA Portal API | Resolving study/run/sample accessions to FASTQ URLs and MD5s | Converts ENA FTP paths to HTTPS mirrors |
| `cellxgene-collection` | CELLxGENE Discover curation API | Resolving collection UUIDs to H5AD/other assets | Use `assets[].url`; never guess h5ad paths |
| `gdc-files` | GDC API | TCGA/TARGET file discovery and open/controlled status | Download with GDC manifest/client for large batches |
| `encode-search` | ENCODE REST API | ENCODE File/Experiment searches | Pass portal filters as `--param key=value` |
| `pride-project` | PRIDE Archive API | Proteomics project metadata by PXD accession | Exact accession path |
| `pride-files` | PRIDE Archive API | Proteomics file lists and public locations | Adds HTTPS equivalents for PRIDE FTP locations |
| `mgnify-study` | MGnify API | Microbiome/metagenomics study metadata | Use ENA for raw reads |
| `mgnify-downloads` | MGnify API | Processed MGnify study outputs | Returns pipeline download records |
| `metabolights-study` | MetaboLights API | Metabolomics study metadata and public FTP/HTTP/Globus URLs | Good for direct public study folders |

## Examples

Search GEO DataSets:

```bash
python3 scripts/omics_api.py ncbi-search \
  --db gds \
  --term '("Homo sapiens"[Organism]) AND liver AND single-cell' \
  --retmax 10
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

## MCP Direction

Do not build an MCP server until the CLI command names and normalized JSON fields have survived real searches. When ready, wrap these same functions as MCP tools:

- `omics_ncbi_search`
- `omics_ena_runs`
- `omics_cellxgene_collection`
- `omics_gdc_files`
- `omics_encode_search`
- `omics_pride_files`
- `omics_mgnify_downloads`
- `omics_metabolights_study`
- `omics_probe_url`

Keep MCP tools thin: validate inputs, call the same adapter logic, and return JSON plus provenance.

