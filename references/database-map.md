# Omics Repository Map

Use this map to choose search targets. Always verify current metadata and links from the live repository.

## General Sequencing And Expression

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| Published expression studies and supplements | NCBI GEO, EBI BioStudies/ArrayExpress | Bulk RNA-seq, microarray, scRNA-seq processed matrices, sample annotations | Raw data often lives in SRA/ENA; GEO supplementary files can be inconsistent |
| Raw reads | NCBI SRA, ENA, DDBJ DRA, NGDC GSA, CNSA | FASTQ/SRA/BAM runs, BioProject/BioSample metadata | Some human datasets are controlled; direct file links may be generated dynamically |
| Study/sample metadata bridge | NCBI BioProject, NCBI BioSample, ENA study/sample, NGDC BioProject/BioSample | Mapping paper -> samples -> runs | Metadata can be sparse or duplicated across mirrors |
| China-hosted sequencing archive | CNCB-NGDC GSA, GSA-Human, CNGB CNSA | China-accessible raw sequencing and multi-omics projects | Human controlled access may require application/login |

## Single-Cell And Spatial

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| Curated `.h5ad` datasets | CELLxGENE Discover | Annotated single-cell/spatial objects and collections | Do not guess asset URLs; get assets from collection/dataset API |
| HCA atlas projects | Human Cell Atlas Data Portal | Raw and processed atlas files | Project pages can point to cloud buckets or partner portals |
| Study-hosted processed matrices | GEO, Single Cell Portal, Figshare, Dryad, Zenodo | Count matrices, metadata, embeddings | Verify file type; embeddings/reference models are not full count matrices |
| Organ/tissue atlases | HuBMAP, KPMP, HTAN, CZ CELLxGENE, HCA | Spatial/single-cell human tissue data | Some files need portal-specific manifests or auth |
| Human Cell Atlas project discovery | HCA Data Portal / Azul API | HCA project metadata by organ/disease/project | Use `hca-catalogs` to avoid stale catalog names |

## Cancer And Human Cohorts

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| TCGA/TARGET and cancer genomics | GDC Data Portal/API | Open harmonized counts, masked somatic variants, clinical metadata | Controlled BAM/FASTQ/germline require dbGaP authorization |
| Processed cancer summaries | cBioPortal | Mutation/CNA/expression clinical summaries | Usually not raw omics; cite original study and portal version |
| International cancer projects | ICGC/ARGO, EGA, dbGaP | Controlled human genomic cohorts | Access committee approval often required |

## Epigenomics And Regulation

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| Regulatory assays | ENCODE Portal | ChIP-seq, ATAC-seq, DNase-seq, RNA-seq, validated metadata | Use portal file metadata; choose genome build carefully |
| Reference epigenomes | Roadmap Epigenomics, ENCODE | Human tissue/cell-type reference tracks | Older builds and file formats vary |
| Literature-mined regulatory data | Cistrome Data Browser, ChIP-Atlas | ChIP/ATAC curated tracks | Check original accession and QC status |

## Proteomics, Metabolomics, Microbiome

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| Proteomics raw/processed | PRIDE/ProteomeXchange, MassIVE, iProX | MS raw files, mzML, peptide/protein IDs | Large files; iProX can be a useful China-accessible source |
| Metabolomics | MetaboLights, Metabolomics Workbench | LC-MS/GC-MS/NMR metadata and peak tables | Data formats and normalization vary widely |
| Microbiome/metagenomics | MGnify, Qiita, NCBI SRA/ENA, GSA | Amplicon and metagenomic runs, processed profiles | Processed taxonomic tables may not match raw run accessions |

## General Supplemental Repositories

| Need | Start Here | Good For | Watch Out |
|---|---|---|---|
| EBI-linked study supplements | BioStudies / ArrayExpress | `S-*`, `E-MTAB-*`, Europe PMC-linked study files | Search hits may be papers without reusable omics matrices |
| General research deposits | Zenodo | h5ad, Seurat, model files, archives, code/data bundles | Search is broad; exact record/DOI lookup is more reliable |
| Article supplements | Figshare | Per-article files with MD5 and direct download URLs | Many results are figures, not raw data |
| Dataset DOI packages | Dryad | Packaged public datasets tied to publications | Often a zip/package; inspect file contents before assuming matrix type |

## Controlled-Access Signals

Treat these as not directly downloadable unless the user has credentials/approval:

- dbGaP study accessions such as `phs...`
- EGA accessions such as `EGAD...`, `EGAS...`
- GSA-Human controlled projects
- GDC controlled files, especially BAM/FASTQ and germline-sensitive data
- Any portal page requiring data access committee approval
