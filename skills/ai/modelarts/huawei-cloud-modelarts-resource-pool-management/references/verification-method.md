# Verification Method

## CLI Verification

All 53 operations are verified available in `hcloud` CLI. Verification was performed using:

```bash
# Check if hcloud is installed
which hcloud

# List all ModelArts operations
hcloud ModelArts --help

# Verify specific operation exists
hcloud ModelArts ListPools --help
hcloud ModelArts CreatePool --help
hcloud ModelArts DeletePool --help
```

## Test Verification Flow

Each test case follows this flow:

1. **CLI Execution** — Try the hcloud command directly
2. **Success** → Record PASS
3. **Failure** → Check if it's a syntax issue
   - Syntax issue → Fix and retry
   - Non-syntax issue → Fallback to SDK
4. **SDK Fallback** — Try Python SDK
   - Success → Record PASS (SDK)
   - Failure → Fallback to API
5. **API Fallback** — Use REST API with user-provided endpoint
   - Success → Record PASS (API)
   - Failure → Record FAIL ⛔

## Read vs Write Operations

- **Read operations** (list, show, query): Execute without confirmation
- **Write operations** (create, delete, update, patch, reboot, etc.): Require explicit user confirmation
- **Destructive operations** (delete pool, delete node pool, batch delete nodes): Show warning + require confirmation
