---
name: huawei-cloud-find-skills
description: |
  Invoke this skill to search, list, query, discover, browse, find and install any Huawei Cloud (华为云) agent skill. Triggers include: "华为云", "华为云有什么skill", "华为云相关skill", "华为云agent skill 市场", "华为云skill类目", "explore Huawei Cloud skills", "show Huawei Cloud skill categories", "does a Huawei Cloud skill exist for...", "which Huawei Cloud skills exist", "搜索华为云技能", "查询华为云skill列表", "有没有管理ECS/OBS/RDS的skill", "帮我找 XX 华为云skill", "介绍 XX Skill 内容", "华为云 XX Skill 具体做什么", "安装华为云Skill".
---

> [!IMPORTANT]
> **When the user wants to search, discover, or install a Huawei Cloud (华为云) agent skill:**
> 1. **Search** — use this skill (`huawei-cloud-find-skills`) to find the relevant Skill.
> 2. **Install** — install the matched Skill (see [Step 3](#step-3-install-skill)).
> 3. **Execute** — follow the installed Skill's instructions to fulfill the request.
>
> This skill handles **skill discovery and installation only** — it does not perform
> Huawei Cloud resource management/query tasks itself; those are handled by the skills it installs.

## Overview

This skill enables users to efficiently search, discover, and install Huawei Cloud skills.

**Dependency**: Python 3.6+ and network access to `gitcode.com` (API v5 for the skill
index) and `github.com` / `raw.githubusercontent.com` (for skill details). Quality telemetry is collected automatically via
`skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent) — no other CLI
or credential is required.

## Privacy & Telemetry

> **透明披露**: 本 skill 在搜索与安装过程中会产生以下对外遥测上报。均为**匿名聚合数据**(技能名/类目/服务等元信息), **不包含**用户输入内容、凭证、云资源数据或个人身份信息。**质量上报默认开启**(opt-out): 如需关闭, 设置环境变量 `export SKILL_QUALITY_REPORT=0` 即可整体关闭。

| 上报内容 | 触发点 | 目的地 | 是否含敏感数据 |
|----------|--------|--------|----------------|
| 搜索 top-3 曝光计数 | `scripts/search-skills.py`（每次搜索） | `devdata2.huaweicloud.com` install-count API | 否（仅技能名/类目/服务） |
| 安装计数 | Step 3.1 `curl`（每次安装前） | `devdata2.huaweicloud.com` install-count API | 否（仅 `skill_id`，即 `skills/<category>/<service>/<name>`） |
| 质量上报 | `skill-quality-cli run` 包装执行 | quality 上报 APIG（测试环境） | 否（执行状态/耗时/技能名） |

- **默认开启 / 关闭方式**: 以上三类上报**默认开启**(未设置该环境变量即会上报)；如需关闭, 执行 `export SKILL_QUALITY_REPORT=0`（`skill-quality-cli` 与 `search-skills.py` 均遵循该开关）。
- 上报均为 **fire-and-forget**，永不阻塞搜索/安装主流程。

## Scenario Description

This skill enables users to:

- **Search Skills**: Find skills by keyword, category, or both (matched against name, description, and triggers)
- **Browse Categories**: Explore available skill categories
- **View Skill Details**: Fetch full SKILL.md content from GitHub for specific skills
- **Install Skills**: Guide users through skill installation via `npx skills add` (GitCode default), `npx skills add https://clawhub.ai/huaweicloudskill/skills/<skill-name>` (ClawHub), or fallback GitHub method

**Architecture**: GitCode API v5 (`index.json` + `cn-en-map.json`) → HTTP GET (base64 decode) → In-memory search → GitHub raw fetch for details → Install

### Use Cases

- "Find a skill for managing ECS instances"
- "What Huawei Cloud skills are available for OBS?"
- "华为云有哪些 VPC 相关的 skill?"
- "Browse all available Huawei Cloud skills"
- "Install a skill for RDS management"
- "帮我找一个华为云网络相关的skill"

## Prerequisites

- **Python 3.6+** must be installed and available as `python` (or `python3`) in `PATH`
- **Network access** to `gitcode.com` (API v5 for index) and `github.com` / `raw.githubusercontent.com` (for skill details)
- **`skill-quality-cli`** — **MANDATORY (Step 0.1)**: ensured by `bash scripts/ensure_cli.sh`
  (idempotent, skips if already present). **MUST be triggered on EVERY execution of this
  skill** before running any search/install command.
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - **质量上报**: 每次搜索(Step 1)与安装(Step 3)命令都必须用 `skill-quality-cli run --skill-name huawei-cloud-find-skills -- ` 包装执行, 保证每次执行都触发质量上报

### Step 0: Check Python Environment

> **MANDATORY**: Before running any script command, verify Python is available.

> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-find-skills -- ` — bare `hcloud` calls are strictly forbidden.**

```bash
# Check Python availability
python --version   # or: python3 --version
```

If the command fails or returns Python 2.x:

1. **Install Python 3**: Download from [python.org](https://www.python.org/downloads/) or use a package manager:
   ```bash
   # macOS
   brew install python3
   # Ubuntu/Debian
   sudo apt-get install python3
   # Windows — download installer from python.org, check "Add Python to PATH"
   ```
2. **Verify after install**: Run `python --version` again to confirm Python 3.6+ is available
3. **If `python` points to Python 2**: Use `python3` instead of `python` in all commands below

### Step 0.1: Ensure `skill-quality-cli` (MANDATORY)

> **MANDATORY**: Before running any search/install command, ensure `skill-quality-cli` is
> installed and available. **This step MUST be triggered on EVERY execution of this skill**,
> immediately after Step 0. It is at the same mandatory level as **Step 0: Check Python
> Environment** — do not skip it even if you believe the CLI is already present
> (`ensure_cli.sh` is idempotent and exits silently when everything is ready).
>
> **披露**: 该 CLI 仅用于本 skill 的**匿名质量遥测上报**(执行状态/耗时, 见
> [Privacy & Telemetry](#privacy--telemetry)); 安装位置 `~/.local/bin`, 不修改系统
> 服务或全局配置; 关闭方式见 [Privacy & Telemetry](#privacy--telemetry)。

```bash
# Ensure ~/.local/bin is on PATH (where skill-quality-cli is installed)
export PATH="$HOME/.local/bin:$PATH"

# Ensure skill-quality-cli is ready (idempotent: installs only if absent;
# also auto-links the CLI into a writable PATH dir so the bare command works)
bash scripts/ensure_cli.sh

# Verify availability
command -v skill-quality-cli && skill-quality-cli version
```

| Outcome | Behavior |
|---------|----------|
| CLI already installed & usable | **Silent pass** — script exits immediately |
| CLI missing | Installs the latest release into `~/.local/bin/` (prints `skill-quality-cli vX.Y.Z 已就绪`) |
| Install fails (no network, etc.) | Prints a warning; **never blocks the flow** |

> `ensure_cli.sh` 会自动把 `skill-quality-cli` 软链到 `PATH` 中第一个可写目录
> (如 `/usr/local/bin`)，因此 `skill-quality-cli` 通常可直接调用。若仍不可用
> (没有任何可写的 PATH 目录)，请在当前 shell 执行：
> ```bash
> export PATH="$HOME/.local/bin:$PATH"
> ```
> Manual one-off install fallback: `bash scripts/install_cli.sh`.

### Step 0.5: Check KooCLI Version (NON-BLOCKING)

> **OPTIONAL**: A KooCLI (`hcloud`) availability/version check that **never blocks the flow**.
> Skills installed later may depend on KooCLI; this step warns early, then **always
> continues to Step 1** regardless of the outcome.

```bash
# Check KooCLI availability & version (non-blocking)
python scripts/check-koocli.py
```

→ [scripts/check-koocli.py](scripts/check-koocli.py) (Python — cross-platform)

| Outcome | Behavior |
|---------|----------|
| `hcloud` installed and version OK (≥ 3.0.0) | **Silent pass** — no output |
| `hcloud` installed but too old | Prints an upgrade reminder (`hcloud update -y`) |
| `hcloud` not installed | Prints an install reminder (official KooCLI guide link) |

> The script always exits `0` — it is informational only and never interrupts
> search or installation.

## Repository Info

```
INDEX_REPO=developer-skill/skills-group-contribution
INDEX_BRANCH=test-for-index
SKILLS_REPO=huaweicloud/huaweicloud-skills
SKILLS_BRANCH=master
RAW_BASE=https://raw.githubusercontent.com/$SKILLS_REPO/$SKILLS_BRANCH
```

## Index Source

The search script fetches the skill index from GitCode API v5 via HTTP GET (base64 auto-decoded):

```
SKILLS_INDEX_URL=https://gitcode.com/api/v5/repos/developer-skill/skills-group-contribution/contents/skills-index/index.json?ref=test-for-index
SKILLS_CN_EN_MAP_URL=https://gitcode.com/api/v5/repos/developer-skill/skills-group-contribution/contents/skills-index/cn-en-map.json?ref=test-for-index
```


## Core Workflow and Core Commands

### Step 1: Search Skills

> **MANDATORY**: The agent MUST execute the search script to search the skill index. Do NOT read the JSON file directly — always use the script.

Given `keyword` (from AI-understood user intent) and optional `category`, run the search script:

> **⚠️ MANDATORY (质量上报)**: 搜索命令必须用 `skill-quality-cli run --skill-name huawei-cloud-find-skills -- ` 包装, 保证每次搜索都触发质量上报。严禁裸调 `python scripts/search-skills.py`。

```powershell
# PowerShell
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -k "<keyword>"
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -k "<keyword>" -c "<category>"
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -c "<category>"
```

```bash
# Bash
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -k "<keyword>"
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -k "<keyword>" -c "<category>"
skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py -c "<category>"
```

> **⚠️ 安全（命令注入防护）**: `keyword`/`category` 来自用户输入，严禁未转义直接拼接到 shell 命令字符串中。若输入包含 `$()`, `$(...)`, 反引号 **` `**`, `;`, `|` 等 shell 元字符，在 Bash/PowerShell 双引号字符串中会触发命令注入。必须按以下方式调用，避免将外部输入拼入 shell 字符串：
> 1. **首选（推荐）**: 用 Python `subprocess` 参数数组方式调用，不经 shell：`subprocess.run([sys.executable, "scripts/search-skills.py", "-k", keyword, "-c", category])`；
> 2. 必须在 shell 中执行时，用**单引号**包裹用户输入（`'<keyword>'`），并先做转义（将输入中的 `'` 替换为 `'\''`）或使用 shell 转义工具（`shlex.quote`）；
> 3. 遇到包含 `$()`, 反引号, `;`, `|` 等元字符的输入时，优先改为参数数组方式，或在展示给用户前对输入做脱敏处理。

→ [scripts/search-skills.py](scripts/search-skills.py) (Python — cross-platform)

**What the script does**:
1. Fetches `index.json` and `cn-en-map.json` via HTTP GET from GitCode API v5 (auto-decodes base64 content)
2. Expands keywords via `cn-en-map.json` (bidirectional CN↔EN, e.g., "ECS" → "ECS, 弹性云服务器, 云服务器")
3. Scores each skill: name match **+10**, trigger match **+8**, description match **+5**, service match **+3**
4. Sorts by score descending, outputs formatted results with matched keywords
5. Reports only the top-3 results' skill names to the install-count API (`skills/<category>/<service>/<name>`) as exposure impressions — fire-and-forget, never blocks or fails the search

**Fallback iteration** (if no results): 1) Switch CN↔EN keywords 2) Expand keywords 3) Remove category filter 4) Try synonyms 5) List all skills

The process should persist until the skill is found or its absence is confirmed. In the event of total failure, notify the user of the specific steps that were attempted.

### Step 2: View Skill Details (optional)

Fetch the full SKILL.md content from GitHub for intent validation. Skip this step if the search results from Step 1 are sufficiently informative.

```bash
# URL pattern — use the skill's category, service, and name from index
DETAIL_URL="https://raw.githubusercontent.com/huaweicloud/huaweicloud-skills/master/skills/${category}/${service}/${name}/SKILL.md"
```

The agent can fetch this URL using `curl` or its web-fetch tool, then present the skill's full documentation to the user.

### Step 3: Install Skill

> **MANDATORY**: Before installing, the agent MUST call the install-count API to record the installation. Then use one of the install commands below. Option A is the default; Option C is a fallback when Option A is unavailable.

#### Step 3.1: Record Install Count

Before executing the install command, call the install-count API. The `skill_id` is constructed from the search results in Step 1: `skills/<category>/<service>/<skill-name>`.

> **IMPORTANT**: The `category` and `service` values MUST be taken directly from the Step 1 search output (format: `name (category/service)`). Do NOT guess or hardcode them.
>

> **⚠️ MANDATORY (质量上报)**: 安装计数请求同样用 `run` 包装, 保证安装流程触发质量上报。

```bash
skill-quality-cli run --skill-name huawei-cloud-find-skills -- curl -s -X POST "https://devdata2.huaweicloud.com/rest/developer/fwdo/rest/developer/servlet/hdskillservice/v1/obs/findcounts/increment" -H "Accept: application/json, text/plain, */*" -H "Content-Type: application/json" -H "Origin: https://skills.huaweicloud.com" -H "Referer: https://skills.huaweicloud.com/" -d "{\"skill_id\":\"skills/<category>/<service>/<skill-name>\"}"
```

> This is a fire-and-forget request. Do NOT block the install flow on its success or failure.

#### Step 3.2: Execute Install Command

> **⚠️ MANDATORY (质量上报)**: 安装命令必须用 `skill-quality-cli run --skill-name huawei-cloud-find-skills -- sh -c '...'` 包装, 保证每次安装都触发质量上报。`sh -c` 内的 `printf "\n"` 用于自动确认 `npx skills add` 的 scope 交互提示。

```bash
# Option A: npx skills add from GitCode (default)
skill-quality-cli run --skill-name huawei-cloud-find-skills -- sh -c 'printf "\n" | npx skills add https://gitcode.com/huaweicloud/huaweicloud-skills.git#master --skill <skill-name> -y'

# Option B: npx skills add from ClawHub
skill-quality-cli run --skill-name huawei-cloud-find-skills -- sh -c 'printf "\n" | npx skills add https://clawhub.ai/huaweicloudskill/skills/<skill-name> -y'

# Option C (fallback): npx skills add from GitHub
skill-quality-cli run --skill-name huawei-cloud-find-skills -- sh -c 'printf "\n" | npx skills add huaweicloud/huaweicloud-skills --skill <skill-name> -y'
```

> **⚠️ 安全**: `<skill-name>` 必须来自 Step 1 搜索结果的规范技能名（`name` 字段），禁止拼接未经校验的用户输入到 `sh -c '...'` 内；若技能名含 `'` 等 shell 元字符，须先转义（`'` → `'\''`）或改用 `npx skills add ... -y` 裸调用（此时质量上报改为安装完成后手动 `skill-quality-cli report --skill-name huawei-cloud-find-skills`）。

If all installation attempts fail, report the error message to the user. Do NOT attempt any method outside the commands above.

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `Keyword` | Optional | Search keyword (matched against name, description, triggers, service) | None |
| `Category` | Optional | Category code for filtering (e.g., "computing", "storage", "network") | None |
| `skill-name` | Required (Step 3) | Exact skill name for installing | None |

## References

| Document | Description |
|----------|-------------|
| GitCode API v5 `index.json` | Skill index fetched via HTTP GET (base64 decoded) |
| GitCode API v5 `cn-en-map.json` | Chinese-English keyword mapping fetched via HTTP GET (base64 decoded) |
| [scripts/search-skills.py](scripts/search-skills.py) | Search script (Python) — fetches from GitCode API v5, expands keywords, scores, sorts, reports top-3 search-result exposures |
| [scripts/check-koocli.py](scripts/check-koocli.py) | Step 0.5 non-blocking KooCLI (`hcloud`) availability/version check |
| [scripts/ensure_cli.sh](scripts/ensure_cli.sh) | **MANDATORY (Step 0.1)** idempotent installer for `skill-quality-cli` (installs only if absent, no auto-upgrade) |
| [scripts/install_cli.sh](scripts/install_cli.sh) | Manual one-off installer for `skill-quality-cli` (user-triggered only) |
| [references/iam-policies.md](references/iam-policies.md) | IAM 权限说明 — 本 Skill 仅访问公开接口，无需任何 IAM 凭证/策略 |
| [references/verification-method.md](references/verification-method.md) | 验证方法 — 各场景的验证步骤与预期结果 |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | 验收标准 — 功能/数据/安全/文件规范验收项 |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI 安装/升级/遥测关闭说明 |

## Search Heuristics

> Optional reference for keyword-to-category hints. The agent can infer categories from `index.json` without these.

- Cloud infrastructure keywords (ecs, bms, vpc, obs, rds, ...) → likely `computing`, `network`, `storage`, etc.
- Tool keywords (cli, terraform, koo) → likely `devtools`
- Management keywords (monitoring, alarm, log) → likely `monitoring`

## Troubleshooting

### Issue: `python` is not recognized as a command

**Cause**: Python 3 is not installed or not in `PATH`
**Solution**: Install Python 3.6+ and ensure it is added to `PATH`. On Windows, re-run the installer and check "Add Python to PATH". Alternatively, use `python3` if available.

### Issue: `skill-quality-cli: command not found` (exit 127)

**Cause**: `skill-quality-cli` is installed into `~/.local/bin/`, which is usually
NOT on the default `PATH`.
**Solution**: Re-run `bash scripts/ensure_cli.sh` — it now auto-links the CLI into the
first writable directory on `PATH` (e.g. `/usr/local/bin`), so the bare command works.
As a manual fallback, run `export PATH="$HOME/.local/bin:$PATH"` in the current shell.
If the CLI is missing entirely, `ensure_cli.sh` installs it idempotently (skips if
already present) and never blocks the business flow.

### Issue: Script fails with `SyntaxError: invalid syntax`

**Cause**: System `python` points to Python 2.x (the script requires Python 3.6+)
**Solution**: Run with `python3` explicitly: `python3 scripts/search-skills.py -k "<keyword>"`

### Issue: Script fails with "Failed to fetch index.json"

**Cause**: GitCode API v5 URL unreachable
**Solution**: Verify network connectivity to `gitcode.com`

### Issue: GitCode API v5 returns 404

**Cause**: File path incorrect or the branch is not `test-for-index`
**Solution**: Verify the skill's `category`, `service`, and `name` from search results

### Issue: Search returns no results

**Cause**: Keywords don't match any skill
**Solution**:
1. Try broader keywords
2. Switch between Chinese and English keywords (e.g., "对象存储" → "obs")
3. List all skills: `python scripts/search-skills.py -c "computing"`

## Notes

- This skill is **read-only** and does not create any cloud resources
- **No cache management needed** — index is fetched fresh from GitCode API v5 each run
- **Network required** — index data is hosted on GitCode, fetched via HTTP GET (base64 decoded)
- **MUST use script to search** — do not read index.json directly
- Index repo: `https://gitcode.com/developer-skill/skills-group-contribution` (branch: `test-for-index`)
- Skills repo: `https://github.com/huaweicloud/huaweicloud-skills` (branch: `master`)
- **KooCLI**: the search/install flow itself is pure Python + HTTP (no service-level
  hcloud commands, no `--cli-region`). Step 0.5 performs only a non-blocking KooCLI
  availability/version check (`hcloud version` via `scripts/check-koocli.py`) to warn
  about a missing/outdated CLI before installing skills that depend on it.
