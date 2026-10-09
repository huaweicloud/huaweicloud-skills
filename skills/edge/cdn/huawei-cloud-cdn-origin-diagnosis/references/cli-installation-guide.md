# CLI Installation Guide

## Huawei Cloud CLI (hcloud / KooCLI)

### Installation

Download and install from the official site:
https://support.huaweicloud.com/hcloudcli/index.html

### Version Check

```bash
hcloud version
```

Ensure the version is >= 3.2.0.

### Configuration

```bash
hcloud configure
```

Enter AK/SK and region as prompted.

### Verify Configuration

```bash
hcloud configure list
```

Check that the output contains a valid AK/SK configuration.

## Python

### Version Check

```bash
python --version
```

Ensure the Python interpreter version is >= 3.8.

## Python Library Dependencies

The origin connectivity probe (`scripts/origin_probe.py`) relies on the
third-party `requests` library.

### Required Libraries

| Library | Minimum Version | Used By |
|---------|-----------------|---------|
| `requests` | >= 2.25 | `scripts/origin_probe.py` |

### Installation

```bash
pip install requests>=2.25
```

### Verification

Confirm both the interpreter and the library import succeed:

```bash
python -c "import requests; assert requests.__version__ >= '2.25'; print('ok')"
```

A successful run prints `ok`. If the import fails or the version is too low,
install or upgrade the library before running the skill.

## Notes

- CDN APIs only support the `cn-north-1` and `ap-southeast-1` regions; using `cn-north-1` is recommended
- All hcloud parameters must use the `--key=value` format (connected with equals sign); space-separated format is not supported
- After credentials are configured, no reconfiguration is needed; hcloud automatically reads the local config file
- `scripts/origin_probe.py` sends HEAD requests by default (GET fallback on HTTP 405) and is read-only with no side effects on the origin server
