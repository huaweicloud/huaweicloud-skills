#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Update Alarm Rule Notification Configuration
# Function: Add/modify/remove SMN notifications for existing alarm rules
#
# Usage:
#   # Add notification to alarm
#   ./scripts/update_alarm_notifications.sh --action add --alarm-id xxx --smn-topic-urn urn:smn:xxx
#
#   # Remove notification from alarm
#   ./scripts/update_alarm_notifications.sh --action remove --alarm-id xxx

set -e

# Default values
ACTION=""
ALARM_ID=""
SMN_TOPIC_URN=""
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --action|-a)
            ACTION="$2"
            shift 2
            ;;
        --alarm-id)
            ALARM_ID="$2"
            shift 2
            ;;
        --smn-topic-urn)
            SMN_TOPIC_URN="$2"
            shift 2
            ;;
        --region|-r)
            REGION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --action, -a ACTION    Action: add, remove"
            echo "  --alarm-id ID          Alarm rule ID (required)"
            echo "  --smn-topic-urn URN    SMN topic URN (required for add action)"
            echo "  --region, -r REGION    Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h             Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Add notification to alarm"
            echo "  $0 --action add --alarm-id alrm-xxx --smn-topic-urn urn:smn:cn-north-4:xxx:ECS_ALARM"
            echo ""
            echo "  # Remove notification from alarm"
            echo "  $0 --action remove --alarm-id alrm-xxx"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help to see usage" >&2
            exit 1
            ;;
    esac
done

# Check if hcloud is installed
if ! command -v hcloud &> /dev/null; then
    echo "Error: hcloud command not found" >&2
    exit 1
fi

# Validate parameters
if [[ -z "$ALARM_ID" ]]; then
    echo "Error: --alarm-id is required" >&2
    exit 1
fi

if [[ -z "$ACTION" ]]; then
    echo "Error: --action is required (add or remove)" >&2
    exit 1
fi

# Main logic
case $ACTION in
    add)
        if [[ -z "$SMN_TOPIC_URN" ]]; then
            echo "Error: For add action, --smn-topic-urn is required" >&2
            exit 1
        fi
        
        echo "Adding notification to alarm..." >&2
        echo "  Alarm ID: $ALARM_ID" >&2
        echo "  SMN Topic URN: $SMN_TOPIC_URN" >&2
        echo "  Region: $REGION" >&2
        echo "" >&2
        
        # Update alarm with notification
        if hcloud CES UpdateAlarm \
            --cli-region="$REGION" \
            --alarm_id="$ALARM_ID" \
            --ok_actions.0="$SMN_TOPIC_URN" \
            --alarm_actions.0="$SMN_TOPIC_URN" 2>&1; then
            echo "✅ Notification added successfully" >&2
        else
            echo "❌ Failed to add notification" >&2
            exit 1
        fi
        ;;
    
    remove)
        echo "Removing notification from alarm..." >&2
        echo "  Alarm ID: $ALARM_ID" >&2
        echo "  Region: $REGION" >&2
        echo "" >&2
        
        # Update alarm without notifications (empty arrays)
        if hcloud CES UpdateAlarm \
            --cli-region="$REGION" \
            --alarm_id="$ALARM_ID" \
            --ok_actions="" \
            --alarm_actions="" 2>&1; then
            echo "✅ Notification removed successfully" >&2
        else
            echo "❌ Failed to remove notification" >&2
            exit 1
        fi
        ;;
    
    *)
        echo "Error: Unknown action '$ACTION'. Valid actions: add, remove" >&2
        exit 1
        ;;
esac

echo "Operation complete" >&2
