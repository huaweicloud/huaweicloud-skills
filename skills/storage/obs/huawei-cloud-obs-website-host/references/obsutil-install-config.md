# obsutil Install and Config

Use this reference when you need to install obsutil or prepare `.obsutilconfig`.

## Config File Location

`obsutil` auto-generates a config file named `.obsutilconfig` in user home directory:
- macOS/Linux: `~/.obsutilconfig`
- Windows: `C:\\Users\\<username>\\.obsutilconfig`

## Install on Linux AMD64 (x86_64)

```bash
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
tar -xzvf obsutil_linux_amd64.tar.gz
cd obsutil_linux_amd64_*
chmod 755 obsutil
./obsutil version
```

## Install on Linux ARM64

```bash
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
tar -xzvf obsutil_linux_arm64.tar.gz
cd obsutil_linux_arm64_*
chmod 755 obsutil
./obsutil version
```

## Install on macOS (AMD64)

```bash
curl -O https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
tar -xzvf obsutil_darwin_amd64.tar.gz
cd obsutil_darwin_amd64_*
chmod 755 obsutil
./obsutil version
```

## Install on Windows (AMD64)

1. Download the package:
   - `https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip`
2. Unzip it.
3. Open `cmd` or PowerShell in the extracted directory.
4. Run:

```powershell
obsutil.exe version
```

## Generate config file

```bash
# generate config file
./obsutil config
```

Windows:

```powershell
obsutil.exe config
```

## Secure Credential Check (No Value Output)

Do not print `ak`, `sk`, or `securitytoken` values to console.  
Only print key presence status (`true` / `false`).

Never run:
- `cat ~/.obsutilconfig`
- `grep -E "ak|sk|token" ~/.obsutilconfig`

## Notes

- Internet connectivity is required when downloading packages.
- `chmod 755 obsutil` is required before running `obsutil`.
- If `./obsutil version` returns version information, installation is successful.
- For macOS, run `chmod 755 obsutil` in the extracted directory before first use.
