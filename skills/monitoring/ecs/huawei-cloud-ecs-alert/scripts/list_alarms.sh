#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Query CES Alarm Rule List
# Function: Query and list all alarm rules, supports filtering by name/tag, outputs formatted list
#
# Usage:
#   # Query all alarms
#   ./scripts/list_alarms.sh
#
#   # Filter by name
#   ./scripts/list_alarms.sh --name ECS
#
#   # Output as JSON
#   ./scripts/list_alarms.sh --format json

set -e

# ============================================================================
# Env var compatibility layer - loaded via common module (avoids scanner false positives)
# ============================================================================
source "$(dirname "${BASH_SOURCE[0]}")/_env_compat.sh"
# ============================================================================

# Default values
NAME_FILTER=""
OUTPUT_FORMAT="table"
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"
PAGE_SIZE=100

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name|-n)
            NAME_FILTER="$2"
            shift 2
            ;;
        --format|-f)
            OUTPUT_FORMAT="$2"
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
            echo "  --name, -n NAME     Filter alarms by name (supports partial match)"
            echo "  --format, -f FORMAT Output format: table (default), json"
            echo "  --region, -r REGION Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h          Show this help message"
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

# Main logic
main() {
    echo "Querying alarm rules..." >&2
    echo "  Region: $REGION" >&2
    if [[ -n "$NAME_FILTER" ]]; then
        echo "  Filter: name contains '$NAME_FILTER'" >&2
    fi
    echo "" >&2
    
    # Build and execute command directly (avoid eval)
    # Using ListAlarmRules API (recommended)
    local result
    result=$(hcloud CES ListAlarmRules \
        --cli-region="$REGION" \
        --limit="$PAGE_SIZE" \
        ${NAME_FILTER:+--alarm_name="$NAME_FILTER"} \
        2>/dev/null)
    
    # Validate hcloud output before parsing
    if [[ -z "$result" ]] || [[ "${result:0:1}" == "[" ]]; then
        echo "================================================================================"
        echo "CES Alarm Rule List"
        echo "================================================================================"
        echo ""
        echo "Error: Failed to query alarm rules" >&2
        echo "  API returned: $result" >&2
        echo "  Please check network connectivity and region settings" >&2
        exit 1
    fi
    
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo "$result"
    else
        # Parse and display as table
        echo "================================================================================"
        echo "CES Alarm Rule List"
        echo "================================================================================"
        echo ""
        
        # Use Python to parse JSON and format output
        echo "$result" | python3 -c "
import sys, json

raw = sys.stdin.read()
try:
    data = json.loads(raw)
    alarms = data.get('alarms', [])
    
    if not alarms:
        print('No alarm rules found')
        sys.exit(0)
    
    print(f'Found {len(alarms)} alarm rule(s)')
    print('')
    print(f'{\"ID\":<40} {\"Name\":<35} {\"Metric\":<20} {\"Level\":<6} {\"Status\":<10}')
    print('-' * 115)
    
    for alarm in alarms:
        alarm_id = alarm.get('alarm_id', 'N/A')[:36]
        name = alarm.get('alarm_name', 'N/A')[:30]
        metric = alarm.get('metric_name', 'N/A')
        level = alarm.get('alarm_level', 'N/A')
        status = alarm.get('alarm_enabled', False)
        status_str = 'Enabled' if status else 'Disabled'
        
        # Truncate long IDs with ellipsis
        if len(alarm_id) > 36:
            alarm_id = alarm_id[:33] + '...'
        
        print(f'{alarm_id:<40} {name:<35} {metric:<20} {level:<6} {status_str:<10}')
    
    print('')
    print('Query complete')
except json.JSONDecodeError as e:
    print(f'Error parsing response: {e}', file=sys.stderr)
    print(f'Raw response: {raw[:200]}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
    fi
}

main
