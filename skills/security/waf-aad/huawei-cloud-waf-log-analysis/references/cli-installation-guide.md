# hcloud CLI Installation Guide

## Prerequisites

- Supported OS: Windows 10+, macOS 10.15+, Linux (Ubuntu 18.04+, CentOS 7+)
- Internet access to download the CLI binary

## Installation Steps

### Windows

1. Download from: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. Extract the archive to a directory that is in your system PATH (or add the extraction directory to PATH)
3. Verify installation:
   ```powershell
   hcloud version
   ```

### Linux / macOS

1. Download the binary for your platform
2. Make executable: `chmod +x hcloud`
3. Move to PATH: `sudo mv hcloud /usr/local/bin/`
4. Verify: `hcloud version`

## Configuration

### Initialize Profile

```bash
hcloud configure
```

This will prompt for:
- Access Key ID (AK)
- Secret Access Key (SK)
- Region (e.g., `cn-north-4`)

### Set Project ID

```bash
hcloud configure set --cli-project-id=<project_id>
```

Project ID can be found in Huawei Cloud Console > My Credentials > Projects.

### Verify Configuration

```bash
hcloud configure list
```

Ensure a valid profile with AK/SK, region, and project ID is displayed.

## Corporate Network Proxy

If behind a corporate proxy, set proxy environment variables before running hcloud commands:

```bash
# Linux/macOS
export HTTP_PROXY="http://proxy.company.com:port"
export HTTPS_PROXY="http://proxy.company.com:port"

# Windows PowerShell
$env:HTTP_PROXY="http://proxy.company.com:port"
$env:HTTPS_PROXY="http://proxy.company.com:port"
```

Note: hcloud is a Go binary and may have proxy compatibility issues on some platforms. If proxy connection fails, consider using a TUN-mode VPN or network-level proxy tool.

## Version Requirement

This skill requires hcloud CLI **v7.2+**. Check your version with `hcloud version`.

Update if needed:
```bash
hcloud update
```

## References

- Official Documentation: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi
