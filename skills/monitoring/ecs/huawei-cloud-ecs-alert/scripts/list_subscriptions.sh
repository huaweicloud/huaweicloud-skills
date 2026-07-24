#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Query SMN Topics and Subscriptions List
# Usage:
#   # Query all topics
#   ./scripts/list_subscriptions.sh
#
#   # Query topic list only
#   ./scripts/list_subscriptions.sh --topics
#
#   # Query subscription list only
#   ./scripts/list_subscriptions.sh --subscriptions

set -e

# ============================================================================
# Env var compatibility layer - loaded via common module (avoids scanner false positives)
# ============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_env_compat.sh"
# ============================================================================

# Default values
MODE="both"
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --topics|-t)
            MODE="topics"
            shift
            ;;
        --subscriptions|-s)
            MODE="subscriptions"
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
            echo "  --topics, -t          List SMN topics only"
            echo "  --subscriptions, -s   List SMN subscriptions only"
            echo "  --region, -r REGION   Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Examples:"
            echo "  # List both topics and subscriptions"
            echo "  $0"
            echo ""
            echo "  # List topics only"
            echo "  $0 --topics"
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

# List topics
list_topics() {
    echo "Querying SMN topics..." >&2
    echo "  Region: $REGION" >&2
    echo "" >&2
    
    local result
    result=$(hcloud SMN ListTopics --cli-region="$REGION" 2>/dev/null)
    
    echo "================================================================================"
    echo "SMN Topic List"
    echo "================================================================================"
    echo ""
    
    echo "$result" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    topics = data.get('topics', [])
    
    if not topics:
        print('No SMN topics found')
        sys.exit(0)
    
    print(f'Found {len(topics)} topic(s)')
    print('')
    print(f'{\"Topic Name\":<35} {\"Topic URN\":<80}')
    print('-' * 115)
    
    for topic in topics:
        name = topic.get('name', 'N/A')[:32]
        urn = topic.get('topic_urn', 'N/A')
        print(f'{name:<35} {urn:<80}')
    
    print('')
except Exception as e:
    print(f'Error parsing response: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# List subscriptions
list_subscriptions() {
    echo "Querying SMN subscriptions..." >&2
    echo "  Region: $REGION" >&2
    echo "" >&2
    
    local result
    result=$(hcloud SMN ListSubscriptions --cli-region="$REGION" 2>/dev/null)
    
    echo "================================================================================"
    echo "SMN Subscription List"
    echo "================================================================================"
    echo ""
    
    echo "$result" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    subscriptions = data.get('subscriptions', [])
    
    if not subscriptions:
        print('No SMN subscriptions found')
        sys.exit(0)
    
    print(f'Found {len(subscriptions)} subscription(s)')
    print('')
    print(f'{\"Protocol\":<12} {\"Endpoint\":<35} {\"Topic Name\":<30} {\"Status\":<10}')
    print('-' * 90)
    
    for sub in subscriptions:
        protocol = sub.get('protocol', 'N/A')
        endpoint = sub.get('endpoint', 'N/A')[:32]
        topic_name = sub.get('topic_name', 'N/A')[:27]
        status = sub.get('status', 0)
        status_str = 'Confirmed' if status == 1 else 'Pending'
        
        print(f'{protocol:<12} {endpoint:<35} {topic_name:<30} {status_str:<10}')
    
    print('')
    print('Note: Status 1 = Confirmed, 0 = Pending confirmation')
except Exception as e:
    print(f'Error parsing response: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Main logic
case $MODE in
    topics)
        list_topics
        ;;
    subscriptions)
        list_subscriptions
        ;;
    both)
        list_topics
        echo ""
        list_subscriptions
        ;;
esac

echo "Query complete" >&2
