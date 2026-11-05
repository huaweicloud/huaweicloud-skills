# CLI Installation and Configuration Guide

Use this reference when you need to install or configure **KooCLI (`hcloud`)** or **`obsutil`**.

> **Before you install — important safety notes**
>
> - **Run everything as a normal (non-root) user.** None of the install commands below require `sudo`, `su`, or root privileges. If your shell reports permission issues, install into a user-owned directory rather than elevating privileges.
> - **Only download from the official Huawei Cloud URLs shown below** (the `*.obs.*.myhuaweicloud.com` and `*.hdn-koocli.obs.*.myhuaweicloud.com` domains). Never fetch these installers from third-party mirrors or random URLs.
> - **Verify the download before running it (the hcloud install script, in particular):** after downloading, compare the file size/hash against the official release page, or review the script content with `less`/`cat` before executing it where possible.
> - **Warning about executing remote scripts:** running an installer downloaded from the network means executing third-party code on your machine. The Huawei Cloud install scripts are official, but you should treat any downloaded-and-executed script with care: inspect it first, and confirm the URL you used is the official one.

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

Download the official installer script and run it. All commands run as your normal user — **no `sudo` or root is used**.

```bash
curl -sSL https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
# Optional: review the script before executing it
less ./hcloud_install.sh
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

All commands run as your normal user in a directory you own — **no `sudo` or root is required**.

```bash
# 1. Download the official package from Huawei Cloud OBS
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
# 2. Extract the archive
tar -xzvf obsutil_linux_amd64.tar.gz
cd obsutil_linux_amd64_*
# 3. chmod only sets the executable bit on obsutil for your current user;
#    it does NOT elevate privileges or run anything with sudo/root.
chmod 755 obsutil
# 4. Verify the version
./obsutil version
```

### Linux ARM64

All commands run as your normal user — **no `sudo` or root is required**.

```bash
# 1. Download the official package from Huawei Cloud OBS
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
# 2. Extract the archive
tar -xzvf obsutil_linux_arm64.tar.gz
cd obsutil_linux_arm64_*
# 3. chmod 755 only sets the executable bit for your current user
chmod 755 obsutil
# 4. Verify the version
./obsutil version
```

### macOS (AMD64)

All commands run as your normal user — **no `sudo` or root is required**.

```bash
# 1. Download the official package from Huawei Cloud OBS
curl -O https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
# 2. Extract the archive
tar -xzvf obsutil_darwin_amd64.tar.gz
cd obsutil_darwin_amd64_*
# 3. chmod 755 only sets the executable bit for your current user
chmod 755 obsutil
# 4. Verify the version
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
- All downloads come from official Huawei Cloud OBS hosting (`obs-community.obs.*.myhuaweicloud.com` / the hcloud `*.hdn-koocli.obs.*.myhuaweicloud.com` domains). Confirm the URL before running anything you downloaded.
- `chmod 755 obsutil` simply makes the `obsutil` binary executable for your current user. It is **not** a sudo/root command and does not require elevated privileges. If you get a "permission denied" error on `chmod` or `./obsutil`, extract into a directory you own instead of switching to root.
- None of the installation steps use `sudo` or root. Running tools as a normal user is the recommended practice.
- If `./obsutil version` returns version information, installation is successful.
- For macOS, run `chmod 755 obsutil` in the extracted directory before first use.
