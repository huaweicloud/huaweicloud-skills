# KooCLI Installation & Authentication Guide

## 1. Install KooCLI (hcloud)

Huawei Cloud CLI (KooCLI) is a single binary. See the official quickstart:
https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

```bash
# Linux x86_64
curl -sSL https://cn-north-4-hww-cloud-download.obs.cn-north-4.myhuaweicloud.com/cli/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh

# Or via Python package manager
pip3 install huaweicloudcli
```

Verify:

```bash
hcloud version
hcloud APIG --help        # should list Available Operations for APIG
```

Keep KooCLI updated so APIG operation/parameter metadata stays current:

```bash
hcloud update -y
```

## 2. Authentication

Two supported ways (AK/SK never hardcoded in this skill):

### Option A — Local profile (recommended for interactive agents)

Configures a named profile `default`:

```bash
hcloud configure set --cli-access-key=YOUR_ACCESS_KEY --cli-secret-key=YOUR_SECRET_KEY
```

Or interactively:

```bash
hcloud configure
```

Check the current profile:

```bash
hcloud configure list
```

### Option B — Environment variables (recommended for CI/agent runtimes)

KooCLI reads the following environment variables (among others):

| Variable | Meaning |
|----------|---------|
| `HUAWEICLOUD_SDK_AK` / `HUAWEI_ACCESS_KEY` | Access Key ID |
| `HUAWEICLOUD_SDK_SK` / `HUAWEI_SECRET_KEY` | Secret Access Key |
| `HUAWEICLOUD_SDK_PROJECT_ID` / `HUAWEI_PROJECT_ID` | Project ID (optional; KooCLI can resolve it) |
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | Security token (only for temporary credentials) |

Example:

```bash
export HUAWEICLOUD_SDK_AK=your-access-key
export HUAWEICLOUD_SDK_SK=your-secret-key
export HUAWEICLOUD_SDK_REGION=cn-north-4
```

### Security rules

- Never print, persist, or hardcode AK/SK — read them from the environment or the local profile only.
- Never run `hcloud configure set` with keys inside a skill document or script.
- Use the most restrictive IAM identity that still allows the needed APIG operations (least privilege, see `references/iam-policies.md`).

## 3. Region and project

APIG is a regional service. Always pass `--cli-region` (e.g. `cn-north-4`,
`ap-southeast-1`). If `--project_id` is not supplied, KooCLI tries the parent
project of the region from the authentication information, then the profile's
`projectId`.

## 4. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `hcloud APIG --help` fails | Update KooCLI: `hcloud update -y` |
| `Missing required parameter(s)` | Check `hcloud APIG <Op> --help` for required params and include them |
| `Authentication failed` / 401 | Re-run `hcloud configure` or refresh AK/SK env vars |
| `No such operation` | Operation names change across API versions — enumerate with `hcloud APIG --help` |