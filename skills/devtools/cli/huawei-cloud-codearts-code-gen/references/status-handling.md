

## Status Handling

### Status: need_input (exit code 10)

**Script output:**
```json
{
  "status": "need_input",
  "code": 10,
  "type": "aksk_required",
  "message": "Huawei Cloud Access Key required",
  "help": {
    "description": "Access Key is used to authenticate CodeArts CLI",
    "tutorial_url": "https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html",
    "console_url": "https://console.huaweicloud.com/iam/?#/mine/accessKey",
    "env_vars": [
      {
        "name": "CODEARTS_CLI_AK",
        "label": "Access Key ID",
        "description": "Huawei Cloud Access Key ID",
        "required": true
      },
      {
        "name": "CODEARTS_CLI_SK",
        "label": "Secret Access Key",
        "description": "Huawei Cloud Secret Access Key",
        "required": true,
        "secret": true
      }
    ],
    "hint": "After providing AK/SK, the agent will save them. No need to re-enter.",
    "save_command": "setup.sh --save-aksk AK SK"
  }
}
```

**Agent displays to user:**
```
========================================
🔐 Huawei Cloud Access Key Required
========================================

Access Key is used to authenticate CodeArts CLI.

📚 Tutorial:
   https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html

🔗 Console:
   https://console.huaweicloud.com/iam/?#/mine/accessKey

📝 Environment variables to configure:
   - CODEARTS_CLI_AK: Access Key ID
   - CODEARTS_CLI_SK: Secret Access Key

   Security Notice:
   - AK/SK will be stored in **PLAINTEXT** in environment variables (path: ~/.bashrc)
   - Please do not disclose your AK/SK to others, to prevent unauthorized use of your Huawei Cloud credentials, which could lead to resource theft or financial losses

   Note: AK/SK are stored only in the local AI Shell environment variables and will NOT be uploaded to any external services, and you can either clear them manually or wait for them to be automatically released when the environment resources are reclaimed to delete them.

   After use, delete with (Linux / macOS):
   bash scripts/setup.sh --clear-aksk
   After use, delete with (Windows PowerShell):
   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -ClearAksk

Please enter:
   Access Key ID: ________________
   Secret Access Key: ________________
```
**After user input, agent executes:**
```bash
setup.sh --save-aksk "user's AK" "user's SK"
```

---

### Status: need_consent (exit code 20)

**Script output:**
```json
{
  "status": "need_consent",
  "code": 20,
  "type": "permission_required",
  "message": "CodeArts CLI needs file read/write permission to generate code",
  "consent": {
    "description": "After configuration, CLI can create and modify files in the specified directory",
    "risk": "Recommend limiting to the workspace directory, avoid global permissions",
    "workspace": "/workspace"
  }
}
```

**Agent displays to user:**
```
========================================
⚠️  File Permission Authorization Required
========================================

CodeArts CLI needs file read/write permission to generate code.

📋 Details:
   - After configuration, CLI can create and modify files in the directory
   - Recommend limiting to the workspace directory
   - Current workspace: /workspace

Authorize? (y/n)
```
**After user agrees:**

Linux / macOS:
```bash
bash scripts/permission.sh --agree /workspace
```

Windows PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/permission.ps1 --agree /workspace
```

**If user declines:**
```
Cannot continue using CodeArts CLI.

Choose:
  [1] Continue fixing - manually configure permissions and retry
  [2] Write code directly - agent writes code directly
```

---

### Status: invalid_arguments (exit code 2)

Emitted by `setup.sh` / `setup.ps1` when `--save-aksk`, `--ak`, or `--sk` is passed without its value,
when AK or SK is an empty string, or when the `~/.bashrc` lock cannot be acquired within the timeout
(`type: "lock_timeout"`).

**Script output:**
```json
{
  "status": "error",
  "code": 2,
  "type": "invalid_arguments",
  "message": "Missing value for --save-aksk: SK is required",
  "fix_hint": "Usage: setup.sh --save-aksk <AK> <SK>",
  "options": [
    {"id": 1, "label": "Continue fixing", "description": "Re-run with both AK and SK"},
    {"id": 2, "label": "Write code directly", "description": "Abandon CodeArts, agent writes code directly"}
  ]
}
```

**Agent displays to user:** the `message` and the `fix_hint`, then requests BOTH the AK and the SK
again. Never forward truncated or empty credentials to the CLI, and never treat this as a
successful configuration.

---

### Status: error (exit code 30/40/50)

**Script output:**
```json
{
  "status": "error",
  "code": 30,
  "type": "download_failed",
  "message": "CLI install script download failed (retried 3 times)",
  "fix_hint": "Check network connection, or manually download: https://...",
  "options": [
    {"id": 1, "label": "Continue fixing", "description": "Try to fix manually"},
    {"id": 2, "label": "Write code directly", "description": "Abandon CodeArts, agent writes code directly"}
  ]
}
```

**Agent displays to user:**
```
========================================
❌ Environment Setup Failed
========================================

Error type: CLI installation failed
Error message: CLI install script download failed (retried 3 times)

💡 Fix suggestion:
   Check network connection, or manually download: https://...

Choose next step:
  [1] Continue fixing
      - Check network
      - Manually install CodeArts CLI
      - Re-run environment check

  [2] Write code directly
      - Abandon CodeArts
      - Agent writes code directly
```
### Status: ready (exit code 0)

**Script output:**
```json
{
  "status": "ready",
  "code": 0,
  "message": "Environment setup complete, ready for code generation"
}
```

**Agent proceeds with code generation.**

---

### Status: cleared (exit code 0)

Emitted by `setup.sh --clear-aksk` (Linux / macOS) and `setup.ps1 -ClearAksk` (Windows) after the
stored `CODEARTS_CLI_AK` / `CODEARTS_CLI_SK` credentials have been removed.

**Script output:**
```json
{
  "status": "cleared",
  "code": 0,
  "message": "AK/SK removed from ~/.bashrc"
}
```

**Agent reports to the user** that the credentials have been deleted locally, and reminds them that
any already-running shell may still hold them in its own environment.

---

### Important: Load AK/SK and PATH

When using `scripts/codearts_run.sh` / `scripts/codearts_run.ps1`, credential loading and CLI
location are handled inside the wrapper — no manual step is needed. The manual steps below apply only
when invoking the `codearts` binary directly.

The script's internal exports only take effect within the script's subprocess.
Before running `codearts` directly, the agent MUST load AK/SK and set PATH.

**Linux / macOS / Windows Git Bash:**
```bash
eval "$(grep -E '^export CODEARTS_CLI_(AK|SK)=' $HOME/.bashrc)"
export PATH="$HOME/.codeartsdoer/installers:$PATH"
```

**Windows PowerShell:**
```powershell
$env:PATH = "$env:USERPROFILE\.codeartsdoer\installers;$env:PATH"
```

---
