#!/bin/bash
# e2e_compare.sh - CompareOptimizationbefore and afterof msprof op PerformanceData
# Usage: bash scripts/e2e_compare.sh <before_dir> <after_dir>
# Comparison ContentPackageinclude: Total time, ArithmeticUtilization, PipeUtilization, L2Cache

set -e

BEFORE_DIR="${1:?Error: before profile data dir is required}"
AFTER_DIR="${2:?Error: after profile data dir is required}"

echo "================================================================="
echo "      based on msprof op ofOperatorPerformanceOptimizationbefore and afterCompareReport"
echo "================================================================="
echo ""
echo "OptimizationpreviousDirectory: $BEFORE_DIR"
echo "OptimizationafterDirectory: $AFTER_DIR"
echo ""

# CompareTotal time
echo "--- 1. Total timeCompare ---"
if [ -f "$BEFORE_DIR/OpBasicInfo.csv" ] && [ -f "$AFTER_DIR/OpBasicInfo.csv" ]; then
    BEFORE_TIME=$(tail -1 "$BEFORE_DIR/OpBasicInfo.csv" | cut -d',' -f2)
    AFTER_TIME=$(tail -1 "$AFTER_DIR/OpBasicInfo.csv" | cut -d',' -f2)
    echo "OptimizationpreviousTotal time: $BEFORE_TIME us"
    echo "OptimizationafterTotal time: $AFTER_TIME us"
    if [ -n "$BEFORE_TIME" ] && [ -n "$AFTER_TIME" ] && [ "$BEFORE_TIME" != "0" ]; then
        SPEEDUP=$(echo "scale=2; ($BEFORE_TIME - $AFTER_TIME) / $BEFORE_TIME * 100" | bc)
        echo "addspeedcompare: ${SPEEDUP}%"
    fi
else
    echo "OpBasicInfo.csv notkeepin, jumpexceedTotal timeCompare"
fi
echo ""

# Compare ArithmeticUtilization
echo "--- 2. CalculationsingleunitutilizeuserateCompare ---"
if [ -f "$BEFORE_DIR/ArithmeticUtilization.csv" ] && [ -f "$AFTER_DIR/ArithmeticUtilization.csv" ]; then
    echo "fingerstandard                     | Optimizationprevious    | Optimizationafter    | modifyimprove"
    echo "-------------------------|-----------|-----------|------"
    
    # Readfingerstandard (jumpexceedtablehead) 
    while IFS=',' read -r METRIC BEFORE_VAL _; do
        AFTER_VAL=$(grep "^$METRIC," "$AFTER_DIR/ArithmeticUtilization.csv" | cut -d',' -f2)
        if [ -n "$AFTER_VAL" ]; then
            DIFF=$(echo "scale=2; $AFTER_VAL - $BEFORE_VAL" | bc 2>/dev/null || echo "N/A")
            printf "%-24s | %-9s | %-9s | %s\n" "$METRIC" "$BEFORE_VAL" "$AFTER_VAL" "$DIFF"
        fi
    done < <(tail -n +2 "$BEFORE_DIR/ArithmeticUtilization.csv")
else
    echo "ArithmeticUtilization.csv notkeepin, jumpexceed"
fi
echo ""

# Compare PipeUtilization
echo "--- 3. PipelinelineutilizeuserateCompare ---"
if [ -f "$BEFORE_DIR/PipeUtilization.csv" ] && [ -f "$AFTER_DIR/PipeUtilization.csv" ]; then
    echo "fingerstandard                     | Optimizationprevious    | Optimizationafter    | modifyimprove"
    echo "-------------------------|-----------|-----------|------"
    while IFS=',' read -r METRIC BEFORE_VAL _; do
        AFTER_VAL=$(grep "^$METRIC," "$AFTER_DIR/PipeUtilization.csv" | cut -d',' -f2)
        if [ -n "$AFTER_VAL" ]; then
            DIFF=$(echo "scale=2; $AFTER_VAL - $BEFORE_VAL" | bc 2>/dev/null || echo "N/A")
            printf "%-24s | %-9s | %-9s | %s\n" "$METRIC" "$BEFORE_VAL" "$AFTER_VAL" "$DIFF"
        fi
    done < <(tail -n +2 "$BEFORE_DIR/PipeUtilization.csv")
else
    echo "PipeUtilization.csv notkeepin, jumpexceed"
fi
echo ""

# Compare L2Cache
echo "--- 4. L2 Cache commandmiddlerateCompare ---"
if [ -f "$BEFORE_DIR/L2Cache.csv" ] && [ -f "$AFTER_DIR/L2Cache.csv" ]; then
    echo "fingerstandard                     | Optimizationprevious    | Optimizationafter    | modifyimprove"
    echo "-------------------------|-----------|-----------|------"
    while IFS=',' read -r METRIC BEFORE_VAL _; do
        AFTER_VAL=$(grep "^$METRIC," "$AFTER_DIR/L2Cache.csv" | cut -d',' -f2)
        if [ -n "$AFTER_VAL" ]; then
            DIFF=$(echo "scale=2; $AFTER_VAL - $BEFORE_VAL" | bc 2>/dev/null || echo "N/A")
            printf "%-24s | %-9s | %-9s | %s\n" "$METRIC" "$BEFORE_VAL" "$AFTER_VAL" "$DIFF"
        fi
    done < <(tail -n +2 "$BEFORE_DIR/L2Cache.csv")
else
    echo "L2Cache.csv notkeepin, jumpexceed"
fi
echo ""

# Compare Memory (ifresulthave) 
echo "--- 5. MemorybandwidthwidthCompare ---"
if [ -f "$BEFORE_DIR/Memory.csv" ] && [ -f "$AFTER_DIR/Memory.csv" ]; then
    echo "fingerstandard                     | Optimizationprevious    | Optimizationafter    | modifyimprove"
    echo "-------------------------|-----------|-----------|------"
    while IFS=',' read -r METRIC BEFORE_VAL _; do
        AFTER_VAL=$(grep "^$METRIC," "$AFTER_DIR/Memory.csv" | cut -d',' -f2)
        if [ -n "$AFTER_VAL" ]; then
            DIFF=$(echo "scale=2; $AFTER_VAL - $BEFORE_VAL" | bc 2>/dev/null || echo "N/A")
            printf "%-24s | %-9s | %-9s | %s\n" "$METRIC" "$BEFORE_VAL" "$AFTER_VAL" "$DIFF"
        fi
    done < <(tail -n +2 "$BEFORE_DIR/Memory.csv")
else
    echo "Memory.csv notkeepin, jumpexceed"
fi
echo ""

echo "================================================================="
echo "                      CompareReportconclusionend"
echo "================================================================="
