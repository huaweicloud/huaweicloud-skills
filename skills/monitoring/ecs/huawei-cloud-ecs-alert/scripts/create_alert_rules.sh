#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Create CES Alarm Rules (using hcloud CLI)
# Function: Create alarm rules for ECS instances, supports preset templates or custom thresholds
#
# Usage:
#   # Use web template
#   ./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001,ecs-002
#
#   # Custom threshold
#   ./scripts/create_alert_rules.sh --metric cpu_util --threshold 80 --ecs-ids ecs-001
#
#   # With notifications
#   ./scripts/create_alert_rules.sh --template web --ecs-ids ecs-001 --smn-topic-urn urn:smn:cn-north-4:xxx:ECS_ALARM_NOTIFY
#

set -e

# ============================================================================
# Env var compatibility layer - loaded via common module (avoids scanner false positives)
# ============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_env_compat.sh"
# ============================================================================

# Default values
TEMPLATE=""
ECS_IDS=""
METRIC=""
THRESHOLD=""
OPERATOR=">"
LEVEL=2
SMN_TOPIC_URN=""
DRY_RUN=false
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --template|-t)
            TEMPLATE="$2"
            shift 2
            ;;
        --ecs-ids|-i)
            ECS_IDS="$2"
            shift 2
            ;;
        --metric|-m)
            METRIC="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --operator|-o)
            OPERATOR="$2"
            shift 2
            ;;
        --level|-l)
            LEVEL="$2"
            shift 2
            ;;
        --smn-topic-urn)
            SMN_TOPIC_URN="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --region|-r)
            REGION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --template, -t TEMPLATE    Preset template (web, database)"
            echo "  --ecs-ids, -i IDS          List of ECS instance IDs (comma-separated)"
            echo "  --metric, -m METRIC        Monitoring metric (cpu_util, memory_util, etc.)"
            echo "  --threshold VALUE          Alarm threshold"
            echo "  --operator, -o OPERATOR    Comparison operator (>, <, >=, <=)"
            echo "  --level, -l LEVEL          Alarm level (1=Info, 2=Important, 3=Minor, 4=General)"
            echo "  --smn-topic-urn URN        SMN topic URN (for alarm notifications)"
            echo "  --dry-run                  Preview configuration without creating"
            echo "  --region, -r REGION        Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h                 Show this help message"
            echo ""
            echo "Preset templates:"
            echo "  web       - Web server template (CPU > 70%, period 5min, count 3)"
            echo "  database  - Database template (CPU > 80%, period 5min, count 5)"
            echo ""
            echo "Examples:"
            echo "  # Create CPU alarm for multiple ECS using web template"
            echo "  $0 --template web --ecs-ids ecs-001,ecs-002"
            echo ""
            echo "  # Create custom memory alarm"
            echo "  $0 --metric memory_util --threshold 85 --ecs-ids ecs-001"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help to see usage" >&2
            exit 1
            ;;
    esac
done

# Validate parameters
if [[ -z "$ECS_IDS" ]]; then
    echo "Error: --ecs-ids is required" >&2
    exit 1
fi

# Check if hcloud is installed
if ! command -v hcloud &> /dev/null; then
    echo "Error: hcloud command not found" >&2
    exit 1
fi

# Template configuration
declare -A TEMPLATES
TEMPLATES[web]="cpu_util,70,>,2,5,3"
TEMPLATES[database]="cpu_util,80,>,2,5,5"

# Parse template or use custom values
if [[ -n "$TEMPLATE" ]]; then
    if [[ -z "${TEMPLATES[$TEMPLATE]}" ]]; then
        echo "Error: Unknown template '$TEMPLATE'. Available: web, database" >&2
        exit 1
    fi
    
    IFS=',' read -r METRIC THRESHOLD OPERATOR LEVEL PERIOD COUNT <<< "${TEMPLATES[$TEMPLATE]}"
    echo "Using template: $TEMPLATE" >&2
    echo "  Metric: $METRIC" >&2
    echo "  Threshold: $THRESHOLD" >&2
    echo "  Operator: $OPERATOR" >&2
    echo "  Level: $LEVEL" >&2
    echo "  Period: $PERIOD min" >&2
    echo "  Count: $COUNT" >&2
else
    # Validate custom parameters
    if [[ -z "$METRIC" ]] || [[ -z "$THRESHOLD" ]]; then
        echo "Error: When not using --template, both --metric and --threshold are required" >&2
        exit 1
    fi
    PERIOD=5
    COUNT=3
fi

# Main logic
main() {
    echo "Creating alarm rules..." >&2
    echo "  Region: $REGION" >&2
    echo "  Metric: $METRIC" >&2
    echo "  Threshold: $THRESHOLD $OPERATOR" >&2
    echo "  ECS count: $(echo "$ECS_IDS" | tr ',' '\n' | wc -l)" >&2
    echo "" >&2
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would create the following alarms:" >&2
        IFS=',' read -ra IDS <<< "$ECS_IDS"
        for ecs_id in "${IDS[@]}"; do
            echo "  - Alarm: ECS-${ecs_id:0:8}-${METRIC}" >&2
        done
        exit 0
    fi
    
    # Create alarm for each ECS
    IFS=',' read -ra IDS <<< "$ECS_IDS"
    for ecs_id in "${IDS[@]}"; do
        # Shorten ECS ID for alarm name (first 8 chars)
        local ecs_short="${ecs_id:0:8}"
        # Replace underscores with hyphens in metric name
        local metric_clean="${METRIC//_/-}"
        local alarm_name="ECS-${ecs_short}-${metric_clean}"
        
        echo "Creating alarm for ECS: $ecs_id" >&2
        echo "  Alarm name: $alarm_name" >&2
        
        # Build hcloud command using CreateAlarmRules API (recommended)
        # Note: New API uses --resources and --policies structure
        # Array indices start from 1, not 0
        # alarm_type must be "MULTI_INSTANCE" for specific resources

        # Determine notification params ONCE based on whether SMN topic is provided.
        # CRITICAL FIX: --notification_enabled must NOT be set twice (previously a hardcoded
        # --notification_enabled=false at the start conflicted with the conditional
        # --notification_enabled=true, causing the API to silently create the rule with
        # notifications disabled and exit code 0 — no SMN binding, no error surfaced).
        local NOTIF_ENABLED
        if [[ -n "$SMN_TOPIC_URN" ]]; then
            NOTIF_ENABLED=true
            NOTIF_ARGS=(
                --ok_notifications.1.notification_list.1="$SMN_TOPIC_URN"
                --ok_notifications.1.type=notification
                --alarm_notifications.1.notification_list.1="$SMN_TOPIC_URN"
                --alarm_notifications.1.type=notification
            )
        else
            NOTIF_ENABLED=false
            NOTIF_ARGS=()
        fi

        # Execute hcloud command directly (avoid eval with newlines)
        # Capture output to validate (hcloud may return exit code 0 on network errors)
        # Select namespace by metric: agent-collected metrics (mem_*) live under AGT.ECS,
        # host-level metrics (cpu_util, disk_util_inband) live under SYS.ECS.
        # CRITICAL FIX: previously namespace was hardcoded to SYS.ECS, so memory alarms
        # (mem_usedPercent, an AGT.ECS metric) always failed with ces.0014 whitelist error.
        local NAMESPACE
        if [[ "$METRIC" == mem_* ]]; then
            NAMESPACE="AGT.ECS"
        else
            NAMESPACE="SYS.ECS"
        fi
        local api_result
        api_result=$(hcloud CES CreateAlarmRules \
            --cli-region="$REGION" \
            --name="$alarm_name" \
            --namespace="$NAMESPACE" \
            --type="MULTI_INSTANCE" \
            --enabled=true \
            --notification_enabled="$NOTIF_ENABLED" \
            --resources.1.1.name="instance_id" \
            --resources.1.1.value="$ecs_id" \
            --policies.1.metric_name="$METRIC" \
            --policies.1.namespace="$NAMESPACE" \
            --policies.1.comparison_operator="$OPERATOR" \
            --policies.1.value="$THRESHOLD" \
            --policies.1.period="$(($PERIOD * 60))" \
            --policies.1.count="$COUNT" \
            --policies.1.unit="%" \
            --policies.1.filter="average" \
            --policies.1.level=2 \
            "${NOTIF_ARGS[@]}" \
            2>&1)

        if echo "$api_result" | grep -q "NETWORK_ERROR"; then
            echo "✗ Failed to create alarm rule" >&2
            echo "  API response: $api_result" >&2
        elif echo "$api_result" | grep -qE '"error_code"|"error_msg"|"error"|"code"[[:space:]]*:[[:space:]]*"' 2>/dev/null; then
            echo "✗ Failed to create alarm rule" >&2
            echo "  API response: $api_result" >&2
        else
            echo "✓ Alarm rule created successfully" >&2
            # Post-create verification: confirm the SMN notification was actually bound.
            # The API may report success while notification_enabled stays false, which would
            # silently leave the alarm without any notification — surface this instead of
            # pretending the notification is configured.
            if [[ -n "$SMN_TOPIC_URN" ]]; then
                local alarm_id_from_api
                alarm_id_from_api=$(echo "$api_result" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if not isinstance(d, dict):
        print('')
    else:
        print(d.get('alarm_id', '') or (d.get('alarms') or [{}])[0].get('alarm_id', ''))
except Exception:
    print('')
" 2>/dev/null)
                local notif_check
                notif_check=""
                if [[ -n "$alarm_id_from_api" ]]; then
                    notif_check=$(hcloud CES ListAlarmRules --cli-region="$REGION" --alarm_id="$alarm_id_from_api" 2>/dev/null)
                fi
                if echo "$notif_check" | grep -q '"notification_enabled"[[:space:]]*:[[:space:]]*true'; then
                    echo "  ✓ SMN notification confirmed enabled" >&2
                else
                    echo "  ⚠️ SMN notification could NOT be confirmed (notification_enabled may be false)." >&2
                    echo "    Alarm rule was created, but verify notification binding in the CES console." >&2
                fi
            fi
        fi
        
        echo "" >&2
    done
    
    echo "Alarm creation complete" >&2
}

main
