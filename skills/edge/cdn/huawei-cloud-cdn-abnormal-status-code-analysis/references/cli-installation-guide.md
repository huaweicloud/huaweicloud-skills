# CLI Installation Guide

## Huawei Cloud CLI (hcloud / KooCLI)

### Installation

Download and install from the official site:
https://support.huaweicloud.com/hcloudcli/index.html

### Version Check

```bash
hcloud version
```

Ensure version >= 3.2.0.

### Configuration

```bash
hcloud configure
```

Follow the prompts to enter AK/SK and region.

### Verify Configuration

```bash
hcloud configure list
```

Check that the output contains a valid AK/SK configuration (mode=AKSK).

## Python Interpreter

The log helper `scripts/fetch_cdn_log.py` requires Python >= 3.8.

```bash
python --version
```

## Python Library Dependencies

| Library | Minimum Version | Used By | Purpose |
|---------|-----------------|---------|---------|
| `requests` | 2.25 | `scripts/fetch_cdn_log.py` | Download + decompress CDN access log (read-only GET) |

Install if missing:

```bash
pip install requests>=2.25
```

### Version Check

```bash
python -c "import requests; print('requests ok')"
```

## Notes

- CDN API supports only two regions: `cn-north-1` and `ap-southeast-1`. Using
  `cn-north-1` uniformly is recommended. **`cn-north-4` is NOT supported by
  CDN** (it returns "cli-region的值不支持").
- All hcloud parameters must use the `--key=value` format (equals sign); the
  space-separated form is unsupported.
- Time parameters are millisecond timestamps, `[start,end)` left-closed
  right-open, aligned to the interval's required points.
- After credentials are configured once, hcloud reads the local configuration
  file automatically; no repeat configuration is needed.
- No `curl`/`gunzip` installation is strictly required — the log helper handles
  download + decompress in Python; `gunzip` is only a fallback.
