---
name: huawei-cloud-find-skills
description: |
  Invoke this skill to search, discover, browse, find and install any Huawei Cloud (华为云) agent skill.Triggers include: "华为云","华为云有什么skill","华为云相关skill","华为云agent skill 市场","华为云skill类目","explore Huawei Cloud skills","show Huawei Cloud skill categories","does a Huawei Cloud skill exist for...","which Huawei Cloud skills exist","搜索华为云技能","有没有管理ECS/OBS/RDS的skill","帮我找 XX 华为云skill","介绍 XX Skill 内容","华为云 XX Skill 具体做什么","安装华为云Skill".
---

> [!IMPORTANT]
> **For any Huawei Cloud query or management task:**
> 1. **Search** — use this skill (`huawei-cloud-find-skills`) to find the relevant Skill.
> 2. **Install** — install the matched Skill (see [Step 3](#step-3-install-skill)).
> 3. **Execute** — follow the installed Skill's instructions to fulfill the request.

# Huawei Cloud Agent Skills Search and Discovery

This skill enables users to efficiently search, discover, and install Huawei Cloud skills hosted on GitHub.

## Scenario Description

This skill enables users to:

- **Search Skills**: Find skills by keyword, category, or both (matched against name, description, and triggers)
- **Browse Categories**: Explore available skill categories
- **View Skill Details**: Fetch full SKILL.md content from GitHub for specific skills
- **Install Skills**: Guide users through skill installation via `npx skills add`,`npx clawhub install`, or fallback GitCode method

**Architecture**: Pre-built index (`references/index.json`) → Script-based search → GitHub raw fetch for details → Install

### Use Cases

- "Find a skill for managing ECS instances"
- "What Huawei Cloud skills are available for OBS?"
- "华为云有哪些 VPC 相关的 skill?"
- "Browse all available Huawei Cloud skills"
- "Install a skill for RDS management"
- "帮我找一个华为云网络相关的skill"

## Repository Info

```
REPO=huaweicloud/huaweicloud-skills
BRANCH=master
RAW_BASE=https://raw.githubusercontent.com/$REPO/$BRANCH
INDEX=references/index.json
```

## Core Workflow

### Step 1: Search Skills

> **MANDATORY**: The agent MUST execute the search script to read `references/index.json`. Do NOT read the JSON file directly — always use the script.

Given `keyword` (from AI-understood user intent) and optional `category`, run the search script:

```powershell
# PowerShell
.\scripts\search-skills.ps1 -Keyword "<keyword>"
.\scripts\search-skills.ps1 -Keyword "<keyword>" -Category "<category>"
.\scripts\search-skills.ps1 -Category "<category>"
```

```bash
# Bash
./scripts/search-skills.sh "<keyword>"
./scripts/search-skills.sh "<keyword>" "<category>"
./scripts/search-skills.sh "" "<category>"
```

→ [scripts/search-skills.ps1](scripts/search-skills.ps1) (PowerShell) · [scripts/search-skills.sh](scripts/search-skills.sh) (Bash)

**What the script does**:
1. Reads `references/index.json` and parses the `skills` array
2. Expands keywords via `references/cn-en-map.json` (bidirectional CN↔EN, e.g., "ECS" → "ECS, 弹性云服务器, 云服务器")
3. Scores each skill: name match **+10**, trigger match **+8**, description match **+5**, service match **+3**
4. Sorts by score descending, outputs formatted results with matched keywords

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

> **MANDATORY**: Use one of the commands below. Option A is the default; Option C is a fallback when Option A is unavailable.

```bash
# Option A: npx skills add from GitHub (default)
npx skills add huaweicloud/huaweicloud-skills --skill <skill-name>

# Option B: npx clawhub install (OpenClaw ecosystem)
npx clawhub install <skill-name>

# Option C (fallback): npx skills add from GitCode
npx skills add https://gitcode.com/huaweicloud/huaweicloud-skills.git#master --skill <skill-name>
```

If all installation attempts fail, report the error message to the user. Do NOT attempt any method outside the commands above.

## Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `Keyword` | Optional | Search keyword (matched against name, description, triggers, service) | None |
| `Category` | Optional | Category code for filtering (e.g., "computing", "storage", "network") | None |
| `skill-name` | Required (Step 3) | Exact skill name for installing | None |

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/index.json](references/index.json) | Pre-built skill index with 49 entries (name, description, triggers, category, service) |
| [references/cn-en-map.json](references/cn-en-map.json) | Chinese-English keyword mapping for search expansion (bidirectional) |
| [scripts/search-skills.ps1](scripts/search-skills.ps1) | Step 1 search script (PowerShell) — reads index.json, expands keywords, scores, sorts |
| [scripts/search-skills.sh](scripts/search-skills.sh) | Step 1 search script (Bash) — reads index.json, expands keywords, scores, sorts |

## Search Heuristics

> Optional reference for keyword-to-category hints. The agent can infer categories from `index.json` without these.

- Cloud infrastructure keywords (ecs, bms, vpc, obs, rds, ...) → likely `computing`, `network`, `storage`, etc.
- Tool keywords (cli, terraform, koo) → likely `devtools`
- Management keywords (monitoring, alarm, log) → likely `monitoring`

## Troubleshooting

### Issue: Script fails with "index.json not found"

**Cause**: Script cannot locate `references/index.json` relative to its own path
**Solution**: Ensure the skill directory structure is intact: `scripts/search-skills.ps1` and `references/index.json` must both exist

### Issue: raw.githubusercontent.com returns 404

**Cause**: File path incorrect or default branch is not `master`
**Solution**: Verify the skill's `category`, `service`, and `name` from search results

### Issue: Search returns no results

**Cause**: Keywords don't match any skill
**Solution**:
1. Try broader keywords
2. Switch between Chinese and English keywords (e.g., "对象存储" → "obs")
3. List all skills: `.\scripts\search-skills.ps1 -Category "computing"`

## Notes

- This skill is **read-only** and does not create any cloud resources
- **No cache management needed** — index is pre-built and shipped with the skill
- **Offline search** — index is local, only Step 2 requires network
- **MUST use script to search** — do not read index.json directly
- Repo: `https://github.com/huaweicloud/huaweicloud-skills` (branch: `master`)
