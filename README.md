# Omics Data Search

Claude Code skill/plugin for finding, verifying, and downloading public omics datasets.

It includes:

- `SKILL.md` for search workflow and link validation discipline.
- `scripts/omics_api.py` for querying common omics repository APIs.
- `servers/omics_mcp.py` and `.mcp.json` for optional Claude Code MCP tools.

## Use As A Standalone Skill

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/XuuChen/omics-data-search-skill ~/.claude/skills/omics-data-search
```

Then invoke it in Claude Code with requests such as:

```text
/omics-data-search find public h5ad or count matrices for human liver fibrosis single-cell RNA-seq
```

## Use As A Plugin With MCP Tools

From a checkout of this repository:

```bash
claude --plugin-dir .
```

Or install through the bundled marketplace:

```text
/plugin marketplace add XuuChen/omics-data-search-skill
/plugin install omics-data-search@xuu-chen-omics
```

The plugin provides a namespaced skill and an MCP server named `omics-data-search`.

The MCP server exposes these tools:

```text
resolve_accession, ncbi_search, probe_url, make_download_plan,
probe_china_access, ena_runs, cellxgene_collection, gdc_files,
encode_search, encode_object, pride_files, mgnify_downloads,
metabolights_study, datacite_doi, supplement_search, biostudies_search,
zenodo_record, figshare_article, dryad_dataset, hca_projects
```

Useful direct CLI checks:

```bash
python3 scripts/omics_api.py resolve-accession --accession PXD000001 --fetch
python3 scripts/omics_api.py supplement-search --query 'Human Lung Cell Atlas HLCA h5ad' --limit 3
python3 scripts/omics_api.py hca-projects --organ liver --size 5
python3 scripts/omics_api.py probe-url --url 'https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1' --range
python3 scripts/omics_api.py make-download-plan --url 'https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1' --output HLCA_full_v1.1_emb.h5ad
python3 scripts/omics_api.py probe-china-access --url 'https://zenodo.org/' --limit 1 --dry-run
```

Protocol-level MCP smoke tests live in `tests/mcp_smoke.py`. A GitHub Actions validation template is included at `references/github-actions-validate.yml`; publishing it as `.github/workflows/validate.yml` requires a GitHub token with `workflow` scope.

## Supported API Families

NCBI E-utilities, ENA, CELLxGENE, GDC, ENCODE, PRIDE, MGnify, MetaboLights, Crossref, DataCite, BioStudies, Zenodo, Figshare, Dryad, HCA/Azul, direct HTTP URL probing, Globalping CN reachability probes, and resumable download-plan generation.
