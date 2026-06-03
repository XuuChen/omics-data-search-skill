# Download And Accessibility Validation

Never call a large file downloadable until headers or a small byte-range request prove it.

## Basic URL Probe

Use `scripts/probe_url.sh` from the skill directory when possible:

```bash
"${CLAUDE_SKILL_DIR}/scripts/probe_url.sh" 'https://example.org/file.h5ad'
```

Manual equivalent:

```bash
url='https://example.org/file.h5ad'
curl -sSIL -L --max-redirs 5 "$url"
curl -sSL -r 0-0 -o /dev/null -D - "$url"
```

Interpretation:

- `200 OK` on `HEAD` with plausible `Content-Length` is good.
- `206 Partial Content` on `Range: bytes=0-0` proves byte-range download works.
- `403`, `401`, login HTML, or small HTML `200` means not directly downloadable.
- `404` means the path is broken; return to the repository API/page instead of guessing variants.
- Some servers do not support `HEAD`; use a tiny `Range` request or official API metadata.

## Large File Download Commands

Use resumable downloads and avoid preallocating huge files on shared filesystems:

```bash
aria2c -c -x 8 -s 8 -k 1M --file-allocation=none -o output.file 'URL'
wget -c -O output.file 'URL'
curl -L -C - -o output.file 'URL'
```

If checksums are available:

```bash
md5sum output.file
sha256sum output.file
```

Compare to repository-provided checksums, not values found in unrelated mirrors.

## China-Mainland / No-VPN Validation

Use this only when the user asks or when mainland accessibility is central to the task.

1. Test from the actual target machine first with `HEAD` and byte range.
2. If the target machine is remote, obey its project SSH/session policy and batch probes.
3. If public CN probes are acceptable, use a measurement service such as Globalping and report city/network/status.
4. Do not claim universal mainland availability. Say "verified from these probes at this time."

Globalping example for `HEAD`:

```bash
host='datasets.cellxgene.cziscience.com'
path='/file.h5ad'

curl -sS -X POST 'https://api.globalping.io/v1/measurements' \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON
{
  "type": "http",
  "target": "${host}",
  "locations": [{"country": "CN", "limit": 3}],
  "measurementOptions": {
    "protocol": "HTTPS",
    "port": 443,
    "request": {
      "method": "HEAD",
      "path": "${path}"
    }
  }
}
JSON
```

Then fetch the returned measurement URL:

```bash
curl -sS 'https://api.globalping.io/v1/measurements/MEASUREMENT_ID' \
  | jq '.status, [.results[] | {city: .probe.city, network: .probe.network, statusCode: .result.statusCode, error: .result.error}]'
```

For true byte retrieval, use `GET` with `Range: bytes=0-0` if the measurement tool supports custom headers.

## Final Evidence Line

For each recommended URL, include one short evidence line:

```text
Verified 2026-06-03: HEAD 200, Range 206, Content-Length 5,873,641,828 bytes, probe/host: Shenzhen Chinanet.
```

If not verified:

```text
Not verified: repository page exists, but direct file URL requires login or API-generated links.
```

