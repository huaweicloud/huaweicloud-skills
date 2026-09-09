#!/usr/bin/env bash
# download-noto-color-emoji.sh — 下载 Google Noto Color Emoji 彩色字体（COLRv1/SVG，Unicode 13+）
#
# 背景:
#   系统 yum 包 google-noto-emoji-fonts 版本过旧（Unicode 10.0，单色），
#   screenshot-guard.mjs 的 emoji 采样集含 Emoji 13.0+ 码点（如 🫡 U+1FAE1），
#   旧字体 cmap 虽有该码点但 Chromium HarfBuzz 对 CBDT/CBLC 渲染不稳定 → canvas 测宽返回 tofu 宽度。
#   需手动下载较新彩色版本 NotoColorEmoji.ttf。
#
# 源优先级（2026-08-31 实测）:
#   1. 华为云 npm 镜像（repo.huaweicloud.com @expo-google-fonts/noto-color-emoji@0.4.6，
#      tarball 8MB 国内直连 ~7s；内含 COLRv1 3993 + SVG 711 彩色字形，cmap 1499 码位）✅ 首选
#   2. jsDelivr CDN 主节点（cdn.jsdelivr.net gh 路径，直接 ttf 10.2MB）✅ 回退
#   （Fasly/jsDelivr npm 路径已移除——国内慢/不稳定；yum/apt 兜底由 preflight.sh 负责）
#
# 用法:
#   bash download-noto-color-emoji.sh [输出路径] [安装目录]
#   默认: 输出到 /tmp/NotoColorEmoji.ttf，安装到 $HOME/.local/share/fonts/noto-color-emoji/
#        （优先用户级安装；无 HOME 或不可写时回退系统字体目录）
#
# exit 0 = 下载+安装成功; exit 1 = 失败。

set -euo pipefail

FONT_PATH="${1:-/tmp/NotoColorEmoji.ttf}"
INSTALL_DIR="${2:-${HOME:+/$HOME/.local/share/fonts/noto-color-emoji}}"
if [ -z "${INSTALL_DIR:-}" ]; then
  INSTALL_DIR="/usr/share/fonts/noto-color-emoji"
fi

# 华为云 npm 镜像（国内可达快，tarball 需 tar 解包提取 ttf）
HUAWEI_NPM_TGZ="https://repo.huaweicloud.com/repository/npm/@expo-google-fonts/noto-color-emoji/-/noto-color-emoji-0.4.6.tgz"
HUAWEI_NPM_TTF_RELPATH="package/400Regular/NotoColorEmoji_400Regular.ttf"
HUAWEI_NPM_TMP="/tmp/noto-color-emoji-0.4.6.tgz"
HUAWEI_NPM_EXTRACT="/tmp/noto-color-emoji-extract"

# jsDelivr CDN 主节点（gh 路径直下 ttf；备用源）
JSDELIVR="https://cdn.jsdelivr.net/gh/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf"

# ---- 下载止损参数（环境变量可覆盖）----
# 总时长上限（秒）：仅作最终兜底，不再是唯一防线
HUAWEI_NPM_MAX_TIME="${HUAWEI_NPM_MAX_TIME:-30}"
JSDELIVR_MAX_TIME="${JSDELIVR_MAX_TIME:-30}"
# 建立连接超时（秒）：主机不可达/握手黑洞时快速放弃，不空等
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-8}"
# 低速止损：连续 N 秒平均速度 < 阈值(bytes/s) 即中断（防龟速耗满 max-time）
#   华为云 npm（预计 ~1.2MB/s）: 连续 5s 低于 200KB/s 视为异常
HUAWEI_NPM_SPEED_LIMIT="${HUAWEI_NPM_SPEED_LIMIT:-204800}"
HUAWEI_NPM_SPEED_TIME="${HUAWEI_NPM_SPEED_TIME:-5}"
#   jsDelivr（国内偏慢）: 连续 5s 低于 50KB/s 视为龟速，立即止损转下个源
JSDELIVR_SPEED_LIMIT="${JSDELIVR_SPEED_LIMIT:-51200}"
JSDELIVR_SPEED_TIME="${JSDELIVR_SPEED_TIME:-5}"

MIN_SIZE=5000000  # 5MB，低于此值视为不完整

log() { echo "[emoji-download] $*"; }
die() { echo "[emoji-download] ❌ $*"; exit 1; }

# curl 封装：连接超时 + 低速止损 + 总时长三重复合，龟速及时中断而非耗满。
curl_stop_loss() {
  local url="$1" out="$2" max_time="$3" speed_limit="$4" speed_time="$5"
  curl -fsSL \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$max_time" \
    --speed-limit "$speed_limit" \
    --speed-time "$speed_time" \
    -o "$out" "$url"
}

# ---- 下载（多源回退，华为云 npm 最优先）----
download() {
  # 1) 华为云 npm 镜像（tarball，需 tar 解包）
  if command -v tar >/dev/null 2>&1; then
    log "尝试华为云 npm 镜像（$HUAWEI_NPM_TGZ）..."
    if curl_stop_loss "$HUAWEI_NPM_TGZ" "$HUAWEI_NPM_TMP" "$HUAWEI_NPM_MAX_TIME" "$HUAWEI_NPM_SPEED_LIMIT" "$HUAWEI_NPM_SPEED_TIME"; then
      rm -rf "$HUAWEI_NPM_EXTRACT"
      mkdir -p "$HUAWEI_NPM_EXTRACT"
      if tar -xzf "$HUAWEI_NPM_TMP" -C "$HUAWEI_NPM_EXTRACT" 2>/dev/null; then
        local extracted
        extracted="$(find "$HUAWEI_NPM_EXTRACT" -type f -name 'NotoColorEmoji_400Regular.ttf' 2>/dev/null | head -1)"
        if [ -n "$extracted" ]; then
          cp -f "$extracted" "$FONT_PATH"
          log "✅ 华为云 npm 下载+解包成功: $FONT_PATH"
          return 0
        fi
        log "⚠️ 华为云 npm tarball 解包未找到字体文件，回退 jsDelivr..."
      else
        log "⚠️ 华为云 npm tarball 解包失败，回退 jsDelivr..."
      fi
    else
      log "⚠️ 华为云 npm 下载失败或龟速止损，回退 jsDelivr..."
    fi
  fi

  # 2) jsDelivr CDN 主节点（直接 ttf）
  log "尝试 jsDelivr CDN（主节点）..."
  if curl_stop_loss "$JSDELIVR" "$FONT_PATH" "$JSDELIVR_MAX_TIME" "$JSDELIVR_SPEED_LIMIT" "$JSDELIVR_SPEED_TIME"; then
    log "✅ jsDelivr CDN 下载成功: $FONT_PATH"
    return 0
  fi
  return 1
}

# ---- 校验文件完整性 ----
verify() {
  local size
  size=$(stat -c%s "$FONT_PATH" 2>/dev/null || stat -f%z "$FONT_PATH" 2>/dev/null || echo 0)
  if [ "$size" -lt "$MIN_SIZE" ]; then
    die "文件过小（$size bytes < $MIN_SIZE），可能不完整"
  fi
  log "文件大小: $size bytes ($(( size / 1024 / 1024 )) MB)"
  # 检查是否为 TrueType 字体（COLR/SVG 表存在即彩色字体）
  if command -v file >/dev/null 2>&1; then
    local ftype
    ftype=$(file "$FONT_PATH" 2>/dev/null || echo "unknown")
    log "文件类型: $ftype"
    case "$ftype" in
      *TrueType*|*OpenType*|*font*) : ;;  # OK
      *) die "文件非字体格式: $ftype" ;;
    esac
  fi
}

# ---- 安装到字体目录（优先用户级 $HOME，避免写系统目录）----
install_font() {
  local target_dir="$INSTALL_DIR"
  if [ ! -d "$target_dir" ] && ! mkdir -p "$target_dir" 2>/dev/null; then
    target_dir=""
  fi
  if [ -z "$target_dir" ] || [ ! -w "$target_dir" ]; then
    # 用户级不可写（如无 HOME / 只读），回退系统字体目录（优先 /usr/local，再 /usr/share）
    local sys_dir
    for sys_dir in "/usr/local/share/fonts/noto-color-emoji" "/usr/share/fonts/noto-color-emoji"; do
      mkdir -p "$sys_dir" 2>/dev/null && [ -w "$sys_dir" ] && { target_dir="$sys_dir"; break; }
    done
    if [ -n "$target_dir" ] && [ "$target_dir" != "$INSTALL_DIR" ]; then
      log "⚠️ 用户级字体目录不可写，回退系统目录: $target_dir"
    fi
  fi
  if [ -z "$target_dir" ] || [ ! -w "$target_dir" ]; then
    log "⚠️ 用户级与系统字体目录均不可写，仅保留字体文件于 $FONT_PATH"
    return 0
  fi
  cp -f "$FONT_PATH" "$target_dir/NotoColorEmoji.ttf"
  log "已安装到 $target_dir/NotoColorEmoji.ttf"
  # 刷新 fontconfig 缓存
  if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f >/dev/null 2>&1 || true
    log "fontconfig 缓存已刷新"
    # 验证 fontconfig 识别
    if fc-list 2>/dev/null | grep -qi "noto color emoji"; then
      log "✅ fontconfig 已识别 Noto Color Emoji"
    else
      log "⚠️ fontconfig 未识别（可能需手动 fc-cache -f）"
    fi
  fi
}

# ---- 主流程 ----
if download; then
  verify
  install_font
  log "✅ Noto Color Emoji 下载+安装完成"
  exit 0
else
  die "所有下载源均失败——请检查网络或手动下载: $HUAWEI_NPM_TGZ"
fi