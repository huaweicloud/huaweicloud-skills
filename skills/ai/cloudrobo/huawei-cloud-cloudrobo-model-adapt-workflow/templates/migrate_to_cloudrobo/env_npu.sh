#!/bin/bash

# =============================================================================
# NPU environment variables (critical for performance — ~15% speedup)
# =============================================================================

# Python path for plugin imports
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# NPU device selection
# Example: export ASCEND_RT_VISIBLE_DEVICES="0,1"
# Note: this is the only valid variable (not ASCEND_DEVICE_ID_LIST, etc.)

# =============================================================================
# VLM backbone path and offline mode
# Uses ${VAR:-default} syntax: keeps the externally set value (allows
# override), otherwise uses the default.
# Example: GR00T_VLM_BACKBONE_PATH=/local/path bash train.sh ... overrides
# the default path.
# =============================================================================
export GR00T_VLM_BACKBONE_PATH="${GR00T_VLM_BACKBONE_PATH:-<default VLM backbone path>}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Memory
export PYTORCH_NPU_ALLOC_CONF="expandable_segments:True"

# Performance (critical — do not remove)
export TASK_QUEUE_ENABLE=2        # pipeline optimization
export COMBINED_ENABLE=1          # operator fusion
export CPU_AFFINITY_CONF=1        # core binding
export ACLNN_CACHE_LIMIT=100000   # operator cache
export ACL_OP_INIT_MODE=0         # lazy initialization

# tcmalloc (10-20% speedup)
[[ -f /usr/lib64/libtcmalloc.so.4 ]] && export LD_PRELOAD=/usr/lib64/libtcmalloc.so.4

export MULTI_STREAM_MEMORY_REUSE=1        # multi-stream memory reuse
export HOST_CACHE_CAPACITY=20             # dynamic shape cache
export HCCL_OP_BASE_FFTS_MODE_ENABLE=TRUE # HCCL FFTS+ optimization
export ASCEND_ENHANCE_enable=1            # Ascend enhancement mode

# Logging (suppress verbose output)
export ASCEND_SLOG_PRINT_TO_STDOUT=0
export ASCEND_GLOBAL_LOG_LEVEL=3
export ASCEND_GLOBAL_EVENT_ENABLE=0

# HCCL distributed training
export HCCL_WHITELIST_DISABLE=1
export HCCL_IF_IP="${HCCL_IF_IP:-$(hostname -I | awk '{print $1}')}"
export HCCL_CONNECT_TIMEOUT=1200
export HCCL_ASYNC_ERROR_HANDLING=0       # disable watchdog to extend verification timeout
export HCCL_EXEC_TIMEOUT=9000            # HCCL execution timeout

export NPU_GRADSCALER_MIN_SCALE=1
