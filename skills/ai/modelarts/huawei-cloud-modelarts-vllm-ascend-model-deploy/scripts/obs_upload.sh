#!/bin/bash
# obsutil 上传模型权重/脚本到 OBS 辅助脚本

set -euo pipefail

OBSUTIL="${OBSUTIL:-obsutil}"
: "${OBS_AK:?需要设置 OBS_AK}"
: "${OBS_SK:?需要设置 OBS_SK}"
: "${OBS_ENDPOINT:?需要设置 OBS_ENDPOINT}"
: "${OBS_BUCKET:?需要设置 OBS_BUCKET}"

LOCAL_PATH="${1:?用法: obs_upload.sh <本地路径> <OBS目标前缀>}"
OBS_PREFIX="${2:?用法: obs_upload.sh <本地路径> <OBS目标前缀>}"

# 已配置过则跳过 config
if [ ! -f "$HOME/.obsutilconfig" ]; then
    "$OBSUTIL" config -i="$OBS_AK" -k="$OBS_SK" -e="$OBS_ENDPOINT"
fi

DEST="obs://${OBS_BUCKET}/${OBS_PREFIX}"

if [ -d "$LOCAL_PATH" ]; then
    echo "[上传] 目录 $LOCAL_PATH -> $DEST"
    "$OBSUTIL" cp "$LOCAL_PATH" "$DEST" -f -r -parallel=100 -u
else
    echo "[上传] 文件 $LOCAL_PATH -> $DEST"
    "$OBSUTIL" cp "$LOCAL_PATH" "$DEST" -f -u
fi

echo "[验证] 列出远端内容:"
"$OBSUTIL" ls "$DEST"
