# Acceptance Criteria

This document defines the pass/fail criteria for testing the DevBridge tunnel skill.

## Criteria Overview

| # | Category | Criteria | Verification Method |
|---|----------|----------|---------------------|
| AC-1 | Installation | DevBridge CLI installed and accessible | `devbridge version` returns version |
| AC-2 | Authentication | User can authenticate | `devbridge auth status` shows logged in |
| AC-3 | Tunnel Creation | Can create a tunnel | `devbridge create` returns tunnel ID |
| AC-4 | Tunnel List | Can list tunnels | `devbridge list` shows created tunnel |
| AC-5 | Tunnel Details | Can view tunnel details | `devbridge show <id>` shows details |
| AC-6 | Tunnel Update | Can update a tunnel | `devbridge update <id>` succeeds |
| AC-7 | Tunnel Delete | Can delete a tunnel | `devbridge delete <id>` succeeds |
| AC-8 | Port Creation | Can add a port to a tunnel | `devbridge port create` succeeds |
| AC-9 | Port List | Can list ports | `devbridge port list` shows ports |
| AC-10 | Port Delete | Can delete a port | `devbridge port delete` succeeds |
| AC-11 | Host | Can host a local service | `devbridge host` shows running address |
| AC-12 | Connect | Remote device can connect | `devbridge connect` establishes mapping |
| AC-13 | Token | Can issue tokens | `devbridge token` returns token |
| AC-14 | Security | No AK/SK in output/logs | Verify no credentials in command output |
| AC-15 | Cleanup | All test resources deleted | `devbridge list` shows no test tunnels |

## Detailed Criteria

### AC-1: CLI Installation

**Preconditions:** None.

**Steps:**
1. Run `devbridge version`.

**✅ Pass criteria:** Command exits with code 0 and displays version number.

```text
0.1.12-release
```

**❌ Fail criteria:** Command not found or exits with non-zero code.

```text
command not found: devbridge
```

### AC-2: Authentication

**Preconditions:** AC-1 passes.

**Steps:**
1. Run `devbridge auth status`.

**Pass criteria:** Output indicates "Logged in" and includes account information.

**Fail criteria:** Output indicates "Not logged in" or command fails.

### AC-3: Tunnel Creation

**Preconditions:** AC-2 passes.

**Steps:**
1. Run `devbridge create ac-test -d "验收测试" -e 1`.

**Pass criteria:** Output contains "Tunnel ID:" with a non-empty value.

**Fail criteria:** Command fails or no tunnel ID returned.

### AC-4: Tunnel List

**Preconditions:** AC-3 passes.

**Steps:**
1. Run `devbridge list`.

**Pass criteria:** Output includes the tunnel created in AC-3.

**Fail criteria:** Created tunnel not in list or command fails.

### AC-5: Tunnel Details

**Preconditions:** AC-3 passes.

**Steps:**
1. Run `devbridge show <tunnelId>`.

**Pass criteria:** Output shows tunnel details (name, description, expiration).

**Fail criteria:** Command fails or details incomplete.

### AC-6: Tunnel Update

**Preconditions:** AC-3 passes.

**Steps:**
1. Run `devbridge update <tunnelId> -n ac-test-updated`.

**Pass criteria:** Command succeeds. `devbridge show <tunnelId>` shows updated name.

**Fail criteria:** Command fails or name not updated.

### AC-7: Tunnel Delete

**Preconditions:** AC-3 passes.

**Steps:**
1. Run `devbridge delete <tunnelId>`.
2. Run `devbridge list`.

**Pass criteria:** Deleted tunnel no longer appears in list.

**Fail criteria:** Tunnel still appears or delete command fails.

### AC-8: Port Creation

**Preconditions:** AC-3 passes (new tunnel created).

**Steps:**
1. Run `devbridge port create <tunnelId> -p 8080 --protocol http`.

**Pass criteria:** Command succeeds and confirms port creation.

**Fail criteria:** Command fails or port not created.

### AC-9: Port List

**Preconditions:** AC-8 passes.

**Steps:**
1. Run `devbridge port list <tunnelId>`.

**Pass criteria:** Output includes port 8080.

**Fail criteria:** Port not listed or command fails.

### AC-10: Port Delete

**Preconditions:** AC-8 passes.

**Steps:**
1. Run `devbridge port delete <tunnelId> -p 8080`.
2. Run `devbridge port list <tunnelId>`.

**Pass criteria:** Port 8080 no longer appears in port list.

**Fail criteria:** Port still listed or delete command fails.

### AC-11: Host

**Preconditions:** AC-8 passes, local service running on port 8080.

**Steps:**
1. Run `devbridge host <tunnelId>` in a terminal.
2. Verify output shows tunnel address.
3. Access tunnel address from a browser.
4. Stop with `Ctrl+C`.

**Pass criteria:** Host starts, displays address, and service is accessible via tunnel address.

**Fail criteria:** Host fails to start or service not accessible.

### AC-12: Connect

**Preconditions:** AC-11 passes, second device with DevBridge CLI installed.

**Steps:**
1. Run `devbridge connect <tunnelId>` on the second device.
2. Access `http://localhost:8080` on the second device.
3. Stop with `Ctrl+C`.

**Pass criteria:** Local port mapping established and service accessible via localhost.

**Fail criteria:** Connection fails or service not accessible.

### AC-13: Token Issuance

**Preconditions:** AC-3 passes.

**Steps:**
1. Run `devbridge token <tunnelId> -s host`.
2. Run `devbridge token <tunnelId> -s connect`.

**Pass criteria:** Both commands return tokens.

**Fail criteria:** Either command fails.

### AC-14: Security Verification

**Preconditions:** All preceding ACs executed.

**Steps:**
1. Review all command output.
2. Verify no AK/SK values appear in any output.
3. Verify no tokens appear in logs or error messages.

**Pass criteria:** No sensitive credentials in any output.

**Fail criteria:** Credentials or tokens exposed in output.

### AC-15: Resource Cleanup

**Preconditions:** All preceding ACs executed.

**Steps:**
1. Delete all test tunnels: run `devbridge delete <tunnelId>` for each.
2. Run `devbridge list`.

**Pass criteria:** No test tunnels remain.

**Fail criteria:** Test tunnels still exist.

## Test Execution

Run all acceptance criteria in sequence:

```bash
#!/bin/bash
set -e

PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        echo "[PASS] $1"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $1"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== AC-1: CLI Installation ==="
devbridge version && check "AC-1" || check "AC-1"

echo "=== AC-2: Authentication ==="
devbridge auth status && check "AC-2" || check "AC-2"

echo "=== AC-3: Tunnel Creation ==="
TUNNEL_ID=$(devbridge create ac-test -d "验收测试" -e 1 | grep "Tunnel ID" | awk '{print $3}')
[ -n "$TUNNEL_ID" ] && check "AC-3" || check "AC-3"

echo "=== AC-4: Tunnel List ==="
devbridge list | grep -q "ac-test" && check "AC-4" || check "AC-4"

echo "=== AC-8: Port Creation ==="
devbridge port create "$TUNNEL_ID" -p 8080 --protocol http && check "AC-8" || check "AC-8"

echo "=== AC-9: Port List ==="
devbridge port list "$TUNNEL_ID" | grep -q "8080" && check "AC-9" || check "AC-9"

echo "=== AC-15: Cleanup ==="
devbridge delete "$TUNNEL_ID" && check "AC-15" || check "AC-15"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
```
