# CLI and Runtime Installation Guide - huawei-cloud-ges-graph

This skill executes queries via **local Python or Node.js scripts** under `scripts/`
(`ges_graph_skill.py` / `ges_graph_skill.js`). No `hcloud` CLI is required for the core
functionality; the scripts talk to the GES business endpoint directly over HTTP.

## Table of Contents

- [1. Runtime Requirements](#1-runtime-requirements)
- [2. Python Setup](#2-python-setup)
- [3. Node.js Setup](#3-nodejs-setup)
- [4. Environment Configuration](#4-environment-configuration)
- [5. Verification](#5-verification)

---

## 1. Runtime Requirements

Choose **one** of the following runtimes:

| Runtime | Version | Required Packages |
|---------|---------|-------------------|
| Python | 3.8+ | `requests` (optional `huaweicloudsdkges`) |
| Node.js | 14+ | none (stdlib `https`/`http`) |

---

## 2. Python Setup

```bash
# Check Python version (must be >= 3.8)
python3 --version

# Install the HTTP client (Core dependency)
pip3 install requests

# Optional but recommended for SDK-level calls: install the official GES SDK
# (the skill also works without it via its built-in HTTP client)
pip3 install huaweicloudsdkges

# Verify the core dependency
python3 -c "import requests; print('requests OK')"
```

---

## 3. Node.js Setup

```bash
# Check Node version (must be >= 14)
node --version

# No external npm packages required — the script only uses stdlib http/https/fs/path/crypto
# Optional: verify the module loads
node -e "require('./scripts/ges_graph_skill.js'); console.log('ges_graph_skill.js OK')"
```

---

## 4. Environment Configuration

The skill reads configuration from **environment variables first**, falling back to a
configuration file (`config/ges_env.csv`) placed next to `SKILL.md`.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GES_GRAPH_IP` | GES service IP | Yes |
| `GES_GRAPH_PORT` | GES service port | Yes |
| `GES_PROJECT_ID` | Project ID | Yes |
| `GES_GRAPH_NAME` | Graph name | Yes |
| `GES_IAM_URL` | IAM service URL (see region table in SKILL.md) | Yes |
| `GES_REGION` | Region | Yes |
| `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` | AK/SK for AKSK auth | Conditional* |
| `GES_USERNAME` / `GES_PASSWORD` / `GES_DOMAIN_NAME` | Username/password auth | Conditional** |
| `GES_TOKEN` | Pre-provisioned token (highest priority) | Optional |

> * AK/SK required when using AKSK authentication.
> ** Username/password/domain required when AKSK is not available.

```bash
export GES_GRAPH_IP=100.95.xxx.xxx
export GES_GRAPH_PORT=80
export GES_PROJECT_ID=your_project_id
export GES_GRAPH_NAME=your_graph_name
export GES_IAM_URL=https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens
export GES_REGION=cn-north-4
export HUAWEI_CLOUD_AK=your_access_key
export HUAWEI_CLOUD_SK=your_secret_key
```

### Configuration File (`config/ges_env.csv`)

Copy `references/ges_env.csv.example` to `config/ges_env.csv` and fill in values.
The file uses CSV format with a `key,value` header. Environment variables always
take precedence over this file.

### Credentials Security Rules

- **Never** hardcode a password/AK/SK literal in code or in the conversation.
- **Never** print AK/SK, password, or token.
- Prefer `GES_TOKEN` / environment variables over inline file content when possible.
- Credentials are read by the scripts from `os.environ` / `process.env` at runtime only.

---

## 5. Verification

After setup, run the check commands below from the skill directory.

### Python

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from ges_graph_skill import EnvConfig
cfg = EnvConfig.load_ges_env()
missing = [k for k in ["graph_ip", "project_id", "graph_name", "iam_url", "username", "password", "domain_name", "region"] if not cfg.get(k)]
print("config OK" if not missing else f"missing: {missing}")
PY
```

### Node.js

```bash
node -e "const fs=require('fs'); const p='config/ges_env.csv'; console.log(fs.existsSync(p) ? 'config file present' : 'no config file (ok if env vars set)');"
```