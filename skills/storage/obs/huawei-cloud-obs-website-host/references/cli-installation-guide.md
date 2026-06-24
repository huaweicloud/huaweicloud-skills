# CLI Installation and Configuration Guide

Use this reference when you need to install or configure **KooCLI (`hcloud`)** or **`obsutil`**.

---

## Table of Contents

- [hcloud (KooCLI)](#hcloud-koocli)
  - [Linux Installation](#linux-installation)
  - [Windows Installation](#windows-installation)
  - [Configure hcloud](#configure-hcloud)
- [obsutil](#obsutil)
  - [Config File Location](#config-file-location)
  - [Linux AMD64 (x86\_64)](#linux-amd64-x86_64)
  - [Linux ARM64](#linux-arm64)
  - [macOS (AMD64)](#macos-amd64)
  - [Windows (AMD64)](#windows-amd64)
  - [Generate Config File](#generate-config-file)
  - [Secure Credential Check](#secure-credential-check)
  - [Notes](#notes)

---

## hcloud (KooCLI)

### Linux Installation

```bash
curl -sSL https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh -y
```

Interactive install:

```bash
bash ./hcloud_install.sh
```

### Windows Installation

1. Download the package:
   - `https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip`
2. Unzip it and get `hcloud.exe`.
3. Add the folder containing `hcloud.exe` to `Path` if desired.
4. Verify:

```powershell
hcloud version
```

### Configure hcloud

Interactive init:

```bash
hcloud configure init
```

AK/SK mode:

```bash
hcloud configure set --cli-profile=default --cli-mode=AKSK --cli-region=<region> --cli-access-key=<ak> --cli-secret-key=<sk>
```

Verify current profile:

```bash
hcloud version
hcloud configure list
```

---

## obsutil

### Config File Location

`obsutil` auto-generates a config file named `.obsutilconfig` in user home directory:

- macOS/Linux: `~/.obsutilconfig`
- Windows: `C:\Users\<username>\.obsutilconfig`

### Linux AMD64 (x86_64)

```bash
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
tar -xzvf obsutil_linux_amd64.tar.gz
cd obsutil_linux_amd64_*
chmod 755 obsutil
./obsutil version
```

### Linux ARM64

```bash
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
tar -xzvf obsutil_linux_arm64.tar.gz
cd obsutil_linux_arm64_*
chmod 755 obsutil
./obsutil version
```

### macOS (AMD64)

```bash
curl -O https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
tar -xzvf obsutil_darwin_amd64.tar.gz
cd obsutil_darwin_amd64_*
chmod 755 obsutil
./obsutil version
```

### Windows (AMD64)

1. Download the package:
   - `https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip`
2. Unzip it.
3. Open `cmd` or PowerShell in the extracted directory.
4. Run:

```powershell
obsutil.exe version
```

### Generate Config File

```bash
# generate config file
./obsutil config
```

Windows:

```powershell
obsutil.exe config
```

### Secure Credential Check (No Value Output)

Do not print `ak`, `sk`, or `securitytoken` values to console.  
Only print key presence status (`true` / `false`).

Never run:

- `cat ~/.obsutilconfig`
- `grep -E "ak|sk|token" ~/.obsutilconfig`

### Notes

- Internet connectivity is required when downloading packages.
- `chmod 755 obsutil` is required before running `obsutil` on Linux/macOS.
- If `./obsutil version` returns version information, installation is successful.
- For macOS, run `chmod 755 obsutil` in the extracted directory before first use.
