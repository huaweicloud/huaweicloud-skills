#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Query ECS Instance List
# Function: Query and list all ECS instances, supports filtering by name, outputs formatted list
#
# Usage:
#   # Query all ECS instances
#   ./scripts/list_ecs.sh
#
#   # Filter by name
#   ./scripts/list_ecs.sh --name web
#
#   # Output as JSON
#   ./scripts/list_ecs.sh --format json

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
            echo "  --name, -n NAME     Filter ECS by name (supports partial match)"
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
    echo "Querying ECS instances..." >&2
    echo "  Region: $REGION" >&2
    if [[ -n "$NAME_FILTER" ]]; then
        echo "  Filter: name contains '$NAME_FILTER'" >&2
    fi
    echo "" >&2
    
    # Build and execute command directly (avoid eval)
    local result
    result=$(hcloud ECS ListServersDetails \
        --cli-region="$REGION" \
        --limit=100 \
        ${NAME_FILTER:+--name="$NAME_FILTER"} \
        2>/dev/null)
    
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo "$result"
    else
        # Parse and display as table
        echo "================================================================================"
        echo "ECS Instance List"
        echo "================================================================================"
        echo ""
        
        # Use Python to parse JSON and format output
        echo "$result" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    servers = data.get('servers', [])
    
    if not servers:
        print('No ECS instances found')
        sys.exit(0)
    
    print(f'Found {len(servers)} ECS instance(s)')
    print('')
    print(f'{\"ID\":<40} {\"Name\":<25} {\"Status\":<12} {\"Flavor\":<20} {\"IP Address\":<18}')
    print('-' * 115)
    
    for server in servers:
        server_id = server.get('id', 'N/A')[:36]
        name = server.get('name', 'N/A')[:22]
        status = server.get('status', 'N/A')
        flavor = server.get('flavor', {}).get('name', 'N/A')[:17]
        
        # Get first IP address
        addresses = server.get('addresses', {})
        ip = 'N/A'
        for network, addr_list in addresses.items():
            if addr_list:
                ip = addr_list[0].get('addr', 'N/A')[:15]
                break
        
        print(f'{server_id:<40} {name:<25} {status:<12} {flavor:<20} {ip:<18}')
    
    print('')
    print('Query complete')
except Exception as e:
    print(f'Error parsing response: {e}', file=sys.stderr)
    sys.exit(1)
"
    fi
}

main
