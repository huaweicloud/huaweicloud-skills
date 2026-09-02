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

Check the output contains a valid AK/SK configuration.

## Python Interpreter

### Version Requirement

Python >= 3.8 is required (the DNS probe script `scripts/dns_resolve.py` relies on it).

### Version Check

```bash
python --version
```

## Python Library Dependencies

The DNS resolution probe (`scripts/dns_resolve.py`) depends on the third-party
`dnspython` library. No `curl` or `dig` binary is required.

### dnspython >= 2.1

Install via pip:

```bash
pip install dnspython>=2.1
```

### Verify Library Availability

```bash
python -c "import dns.resolver; print('dnspython ok')"
```

If the import fails, install the library as shown above. The probe script also
self-checks the import and emits a JSON error with
`error.reason = "missing_library"` (exit code 2) when the library is absent.

## Notes

- CDN APIs only support two regions: `cn-north-1` and `ap-southeast-1`; use `cn-north-1` to avoid confusion
- All hcloud parameters must use the `--key=value` format (connected with equals sign); space-separated format is not supported
- Once configured, credentials do not need to be reconfigured; hcloud reads the local config file automatically
- The DNS probe enforces a 10-second timeout via `python scripts/dns_resolve.py --domain <domain_name> --timeout 10` (default 10)
- No `curl` or `dig` binary is required; all DNS probing is performed through `dnspython`
