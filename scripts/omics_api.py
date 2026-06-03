#!/usr/bin/env python3
"""Small public-omics API adapter for Claude Code skills.

Outputs JSON only. Uses the Python standard library so it works on most HPC
login nodes without installing dependencies.
"""

import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request


USER_AGENT = "omics-data-search-skill/0.2 (+https://github.com/XuuChen/omics-data-search-skill)"


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


def build_parser():
    parser = argparse.ArgumentParser(description="Query common public omics repository APIs.")
    sub = parser.add_subparsers(dest="command", required=True)

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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
