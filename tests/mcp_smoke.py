#!/usr/bin/env python3
"""Protocol-level smoke test for the bundled stdio MCP server."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "servers" / "omics_mcp.py"


def rpc(proc, method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("MCP server closed stdout")
    response = json.loads(line)
    if "error" in response:
        raise AssertionError(response["error"])
    return response["result"]


def main():
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=str(ROOT),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        init = rpc(
            proc,
            "initialize",
            {"protocolVersion": "2025-06-18", "clientInfo": {"name": "smoke", "version": "0"}},
            1,
        )
        assert init["serverInfo"]["version"] == "0.5.0"

        tools = rpc(proc, "tools/list", request_id=2)["tools"]
        names = {tool["name"] for tool in tools}
        expected = {"probe_url", "probe_china_access", "make_download_plan", "resolve_accession"}
        missing = expected - names
        assert not missing, f"missing tools: {sorted(missing)}"
        assert len(tools) >= 20

        plan = rpc(
            proc,
            "tools/call",
            {
                "name": "make_download_plan",
                "arguments": {
                    "url": "https://zenodo.org/records/7599104/files/HLCA_full_v1.1_emb.h5ad?download=1",
                    "output": "HLCA_full_v1.1_emb.h5ad",
                },
            },
            3,
        )
        assert not plan["isError"]
        assert "aria2c" in plan["content"][0]["text"]

        dry_run = rpc(
            proc,
            "tools/call",
            {
                "name": "probe_china_access",
                "arguments": {
                    "url": "https://zenodo.org/",
                    "method": "HEAD",
                    "dry_run": True,
                    "limit": 1,
                },
            },
            4,
        )
        assert not dry_run["isError"]
        assert dry_run["structuredContent"]["normalized"]["dry_run"] is True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
