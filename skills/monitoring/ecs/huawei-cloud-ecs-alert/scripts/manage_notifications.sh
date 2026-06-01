#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Manage Alarm Notifications (SMN Topic Subscriptions)
# Function: Create/delete SMN subscriptions, configure alarm notification recipients
#
# Usage:
#   # Create email subscription (requires token confirmation, recommended via console)
#   ./scripts/manage_notifications.sh --action create --protocol email --endpoint user@example.com --topic-urn urn:smn:xxx
#
#   # Delete subscription
#   ./scripts/manage_notifications.sh --action delete --subscription-urn urn:smn:xxx:subscription

set -e

# Default values
ACTION=""
PROTOCOL=""
ENDPOINT=""
TOPIC_URN=""
SUBSCRIPTION_URN=""
REMARK="ECS Alarm Notification"
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --action|-a)
            ACTION="$2"
            shift 2
            ;;
        --protocol|-p)
            PROTOCOL="$2"
            shift 2
            ;;
        --endpoint|-e)
            ENDPOINT="$2"
            shift 2
            ;;
        --topic-urn)
            TOPIC_URN="$2"
            shift 2
            ;;
        --subscription-urn)
            SUBSCRIPTION_URN="$2"
            shift 2
            ;;
        --remark)
            REMARK="$2"
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
            echo "  --action, -a ACTION        Action: create, delete"
            echo "  --protocol, -p PROTOCOL    Protocol: email, sms (required for create)"
            echo "  --endpoint, -e ENDPOINT    Endpoint: email address or phone number (required for create)"
            echo "  --topic-urn URN            SMN topic URN (required for create)"
            echo "  --subscription-urn URN     SMN subscription URN (required for delete)"
            echo "  --remark TEXT              Subscription remark (optional)"
            echo "  --region, -r REGION        Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h                 Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Create email subscription"
            echo "  $0 --action create --protocol email --endpoint user@example.com --topic-urn urn:smn:cn-north-4:xxx:ECS_ALARM"
            echo ""
            echo "  # Delete subscription"
            echo "  $0 --action delete --subscription-urn urn:smn:cn-north-4:xxx:subscription-id"
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
if [[ -z "$ACTION" ]]; then
    echo "Error: --action is required (create or delete)" >&2
    exit 1
fi

# Main logic
case $ACTION in
    create)
        if [[ -z "$PROTOCOL" ]] || [[ -z "$ENDPOINT" ]] || [[ -z "$TOPIC_URN" ]]; then
            echo "Error: For create action, --protocol, --endpoint, and --topic-urn are required" >&2
            exit 1
        fi
        
        echo "Creating SMN subscription..." >&2
        echo "  Region: $REGION" >&2
        echo "  Protocol: $PROTOCOL" >&2
        echo "  Endpoint: $ENDPOINT" >&2
        echo "  Topic URN: $TOPIC_URN" >&2
        echo "  Remark: $REMARK" >&2
        echo "" >&2
        
        RESULT=$(hcloud SMN AddSubscription \
            --cli-region="$REGION" \
            --topic_urn="$TOPIC_URN" \
            --protocol="$PROTOCOL" \
            --endpoint="$ENDPOINT" \
            --remark="$REMARK" 2>&1)
        
        if echo "$RESULT" | grep -q "subscription_urn"; then
            SUBSCRIPTION_URN=$(echo "$RESULT" | grep -oP 'urn:smn:[^"]*')
            echo "✅ Subscription created successfully!" >&2
            echo "   Subscription URN: $SUBSCRIPTION_URN" >&2
            echo "" >&2
            if [[ "$PROTOCOL" == "email" ]]; then
                echo "⚠️  IMPORTANT: Please check email $ENDPOINT and click the confirmation link" >&2
                echo "   Subscription will only be active after confirmation" >&2
            fi
        else
            echo "❌ Failed to create subscription: $RESULT" >&2
            exit 1
        fi
        ;;
    
    delete)
        if [[ -z "$SUBSCRIPTION_URN" ]]; then
            echo "Error: For delete action, --subscription-urn is required" >&2
            exit 1
        fi
        
        echo "Deleting SMN subscription..." >&2
        echo "  Subscription URN: $SUBSCRIPTION_URN" >&2
        echo "  Region: $REGION" >&2
        echo "" >&2
        
        if hcloud SMN DeleteSubscription \
            --cli-region="$REGION" \
            --subscription_urn="$SUBSCRIPTION_URN" 2>&1; then
            echo "✅ Subscription deleted successfully" >&2
        else
            echo "❌ Failed to delete subscription" >&2
            exit 1
        fi
        ;;
    
    *)
        echo "Error: Unknown action '$ACTION'. Valid actions: create, delete" >&2
        exit 1
        ;;
esac

echo "Operation complete" >&2
