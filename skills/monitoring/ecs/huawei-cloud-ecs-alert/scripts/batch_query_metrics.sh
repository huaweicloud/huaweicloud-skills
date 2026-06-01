#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Batch Query Monitoring Metrics
# Function: Batch query monitoring data for multiple ECS instances (CPU/memory/disk, etc.)
#
# Usage:
#   # Query CPU data for a single ECS
#   ./scripts/batch_query_metrics.sh --ecs-ids ecs-001 --metric cpu_util --period 1h
#
#   # Batch query multiple ECS instances
#   ./scripts/batch_query_metrics.sh --ecs-ids ecs-001,ecs-002,ecs-003 --metric cpu_util --period 24h --format table
#
#   # Export as JSON
#   ./scripts/batch_query_metrics.sh --ecs-ids ecs-001 --metric cpu_util --period 24h --format json > metrics.json
#

set -e

# Default values
ECS_IDS=""
METRIC=""
PERIOD="1h"
OUTPUT_FORMAT="table"
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ecs-ids|-i)
            ECS_IDS="$2"
            shift 2
            ;;
        --metric|-m)
            METRIC="$2"
            shift 2
            ;;
        --period|-p)
            PERIOD="$2"
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
            echo "  --ecs-ids, -i IDS     List of ECS instance IDs (comma-separated)"
            echo "  --metric, -m METRIC   Monitoring metric (cpu_util, memory_util, disk_util, etc.)"
            echo "  --period, -p PERIOD   Time range (1h, 24h, 7d, 30d)"
            echo "  --format, -f FORMAT   Output format: table (default), json, csv"
            echo "  --region, -r REGION   Huawei Cloud region (default: cn-north-4)"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Common metrics:"
            echo "  cpu_util      - CPU utilization (%)"
            echo "  memory_util   - Memory utilization (%) (requires Agent)"
            echo "  disk_util     - Disk utilization (%) (requires Agent)"
            echo "  net_bitRecv   - Network inbound traffic (Kbps)"
            echo "  net_bitSent   - Network outbound traffic (Kbps)"
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

if [[ -z "$METRIC" ]]; then
    echo "Error: --metric is required" >&2
    exit 1
fi

# Check if hcloud is installed
if ! command -v hcloud &> /dev/null; then
    echo "Error: hcloud command not found" >&2
    exit 1
fi

# Parse time range
parse_period() {
    local period="$1"
    local now
    now=$(date +%s)
    
    case $period in
        1h)
            echo $((now - 3600))
            ;;
        24h)
            echo $((now - 86400))
            ;;
        7d)
            echo $((now - 604800))
            ;;
        30d)
            echo $((now - 2592000))
            ;;
        *)
            # Default 1 hour
            echo $((now - 3600))
            ;;
    esac
}

# Query monitoring data
query_metric() {
    local ecs_id="$1"
    local metric="$2"
    local from_ts="$3"
    local to_ts="$4"
    local region="$5"
    
    # Convert to milliseconds
    local from_ms=$((from_ts * 1000))
    local to_ms=$((to_ts * 1000))
    
    hcloud CES ShowMetricData \
        --cli-region="$region" \
        --namespace=SYS.ECS \
        --metric_name="$metric" \
        --dim.0="instance_id,$ecs_id" \
        --period=300 \
        --filter=average \
        --from="$from_ms" \
        --to="$to_ms"
}

# Main logic
main() {
    echo "Batch querying monitoring data..." >&2
    echo "  Region: $REGION" >&2
    echo "  Metric: $METRIC" >&2
    echo "  Time range: $PERIOD" >&2
    echo "  ECS count: $(echo "$ECS_IDS" | tr ',' '\n' | wc -l)" >&2
    echo "" >&2
    
    # Calculate time range
    local to_ts
    to_ts=$(date +%s)
    local from_ts
    from_ts=$(parse_period "$PERIOD")
    
    # Store results
    declare -A results
    
    # Query monitoring data for each ECS
    IFS=',' read -ra IDS <<< "$ECS_IDS"
    for ecs_id in "${IDS[@]}"; do
        echo "Querying ECS: $ecs_id" >&2
        
        local metric_data
        metric_data=$(query_metric "$ecs_id" "$METRIC" "$from_ts" "$to_ts" "$REGION" 2>/dev/null || echo "{}")
        
        results["$ecs_id"]="$metric_data"
    done
    
    echo "" >&2
    
    # Process based on output format
    case $OUTPUT_FORMAT in
        json)
            echo "{"
            local first=true
            for ecs_id in "${!results[@]}"; do
                if [[ "$first" == true ]]; then
                    first=false
                else
                    echo ","
                fi
                echo "  \"$ecs_id\": ${results[$ecs_id]}"
            done
            echo "}"
            ;;
        csv)
            echo "ecs_id,timestamp,value"
            for ecs_id in "${!results[@]}"; do
                echo "${results[$ecs_id]}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
datapoints = data.get('datapoints', [])
for dp in datapoints:
    ts = dp.get('timestamp', '')
    val = dp.get('average', '')
    print(f'$ecs_id,{ts},{val}')
"
            done
            ;;
        table|*)
            echo "================================================================================"
            echo "Monitoring Data Query Results"
            echo "================================================================================"
            echo ""
            
            for ecs_id in "${!results[@]}"; do
                echo "ECS: $ecs_id"
                echo "${results[$ecs_id]}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
datapoints = data.get('datapoints', [])

if not datapoints:
    print('  No data available')
else:
    values = [dp.get('average', 0) for dp in datapoints]
    avg_val = sum(values) / len(values) if values else 0
    max_val = max(values) if values else 0
    min_val = min(values) if values else 0
    
    print(f'  Data points: {len(datapoints)}')
    print(f'  Average: {avg_val:.2f}')
    print(f'  Maximum: {max_val:.2f}')
    print(f'  Minimum: {min_val:.2f}')
"
                echo ""
            done
            ;;
    esac
    
    echo "Query complete" >&2
}

main
