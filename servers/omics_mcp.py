#!/usr/bin/env python3
"""Minimal stdio MCP server for omics-data-search.

This server intentionally wraps scripts/omics_api.py instead of reimplementing
repository logic. It speaks newline-delimited JSON-RPC over stdin/stdout and
uses no third-party dependencies.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


SERVER_NAME = "omics-data-search"
SERVER_VERSION = "0.5.0"
PROTOCOL_VERSION = "2025-06-18"
ROOT = Path(__file__).resolve().parents[1]
OMICS_API = ROOT / "scripts" / "omics_api.py"


def schema(properties, required=None, additional=False):
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": additional,
    }


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}
STRING_ARRAY = {"type": "array", "items": {"type": "string"}}


TOOLS = [
    {
        "name": "resolve_accession",
        "title": "Resolve Omics Accession",
        "description": "Identify likely repositories for GSE/SRR/PRJNA/PXD/MTBLS/MGYS/ENCFF/DOI/UUID inputs and optionally fetch exact details.",
        "inputSchema": schema(
            {
                "accession": {**STRING, "description": "Accession, DOI, UUID, or record identifier."},
                "fetch": {**BOOLEAN, "description": "Fetch exact details for supported route types."},
                "limit": {**INTEGER, "description": "Maximum records for fetched list-style lookups."},
            },
            ["accession"],
        ),
    },
    {
        "name": "ncbi_search",
        "title": "Search NCBI",
        "description": "Search NCBI Entrez databases such as gds, sra, pubmed, bioproject, or biosample.",
        "inputSchema": schema({"db": STRING, "term": STRING, "retmax": INTEGER}, ["db", "term"]),
    },
    {
        "name": "probe_url",
        "title": "Probe Download URL",
        "description": "Verify a direct download URL with HEAD and byte-range checks before recommending a large download.",
        "inputSchema": schema(
            {
                "url": {**STRING, "description": "Absolute http(s) URL to probe."},
                "range": {**BOOLEAN, "description": "Also request Range: bytes=0-0. Defaults to true."},
                "timeout": {**INTEGER, "description": "Per-request timeout in seconds."},
            },
            ["url"],
        ),
    },
    {
        "name": "make_download_plan",
        "title": "Make Download Plan",
        "description": "Generate resumable aria2c/wget/curl commands and checksum/size validation commands for a verified URL.",
        "inputSchema": schema(
            {
                "url": {**STRING, "description": "Absolute download URL."},
                "output": {**STRING, "description": "Output filename. Defaults to the URL basename."},
                "expected_size": {**INTEGER, "description": "Expected file size in bytes, if known."},
                "md5": {**STRING, "description": "Repository-provided MD5 checksum, if known."},
                "sha256": {**STRING, "description": "Repository-provided SHA256 checksum, if known."},
                "connections": {**INTEGER, "description": "aria2c split/connection count."},
            },
            ["url"],
        ),
    },
    {
        "name": "probe_china_access",
        "title": "Probe China-Mainland Access",
        "description": "Use public Globalping CN probes for point-in-time HTTP reachability checks; report city/network/status without claiming universal access.",
        "inputSchema": schema(
            {
                "url": {**STRING, "description": "Absolute http(s) URL to probe."},
                "limit": {**INTEGER, "description": "Number of CN probes to request."},
                "method": {"type": "string", "enum": ["HEAD", "RANGE"], "description": "HEAD or GET with Range: bytes=0-0."},
                "timeout": {**INTEGER, "description": "Total polling timeout in seconds."},
                "dry_run": {**BOOLEAN, "description": "Return the measurement payload without starting a probe."},
            },
            ["url"],
        ),
    },
    {
        "name": "ena_runs",
        "title": "Resolve ENA Runs",
        "description": "Resolve study/run/sample accessions to ENA read_run records, FASTQ HTTPS URLs, and MD5s.",
        "inputSchema": schema({"accession": STRING, "query": STRING, "limit": INTEGER}),
    },
    {
        "name": "cellxgene_collection",
        "title": "Resolve CELLxGENE Collection",
        "description": "Resolve a CELLxGENE collection UUID to datasets and asset URLs such as H5AD files.",
        "inputSchema": schema({"collection_id": STRING}, ["collection_id"]),
    },
    {
        "name": "gdc_files",
        "title": "Search GDC Files",
        "description": "Search GDC files by project, data category/type, and open/controlled access status.",
        "inputSchema": schema(
            {
                "project": STRING_ARRAY,
                "data_category": STRING_ARRAY,
                "data_type": STRING_ARRAY,
                "access": {"type": "array", "items": {"type": "string", "enum": ["open", "controlled"]}},
                "size": INTEGER,
            }
        ),
    },
    {
        "name": "encode_search",
        "title": "Search ENCODE",
        "description": "Search ENCODE using portal-style filters. Pass params as an object of key/value filters.",
        "inputSchema": schema(
            {
                "type": {**STRING, "description": "ENCODE object type, default File."},
                "params": {"type": "object", "additionalProperties": {"type": "string"}},
                "limit": INTEGER,
            }
        ),
    },
    {
        "name": "encode_object",
        "title": "Fetch ENCODE Object",
        "description": "Fetch ENCODE file/experiment/biosample/donor/library details by accession.",
        "inputSchema": schema({"accession": STRING}, ["accession"]),
    },
    {
        "name": "pride_files",
        "title": "List PRIDE Files",
        "description": "List public PRIDE project files and download locations for a PXD accession.",
        "inputSchema": schema({"accession": STRING, "limit": INTEGER}, ["accession"]),
    },
    {
        "name": "mgnify_downloads",
        "title": "List MGnify Downloads",
        "description": "List processed MGnify study downloads for MGYS/ERP/PRJ accessions.",
        "inputSchema": schema({"accession": STRING, "page_size": INTEGER}, ["accession"]),
    },
    {
        "name": "metabolights_study",
        "title": "Fetch MetaboLights Study",
        "description": "Fetch MetaboLights public study metadata and public HTTP/FTP/Globus locations.",
        "inputSchema": schema({"accession": STRING}, ["accession"]),
    },
    {
        "name": "datacite_doi",
        "title": "Fetch DataCite DOI",
        "description": "Fetch DataCite metadata for dataset DOIs, useful for Zenodo, Dryad, Figshare, and BioStudies records.",
        "inputSchema": schema({"doi": STRING}, ["doi"]),
    },
    {
        "name": "supplement_search",
        "title": "Search Supplemental Repositories",
        "description": "Search BioStudies, Zenodo, Figshare, and Dryad together for paper supplements and processed matrices.",
        "inputSchema": schema({"query": STRING, "limit": INTEGER}, ["query"]),
    },
    {
        "name": "biostudies_search",
        "title": "Search BioStudies",
        "description": "Search BioStudies and ArrayExpress-indexed records.",
        "inputSchema": schema({"query": STRING, "page_size": INTEGER}, ["query"]),
    },
    {
        "name": "zenodo_record",
        "title": "Fetch Zenodo Record",
        "description": "Fetch Zenodo record details and files by record ID, record URL, or Zenodo DOI.",
        "inputSchema": schema({"record": STRING}, ["record"]),
    },
    {
        "name": "figshare_article",
        "title": "Fetch Figshare Article",
        "description": "Fetch Figshare article metadata and file download URLs.",
        "inputSchema": schema({"article_id": STRING}, ["article_id"]),
    },
    {
        "name": "dryad_dataset",
        "title": "Fetch Dryad Dataset",
        "description": "Fetch Dryad dataset metadata and packaged download URL by DOI.",
        "inputSchema": schema({"identifier": STRING}, ["identifier"]),
    },
    {
        "name": "hca_projects",
        "title": "Search HCA Projects",
        "description": "Search HCA/Azul projects by organ, disease, project UUID, or raw Azul filters JSON.",
        "inputSchema": schema(
            {
                "catalog": STRING,
                "organ": STRING_ARRAY,
                "disease": STRING_ARRAY,
                "project_id": STRING_ARRAY,
                "filters_json": STRING,
                "size": INTEGER,
            }
        ),
    },
]


TOOL_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def result(request_id, payload):
    send({"jsonrpc": "2.0", "id": request_id, "result": payload})


def error(request_id, code, message, data=None):
    payload = {"code": code, "message": message}
    if data is not None:
        payload["data"] = data
    send({"jsonrpc": "2.0", "id": request_id, "error": payload})


def add_arg(argv, flag, value):
    if value is None or value == "" or value == []:
        return
    if isinstance(value, bool):
        if value:
            argv.append(flag)
        return
    if isinstance(value, list):
        for item in value:
            if item is not None and item != "":
                argv.extend([flag, str(item)])
        return
    argv.extend([flag, str(value)])


def argv_for_tool(name, args):
    args = args or {}
    mapping = {
        "resolve_accession": "resolve-accession",
        "ncbi_search": "ncbi-search",
        "probe_url": "probe-url",
        "make_download_plan": "make-download-plan",
        "probe_china_access": "probe-china-access",
        "ena_runs": "ena-runs",
        "cellxgene_collection": "cellxgene-collection",
        "gdc_files": "gdc-files",
        "encode_search": "encode-search",
        "encode_object": "encode-object",
        "pride_files": "pride-files",
        "mgnify_downloads": "mgnify-downloads",
        "metabolights_study": "metabolights-study",
        "datacite_doi": "datacite-doi",
        "supplement_search": "supplement-search",
        "biostudies_search": "biostudies-search",
        "zenodo_record": "zenodo-record",
        "figshare_article": "figshare-article",
        "dryad_dataset": "dryad-dataset",
        "hca_projects": "hca-projects",
    }
    command = mapping[name]
    argv = [sys.executable, str(OMICS_API), command]

    if name == "resolve_accession":
        add_arg(argv, "--accession", args.get("accession"))
        add_arg(argv, "--fetch", args.get("fetch"))
        add_arg(argv, "--limit", args.get("limit"))
    elif name == "ncbi_search":
        add_arg(argv, "--db", args.get("db"))
        add_arg(argv, "--term", args.get("term"))
        add_arg(argv, "--retmax", args.get("retmax"))
    elif name == "probe_url":
        add_arg(argv, "--url", args.get("url"))
        if args.get("range") is False:
            argv.append("--no-range")
        else:
            argv.append("--range")
        add_arg(argv, "--timeout", args.get("timeout"))
    elif name == "make_download_plan":
        add_arg(argv, "--url", args.get("url"))
        add_arg(argv, "--output", args.get("output"))
        add_arg(argv, "--expected-size", args.get("expected_size"))
        add_arg(argv, "--md5", args.get("md5"))
        add_arg(argv, "--sha256", args.get("sha256"))
        add_arg(argv, "--connections", args.get("connections"))
    elif name == "probe_china_access":
        add_arg(argv, "--url", args.get("url"))
        add_arg(argv, "--limit", args.get("limit"))
        add_arg(argv, "--method", args.get("method"))
        add_arg(argv, "--timeout", args.get("timeout"))
        add_arg(argv, "--dry-run", args.get("dry_run"))
    elif name == "ena_runs":
        add_arg(argv, "--accession", args.get("accession"))
        add_arg(argv, "--query", args.get("query"))
        add_arg(argv, "--limit", args.get("limit"))
    elif name == "cellxgene_collection":
        add_arg(argv, "--collection-id", args.get("collection_id"))
    elif name == "gdc_files":
        add_arg(argv, "--project", args.get("project"))
        add_arg(argv, "--data-category", args.get("data_category"))
        add_arg(argv, "--data-type", args.get("data_type"))
        add_arg(argv, "--access", args.get("access"))
        add_arg(argv, "--size", args.get("size"))
    elif name == "encode_search":
        add_arg(argv, "--type", args.get("type"))
        params = args.get("params") or {}
        for key, value in params.items():
            add_arg(argv, "--param", f"{key}={value}")
        add_arg(argv, "--limit", args.get("limit"))
    elif name in {"encode_object", "pride_files", "mgnify_downloads", "metabolights_study"}:
        add_arg(argv, "--accession", args.get("accession"))
        if name == "pride_files":
            add_arg(argv, "--limit", args.get("limit"))
        if name == "mgnify_downloads":
            add_arg(argv, "--page-size", args.get("page_size"))
    elif name == "datacite_doi":
        add_arg(argv, "--doi", args.get("doi"))
    elif name == "supplement_search":
        add_arg(argv, "--query", args.get("query"))
        add_arg(argv, "--limit", args.get("limit"))
    elif name == "biostudies_search":
        add_arg(argv, "--query", args.get("query"))
        add_arg(argv, "--page-size", args.get("page_size"))
    elif name == "zenodo_record":
        add_arg(argv, "--record", args.get("record"))
    elif name == "figshare_article":
        add_arg(argv, "--article-id", args.get("article_id"))
    elif name == "dryad_dataset":
        add_arg(argv, "--identifier", args.get("identifier"))
    elif name == "hca_projects":
        add_arg(argv, "--catalog", args.get("catalog"))
        add_arg(argv, "--organ", args.get("organ"))
        add_arg(argv, "--disease", args.get("disease"))
        add_arg(argv, "--project-id", args.get("project_id"))
        add_arg(argv, "--filters-json", args.get("filters_json"))
        add_arg(argv, "--size", args.get("size"))
    return argv


def call_tool(name, arguments):
    if name not in TOOL_BY_NAME:
        raise KeyError(f"Unknown tool: {name}")
    proc = subprocess.run(
        argv_for_tool(name, arguments),
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=180,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    if proc.returncode != 0:
        return {
            "content": [{"type": "text", "text": proc.stderr or proc.stdout or f"Command failed: {proc.returncode}"}],
            "isError": True,
        }
    try:
        structured = json.loads(proc.stdout)
    except json.JSONDecodeError:
        structured = {"stdout": proc.stdout}
    return {
        "content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False, indent=2)}],
        "structuredContent": structured,
        "isError": False,
    }


def handle(request):
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if request_id is None:
        return
    if method == "initialize":
        client_version = params.get("protocolVersion")
        result(
            request_id,
            {
                "protocolVersion": client_version or PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": "Use these tools to query public omics repository APIs and return JSON-backed provenance.",
            },
        )
    elif method == "ping":
        result(request_id, {})
    elif method == "tools/list":
        result(request_id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            result(request_id, call_tool(name, arguments))
        except KeyError as exc:
            error(request_id, -32602, str(exc))
        except subprocess.TimeoutExpired:
            result(
                request_id,
                {"content": [{"type": "text", "text": "Tool timed out after 180 seconds."}], "isError": True},
            )
        except Exception as exc:
            result(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
    elif method == "resources/list":
        result(request_id, {"resources": []})
    elif method == "prompts/list":
        result(request_id, {"prompts": []})
    else:
        error(request_id, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            error(None, -32700, f"Parse error: {exc}")
            continue
        if isinstance(message, list):
            for item in message:
                handle(item)
        else:
            handle(message)


if __name__ == "__main__":
    main()
