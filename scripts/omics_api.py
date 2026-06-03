#!/usr/bin/env python3
"""Small public-omics API adapter for Claude Code skills.

Outputs JSON only. Uses the Python standard library so it works on most HPC
login nodes without installing dependencies.
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request


USER_AGENT = "omics-data-search-skill/0.3 (+https://github.com/XuuChen/omics-data-search-skill)"


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def default_ssl_context():
    paths = ssl.get_default_verify_paths()
    candidates = [
        os.environ.get("SSL_CERT_FILE"),
        os.environ.get("CURL_CA_BUNDLE"),
        paths.cafile,
        paths.openssl_cafile,
        "/etc/ssl/cert.pem",
        "/opt/homebrew/etc/openssl@3/cert.pem",
        "/usr/local/etc/openssl@3/cert.pem",
    ]
    for cafile in candidates:
        if cafile and os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def request_json(url, params=None, method="GET", body=None, headers=None):
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{query}"

    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    context = default_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as resp:
            text = resp.read().decode("utf-8")
            return {
                "ok": True,
                "url": resp.geturl(),
                "status": resp.status,
                "headers": dict(resp.headers.items()),
                "json": json.loads(text) if text else None,
            }
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = text[:4000]
        return {
            "ok": False,
            "url": url,
            "status": exc.code,
            "error": exc.reason,
            "body": parsed,
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def safe_get(mapping, *keys):
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def limit_list(values, limit):
    if limit is None:
        return values
    return values[:limit]


def ftp_to_https(value):
    if value.startswith("ftp://ftp.sra.ebi.ac.uk/"):
        return value.replace("ftp://", "https://", 1)
    if value.startswith("ftp.sra.ebi.ac.uk/"):
        return "https://" + value
    if value.startswith("ftp://ftp.pride.ebi.ac.uk/"):
        return value.replace("ftp://", "https://", 1)
    if value.startswith("ftp.pride.ebi.ac.uk/"):
        return "https://" + value
    return value


def split_semicolon(value):
    if not value:
        return []
    return [item for item in value.split(";") if item]


def classify_accession(value):
    token = value.strip()
    upper = token.upper()
    routes = []

    def add(repository, command, reason, **kwargs):
        routes.append({"repository": repository, "command": command, "reason": reason, **kwargs})

    if re.match(r"^GSE\d+$|^GSM\d+$|^GPL\d+$", upper):
        add("NCBI GEO", "ncbi-search --db gds", "GEO-style accession")
    if re.match(r"^SRR\d+$|^ERR\d+$|^DRR\d+$|^SRP\d+$|^ERP\d+$|^DRP\d+$|^PRJNA\d+$|^PRJEB\d+$|^PRJDB\d+$|^SAMN\d+$|^SAMEA\d+$|^SAMD\d+$", upper):
        add("ENA Portal API", "ena-runs", "INSDC/SRA/ENA/DRA run, study, project, or sample accession")
        add("NCBI SRA", "ncbi-search --db sra", "NCBI SRA may hold the primary record or cross-reference")
    if re.match(r"^PXD\d+$", upper):
        add("PRIDE Archive", "pride-project / pride-files", "ProteomeXchange/PRIDE accession")
    if re.match(r"^MTBLS\d+$", upper):
        add("MetaboLights", "metabolights-study", "MetaboLights study accession")
    if re.match(r"^MGYS\d+$", upper):
        add("MGnify", "mgnify-study / mgnify-downloads", "MGnify study accession")
    if re.match(r"^S-[A-Z0-9]+", upper):
        add("BioStudies", "biostudies-study", "BioStudies/ArrayExpress-style accession")
    if re.match(r"^E-MTAB-\d+$|^E-GEOD-\d+$|^E-[A-Z]+-\d+$", upper):
        add("BioStudies / ArrayExpress", "biostudies-search", "ArrayExpress-style accession")
    if re.match(r"^ENCFF[A-Z0-9]+$|^ENCSR[A-Z0-9]+$|^ENCBS[A-Z0-9]+$|^ENCDO[A-Z0-9]+$|^ENCLB[A-Z0-9]+$", upper):
        add("ENCODE", "encode-object", "ENCODE accession")
    if re.match(r"^10\.5281/ZENODO\.\d+$", upper):
        add("Zenodo", "zenodo-record", "Zenodo DOI")
    if re.match(r"^\d{6,}$", token):
        add("Zenodo", "zenodo-record", "Numeric Zenodo record IDs are common, but this is ambiguous")
        add("Figshare", "figshare-article", "Numeric Figshare article IDs are common, but this is ambiguous")
    if re.match(r"^10\.6084/M9\.FIGSHARE\.", upper):
        add("Figshare", "figshare-search / figshare-article", "Figshare DOI")
    if re.match(r"^10\.5061/DRYAD\.", upper) or upper.startswith("DOI:10.5061/DRYAD."):
        add("Dryad", "dryad-dataset", "Dryad DOI")
    if re.match(r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$", upper):
        add("CELLxGENE Discover", "cellxgene-collection", "UUID may be a CELLxGENE collection")
        add("HCA Data Portal", "hca-projects --project-id", "UUID may be an HCA project")
    if re.match(r"^10\.", token):
        add("DataCite", "datacite-doi", "Dataset DOI metadata; many repositories use DataCite instead of Crossref")
        data_doi_prefix = re.match(r"^10\.(5281|5061|6084|6019)/", upper)
        if not data_doi_prefix:
            add("Crossref", "crossref-work", "DOI; use article metadata to find data availability and related identifiers")
        add("Zenodo/Figshare/Dryad/BioStudies", "supplement-search", "DOI may be indexed by a supplemental-data repository")
    if not routes:
        add("General search", "supplement-search / ncbi-search", "No specific accession pattern matched")
    return routes


def cmd_ncbi_search(args):
    params = {
        "db": args.db,
        "term": args.term,
        "retmode": "json",
        "retmax": args.retmax,
        "tool": "omics-data-search",
    }
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    res = request_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params)
    emit({"source": "NCBI E-utilities", "command": "ncbi-search", "request": params, "response": res})


def cmd_ncbi_summary(args):
    params = {
        "db": args.db,
        "id": args.ids,
        "retmode": "json",
        "tool": "omics-data-search",
    }
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    res = request_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params=params)
    emit({"source": "NCBI E-utilities", "command": "ncbi-summary", "request": params, "response": res})


def ena_query_for_accession(accession):
    a = accession.strip()
    upper = a.upper()
    if upper.startswith(("SRR", "ERR", "DRR")):
        return f'run_accession="{a}"'
    if upper.startswith(("SRP", "ERP", "DRP")):
        return f'secondary_study_accession="{a}"'
    if upper.startswith("PRJ"):
        return f'study_accession="{a}"'
    if upper.startswith(("SAMN", "SAMEA", "SAMD")):
        return f'sample_accession="{a}"'
    return (
        f'study_accession="{a}" OR secondary_study_accession="{a}" OR '
        f'run_accession="{a}" OR sample_accession="{a}" OR secondary_sample_accession="{a}"'
    )


def normalize_ena_run(row):
    fastq_ftp = split_semicolon(row.get("fastq_ftp", ""))
    submitted_ftp = split_semicolon(row.get("submitted_ftp", ""))
    return {
        **row,
        "fastq_https": [ftp_to_https(x) for x in fastq_ftp],
        "submitted_https": [ftp_to_https(x) for x in submitted_ftp],
    }


def cmd_ena_runs(args):
    fields = args.fields or (
        "run_accession,study_accession,secondary_study_accession,sample_accession,"
        "scientific_name,instrument_platform,library_strategy,library_layout,"
        "fastq_ftp,fastq_md5,submitted_ftp,submitted_md5"
    )
    query = args.query or ena_query_for_accession(args.accession)
    params = {
        "result": "read_run",
        "query": query,
        "fields": fields,
        "format": "json",
        "limit": args.limit,
    }
    res = request_json("https://www.ebi.ac.uk/ena/portal/api/search", params=params)
    rows = res.get("json") if res.get("ok") else None
    normalized = [normalize_ena_run(row) for row in rows] if isinstance(rows, list) else None
    emit({
        "source": "ENA Portal API",
        "command": "ena-runs",
        "request": params,
        "normalized": normalized,
        "response": res,
    })


def normalize_cellxgene_dataset(dataset):
    assets = []
    for asset in dataset.get("assets", []) or []:
        assets.append({
            "filetype": asset.get("filetype"),
            "filesize": asset.get("filesize"),
            "url": asset.get("url"),
        })
    return {
        "dataset_id": dataset.get("dataset_id"),
        "dataset_version_id": dataset.get("dataset_version_id"),
        "title": dataset.get("title"),
        "cell_count": dataset.get("cell_count"),
        "citation": dataset.get("citation"),
        "assets": assets,
    }


def cmd_cellxgene_collection(args):
    url = f"https://api.cellxgene.cziscience.com/curation/v1/collections/{args.collection_id}"
    res = request_json(url)
    data = res.get("json") if res.get("ok") else {}
    normalized = {
        "collection_id": data.get("collection_id"),
        "collection_url": data.get("collection_url"),
        "title": data.get("name") or data.get("title"),
        "datasets": [normalize_cellxgene_dataset(ds) for ds in data.get("datasets", [])],
    } if isinstance(data, dict) else None
    emit({
        "source": "CELLxGENE Discover curation API",
        "command": "cellxgene-collection",
        "normalized": normalized,
        "response": res,
    })


def gdc_filter(field, values):
    return {"op": "in", "content": {"field": field, "value": values}}


def cmd_gdc_files(args):
    content = []
    if args.project:
        content.append(gdc_filter("cases.project.project_id", args.project))
    if args.data_category:
        content.append(gdc_filter("data_category", args.data_category))
    if args.data_type:
        content.append(gdc_filter("data_type", args.data_type))
    if args.access:
        content.append(gdc_filter("access", args.access))

    body = {
        "fields": args.fields,
        "format": "JSON",
        "size": args.size,
    }
    if content:
        body["filters"] = {"op": "and", "content": content}
    res = request_json("https://api.gdc.cancer.gov/files", method="POST", body=body)
    emit({"source": "GDC API", "command": "gdc-files", "request": body, "response": res})


def cmd_encode_search(args):
    params = {"format": "json", "limit": args.limit}
    for param in args.param:
        if "=" not in param:
            raise SystemExit(f"ENCODE --param must be key=value, got: {param}")
        key, value = param.split("=", 1)
        params.setdefault(key, [])
        if isinstance(params[key], list):
            params[key].append(value)
        else:
            params[key] = [params[key], value]
    if "type" not in params:
        params["type"] = args.type
    res = request_json("https://www.encodeproject.org/search/", params=params)
    data = res.get("json") if res.get("ok") else {}
    graph = data.get("@graph", []) if isinstance(data, dict) else []
    normalized = []
    for item in graph:
        href = item.get("href")
        download_url = urllib.parse.urljoin("https://www.encodeproject.org", href) if href else None
        normalized.append({
            "accession": item.get("accession"),
            "dataset": item.get("dataset"),
            "file_format": item.get("file_format"),
            "file_type": item.get("file_type"),
            "output_type": item.get("output_type"),
            "assembly": item.get("assembly"),
            "file_size": item.get("file_size"),
            "status": item.get("status"),
            "download_url": download_url,
        })
    emit({
        "source": "ENCODE REST API",
        "command": "encode-search",
        "request": params,
        "normalized": normalized,
        "response": res,
    })


def cmd_pride_project(args):
    url = f"https://www.ebi.ac.uk/pride/ws/archive/v3/projects/{args.accession}"
    res = request_json(url)
    emit({"source": "PRIDE Archive API", "command": "pride-project", "response": res})


def normalize_pride_file(item):
    locations = []
    for loc in item.get("publicFileLocations", []) or []:
        value = loc.get("value")
        locations.append({
            "protocol": loc.get("name"),
            "url": value,
            "https_url": ftp_to_https(value) if value else None,
        })
    category = item.get("fileCategory") or {}
    return {
        "accession": item.get("accession"),
        "file_name": item.get("fileName"),
        "file_size_bytes": item.get("fileSizeBytes"),
        "category": category.get("value") or category.get("name"),
        "checksum": item.get("checksum"),
        "locations": locations,
    }


def cmd_pride_files(args):
    url = f"https://www.ebi.ac.uk/pride/ws/archive/v3/projects/{args.accession}/files/all"
    res = request_json(url)
    rows = res.get("json") if res.get("ok") else None
    normalized = [normalize_pride_file(row) for row in limit_list(rows, args.limit)] if isinstance(rows, list) else None
    emit({
        "source": "PRIDE Archive API",
        "command": "pride-files",
        "normalized": normalized,
        "response": res,
    })


def cmd_mgnify_study(args):
    url = f"https://www.ebi.ac.uk/metagenomics/api/latest/studies/{args.accession}"
    res = request_json(url)
    emit({"source": "MGnify API", "command": "mgnify-study", "response": res})


def cmd_mgnify_downloads(args):
    url = f"https://www.ebi.ac.uk/metagenomics/api/latest/studies/{args.accession}/downloads"
    res = request_json(url, params={"page_size": args.page_size})
    emit({"source": "MGnify API", "command": "mgnify-downloads", "response": res})


def cmd_metabolights_study(args):
    url = f"https://www.ebi.ac.uk/metabolights/ws/studies/{args.accession}"
    res = request_json(url)
    data = res.get("json") if res.get("ok") else {}
    study = data.get("mtblsStudy", {}) if isinstance(data, dict) else {}
    normalized = {
        "accession": args.accession,
        "study_status": study.get("studyStatus"),
        "first_public_date": study.get("firstPublicDate"),
        "study_http_url": study.get("studyHttpUrl"),
        "study_ftp_url": study.get("studyFtpUrl"),
        "study_globus_url": study.get("studyGlobusUrl"),
        "read_access": study.get("read_access"),
    }
    emit({
        "source": "MetaboLights API",
        "command": "metabolights-study",
        "normalized": normalized,
        "response": res,
    })


def cmd_crossref_search(args):
    params = {"rows": args.rows}
    if args.title:
        params["query.title"] = args.title
    else:
        params["query"] = args.query
    res = request_json("https://api.crossref.org/works", params=params)
    items = safe_get(res.get("json") or {}, "message", "items") or []
    normalized = []
    for item in items[: args.rows]:
        normalized.append({
            "doi": item.get("DOI"),
            "title": (item.get("title") or [None])[0],
            "type": item.get("type"),
            "container_title": (item.get("container-title") or [None])[0],
            "published": item.get("published-print") or item.get("published-online") or item.get("created"),
            "url": item.get("URL"),
        })
    emit({"source": "Crossref API", "command": "crossref-search", "request": params, "normalized": normalized, "response": res})


def cmd_crossref_work(args):
    doi = args.doi.strip()
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    res = request_json(url)
    item = safe_get(res.get("json") or {}, "message") or {}
    normalized = {
        "doi": item.get("DOI"),
        "title": (item.get("title") or [None])[0],
        "type": item.get("type"),
        "container_title": (item.get("container-title") or [None])[0],
        "published": item.get("published-print") or item.get("published-online") or item.get("created"),
        "url": item.get("URL"),
        "relation": item.get("relation"),
    }
    emit({"source": "Crossref API", "command": "crossref-work", "normalized": normalized, "response": res})


def cmd_datacite_doi(args):
    doi = args.doi.strip()
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="")
    res = request_json(url)
    attrs = safe_get(res.get("json") or {}, "data", "attributes") or {}
    normalized = {
        "doi": attrs.get("doi"),
        "publisher": attrs.get("publisher"),
        "publication_year": attrs.get("publicationYear"),
        "title": (attrs.get("titles") or [{}])[0].get("title") if attrs.get("titles") else None,
        "resource_type": safe_get(attrs, "types", "resourceTypeGeneral"),
        "url": attrs.get("url"),
        "related_identifiers": attrs.get("relatedIdentifiers"),
    }
    emit({"source": "DataCite API", "command": "datacite-doi", "normalized": normalized, "response": res})


def normalize_biostudies_hit(hit):
    return {
        "accession": hit.get("accession"),
        "type": hit.get("type"),
        "title": hit.get("title"),
        "author": hit.get("author"),
        "files": hit.get("files"),
        "links": hit.get("links"),
        "release_date": hit.get("release_date"),
        "is_public": hit.get("isPublic"),
    }


def cmd_biostudies_search(args):
    params = {"query": args.query, "pageSize": args.page_size}
    res = request_json("https://www.ebi.ac.uk/biostudies/api/v1/search", params=params)
    hits = (res.get("json") or {}).get("hits", []) if res.get("ok") else []
    emit({
        "source": "BioStudies API",
        "command": "biostudies-search",
        "request": params,
        "normalized": [normalize_biostudies_hit(hit) for hit in hits],
        "response": res,
    })


def cmd_biostudies_study(args):
    url = f"https://www.ebi.ac.uk/biostudies/api/v1/studies/{urllib.parse.quote(args.accession)}/info"
    res = request_json(url)
    data = res.get("json") if res.get("ok") else {}
    normalized = {
        "accession": args.accession,
        "is_public": data.get("isPublic") if isinstance(data, dict) else None,
        "files": data.get("files") if isinstance(data, dict) else None,
        "http_link": data.get("httpLink") if isinstance(data, dict) else None,
        "ftp_link": data.get("ftpLink") if isinstance(data, dict) else None,
        "globus_link": data.get("globusLink") if isinstance(data, dict) else None,
        "relative_path": data.get("relPath") if isinstance(data, dict) else None,
    }
    emit({"source": "BioStudies API", "command": "biostudies-study", "normalized": normalized, "response": res})


def normalize_zenodo_record(record):
    metadata = record.get("metadata") or {}
    files = []
    for item in record.get("files", []) or []:
        links = item.get("links") or {}
        files.append({
            "key": item.get("key"),
            "size": item.get("size"),
            "checksum": item.get("checksum"),
            "download_url": links.get("self") or links.get("download"),
        })
    return {
        "id": record.get("id") or record.get("recid"),
        "doi": record.get("doi") or metadata.get("doi"),
        "title": metadata.get("title") or record.get("title"),
        "publication_date": metadata.get("publication_date"),
        "access_right": metadata.get("access_right"),
        "resource_type": safe_get(metadata, "resource_type", "title"),
        "html_url": safe_get(record, "links", "self_html"),
        "files": files,
    }


def cmd_zenodo_search(args):
    params = {"q": args.query, "size": args.size}
    res = request_json("https://zenodo.org/api/records", params=params)
    hits = safe_get(res.get("json") or {}, "hits", "hits") or []
    emit({
        "source": "Zenodo REST API",
        "command": "zenodo-search",
        "request": params,
        "normalized": [normalize_zenodo_record(record) for record in hits],
        "response": res,
    })


def zenodo_record_id(value):
    text = value.strip()
    match = re.search(r"zenodo\.(\d+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"/records/(\d+)", text)
    if match:
        return match.group(1)
    return text


def cmd_zenodo_record(args):
    recid = zenodo_record_id(args.record)
    res = request_json(f"https://zenodo.org/api/records/{urllib.parse.quote(recid)}")
    normalized = normalize_zenodo_record(res.get("json") or {}) if res.get("ok") else None
    emit({"source": "Zenodo REST API", "command": "zenodo-record", "normalized": normalized, "response": res})


def normalize_figshare_article(article):
    files = []
    for item in article.get("files", []) or []:
        files.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "size": item.get("size"),
            "download_url": item.get("download_url"),
            "md5": item.get("computed_md5") or item.get("supplied_md5"),
            "mimetype": item.get("mimetype"),
        })
    return {
        "id": article.get("id"),
        "title": article.get("title"),
        "doi": article.get("doi"),
        "resource_doi": article.get("resource_doi"),
        "resource_title": article.get("resource_title"),
        "url_public_html": article.get("url_public_html") or article.get("figshare_url"),
        "published_date": article.get("published_date"),
        "is_public": article.get("is_public"),
        "download_disabled": article.get("download_disabled"),
        "files": files,
    }


def cmd_figshare_search(args):
    body = {"search_for": args.query, "page_size": args.page_size}
    res = request_json("https://api.figshare.com/v2/articles/search", method="POST", body=body)
    rows = res.get("json") if res.get("ok") else []
    emit({
        "source": "Figshare API",
        "command": "figshare-search",
        "request": body,
        "normalized": [normalize_figshare_article(row) for row in rows] if isinstance(rows, list) else None,
        "response": res,
    })


def cmd_figshare_article(args):
    res = request_json(f"https://api.figshare.com/v2/articles/{urllib.parse.quote(str(args.article_id))}")
    normalized = normalize_figshare_article(res.get("json") or {}) if res.get("ok") else None
    emit({"source": "Figshare API", "command": "figshare-article", "normalized": normalized, "response": res})


def dryad_identifier(value):
    text = value.strip()
    if text.lower().startswith("doi:"):
        return text
    if text.startswith("10.5061/"):
        return "doi:" + text
    return text


def normalize_dryad_dataset(dataset):
    links = dataset.get("_links") or {}
    download = safe_get(links, "stash:download", "href")
    return {
        "identifier": dataset.get("identifier"),
        "id": dataset.get("id"),
        "title": dataset.get("title"),
        "storage_size": dataset.get("storageSize"),
        "publication_date": dataset.get("publicationDate"),
        "related_publication_doi": dataset.get("relatedPublicationDOI"),
        "download_url": urllib.parse.urljoin("https://datadryad.org", download) if download else None,
    }


def cmd_dryad_search(args):
    params = {"q": args.query, "per_page": args.per_page}
    res = request_json("https://datadryad.org/api/v2/search", params=params)
    datasets = safe_get(res.get("json") or {}, "_embedded", "stash:datasets") or []
    emit({
        "source": "Dryad API",
        "command": "dryad-search",
        "request": params,
        "normalized": [normalize_dryad_dataset(ds) for ds in datasets],
        "response": res,
    })


def cmd_dryad_dataset(args):
    ident = dryad_identifier(args.identifier)
    url = "https://datadryad.org/api/v2/datasets/" + urllib.parse.quote(ident, safe="")
    res = request_json(url)
    normalized = normalize_dryad_dataset(res.get("json") or {}) if res.get("ok") else None
    emit({"source": "Dryad API", "command": "dryad-dataset", "normalized": normalized, "response": res})


def cmd_hca_catalogs(args):
    res = request_json("https://service.azul.data.humancellatlas.org/index/catalogs")
    data = res.get("json") if res.get("ok") else {}
    normalized = {
        "default_catalog": data.get("default_catalog") if isinstance(data, dict) else None,
        "catalogs": sorted((data.get("catalogs") or {}).keys()) if isinstance(data, dict) else [],
    }
    emit({"source": "HCA Azul Data Browser API", "command": "hca-catalogs", "normalized": normalized, "response": res})


def hca_default_catalog():
    res = request_json("https://service.azul.data.humancellatlas.org/index/catalogs")
    data = res.get("json") if res.get("ok") else {}
    return data.get("default_catalog") if isinstance(data, dict) else "dcp59"


def normalize_hca_project(hit):
    project = (hit.get("projects") or [{}])[0]
    return {
        "entry_id": hit.get("entryId"),
        "project_id": project.get("projectId"),
        "project_title": project.get("projectTitle"),
        "project_shortname": project.get("projectShortname"),
        "estimated_cell_count": project.get("estimatedCellCount"),
        "data_use_restriction": project.get("dataUseRestriction"),
        "publications": project.get("publications"),
        "file_type_summaries": hit.get("fileTypeSummaries"),
    }


def cmd_hca_projects(args):
    catalog = args.catalog or hca_default_catalog()
    filters = {}
    if args.organ:
        filters["organ"] = {"is": args.organ}
    if args.disease:
        filters["sampleDisease"] = {"is": args.disease}
    if args.project_id:
        filters["projectId"] = {"is": args.project_id}
    if args.filters_json:
        filters.update(json.loads(args.filters_json))
    params = {"catalog": catalog, "size": args.size}
    if filters:
        params["filters"] = json.dumps(filters)
    res = request_json("https://service.azul.data.humancellatlas.org/index/projects", params=params)
    hits = (res.get("json") or {}).get("hits", []) if res.get("ok") else []
    emit({
        "source": "HCA Azul Data Browser API",
        "command": "hca-projects",
        "request": params,
        "normalized": [normalize_hca_project(hit) for hit in hits],
        "response": res,
    })


def encode_path_for_accession(accession):
    upper = accession.upper()
    if upper.startswith("ENCFF"):
        return f"/files/{upper}/"
    if upper.startswith("ENCSR"):
        return f"/experiments/{upper}/"
    if upper.startswith("ENCBS"):
        return f"/biosamples/{upper}/"
    if upper.startswith("ENCDO"):
        return f"/donors/{upper}/"
    if upper.startswith("ENCLB"):
        return f"/libraries/{upper}/"
    return f"/search/?searchTerm={urllib.parse.quote(accession)}"


def cmd_encode_object(args):
    path = encode_path_for_accession(args.accession)
    url = urllib.parse.urljoin("https://www.encodeproject.org", path)
    res = request_json(url, params={"format": "json"})
    data = res.get("json") if res.get("ok") else {}
    href = data.get("href") if isinstance(data, dict) else None
    normalized = {
        "accession": data.get("accession") if isinstance(data, dict) else args.accession,
        "title": data.get("title") if isinstance(data, dict) else None,
        "status": data.get("status") if isinstance(data, dict) else None,
        "file_format": data.get("file_format") if isinstance(data, dict) else None,
        "output_type": data.get("output_type") if isinstance(data, dict) else None,
        "download_url": urllib.parse.urljoin("https://www.encodeproject.org", href) if href else None,
    }
    emit({"source": "ENCODE REST API", "command": "encode-object", "normalized": normalized, "response": res})


def cmd_supplement_search(args):
    results = {}
    results["biostudies"] = request_json(
        "https://www.ebi.ac.uk/biostudies/api/v1/search",
        params={"query": args.query, "pageSize": args.limit},
    )
    results["zenodo"] = request_json("https://zenodo.org/api/records", params={"q": args.query, "size": args.limit})
    results["figshare"] = request_json(
        "https://api.figshare.com/v2/articles/search",
        method="POST",
        body={"search_for": args.query, "page_size": args.limit},
    )
    results["dryad"] = request_json("https://datadryad.org/api/v2/search", params={"q": args.query, "per_page": args.limit})
    normalized = {
        "biostudies": [normalize_biostudies_hit(hit) for hit in ((results["biostudies"].get("json") or {}).get("hits", []) if results["biostudies"].get("ok") else [])],
        "zenodo": [normalize_zenodo_record(record) for record in (safe_get(results["zenodo"].get("json") or {}, "hits", "hits") or [])],
        "figshare": [normalize_figshare_article(row) for row in (results["figshare"].get("json") if results["figshare"].get("ok") else [])[: args.limit]],
        "dryad": [normalize_dryad_dataset(ds) for ds in (safe_get(results["dryad"].get("json") or {}, "_embedded", "stash:datasets") or [])],
    }
    emit({"source": "Supplemental repository APIs", "command": "supplement-search", "query": args.query, "normalized": normalized, "responses": results})


def cmd_resolve_accession(args):
    routes = classify_accession(args.accession)
    fetched = []
    if args.fetch:
        for route in routes:
            command = route["command"]
            if command.startswith("ena-runs"):
                query = ena_query_for_accession(args.accession)
                fetched.append({"route": route, "response": request_json("https://www.ebi.ac.uk/ena/portal/api/search", params={"result": "read_run", "query": query, "fields": "run_accession,study_accession,secondary_study_accession,fastq_ftp,fastq_md5", "format": "json", "limit": args.limit})})
            elif command.startswith("pride"):
                fetched.append({"route": route, "project": request_json(f"https://www.ebi.ac.uk/pride/ws/archive/v3/projects/{args.accession}"), "files": request_json(f"https://www.ebi.ac.uk/pride/ws/archive/v3/projects/{args.accession}/files/all")})
            elif command.startswith("metabolights"):
                fetched.append({"route": route, "response": request_json(f"https://www.ebi.ac.uk/metabolights/ws/studies/{args.accession}")})
            elif command.startswith("mgnify"):
                fetched.append({"route": route, "study": request_json(f"https://www.ebi.ac.uk/metagenomics/api/latest/studies/{args.accession}"), "downloads": request_json(f"https://www.ebi.ac.uk/metagenomics/api/latest/studies/{args.accession}/downloads", params={"page_size": args.limit})})
            elif command.startswith("biostudies-study"):
                fetched.append({"route": route, "response": request_json(f"https://www.ebi.ac.uk/biostudies/api/v1/studies/{urllib.parse.quote(args.accession)}/info")})
            elif command.startswith("zenodo-record"):
                recid = zenodo_record_id(args.accession)
                fetched.append({"route": route, "response": request_json(f"https://zenodo.org/api/records/{urllib.parse.quote(recid)}")})
            elif command.startswith("dryad-dataset"):
                ident = dryad_identifier(args.accession)
                fetched.append({"route": route, "response": request_json("https://datadryad.org/api/v2/datasets/" + urllib.parse.quote(ident, safe=""))})
            elif command.startswith("datacite-doi"):
                fetched.append({"route": route, "response": request_json("https://api.datacite.org/dois/" + urllib.parse.quote(args.accession, safe=""))})
            elif command.startswith("crossref-work"):
                fetched.append({"route": route, "response": request_json("https://api.crossref.org/works/" + urllib.parse.quote(args.accession, safe=""))})
            elif command.startswith("encode-object"):
                path = encode_path_for_accession(args.accession)
                fetched.append({"route": route, "response": request_json(urllib.parse.urljoin("https://www.encodeproject.org", path), params={"format": "json"})})
    emit({"source": "Omics API adapter", "command": "resolve-accession", "accession": args.accession, "routes": routes, "fetched": fetched})


def build_parser():
    parser = argparse.ArgumentParser(description="Query common public omics repository APIs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("resolve-accession", help="Identify likely repositories for an accession/DOI and optionally fetch details.")
    p.add_argument("--accession", required=True)
    p.add_argument("--fetch", action="store_true", help="Fetch exact details for supported route types.")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_resolve_accession)

    p = sub.add_parser("ncbi-search", help="Search an NCBI Entrez database.")
    p.add_argument("--db", required=True, help="Entrez database, e.g. gds, sra, pubmed, bioproject.")
    p.add_argument("--term", required=True)
    p.add_argument("--retmax", type=int, default=20)
    p.set_defaults(func=cmd_ncbi_search)

    p = sub.add_parser("ncbi-summary", help="Fetch NCBI Entrez summaries for comma-separated IDs.")
    p.add_argument("--db", required=True)
    p.add_argument("--ids", required=True)
    p.set_defaults(func=cmd_ncbi_summary)

    p = sub.add_parser("ena-runs", help="Find ENA read_run records and FASTQ paths.")
    p.add_argument("--accession", default="", help="Study, run, or sample accession.")
    p.add_argument("--query", default="", help="Raw ENA Portal query. Overrides --accession.")
    p.add_argument("--fields", default="")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_ena_runs)

    p = sub.add_parser("cellxgene-collection", help="Resolve CELLxGENE collection datasets and assets.")
    p.add_argument("--collection-id", required=True)
    p.set_defaults(func=cmd_cellxgene_collection)

    p = sub.add_parser("gdc-files", help="Search GDC files.")
    p.add_argument("--project", action="append", help="Project ID, e.g. TCGA-LUAD. Repeatable.")
    p.add_argument("--data-category", action="append", help="Data category. Repeatable.")
    p.add_argument("--data-type", action="append", help="Data type. Repeatable.")
    p.add_argument("--access", action="append", choices=["open", "controlled"])
    p.add_argument("--size", type=int, default=20)
    p.add_argument(
        "--fields",
        default="file_id,file_name,data_type,data_format,access,file_size,cases.submitter_id",
    )
    p.set_defaults(func=cmd_gdc_files)

    p = sub.add_parser("encode-search", help="Search ENCODE with generic key=value filters.")
    p.add_argument("--type", default="File", help="ENCODE object type if not supplied via --param.")
    p.add_argument("--param", action="append", default=[], help="Search parameter, e.g. assay_term_name=RNA-seq.")
    p.add_argument("--limit", default="10")
    p.set_defaults(func=cmd_encode_search)

    p = sub.add_parser("encode-object", help="Fetch an ENCODE object by accession, e.g. ENCFF..., ENCSR....")
    p.add_argument("--accession", required=True)
    p.set_defaults(func=cmd_encode_object)

    p = sub.add_parser("pride-project", help="Fetch a PRIDE project by PXD accession.")
    p.add_argument("--accession", required=True)
    p.set_defaults(func=cmd_pride_project)

    p = sub.add_parser("pride-files", help="List PRIDE project files.")
    p.add_argument("--accession", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_pride_files)

    p = sub.add_parser("mgnify-study", help="Fetch an MGnify study by MGYS/ERP/PRJ accession.")
    p.add_argument("--accession", required=True)
    p.set_defaults(func=cmd_mgnify_study)

    p = sub.add_parser("mgnify-downloads", help="List MGnify processed study downloads.")
    p.add_argument("--accession", required=True)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(func=cmd_mgnify_downloads)

    p = sub.add_parser("metabolights-study", help="Fetch MetaboLights study metadata and public URLs.")
    p.add_argument("--accession", required=True)
    p.set_defaults(func=cmd_metabolights_study)

    p = sub.add_parser("crossref-search", help="Search Crossref works by title or general query.")
    p.add_argument("--query", default="")
    p.add_argument("--title", default="")
    p.add_argument("--rows", type=int, default=5)
    p.set_defaults(func=cmd_crossref_search)

    p = sub.add_parser("crossref-work", help="Fetch a Crossref work by DOI.")
    p.add_argument("--doi", required=True)
    p.set_defaults(func=cmd_crossref_work)

    p = sub.add_parser("datacite-doi", help="Fetch DataCite metadata for dataset DOIs.")
    p.add_argument("--doi", required=True)
    p.set_defaults(func=cmd_datacite_doi)

    p = sub.add_parser("biostudies-search", help="Search BioStudies and ArrayExpress-indexed records.")
    p.add_argument("--query", required=True)
    p.add_argument("--page-size", type=int, default=10)
    p.set_defaults(func=cmd_biostudies_search)

    p = sub.add_parser("biostudies-study", help="Fetch BioStudies study file/location info.")
    p.add_argument("--accession", required=True)
    p.set_defaults(func=cmd_biostudies_study)

    p = sub.add_parser("zenodo-search", help="Search Zenodo records.")
    p.add_argument("--query", required=True)
    p.add_argument("--size", type=int, default=10)
    p.set_defaults(func=cmd_zenodo_search)

    p = sub.add_parser("zenodo-record", help="Fetch a Zenodo record by record ID, record URL, or Zenodo DOI.")
    p.add_argument("--record", required=True)
    p.set_defaults(func=cmd_zenodo_record)

    p = sub.add_parser("figshare-search", help="Search Figshare public articles.")
    p.add_argument("--query", required=True)
    p.add_argument("--page-size", type=int, default=10)
    p.set_defaults(func=cmd_figshare_search)

    p = sub.add_parser("figshare-article", help="Fetch Figshare article details and file URLs.")
    p.add_argument("--article-id", required=True)
    p.set_defaults(func=cmd_figshare_article)

    p = sub.add_parser("dryad-search", help="Search Dryad datasets.")
    p.add_argument("--query", required=True)
    p.add_argument("--per-page", type=int, default=10)
    p.set_defaults(func=cmd_dryad_search)

    p = sub.add_parser("dryad-dataset", help="Fetch Dryad dataset metadata by DOI identifier.")
    p.add_argument("--identifier", required=True, help="Example: 10.5061/dryad.t76hdr806")
    p.set_defaults(func=cmd_dryad_dataset)

    p = sub.add_parser("hca-catalogs", help="List HCA Azul catalogs and default catalog.")
    p.set_defaults(func=cmd_hca_catalogs)

    p = sub.add_parser("hca-projects", help="Search HCA Azul projects with optional facet filters.")
    p.add_argument("--catalog", default="")
    p.add_argument("--organ", action="append")
    p.add_argument("--disease", action="append")
    p.add_argument("--project-id", action="append")
    p.add_argument("--filters-json", default="", help="Raw Azul filters JSON merged with shortcut filters.")
    p.add_argument("--size", type=int, default=10)
    p.set_defaults(func=cmd_hca_projects)

    p = sub.add_parser("supplement-search", help="Search BioStudies, Zenodo, Figshare, and Dryad together.")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_supplement_search)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
