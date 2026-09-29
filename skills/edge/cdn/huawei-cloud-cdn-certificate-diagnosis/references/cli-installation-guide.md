# CLI Installation Guide

This skill depends on two types of tools: Huawei Cloud CLI (hcloud / KooCLI) and Python (>= 3.8). The certificate probe (`scripts/cert_probe.py`) uses only the Python standard library (`ssl`, `socket`); no third-party packages need to be installed.

## Huawei Cloud CLI (hcloud / KooCLI)

### Installation

Download and install from the official site:
https://support.huaweicloud.com/hcloudcli/index.html

### Version Check

```bash
hcloud version
```

Ensure the version >= 3.2.0.

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

### Version Requirement

The `scripts/cert_probe.py` and `scripts/cert_expiry_check.py` scripts of this skill require **Python >= 3.8**.

### Installation

- **Windows**: download from https://www.python.org/downloads/; check "Add Python to PATH" during installation
- **Linux**: `yum install python3` or `apt install python3`
- **macOS**: `brew install python` or use the pre-installed version

### Version Check

```bash
python --version
```

Or (on some systems):

```bash
python3 --version
```

Confirm the output >= `Python 3.8.x`.

## Python Library Dependencies

This skill's probe scripts depend **only on the Python standard library**; no third-party packages need to be installed via `pip`.

| Script | Required Python libraries | Install command |
|--------|---------------------------|-----------------|
| `scripts/cert_probe.py` | stdlib `ssl`, `socket` (ship with the interpreter) | _(none — no `pip install` required)_ |
| `scripts/cert_expiry_check.py` | stdlib `argparse`, `json`, `sys`, `time` | _(none — no `pip install` required)_ |

### Library Availability Check

Because `cert_probe.py` uses stdlib modules that always ship with the interpreter, the availability check reduces to confirming the Python version meets the >= 3.8 requirement above. If those imports were to fail on a stripped/minimal interpreter build, run:

```bash
python -c "import ssl, socket; print('ok')"
```

A failure indicates the host's Python interpreter is missing its standard library; reinstall a complete Python >= 3.8 build as documented under **Installation** above. No `pip install` will recover from this state because `ssl` and `socket` ship with the interpreter itself.

## Notes

- CDN APIs only support two regions: `cn-north-1` and `ap-southeast-1`; recommend using `cn-north-1`
- All hcloud parameters must use the `--key=value` format (equals sign); space-separated format is not supported
- After credentials are configured, there is no need to repeat configuration; hcloud automatically reads the local configuration file
- The `cert_probe.py` probe enforces a 10-second timeout by default (configurable via `--timeout`, range 1-30)
- If the `python` command points to Python 2, use `python3 scripts/cert_probe.py` instead
