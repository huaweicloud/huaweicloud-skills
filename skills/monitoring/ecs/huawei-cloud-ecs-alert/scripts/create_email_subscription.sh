#!/bin/bash
# SMN Email Subscription Creation Script
# Automatically uses hcloud CLI configured AK/SK, no need to set environment variables manually
#
# Usage:
#   ./scripts/create_email_subscription.sh

set -e

# Support environment variable configuration or use default placeholder values
TOPIC_URN="${SMN_TOPIC_URN:-urn:smn:cn-north-4:xxxxxxxxxxxxxxxxxxxxxxxxxxxxx:ECS_ALARM_NOTIFY}"
ENDPOINT="${ENDPOINT:-}"
REMARK="${REMARK:-ECS CPU Alarm Notification}"
REGION="${REGION:-cn-north-4}"

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
