# CLI Installation Guide — huawei-cloud-vpc-network-diagnosis-management

This skill executes all business commands through the **KooCLI (`hcloud`)** and reports
quality telemetry through **`skill-quality-cli`**. Both are required (the latter is ensured
automatically; see Step 0 in SKILL.md).

## 1. hcloud (KooCLI) installation

**Recommended — pip package (Python 3.6+):**

```bash
pip install huaweicloudcli
hcloud --version          # KooCLI 7.2.x or later recommended
```

**Alternative — official installer / cloud-shell:**

Download the offline package from the official KooCLI download page and follow its
installer, or use the CLI that is pre-bundled in Huawei Cloud CloudShell — see
https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

After installing, always upgrade to the latest version:

```bash
hcloud update -y
```

## 2. Authentication

Two supported modes — configure at least one.

### Mode A: AK/SK environment variables (preferred for agents)

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-secret-access-key>
# optional: export HUAWEICLOUD_SDK_SECURITY_TOKEN=<token>   (temporary credentials)
```

Verify:

```bash
hcloud VPC ListVpcs/v3 --cli-region=cn-north-4 --limit=1
```

### Mode B: Local hcloud profile

Create the profile interactively (keys are never typed into chat or the command line —
never pass `--cli-access-key` / `--cli-secret-key` as arguments, they would leak the
credentials into shell history and logs):

```bash
hcloud configure set --cli-profile=default --cli-mode=AKSK --cli-region=cn-north-4
# follow the interactive prompt to enter the access key and secret key
```

Verify:

```bash
hcloud configure list    # shows a profile with mode AKSK and a real accessKeyId
```

> Security: never paste AK/SK into chat, reports, or code. Read them from environment
> variables or the encrypted local profile only.

## 3. skill-quality-cli (quality telemetry)

Automatically installed by the skill on first use:

```bash
bash scripts/ensure_cli.sh          # idempotent: installs only if absent
export PATH="$HOME/.local/bin:$PATH"
skill-quality-cli version           # verify
```

Manual upgrade (no auto-upgrade):

```bash
skill-quality-cli upgrade
```

Disable telemetry (rare):

```bash
export SKILL_QUALITY_REPORT=0
```

If the download endpoint is unreachable, business commands still work — telemetry degrades
silently and resumes when connectivity returns.

## 4. Troubleshooting

| Problem | Fix |
| ------- | --- |
| `hcloud: command not found` | Re-run the install script or add `~/.hcloud` to PATH |
| `APIGW.0301 Unauthorized` | Stale AK/SK → re-export or re-run `hcloud configure set` |
| `缺少必填参数:project_id` | Auth incomplete → the profile/region is missing; pass `--cli-region` explicitly |
| `skill-quality-cli: command not found` (exit 127) | `~/.local/bin` missing from PATH → `export PATH="$HOME/.local/bin:$PATH"` or call `~/.local/bin/skill-quality-cli` |