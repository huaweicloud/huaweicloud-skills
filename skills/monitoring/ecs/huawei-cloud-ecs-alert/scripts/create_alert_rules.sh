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
        
        # Build hcloud command
        local cmd="hcloud CES CreateAlarm \\
            --cli-region=\"$REGION\" \\
            --alarm_name=\"$alarm_name\" \\
            --alarm_type=\"MONITOR\" \\
            --alarm_level=$LEVEL \\
            --namespace=SYS.ECS \\
            --metric_name=\"$METRIC\" \\
            --dim.0=\"instance_id,$ecs_id\" \\
            --period=$PERIOD \\
            --filter=average \\
            --condition.0.metric_name=\"$METRIC\" \\
            --condition.0.operator=\"$OPERATOR\" \\
            --condition.0.threshold=$THRESHOLD \\
            --condition.0.count=$COUNT \\
            --condition.0.unit=\"\" \\
            --alarm_enabled=true"
        
        # Add SMN notification if provided
        if [[ -n "$SMN_TOPIC_URN" ]]; then
            cmd="$cmd \\
            --ok_actions.0=\"$SMN_TOPIC_URN\" \\
            --alarm_actions.0=\"$SMN_TOPIC_URN\""
        fi
        
        # Execute command
        if eval "$cmd"; then
            echo "  ✓ Alarm created successfully" >&2
        else
            echo "  ✗ Failed to create alarm" >&2
        fi
        
        echo "" >&2
    done
    
    echo "Alarm creation complete" >&2
}

main
