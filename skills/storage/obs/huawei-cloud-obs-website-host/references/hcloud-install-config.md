# hcloud Install and Configure

Use this reference when you need to install or configure KooCLI (`hcloud`).

## Linux

```bash
curl -sSL https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh
bash ./hcloud_install.sh -y
```

Interactive install:

```bash
bash ./hcloud_install.sh
```

## Windows

1. Download the package:
   - `https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip`
2. Unzip it and get `hcloud.exe`.
3. Add the folder containing `hcloud.exe` to `Path` if desired.
4. Verify:

```powershell
hcloud version
```

## Configure

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
