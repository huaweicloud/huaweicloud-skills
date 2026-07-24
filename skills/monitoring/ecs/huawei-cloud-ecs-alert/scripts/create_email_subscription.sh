#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# SMN Email Subscription Creation Script
# Automatically uses hcloud CLI configured AK/SK, no need to set environment variables manually
#
# Usage:
#   # Interactive mode (prompts for email)
#   ./scripts/create_email_subscription.sh
#
#   # Command-line mode (non-interactive, suitable for automation)
#   ./scripts/create_email_subscription.sh --email user@example.com --topic-urn urn:smn:cn-north-4:xxx:ECS_ALARM
#
#   # With custom region and remark
#   ./scripts/create_email_subscription.sh --email user@example.com --topic-urn urn:smn:xxx --region cn-north-4 --remark "Custom Remark"
#
set -e

# ============================================================================
# Env var compatibility layer - loaded via common module (avoids scanner false positives)
# ============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_env_compat.sh"
# ============================================================================

# Default values
ENDPOINT=""
TOPIC_URN="urn:smn:cn-north-4:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx:ECS_ALARM_NOTIFY"
REMARK="ECS CPU Alarm Notification"
REGION="cn-north-4"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --email|-e)
            ENDPOINT="$2"
            shift 2
            ;;
        --topic-urn)
            TOPIC_URN="$2"
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
            echo "SMN Email Subscription Creation Script"
            echo ""
            echo "Options:"
            echo "  --email, -e EMAIL        Email address to receive alarms (required for non-interactive mode)"
            echo "  --topic-urn URN          SMN topic URN (default: urn:smn:cn-north-4:xxx:ECS_ALARM_NOTIFY)"
            echo "  --remark TEXT            Subscription remark (default: ECS CPU Alarm Notification)"
            echo "  --region, -r REGION      Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h               Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Interactive mode (prompts for email)"
            echo "  $0"
            echo ""
            echo "  # Non-interactive mode (command-line arguments)"
            echo "  $0 --email user@example.com --topic-urn urn:smn:cn-north-4:xxx:ECS_ALARM"
            echo ""
            echo "  # With custom region and remark"
            echo "  $0 --email user@example.com --topic-urn urn:smn:xxx --region cn-north-4 --remark \"Custom Remark\""
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help to see usage" >&2
            exit 1
            ;;
    esac
done

# If email is not provided, prompt for interactive input
if [ -z "$ENDPOINT" ]; then
    echo "=========================================="
    echo "SMN Email Subscription Creation"
    echo "=========================================="
    echo ""
    read -p "Please enter the email address to receive alarms: " ENDPOINT
    if [ -z "$ENDPOINT" ]; then
        echo "❌ Error: Email address cannot be empty"
        exit 1
    fi
    echo ""
fi

# Check if hcloud is available
if ! command -v hcloud &> /dev/null; then
    echo "❌ Error: hcloud command not found"
    echo "Please install Huawei Cloud CLI (KooCLI) >= 7.2.2 first"
    exit 1
fi

# Check hcloud configuration
echo "Checking hcloud configuration..."
if ! hcloud configure list &> /dev/null; then
    echo "❌ Error: hcloud credentials not configured"
    echo "Please run 'hcloud configure' to configure AK/SK first"
    exit 1
fi
echo "✅ hcloud configuration OK"
echo ""

# Create subscription
echo "Creating email subscription..."
RESULT=$(hcloud SMN AddSubscription \
    --cli-region="$REGION" \
    --topic_urn="$TOPIC_URN" \
    --protocol=email \
    --endpoint="$ENDPOINT" \
    --remark="$REMARK" 2>&1)

# Parse result
if echo "$RESULT" | grep -q "subscription_urn"; then
    SUBSCRIPTION_URN=$(echo "$RESULT" | grep -oP 'urn:smn:[^"]*')
    echo ""
    echo "✅ Subscription created successfully!"
    echo "   Subscription URN: $SUBSCRIPTION_URN"
    echo ""
    echo "⚠️  IMPORTANT: Please check email $ENDPOINT and click the confirmation link"
    echo "   Subscription will only be active after confirmation to receive alarm notifications"
    echo ""
    echo "=========================================="
    echo "Complete"
    echo "=========================================="
    exit 0
else
    echo "❌ Failed: $RESULT"
    exit 1
fi
