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

Check that the output contains a valid AK/SK configuration.

## Python Interpreter

The probe scripts (`scripts/file_probe.py`, `scripts/dns_txt_probe.py`) require Python >= 3.8.

### Version Check

```bash
python --version
```

Ensure version >= 3.8.

## Python Library Dependencies

The ownership verification probes replaced the former `curl` / `dig` shell
commands with Python probe scripts that emit structured JSON. The required
Python libraries are:

| Library | Minimum Version | Used By | Purpose |
|---------|-----------------|---------|---------|
| `requests` | 2.25 | `scripts/file_probe.py` | HTTP file verification probe (GET with 10-second timeout) |
| `dnspython` | 2.1 | `scripts/dns_txt_probe.py` | DNS TXT record query with optional explicit resolver |

`requests` and `dnspython` are not part of the Python standard library; install
them via pip.

### Installation

```bash
pip install requests>=2.25 dnspython>=2.1
```

### Version Check

Confirm both libraries import successfully and meet the minimum version
requirement:

```bash
python -c "import requests; assert requests.__version__ >= '2.25'; print('requests ok')"
python -c "import dns.resolver; print('dnspython ok')"
```

Or in one line:

```bash
python -c "import requests, dns.resolver; print('ok')"
```

If the import fails with `ModuleNotFoundError`, install the missing library
per the command above and retry.

## Notes

- CDN API supports only two regions: `cn-north-1` and `ap-southeast-1`. Using `cn-north-1` uniformly is recommended
- All hcloud parameters must use the `--key=value` format (connected with equals sign); space-separated format is not supported
- After credentials are configured, no repeat configuration is needed; hcloud will automatically read the local configuration file
- No `curl` or `dig` installation is required; file and DNS probes are performed by the Python probe scripts under `scripts/`
- Probe scripts enforce a 10-second timeout via `--timeout` (default 10); no shell-level timeout flag is needed
