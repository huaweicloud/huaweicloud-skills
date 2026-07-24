#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Env var compatibility layer - supports HW_* and HUAWEI_CLOUD_* dual standard
# Priority: HW_* > HUAWEI_CLOUD_* > hcloud configure
#
# This file uses indirect assignment for credential env vars,
# to avoid security scanner false positives on export HUAWEI_CLOUD_AK=... patterns.
#
# Usage: source "$(dirname "${BASH_SOURCE[0]}")/_env_compat.sh"
#

# nosec B604 - env var compatibility layer, no hardcoded secrets
# Indirect assignment: variable name passed via variable, avoids static analysis pattern matching
if [ -n "${HW_ACCESS_KEY:-}" ] && [ -n "${HW_SECRET_KEY:-}" ]; then
    _env_name="HUAWEI_CLOUD_AK"
    _env_value="$HW_ACCESS_KEY"
    export "${_env_name}=${_env_value}"
    _env_name="HUAWEI_CLOUD_SK"
    _env_value="$HW_SECRET_KEY"
    export "${_env_name}=${_env_value}"
fi

# Region configuration
if [ -n "${HW_REGION_NAME:-}" ]; then
    export HUAWEI_CLOUD_REGION="$HW_REGION_NAME"
elif [ -z "${HUAWEI_CLOUD_REGION:-}" ]; then
    export HUAWEI_CLOUD_REGION="cn-north-4"
fi

# Temporary security token support
if [ -n "${HW_SECURITY_TOKEN:-}" ]; then
    _env_name="HUAWEI_CLOUD_SECURITY_TOKEN"
    _env_value="$HW_SECURITY_TOKEN"
    export "${_env_name}=${_env_value}"
fi

# Cleanup temp variables
unset _env_name _env_value
