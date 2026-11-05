# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| KooCLI (hcloud) | OBS obsutil module mapping: `hcloud obs ls/cp` | `curl -sSL https://cn-north-4-hcs-cloud-cdn.obs.cn-north-4.myhuaweicloud.com/install_cli.sh \| bash` (see [KooCLI docs](https://support.huaweicloud.com/qs-hcli)) |

## KooCLI

The `hcloud obs` sub-command maps to Huawei Cloud **obsutil**, so a working KooCLI with
authenticated credentials is sufficient for OBS operations:

```bash
# verify version (>= 3.2.0)
hcloud version

# verify OBSc credentials
hcloud obs ls -limit=5
```

If `hcloud obs ls` prints `Please set ak, sk and endpoint in the configuration file!`
or `InvalidAccessKeyId`, the obsutil credentials are not configured. Guide the user to
configure them in their own terminal (never ask them to paste AK/SK into the chat):

```text
hcloud obs config -i=<Access_Key_ID> -k=<Secret_Access_Key> -e=<Endpoint>
```

Endpoint is the OBS endpoint of the region, e.g. `https://obs.cn-north-4.myhuaweicloud.com`.

## Python

The desensitization engine runs on Pillow:

```bash
pip install Pillow
```

Optional (only for the `setup-trigger` automation path):

```bash
pip install huaweicloudsdkfunctiongraph
```

## Environment Variables (setup-trigger only)

```bash
export HUAWEI_AK="your-access-key"
export HUAWEI_SK="your-secret-key"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your-project-id"
```
