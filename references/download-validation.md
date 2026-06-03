# Download And Accessibility Validation

Never call a large file downloadable until headers or a small byte-range request prove it.

## Basic URL Probe

Use the structured API adapter first:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" probe-url \
  --url 'https://example.org/file.h5ad' \
  --range
```

Use `scripts/probe_url.sh` from the skill directory as a shell fallback:

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

Generate a command plan when possible:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" make-download-plan \
  --url 'https://example.org/file.h5ad' \
  --output file.h5ad \
  --expected-size 123456789 \
  --md5 REPOSITORY_MD5
```

Manual equivalent: use resumable downloads and avoid preallocating huge files on shared filesystems:

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

Structured Globalping helper:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" probe-china-access \
  --url 'https://example.org/file.h5ad' \
  --method RANGE \
  --limit 3
```

Dry-run the measurement payload in CI or before spending public probe credits:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/omics_api.py" probe-china-access \
  --url 'https://example.org/file.h5ad' \
  --method RANGE \
  --limit 3 \
  --dry-run
```

For true byte retrieval, use `--method RANGE`. The helper sends `GET` with `Range: bytes=0-0` and reports city/network/status.

## Final Evidence Line

For each recommended URL, include one short evidence line:

```text
Verified 2026-06-03: HEAD 200, Range 206, Content-Length 5,873,641,828 bytes, probe/host: Shenzhen Chinanet.
```

If not verified:

```text
Not verified: repository page exists, but direct file URL requires login or API-generated links.
```
