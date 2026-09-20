# Verification Method

## Overview

This document defines verification steps for each stage of the OptVerse Solver Assistant workflow.

## 1. Installation Verification

### 1.1 CLI Version

```bash
hcloud version
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| Returns version >= 7.2.2 | Reinstall KooCLI from official source |

### 1.2 Configuration Check

```bash
hcloud configure list
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| Profile with `mode: AKSK` exists | No profile found: instruct the user to run `hcloud configure init` themselves (AK/SK credential configuration is the user's responsibility; the agent must NOT write credentials on their behalf) |
| `region` is set to `cn-east-3` | Region not set: instruct the user to run `hcloud configure set --cli-region=cn-east-3` themselves |

### 1.3 Python Environment

```bash
python --version
python -c "import requests; print('OK')"
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| Python >= 3.8 | Install Python 3.8+ |
| `requests` imported successfully | Run `pip install requests` |

### 1.4 Environment Variables

```bash
# Verify env vars are set (should show masked values)
python -c "import os; print('AK:', os.environ.get('OPTVERSE_AK','NOT SET')[:4]+'****')"
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| `AK: XXXX****` (masked) | Set `OPTVERSE_AK` and `OPTVERSE_SK` env vars |

## 2. Per-Step Verification

### Step 1: Upload Requirement File

```bash
hcloud OptVerse UploadFile \
  --X-Chat-Route-Id=<route-id> \
  --agent_type=optverse \
  --file="<file-path>" \
  --cli-region=cn-east-3
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| HTTP 201 with `chat_id` in response | Check file path exists; verify AK/SK permissions |

### Step 2: Create Chat (Round 1)

```bash
python scripts/create_chat.py \
  --message="<requirement text>" \
  --agent_type=optverse \
  --filenames="<filename>"
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| JSON output with `chat_id`, `id`, `content` | Check env vars; verify endpoint; check SSE parsing |

### Step 3: List & Download Artifacts

```bash
hcloud OptVerse ListArtifacts --chat_id=<chat_id> --cli-region=cn-east-3
hcloud OptVerse DownloadFile --chat_id=<chat_id> --filename=<filename> --X-Need-Content=true --cli-region=cn-east-3
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| Artifacts list non-empty | Verify chat_id is correct; check stage completion |
| Download returns `content` field | Set `--X-Need-Content=true` |

### Step 4-8: Confirmation Rounds

```bash
python scripts/create_chat.py --message="确认" --agent_type=optverse --chat_id=<chat_id>
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| JSON output with new `id` (different from previous) | Verify `chat_id` and route_id consistency |
| `content` contains next-stage response | Check if previous stage was fully confirmed |

### Step 9: Publish

```bash
hcloud OptVerse PublishChat --chat_id=<chat_id> --name="<name>" --type=optverse --cli-region=cn-east-3
```

| Success Criteria | Failure Handling |
|-----------------|------------------|
| HTTP 200 with `id` in response | Verify all stages confirmed; check publish permissions |

## 3. End-to-End Verification Checklist

- [ ] hcloud version returns >= 7.2.2
- [ ] hcloud configure list shows valid AKSK profile
- [ ] OPTVERSE_AK and OPTVERSE_SK environment variables set
- [ ] Python 3.8+ with requests library installed
- [ ] UploadFile returns chat_id successfully
- [ ] create_chat.py returns chat_id, id, and content
- [ ] ListArtifacts shows artifacts per stage
- [ ] DownloadFile returns file content
- [ ] All 4 confirmation rounds return new response IDs
- [ ] PublishChat returns published asset ID
