# Query Recipes

Use exact identifiers first. Use broad web search only to discover official accession pages, then switch to repository APIs/pages.

## Query Decomposition

Build queries from these facets:

- Organism: `human`, `Homo sapiens`, `mouse`, strain if relevant.
- Anatomy: tissue, organ, cell type, developmental stage.
- Condition: disease names, synonyms, ontology terms, treatment, genotype.
- Modality: `scRNA-seq`, `snRNA-seq`, `spatial transcriptomics`, `Visium`, `bulk RNA-seq`, `ATAC-seq`, `WGS`, `WES`, `methylation`, `proteomics`, `metabolomics`, `metagenomics`.
- Data need: `raw FASTQ`, `count matrix`, `h5ad`, `loom`, `Seurat`, `metadata`, `clinical`.
- Access: `public`, `controlled`, `China`, `no VPN`, `mirror`.

## Paper-To-Data Search

1. Search exact paper title plus `data availability`, `GEO`, `SRA`, `ENA`, `ArrayExpress`, `CELLxGENE`, `Zenodo`, `Figshare`, or `Dryad`.
2. Check the paper's data availability statement and supplementary tables.
3. Search accession IDs from the paper in their primary repository.
4. If a paper gives a collection page but no file URL, inspect the repository API or page assets rather than guessing paths.

Useful web queries:

```text
"paper title" +"data availability"
"paper title" +(GEO OR SRA OR ENA OR ArrayExpress OR CELLxGENE OR Zenodo)
site:ncbi.nlm.nih.gov/geo "disease" "tissue" "single-cell"
site:cellxgene.cziscience.com/collections "tissue" "disease"
site:ebi.ac.uk/ena "study accession or paper title"
```

## NCBI E-utilities

Use URL-encoded terms. Search GEO DataSets (`gds`) for studies and SRA (`sra`) for raw runs.

```bash
BASE='https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
TERM='("Homo sapiens"[Organism]) AND ("lung"[All Fields]) AND ("single-cell"[All Fields])'

curl -sS "$BASE/esearch.fcgi?db=gds&retmode=json&retmax=20&term=$(python3 - <<'PY'
import urllib.parse
print(urllib.parse.quote('("Homo sapiens"[Organism]) AND ("lung"[All Fields]) AND ("single-cell"[All Fields])'))
PY
)"

curl -sS "$BASE/esearch.fcgi?db=sra&retmode=json&retmax=20&term=$(python3 - <<'PY'
import urllib.parse
print(urllib.parse.quote('("Homo sapiens"[Organism]) AND ("lung"[All Fields]) AND ("RNA-Seq"[Strategy])'))
PY
)"
```

For accessions, query exact strings such as `GSE...`, `SRP...`, `PRJNA...`, `SRR...`.

## ENA Portal API

ENA is often the easiest way to obtain direct FASTQ FTP/HTTPS paths for SRA/ENA runs.

```bash
curl -sS -G 'https://www.ebi.ac.uk/ena/portal/api/search' \
  --data-urlencode 'result=read_run' \
  --data-urlencode 'query=study_accession="PRJNA000000"' \
  --data-urlencode 'fields=run_accession,study_accession,sample_accession,scientific_name,instrument_platform,library_strategy,fastq_ftp,fastq_md5,submitted_ftp,submitted_md5' \
  --data-urlencode 'format=tsv'
```

If the user gives `SRP`, `ERP`, `DRP`, `PRJNA`, or `SRR`, try ENA even when the original source is NCBI.

## CELLxGENE Discover

For collection pages, extract the collection UUID and query the curation API:

```bash
COLLECTION_ID='collection-uuid-here'
curl -sS -L "https://api.cellxgene.cziscience.com/curation/v1/collections/${COLLECTION_ID}" \
  | jq -r '.datasets[] | [.dataset_id, .title, (.cell_count|tostring), (.assets[]? | select(.filetype=="H5AD") | .filesize|tostring), (.assets[]? | select(.filetype=="H5AD") | .url)] | @tsv'
```

Do not invent `datasets.cellxgene.cziscience.com/*.h5ad` paths. Use `assets[].url`.

## GDC API

Use GDC for TCGA/TARGET files and manifests. Prefer the portal/API metadata over guessed UUID URLs.

```bash
curl -sS 'https://api.gdc.cancer.gov/files?size=10&pretty=true' \
  -H 'Content-Type: application/json' \
  -d '{"filters":{"op":"and","content":[{"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-LUAD"]}},{"op":"in","content":{"field":"data_category","value":["Transcriptome Profiling"]}}]},"fields":"file_id,file_name,data_type,data_format,access,file_size,cases.submitter_id"}'
```

For actual downloads, use a GDC manifest plus `gdc-client` when many files are needed.

## Candidate Scoring

Prefer candidates with:

- Exact organism/tissue/disease/modality match.
- Public processed data if the user needs immediate analysis.
- Raw data plus high-quality metadata if reprocessing is needed.
- Stable accession pages and API-discoverable files.
- Checksums or content lengths.
- Clear publication and citation.

