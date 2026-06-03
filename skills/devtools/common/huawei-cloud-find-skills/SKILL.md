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
- **Install Skills**: Guide users through skill installation via `npx skills add`

**Architecture**: Pre-built index (`references/index.json`) → Smart search → GitHub raw fetch for details → Install

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

Given `keyword` (from AI-understood user intent) and optional `category`, read `references/index.json` and search for matching skills.

**Scoring algorithm** (per skill, higher = better match):
- Name contains keyword → **+10** points
- Any trigger contains keyword → **+8** points
- Description contains keyword → **+5** points

Results are sorted by score descending.

**Search modes**:
- **Keyword only**: `search-skills -Keyword "ECS"` — matches across name/description/triggers
- **Category only**: `search-skills -Category "storage"` — filters by category field
- **Combined**: `search-skills -Keyword "OBS" -Category "storage"` — both constraints

**Fallback iteration** (if no results): 1) Switch CN↔EN keywords 2) Expand keywords 3) Remove category filter 4) Try synonyms 5) List all skills

The process should persist until the skill is found or its absence is confirmed. In the event of total failure, notify the user of the specific steps that were attempted.

### Step 2: View Skill Details (optional)

Fetch the full SKILL.md content from GitHub for intent validation. Skip this step if the search results from Step 1 are sufficiently informative.

```bash
# URL pattern
DETAIL_URL="https://raw.githubusercontent.com/huaweicloud/huaweicloud-skills/master/skills/${category}/${service}/${skill-name}/SKILL.md"
```

The agent can fetch this URL using `curl` or its web-fetch tool, then present the skill's full description to the user.

### Step 3: Install Skill

Trigger the installation routine corresponding to the desired skill.

```bash
# Option A: Using npx skills add (default)
npx skills add huaweicloud/huaweicloud-skills --skill <skill-name>

# Option B: Using npx clawhub install (OpenClaw ecosystem)
npx clawhub install <skill-name>
```

Restart (optional) Agent to verify and load the new skill.

## Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `Keyword` | Optional | Search keyword (matched against name, description, triggers) | None |
| `Category` | Optional | Category code for filtering (e.g., "computing", "storage", "network") | None |
| `skill-name` | Required (Step 3-4) | Exact skill name for viewing details or installing | None |

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/index.json](references/index.json) | Pre-built skill index with 37 entries (name, description, triggers, category, service) |

## Search Heuristics

> Optional reference for keyword-to-category hints. The agent can infer categories from `index.json` without these.

- Cloud infrastructure keywords (ecs, bms, vpc, obs, rds, ...) → likely `computing`, `network`, `storage`, etc.
- Tool keywords (cli, terraform, koo) → likely `devtools`
- Management keywords (monitoring, alarm, log) → likely `monitoring`

## Troubleshooting

### Issue: raw.githubusercontent.com returns 404

**Cause**: File path incorrect or default branch is not `master`
**Solution**: Verify the skill's `category`, `service`, and `name` from `references/index.json`

### Issue: Search returns no results

**Cause**: Keywords don't match any skill
**Solution**:
1. Try broader keywords
2. Switch between Chinese and English keywords (e.g., "对象存储" → "obs")
3. List all skills from the index

## Notes

- This skill is **read-only** and does not create any cloud resources
- **No cache management needed** — index is pre-built and shipped with the skill
- **Offline search** — index is local, only Step 2 requires network
- Repo: `https://github.com/huaweicloud/huaweicloud-skills` (branch: `master`)