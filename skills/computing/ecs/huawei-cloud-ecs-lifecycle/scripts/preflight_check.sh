#!/usr/bin/env bash
#
# preflight_check.sh -- Step 0 environment validation for the
# huawei-cloud-ecs-lifecycle Skill (issue #942).
#
# PURPOSE
#   Validate the runtime environment BEFORE any ECS workflow step runs, so that a
#   missing KooCLI, missing credentials or an unresolved region is reported here
#   with actionable remediation, instead of failing later at Step 3/4 with
#   "command not found".
#
# USAGE
#   bash scripts/preflight_check.sh [--region <region>] [--skip-auth-check]
#
#   --region <region>   Region used for the read-only smoke check (for example
#                       cn-north-4). When omitted, the script falls back to
#                       $HUAWEICLOUD_SDK_REGION, then $HUAWEI_REGION, then the
#                       region of the active KooCLI profile. There is NO implicit
#                       default region: an unresolved region is a FAIL.
#   --skip-auth-check   Skip the read-only credential smoke check (check 5).
#                       Use offline or in air-gapped pipelines; installation,
#                       credentials and region are still checked.
#   -h, --help          Print this usage text and exit 0.
#
# EXIT CODES
#   0  environment ready
#   1  environment NOT ready -- the workflow must not continue; the [FAIL] lines
#      and the remediation block below say what to fix
#   2  invalid command line
#
# CHECKS (one [OK]/[FAIL] line each)
#   1/5 KooCLI installed and reachable via `command -v hcloud`
#   2/5 `hcloud version` executes (NOT `hcloud --version`, which is a USE_ERROR)
#   3/5 credentials present: a KooCLI profile with an access key, or
#       HUAWEICLOUD_SDK_AK/SK, or HUAWEI_ACCESS_KEY/SECRET_KEY
#   4/5 region resolvable (--region > $HUAWEICLOUD_SDK_REGION > $HUAWEI_REGION >
#       active profile region)
#   5/5 read-only smoke: `hcloud ECS ListServersDetails --cli-region=<region>
#       --limit=1` returns a countable response
#
# NOTES
#   * POSIX-compatible code, no bash 4+ syntax (works on bash 3.2 / dash as well as
#     bash 5); syntax-check with: bash -n scripts/preflight_check.sh
#   * `set -u` only (no `set -e`), because several checks intentionally run
#     commands that return non-zero and inspect the result.
#   * Never prints AK/SK or any other secret. `hcloud configure list` output is
#     used for boolean detection only, and any captured hcloud text is masked
#     (>= 20 alphanumeric characters -> <redacted>) before it is echoed.
#   * KooCLI exits 0 even for USE_ERROR, so each check validates the RESPONSE,
#     not merely the exit code.
#   * The correct version probe is `hcloud version`; `hcloud --version` fails with
#     "[USE_ERROR]参数--version的格式错误,正确格式为:--param=value".
#   * Diagnostics go to stdout; the script is safe to pipe into a log.

set -u

PROG_NAME="preflight_check.sh"
GUIDE_REL="references/cli-installation-guide.md"

REGION_ARG=""
SKIP_AUTH_CHECK="no"
FAILED_CHECKS=0

usage() {
    cat <<'USAGE_EOF'
Usage: bash scripts/preflight_check.sh [--region <region>] [--skip-auth-check]

  --region <region>   Region used for the read-only smoke check (e.g. cn-north-4).
                      Falls back to $HUAWEICLOUD_SDK_REGION, then $HUAWEI_REGION,
                      then the active KooCLI profile region.
  --skip-auth-check   Skip the read-only credential smoke check (offline use).
  -h, --help          Show this help.

Exit codes: 0 = environment ready, 1 = environment not ready, 2 = invalid usage.
USAGE_EOF
}

ok() {
    printf '[OK]   %s\n' "$1"
}

fail() {
    printf '[FAIL] %s\n' "$1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

skip() {
    printf '[SKIP] %s\n' "$1"
}

# Mask credential-looking tokens and normalise line endings before any captured
# hcloud output is echoed. AK/SK values must never reach the console or a log.
mask() {
    printf '%s\n' "$1" | tr -d '\r' | sed -e 's/[A-Za-z0-9]\{20,\}/<redacted>/g'
}

# Print only the first error-ish line of a captured hcloud response, truncated.
first_error_line() {
    mask "$1" | grep -E 'USE_ERROR|\[ERROR\]|error_code|error_msg' | head -n 1 | cut -c1-200
}

# Region of the active profile, or empty. jq is used when available (correct for
# multi-profile configs); otherwise the first non-empty "region" value is taken.
profile_region() {
    if [ -z "$CONF_OUT" ]; then
        return 0
    fi
    if command -v jq >/dev/null 2>&1; then
        printf '%s\n' "$CONF_OUT" | jq -r '(.current) as $c | (.profiles[]? | select(.name == $c) | .region) // empty' 2>/dev/null | head -n 1
        return 0
    fi
    printf '%s\n' "$CONF_OUT" | sed -n 's/.*"region":[ ]*"\([^"]\{1,\}\)".*/\1/p' | head -n 1
}

print_remediation() {
    printf '\n---- Remediation: environment not ready ----\n'
    printf 'Full instructions: %s\n' "$GUIDE_PATH"
    cat <<'REMEDY_EOF'

1) Install the KooCLI 'hcloud' binary and put it on PATH (Linux / macOS / Git Bash):
     curl -fL -o hcloud.tar.gz https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz
     sha256sum hcloud.tar.gz
     tar -xzf hcloud.tar.gz && chmod +x hcloud && sudo mv hcloud /usr/local/bin/
   Verify with:  hcloud version      (NOT 'hcloud --version' - that is a USE_ERROR)

2) Authenticate -- either a CLI profile:
     hcloud configure set --cli-region=<region> --access-key=<AK> --secret-key=<SK>
   or environment variables:
     export HUAWEICLOUD_SDK_AK=<AK>
     export HUAWEICLOUD_SDK_SK=<SK>
     export HUAWEICLOUD_SDK_REGION=<region>

3) Resolve the region when the profile has none:
     hcloud configure set --cli-region=<region>
   or:  export HUAWEICLOUD_SDK_REGION=<region>

4) Re-run the preflight check:
     bash scripts/preflight_check.sh --region <region>

Never commit, echo or paste AK/SK values.
REMEDY_EOF
}

# ---------------------------------------------------------------- arguments --
while [ $# -gt 0 ]; do
    case "$1" in
        --region)
            if [ $# -lt 2 ]; then
                printf 'ERROR: --region requires a value\n' >&2
                usage >&2
                exit 2
            fi
            REGION_ARG="$2"
            shift 2
            ;;
        --region=*)
            REGION_ARG="${1#--region=}"
            shift
            ;;
        --skip-auth-check)
            SKIP_AUTH_CHECK="yes"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'ERROR: unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -n "$REGION_ARG" ]; then
    REGION_ARG_TRIM=$(printf '%s' "$REGION_ARG" | tr -d '[:space:]')
    if [ -z "$REGION_ARG_TRIM" ]; then
        printf 'ERROR: --region must not be empty\n' >&2
        usage >&2
        exit 2
    fi
    REGION_ARG="$REGION_ARG_TRIM"
fi

# Resolve the guide path relative to this script so the remediation hint works
# from any working directory.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../$GUIDE_REL" ]; then
    GUIDE_PATH="$SCRIPT_DIR/../$GUIDE_REL"
else
    GUIDE_PATH="$GUIDE_REL"
fi

printf '==== ECS lifecycle preflight check (hcloud) ====\n'
printf 'Skill: huawei-cloud-ecs-lifecycle | script: %s\n' "$PROG_NAME"

# ------------------------------------------------------- 1/5 hcloud on PATH --
printf '\n-- Check 1/5: KooCLI installed and on PATH --\n'
HCLOUD_BIN=""
if command -v hcloud >/dev/null 2>&1; then
    HCLOUD_BIN=$(command -v hcloud)
    ok "1/5 hcloud found on PATH: $HCLOUD_BIN"
else
    fail "1/5 hcloud NOT found on PATH (command -v hcloud failed); install KooCLI and add it to PATH"
fi

# ---------------------------------------------------- 2/5 hcloud version OK --
printf '\n-- Check 2/5: hcloud version --\n'
HCLOUD_USABLE="no"
VERSION_NUM=""
if [ -n "$HCLOUD_BIN" ]; then
    VERSION_OUT=$(hcloud version 2>&1)
    VERSION_RC=$?
    VERSION_NUM=$(printf '%s\n' "$VERSION_OUT" | tr -d '\r' \
        | sed -n 's/.*\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' | tail -n 1)
    case "$VERSION_OUT" in
        *USE_ERROR*|*ERROR*)
            fail "2/5 'hcloud version' reported an error (exit $VERSION_RC): $(first_error_line "$VERSION_OUT")"
            ;;
        *)
            if [ -n "$VERSION_NUM" ]; then
                HCLOUD_USABLE="yes"
                ok "2/5 'hcloud version' OK (KooCLI $VERSION_NUM)"
            else
                fail "2/5 'hcloud version' produced no version string (exit $VERSION_RC)"
            fi
            ;;
    esac
else
    fail "2/5 'hcloud version' not evaluated: hcloud is not available"
fi

# --------------------------------------------------------- 3/5 credentials --
printf '\n-- Check 3/5: credentials available --\n'
CONF_OUT=""
CUR_PROFILE=""
CRED_SOURCE=""
if [ -n "$HCLOUD_BIN" ]; then
    CONF_OUT=$(hcloud configure list 2>&1)
    CUR_PROFILE=$(printf '%s\n' "$CONF_OUT" | tr -d '\r' \
        | sed -n 's/.*"current":[ ]*"\([^"]*\)".*/\1/p' | head -n 1)
    if printf '%s\n' "$CONF_OUT" | grep -q '"accessKeyId"[[:space:]]*:[[:space:]]*"[^"]'; then
        CRED_SOURCE="KooCLI profile '${CUR_PROFILE}' (access key configured; value not shown)"
    elif printf '%s\n' "$CONF_OUT" | grep -q '"securityToken"[[:space:]]*:[[:space:]]*"[^"]'; then
        CRED_SOURCE="KooCLI profile '${CUR_PROFILE}' (temporary security token configured; value not shown)"
    fi
fi
if [ -z "$CRED_SOURCE" ]; then
    if [ -n "${HUAWEICLOUD_SDK_AK:-}" ] && [ -n "${HUAWEICLOUD_SDK_SK:-}" ]; then
        CRED_SOURCE="environment variables HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK (values not shown)"
    elif [ -n "${HUAWEI_ACCESS_KEY:-}" ] && [ -n "${HUAWEI_SECRET_KEY:-}" ]; then
        CRED_SOURCE="environment variables HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY (values not shown)"
    fi
fi
if [ -n "$CRED_SOURCE" ]; then
    ok "3/5 credentials present: $CRED_SOURCE"
else
    fail "3/5 no usable credentials found: no KooCLI profile with an access key, and no HUAWEICLOUD_SDK_AK/SK or HUAWEI_ACCESS_KEY/SECRET_KEY environment variables"
fi

# --------------------------------------------------------------- 4/5 region --
printf '\n-- Check 4/5: region resolvable --\n'
REGION=""
REGION_SOURCE=""
if [ -n "$REGION_ARG" ]; then
    REGION="$REGION_ARG"
    REGION_SOURCE="--region argument"
elif [ -n "${HUAWEICLOUD_SDK_REGION:-}" ]; then
    REGION="$HUAWEICLOUD_SDK_REGION"
    REGION_SOURCE="HUAWEICLOUD_SDK_REGION"
elif [ -n "${HUAWEI_REGION:-}" ]; then
    REGION="$HUAWEI_REGION"
    REGION_SOURCE="HUAWEI_REGION"
else
    REGION=$(profile_region)
    if [ -n "$REGION" ]; then
        REGION_SOURCE="active KooCLI profile '${CUR_PROFILE}'"
    fi
fi
if [ -n "$REGION" ]; then
    ok "4/5 region resolved: $REGION (source: $REGION_SOURCE)"
else
    fail "4/5 no region resolved: pass --region <region>, or export HUAWEICLOUD_SDK_REGION=<region>, or run 'hcloud configure set --cli-region=<region>' to set the profile region"
fi

# -------------------------------------------------- 5/5 read-only smoke test --
printf '\n-- Check 5/5: read-only credential smoke test --\n'
if [ "$SKIP_AUTH_CHECK" = "yes" ]; then
    skip "5/5 read-only smoke skipped (--skip-auth-check); credential usability is NOT verified"
elif [ "$HCLOUD_USABLE" != "yes" ]; then
    fail "5/5 read-only smoke not evaluated: hcloud is not usable"
elif [ -z "$REGION" ]; then
    fail "5/5 read-only smoke not evaluated: no region resolved"
else
    SMOKE_OUT=$(hcloud ECS ListServersDetails --cli-region="$REGION" --limit=1 2>&1)
    SMOKE_RC=$?
    SMOKE_COUNT=$(printf '%s\n' "$SMOKE_OUT" | tr -d '\r' \
        | sed -n 's/.*"count":[ ]*\([0-9][0-9]*\).*/\1/p' | head -n 1)
    if [ -n "$SMOKE_COUNT" ]; then
        ok "5/5 read-only smoke OK: hcloud ECS ListServersDetails --cli-region=$REGION --limit=1 returned count=$SMOKE_COUNT"
    else
        SMOKE_REASON=$(first_error_line "$SMOKE_OUT")
        if [ -n "$SMOKE_REASON" ]; then
            fail "5/5 read-only smoke FAILED (exit $SMOKE_RC): $SMOKE_REASON"
        else
            fail "5/5 read-only smoke FAILED (exit $SMOKE_RC): response contained no \"count\" field"
        fi
    fi
fi

# ------------------------------------------------------------- final verdict --
printf '\n==== Preflight result ====\n'
if [ "$FAILED_CHECKS" -eq 0 ]; then
    if [ "$SKIP_AUTH_CHECK" = "yes" ]; then
        printf 'PREFLIGHT RESULT: PASS - KooCLI installed, credentials present, region %s. Credential usability NOT verified (--skip-auth-check).\n' "$REGION"
    else
        printf 'PREFLIGHT RESULT: PASS - KooCLI installed, credentials usable, region %s (read-only smoke OK).\n' "$REGION"
    fi
    exit 0
fi

printf 'PREFLIGHT RESULT: FAIL - %s check(s) failed; abort the ECS workflow and fix the [FAIL] items above.\n' "$FAILED_CHECKS"
print_remediation
exit 1
