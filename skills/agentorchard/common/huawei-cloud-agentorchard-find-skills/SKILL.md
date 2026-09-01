---
name: huawei-cloud-agentorchard-find-skills
description: | 
    Search, discover, browse and install AI Gallery Agent skills via natural language. Triggers include: "AI Gallery", "AI Gallery有什么skill", "有什么skill", "AI Gallery相关skill", "AI Gallery agent skill 市场", "AI Gallery skill类目", "skill 市场", "搜索AI Gallery skill", "安装skill", "订阅skill", "有没有XX skill", "有没有XX的能力", "帮我找 XX skill", "帮我找一个能XX的工具", "我想扩展功能", "介绍 XX Skill 内容", "XX Skill 具体做什么", "explore AI Gallery skills", "show AI Gallery skill categories", "does an AI Gallery skill exist for...", "which AI Gallery skills exist", "search skill", "find skill".
---

# Overview

This skill enables the Agent to efficiently search, discover, and install skills 
from AI Gallery. Simply input natural language; the Agent automatically understands 
intent and executes searches, returning results in natural language.

## Scenarios

This skill enables the Agent to:

- **Search skills** — Find skills by keyword
- **View skill details** — Jump to AI Gallery detail page for full documentation
- **Subscribe to skills** — Complete skill installation via AI Gallery subscription page

### Usage Examples

- "帮我找一个图像分类的 skill"
- "AI Gallery 有哪些 NLP 相关的skill？"
- "有没有数据预处理的 skill？"
- "浏览所有可用的 AI Gallery skill"
- "找一个文本生成的 skill"

## Prerequisites

- **Agent runtime** requires Python 3.6+ (script execution environment)
- **Network access** to AI Gallery API (`devdata.huaweicloud.com`)
- **No authentication required** — the API is public and read-only

## Workflow

### Step 1: Execute Search Script

Based on user input, run the search script (**execute only once**):

```bash
PYTHONIOENCODING=utf-8 python scripts/search_skills.py -k "<user input>"
```

> [!IMPORTANT]
> **Agent must follow these rules:**
>
> 1. **Execute only once** — No repeated runs, no retries
> 2. **Output script results directly** — No additional explanation, intermediate messages, or summaries
> 3. **No extra operations** — Show exactly what the script outputs
> 4. **Use UTF-8 encoding** — Must set `PYTHONIOENCODING=utf-8` when running the script
> 5. **No direct API calls** — Must use the script; do not bypass it to call the API directly

The script automatically handles all scenarios:

| User Input Type | Script Output |
|-----------------|---------------|
| Browse intent (e.g., "有什么skill") | Hot skills + guidance |
| Search intent (e.g., "银行") | Matching skill list |
| No results (e.g., gibberish) | Guidance |

**The Agent only needs to display the script output directly to the user, without adding any extra operations.**

### Step 2: View Details & Subscribe (Optional)

After the user selects a skill, guide them to visit the detail page and subscribe.

**Rules:**
- Only show the detail page URL when a specific `show_id` is available from the search results
- Format: `详情页：https://pangu.huaweicloud.com/gallery/asset-detail.html?id={show_id}`
- Do NOT show URL templates or placeholder formats like `?id={show_id}` to the user

The user clicks the "Subscribe" button on the detail page to complete installation.

## Core Commands

| Command | Purpose |
|---------|---------|
| `PYTHONIOENCODING=utf-8 python scripts/search_skills.py -k "<keyword>"` | Search skills by keyword |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `-k, --keyword` | No | Search keyword, supports space/comma/semicolon separated | `-k "银行"` |
| `--api-base` | No | AI Gallery API base URL (has default) | `--api-base "https://..."` |

## Reference Documents

- `references/cli-installation-guide.md` — Environment setup and prerequisites
- `references/iam-policies.md` — IAM policy notes (public API, no credentials needed)
- `references/verification-method.md` — Functional verification methods
- `references/acceptance-criteria.md` — Acceptance criteria and checklist
- `references/dataflow-diagram.md` — Data flow diagram
