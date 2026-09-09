#!/usr/bin/env bash
# preflight.sh — 渲染（截图 / 封面 / 图表）前一次性「字体 + 依赖 + 工具」门禁（fail-stop）
#
# 用法:
#   bash <skill>/scripts/preflight.sh
#
# 行为:
#   - 自动检测平台（Linux / macOS / Windows-MSYS2）
#   - 依次校验 CJK/emoji 字体、fontconfig 中文映射（非 Windows）、fontconfig emoji 路由（非 Windows）、图表依赖（numpy/pillow）、必要工具
#   - 缺失项尝试就地补齐（Linux 用 yum/apt-get，macOS 用 brew，Windows 字体默认预装仅补依赖）
#   - 全部通过 → 写结构化标记文件（含 gate/platform/cjk_match 等字段）并 exit 0
#   - 任一步失败 → exit 1（调用方必须停止渲染/截图/合成，禁止继续）
# 平台: Linux（EulerOS/Debian 等）、macOS、Windows（Git Bash / MSYS2；字体自带，主要补 numpy/pillow）

set -euo pipefail

# 防 SIGPIPE 杀死脚本：shell 工具超时关闭 stdout 管道后，下一次 echo 写入触发 SIGPIPE →
# exit 141，主进程死亡 → gate 文件永远不写 → 调用方轮询标记文件徒劳（已实测浪费 180s）。
# 忽略 SIGPIPE + log()/die() 加 || true 防 set -e 在 echo 写入失败时退出。
trap '' PIPE

# ---- 标记文件路径（跨平台）----
if [[ -n "${OS:-}" && "$OS" == "Windows_NT" ]] || uname -s 2>/dev/null | grep -qiE 'MINGW|MSYS|CYGWIN'; then
  IS_WINDOWS=1
  # 与 Node 系脚本 os.tmpdir() 一致（C:\Users\<user>\AppData\Local\Temp），非 C:\tmp
  if command -v node >/dev/null 2>&1; then
    MARKER_DIR="$(node -e "process.stdout.write(require('os').tmpdir())" 2>/dev/null)"
  fi
  MARKER_DIR="${MARKER_DIR:-${TEMP:-${TMP:-C:\\Windows\\Temp}}}"
  MARKER="$MARKER_DIR/font-gate-ok"
else
  IS_WINDOWS=0
  MARKER=/tmp/font-gate-ok
fi

# 日志落盘：shell 工具超时关闭 stdout 管道后 log()/die() 输出丢失，失败排查变黑盒。
# 同时写一份到临时文件，agent 可 Read 排查（正常路径靠 gate 文件判定，不影响）。
PREFLIGHT_LOG="${MARKER%/*}/preflight.log"
: > "$PREFLIGHT_LOG" 2>/dev/null || true
log() { echo "[preflight] $*" 2>/dev/null || true; echo "[preflight] $*" >> "$PREFLIGHT_LOG" 2>/dev/null || true; }
die() { echo "[preflight] ❌ $*" 2>/dev/null || true; echo "[preflight] ❌ $*" >> "$PREFLIGHT_LOG" 2>/dev/null || true; exit 1; }

# ---- 用户优先安装原则（$HOME）：pip 加 --user，fontconfig conf 用 XDG 用户目录 ----
# 无 root 权限的 AI DevSpace / CodeArts 沙箱等环境优先写入 $HOME，避免写系统目录：
#  - pip 依赖 → --user（~/.local/lib），venv 内 --user 不可用时回退系统级
#  - fontconfig 规则 → ~/.config/fontconfig/conf.d（fontconfig 原生读取 XDG 用户目录）
_TS_SRC="https://pypi.tuna.tsinghua.edu.cn/simple"
pip_user_install() {
  # $1 = python 解释器；其余 = 包名
  # stderr 进 PREFLIGHT_LOG（不占 stdout）：补装失败原因保留在日志里供排查
  local py_bin="$1"; shift
  "$py_bin" -m pip install -q --index-url="${_TS_SRC}" --user "$@" >>"$PREFLIGHT_LOG" 2>&1 \
    && return 0
  "$py_bin" -m pip install -q --index-url="${_TS_SRC}" "$@" >>"$PREFLIGHT_LOG" 2>&1
}

# ---- 发现所有可用的 Python 3+ 解释器 ----
# 背景: 系统可能同时存在 python3 (3.9) 和 python (3.11)，site-packages 互不可见。
#       preflight 只装到一个 → agent 用另一个调用脚本时 ModuleNotFoundError。
#       方案: 发现所有 python3+ 解释器（含 PATH 内非标准命名 python3.x），依赖装到每一个，
#       gate 文件记录列表。用真实路径去重（python3 与 python 可能指向同一二进制）。
all_python_bins() {
  local bins="" seen="" cand real_path cands
  # 候选名：标准命名 + PATH 内所有 python3* / python（覆盖 python3.8/python3.13 等非固定候选名）
  cands="python3 python python3.13 python3.12 python3.11 python3.10 python3.9 python3.8"
  for cand in $cands; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
      # 按实际路径去重（python3 和 python 可能指向同一个二进制）
      real_path="$(readlink -f "$(command -v "$cand")" 2>/dev/null || command -v "$cand")"
      case " $seen " in
        *" $real_path "*) ;;           # 该二进制已收录，跳过
        *) seen="$seen $real_path"; bins="${bins:+$bins }$cand" ;;
      esac
    fi
  done
  printf '%s' "$bins"
}

# 将依赖安装到所有可用 Python 解释器（numpy/pillow/playwright）
# $1 = 主解释器（已装过，跳过）；其余解释器补装
# 返回: 真正就绪的解释器命令名列表（补装失败的解释器不列入 gate python_bins，并记录到日志）
ensure_deps_all_pythons() {
  local primary="$1" py all_bins primary_real py_real ready="" failed=""
  all_bins="$(all_python_bins)"
  log "发现 Python 解释器: ${all_bins:-$primary}"
  primary_real="$(readlink -f "$(command -v "$primary")" 2>/dev/null || command -v "$primary")"
  for py in $all_bins; do
    py_real="$(readlink -f "$(command -v "$py")" 2>/dev/null || command -v "$py")"
    # 按真实路径判断是否与主解释器同一二进制（避免命令名不同但同路径导致重复补装）
    if [ "$py_real" = "$primary_real" ]; then
      ready="${ready:+$ready }$py"
      continue
    fi
    log "为 $py 补装 numpy/pillow/playwright（避免多解释器 site-packages 不互通）..."
    if pip_user_install "$py" numpy pillow && pip_user_install "$py" playwright; then
      ready="${ready:+$ready }$py"
    else
      failed="${failed:+$failed }$py"
      log "⚠️ $py 依赖补装失败（详情见 $PREFLIGHT_LOG）——gate 不记录该解释器，后续用它调脚本可能 ModuleNotFoundError"
    fi
  done
  [[ -z "$failed" ]] || log "⚠️ 以下解释器依赖补装失败: $failed"
  printf '%s' "${ready:-$primary}"
}
resolve_fontconf_dir() {
  local user_dir="/etc/fonts/conf.d"
  if [ -n "${HOME:-}" ] && mkdir -p "$HOME/.config/fontconfig/conf.d" 2>/dev/null && [ -w "$HOME/.config/fontconfig/conf.d" ]; then
    user_dir="$HOME/.config/fontconfig/conf.d"
  fi
  printf '%s' "$user_dir"
}

# ---- 安装 Chromium（下载输出压缩：完整 \r 进度条 ~100 行 → 25/50/75/100% 里程碑）----
# 进度条原始输出形如 `|■■■■■■□□□□...| 50% of 185.7 MiB`，每行都进上下文很费 token；
# 此处把 \r 折叠后只保留 25/50/75/100% 里程碑与最终状态，同时在 <$HOME> 临时文件留全量日志供排障。
# 返回码 = playwright install 实际退出码（不受管道影响）。
playwright_install() {
  local py_bin="$1" dl_log
  dl_log="$(mktemp 2>/dev/null || echo "/tmp/playwright-install-$$.log")"
  rm -f "$dl_log"
  local rc=0
  "$py_bin" -m playwright install chromium >"$dl_log" 2>&1 || rc=$?
  # 里程碑抽取（\r → \n，取 25/50/75/100% 各一次）
  if command -v tr >/dev/null 2>&1 && command -v awk >/dev/null 2>&1; then
    tr '\r' '\n' < "$dl_log" 2>/dev/null \
      | grep -oE '[0-9]+([.][0-9]+)?%' \
      | awk 'function p(s){sub(/%/,"",s);return s+0}
             $0!="" {v=p($0);
               if (!m25 && v>=25){print "  25%"; m25=1}
               if (!m50 && v>=50){print "  50%"; m50=1}
               if (!m75 && v>=75){print "  75%"; m75=1}
               if (!m100 && v>=100){print "  100%"; m100=1}}' 2>/dev/null \
      | while IFS= read -r l; do log "  Chromium 下载进度: $l"; done || true
  fi
  rm -f "$dl_log"
  return "$rc"
}

PLATFORM="$(uname -s)"
log "启动渲染前 preflight（$PLATFORM）"

# ---- fc-match 文件路径提取（兼容 fontconfig 2.13.94 的 --format bug）----
# 背景: fontconfig 2.13.94（HCE/EulerOS arm64）上 `fc-match --format='%file' ...` 报
#       `Pattern format error: expected '{' at 2`，无法提取字体文件路径。
# 回退链: 先试 --format='%file'；失败（输出含 "Pattern format error"/为空）则
#        改用不带 --format 的 `fc-match '<pat>'`，其输出形如
#        `/path/to/NotoSansCJK-Regular.ttc: "Noto Sans CJK SC" "Regular"`，
#        用 cut -d: -f1 取路径段。
fc_match_file() {
  local pattern="$1"
  local out
  out="$(fc-match --format='%file' "$pattern" 2>/dev/null || true)"
  if [[ -n "$out" && "$out" != *"Pattern format error"* && "$out" != *"Pattern error"* && "$out" != *"expected '{'"* ]]; then
    printf '%s' "$out"
    return 0
  fi
  # 回退: 不带 --format，解析 "path: family style" 行
  out="$(fc-match "$pattern" 2>/dev/null || true)"
  if [[ -n "$out" ]]; then
    printf '%s' "$out" | cut -d: -f1
    return 0
  fi
  return 1
}

# ---- EulerOS 检测（供 Linux 分支的 playwright 系统依赖自动补装；非 Windows 才有意义）----
# 注: Huawei Cloud EulerOS 2.0 的 /etc/os-release 为 ID=hce, ID_LIKE=(空)，
#     旧 case 模式 *euler*/*centos*/*rhel*/*fedora* 不匹配 "hce" → IS_EULEROS=0 → yum 依赖块被跳过。
#     方案 A+B: case 加 *hce*，并兜底匹配 NAME 字段（防未来新发行版 ID 再变）。
IS_EULEROS=0
if [[ -f /etc/os-release ]]; then
  . /etc/os-release 2>/dev/null || true
  case "${ID:-}${ID_LIKE:-}" in
    *euler*|*hce*|*centos*|*rhel*|*fedora*) IS_EULEROS=1 ;;
  esac
  [[ "$IS_EULEROS" == "0" && "${NAME:-}" == *Euler* ]] && IS_EULEROS=1
fi

# ---- playwright 可用性（截图守卫依赖；Python 版，pip 安装）----
# 跨平台: EulerOS/yum 自动补系统依赖（Windows 自带 DLL 跳过）；pip 包 + headless shell 检查与下载统一。

ensure_playwright() {
  local py_bin="${1:-python3}"
  if [[ "$IS_EULEROS" == "1" ]] && command -v yum >/dev/null 2>&1; then
    log "检测到 EulerOS/yum，自动补齐 Chromium 系统依赖（含 GL 系列/at-spi2-core/libXfixes 等，映射表见 references/work-preparation.md）..."
    yum install -y \
      atk at-spi2-atk at-spi2-core \
      alsa-lib \
      pango nss nspr cups-libs \
      libXcomposite libXdamage libXext libXfixes libXrandr libXtst libXScrnSaver \
      mesa-libgbm mesa-libGL mesa-libEGL mesa-libGLES \
      libdrm \
      >/dev/null 2>&1 \
      || { log "⚠️ yum 安装 Chromium 系统依赖失败——请按 references/work-preparation.md 的映射表手动补齐。"; }
  fi
  # 检查 Python playwright 包
  if ! "$py_bin" -c "import playwright" >/dev/null 2>&1; then
    log "playwright 包不可用，尝试 pip 安装（优先 --user/$HOME）..."
    pip_user_install "$py_bin" playwright \
      || pip_user_install "$py_bin" playwright \
      || { log "⚠️ pip 安装 playwright 失败，按需稍后手动安装（见 SKILL.md Step 5）。"; return 1; }
  fi
  "$py_bin" -c "import playwright" >/dev/null 2>&1 || { log "⚠️ playwright 仍不可用"; return 1; }

  # 校验浏览器是否可实际启动：先试系统 Chrome（channel），再试 bundled Chromium
  local _browser_ok=0
  # 1) 先试系统 Chrome（channel: 'chrome'）—— arm64 有系统 Chrome 时跳过 ~300MB 下载
  if "$py_bin" -c "from playwright.sync_api import sync_playwright; pw=sync_playwright().start(); b=pw.chromium.launch(headless=True,channel='chrome',args=['--no-sandbox']); b.close(); pw.stop()" >/dev/null 2>&1; then
    log "✅ 复用系统 Chrome（channel），无需下载 Chromium"
    _browser_ok=1
  fi
  # 2) 再试 bundled Chromium（无 channel）
  if [[ "$_browser_ok" == "0" ]]; then
    if "$py_bin" -c "from playwright.sync_api import sync_playwright; pw=sync_playwright().start(); b=pw.chromium.launch(headless=True,args=['--no-sandbox']); b.close(); pw.stop()" >/dev/null 2>&1; then
      log "✅ Playwright bundled Chromium 可用"
      _browser_ok=1
    fi
  fi
  # 3) 均不可用 → 用国内镜像 + playwright install 下载 Chromium
  #    Playwright 自己管路径和权限，无需手动下载/解压/symlink
  if [[ "$_browser_ok" == "0" ]]; then
    log "Chromium 未就绪，开始下载（headless shell ~111MB，进度按里程碑输出）..."
    export PLAYWRIGHT_DOWNLOAD_HOST="https://cdn.npmmirror.com/binaries/playwright"
    log "使用国内镜像: $PLAYWRIGHT_DOWNLOAD_HOST"
    if playwright_install "$py_bin"; then
      log "✅ Chromium 下载完成"
    else
      log "⚠️ 国内镜像下载失败，回退官方 CDN..."
      unset PLAYWRIGHT_DOWNLOAD_HOST
      playwright_install "$py_bin" \
        || { log "⚠️ 下载失败——请手动执行: $py_bin -m playwright install chromium（或安装系统 Chrome: yum install -y google-chrome-stable / apt-get install -y chromium-browser）"; return 1; }
      log "✅ Chromium 下载完成（官方 CDN）"
    fi
  fi
  log "playwright + Chromium headless shell 可用"
  return 0
}

# ================================================================
# Windows 分支（MSYS2 / Git Bash / Cygwin）
# ================================================================
if [[ "$IS_WINDOWS" == "1" ]]; then
  # Windows 10/11 默认预装微软雅黑 + Segoe UI Emoji，字体无需安装
  log "Windows 环境：CJK + emoji 字体默认预装（微软雅黑 + Segoe UI Emoji）"

  # 仍需 python3 + numpy/pillow（图表/像素校验依赖）
  # ⚠️ Windows 上 python3 可能是 WindowsApps Store stub，必须验证可执行性
  pick_python() {
    for cand in python3 python; do
      if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
        printf '%s' "$cand"; return 0
      fi
    done
    return 1
  }
  PYTHON_BIN="$(pick_python)" || die "缺可用的 python3（Windows 需安装 Python 3.x 并加入 PATH；注意 WindowsApps 下的 python3 可能是 Store stub，用 python 替代）。下载地址: https://mirrors.huaweicloud.com/python/"

  if ! "$PYTHON_BIN" -c "import numpy, PIL" >/dev/null 2>&1; then
    log "安装 numpy/pillow ..."
    local _pip_idx="https://pypi.tuna.tsinghua.edu.cn/simple"
    "$PYTHON_BIN" -m pip install -q --index-url="$_pip_idx" numpy pillow 2>/dev/null || "$PYTHON_BIN" -m pip install -q --index-url="$_pip_idx" numpy pillow || true
  fi
  "$PYTHON_BIN" -c "import numpy, PIL" >/dev/null 2>&1 || die "numpy/pillow 仍不可用——请运行: pip install numpy pillow；若已安装仍报错，检查 python3 是否为 Windows Store stub（用 python 替代）"

  # Windows 优先复用系统 Edge/Chrome，避免下载 ~300MB Chromium
  ensure_playwright_windows() {
    local chan out
    # Python playwright 已在上方安装（pip install playwright），此处只校验浏览器启动
    for chan in msedge chrome; do
      # 捕获 stderr 并区分 playwright 初始化失败（PW_START_FAIL）与具体 channel
      # 启动失败（LAUNCH_FAIL_*），避免异常被静默吞掉导致误判 Edge 不可用而回退下载
      out="$("$PYTHON_BIN" -c "
from playwright.sync_api import sync_playwright
try:
    pw = sync_playwright().start()
except Exception as e:
    print('PW_START_FAIL:' + str(e), flush=True)
    exit(1)
try:
    b = pw.chromium.launch(headless=True, channel='$chan')
    b.close()
    pw.stop()
    print('OK_$chan', flush=True)
except Exception as e:
    print('LAUNCH_FAIL_$chan:' + str(e), flush=True)
    exit(1)
" 2>&1)" || true
      if [[ "$out" == *"OK_"* ]]; then
        log "✅ Windows 复用系统浏览器 ${chan}，无需下载 Chromium"
        return 0
      fi
      if [[ "$out" == *"PW_START_FAIL"* ]]; then
        log "⚠️ playwright 初始化失败: ${out#*PW_START_FAIL:}（尝试回退下载）"
      fi
    done
    ensure_playwright "$PYTHON_BIN"
  }
  # playwright 就绪后再写标记（避免并行 screenshot_guard 读到标记却无 playwright → ModuleNotFoundError）
  ensure_playwright_windows || die "playwright 不可用——截图/封面/图表均依赖它，请按 SKILL.md Step 5 补齐后再跑本脚本"

  # 为所有其他可用 Python 解释器补装依赖
  ALL_PY_BINS="$(ensure_deps_all_pythons "$PYTHON_BIN")"

  # 写结构化标记
  mkdir -p "$MARKER_DIR" 2>/dev/null || true
  printf 'ok=true\ngate=preflight\nplatform=windows\ncjk_match=Microsoft-YaHei(preinstalled)\nemoji=ok(preinstalled)\nfontconfig=n/a\ndeps=numpy,pillow,playwright\npython_bins=%s\nts=%s\n' "$ALL_PY_BINS" "$(date -u +%FT%TZ 2>/dev/null || date +%FT%TZ)" > "$MARKER"
  log "✅ preflight 通过（Windows），已写入 $MARKER"
  exit 0
fi

# ================================================================
# macOS 分支
# ================================================================
if [[ "$PLATFORM" == "Darwin" ]]; then
  command -v python3 >/dev/null 2>&1 || die "缺 python3（macOS 需安装: brew install python3，或从 https://mirrors.huaweicloud.com/python/ 下载）"

  # CJK 字体
  zh_fonts="$(fc-list :lang=zh 2>/dev/null || true)"
  if [[ -z "$zh_fonts" ]]; then
    log "安装 CJK 字体（brew）..."
    command -v brew >/dev/null 2>&1 || die "缺 Homebrew，请先安装: https://brew.sh"
    brew install font-noto-sans-cjk >/dev/null 2>&1 || die "安装 font-noto-sans-cjk 失败"
    fc-cache -f >/dev/null 2>&1 || true
    zh_fonts="$(fc-list :lang=zh 2>/dev/null || true)"
  fi
  [[ -n "$zh_fonts" ]] || die "CJK 字体安装后仍不可用"

  # Emoji 字体
  emoji_fonts="$(fc-list 2>/dev/null | grep -i emoji || true)"
  if [[ -z "$emoji_fonts" ]]; then
    log "安装 Emoji 字体（brew）..."
    brew install font-noto-color-emoji >/dev/null 2>&1 || die "安装 font-noto-color-emoji 失败"
    fc-cache -f >/dev/null 2>&1 || true
    emoji_fonts="$(fc-list 2>/dev/null | grep -i emoji || true)"
  fi
  [[ -n "$emoji_fonts" ]] || die "Emoji 字体不可用"
  # 字形覆盖校验（与 Linux 分支一致）
  emoji_glyph_1f600="$(fc-list :charset=1F600 2>/dev/null | grep -i emoji || true)"
  [[ -n "$emoji_glyph_1f600" ]] || die "Emoji 字体族名存在但 😀 (U+1F600) 字形未覆盖——请确认彩色 emoji 已正确安装"

  # fontconfig 中文映射
  match_file="$(fc_match_file 'sans-serif:lang=zh' || true)"
  if [[ "$match_file" == *DejaVuSans.ttf* ]]; then
    log "⚠️ fontconfig 中文映射到 DejaVu Sans（无 CJK），macOS 通常由系统字体兜底，跳过自定义 conf"
    match_file="$(fc_match_file 'sans-serif:lang=zh' || true)"
  fi
  log "fontconfig 中文 → $match_file"

  # numpy/pillow
  if ! python3 -c "import numpy, PIL" >/dev/null 2>&1; then
    log "安装 numpy/pillow ..."
    local _pip_idx="https://pypi.tuna.tsinghua.edu.cn/simple"
    pip3 install -q --index-url="$_pip_idx" numpy pillow 2>/dev/null || pip3 install -q --index-url="$_pip_idx" numpy pillow || true
  fi
  python3 -c "import numpy, PIL" >/dev/null 2>&1 || die "numpy/pillow 仍不可用"

  fc-cache -f >/dev/null 2>&1 || true
  # playwright 就绪后再写标记（避免并行 screenshot_guard 读到标记却无 playwright → ModuleNotFoundError）
  ensure_playwright python3 \
    || die "playwright 不可用——截图/封面/图表均依赖它，请按 SKILL.md Step 5 补齐后再跑本脚本"
  ALL_PY_BINS="$(ensure_deps_all_pythons python3)"
  printf 'ok=true\ngate=preflight\nplatform=macos\ncjk_match=%s\nemoji=ok\nfontconfig=ok\ndeps=numpy,pillow,playwright\npython_bins=%s\nts=%s\n' "$match_file" "$ALL_PY_BINS" "$(date -u +%FT%TZ)" > "$MARKER"
  log "✅ preflight 通过（macOS），已写入 $MARKER"
  exit 0
fi

# ================================================================
# Linux 分支（EulerOS / CentOS / Debian / Ubuntu 等）
# ================================================================
# 0) 工具
command -v fc-list >/dev/null 2>&1 || {
  log "缺 fontconfig，尝试安装..."
  if command -v yum >/dev/null 2>&1; then
    yum install -y fontconfig >/dev/null 2>&1 || die "fontconfig 缺失且无法安装"
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get install -y fontconfig >/dev/null 2>&1 || die "fontconfig 缺失且无法安装"
  else
    die "fontconfig 缺失且找不到 yum/apt-get"
  fi
}
command -v python3 >/dev/null 2>&1 || die "缺 python3（安装方式: yum install -y python3 / apt-get install -y python3，或从 https://mirrors.huaweicloud.com/python/ 下载源码编译）"

# 检测包管理器
if command -v yum >/dev/null 2>&1; then
  PKG_MGR="yum"
elif command -v apt-get >/dev/null 2>&1; then
  PKG_MGR="apt-get"
else
  PKG_MGR=""
fi

# 1) CJK 中文字体
# 注: 不能用 `fc-list | grep -q .` —— grep -q 读到首行即退出，使 fc-list 收到 SIGPIPE，
#    配合 `set -o pipefail` 会返回 141 造成误判。改为捕获全部输出再判空。
zh_fonts="$(fc-list :lang=zh 2>/dev/null || true)"
if [[ -z "$zh_fonts" ]]; then
  log "安装 CJK 字体..."
  if [[ "$PKG_MGR" == "yum" ]]; then
    yum install -y google-noto-cjk-fonts >/dev/null 2>&1 || die "安装 google-noto-cjk-fonts 失败"
    # 验证字体文件实际落盘（rpm 元数据可能存在但 .ttc 文件缺失）
    # google-noto-cjk-fonts 是元包，实际 .ttc 文件在子包 google-noto-sans-cjk-ttc-fonts /
    # google-noto-serif-cjk-ttc-fonts 中；reinstall 元包不会重装子包，需显式 reinstall 子包
    if ! ls /usr/share/fonts/google-noto-cjk/*.ttc 2>/dev/null | grep -q .; then
      log "CJK 字体包已安装但 .ttc 文件缺失，尝试 reinstall 元包 + ttc 子包..."
      yum reinstall -y google-noto-cjk-fonts \
        google-noto-sans-cjk-ttc-fonts \
        google-noto-serif-cjk-ttc-fonts >/dev/null 2>&1 || true
      fc-cache -f >/dev/null 2>&1 || true
      # 二次校验：若 ttc 子包名不同（其他发行版），尝试逐个 install
      if ! ls /usr/share/fonts/google-noto-cjk/*.ttc 2>/dev/null | grep -q .; then
        log "reinstall 后 .ttc 仍缺失，尝试单独 install ttc 子包..."
        yum install -y google-noto-sans-cjk-ttc-fonts \
          google-noto-serif-cjk-ttc-fonts >/dev/null 2>&1 || true
        fc-cache -f >/dev/null 2>&1 || true
      fi
    fi
  elif [[ "$PKG_MGR" == "apt-get" ]]; then
    apt-get install -y fonts-noto-cjk >/dev/null 2>&1 || die "安装 fonts-noto-cjk 失败"
  else
    die "找不到 yum/apt-get，无法安装 CJK 字体"
  fi
  fc-cache -f >/dev/null 2>&1 || true
  zh_fonts="$(fc-list :lang=zh 2>/dev/null || true)"
fi
[[ -n "$zh_fonts" ]] || die "CJK 字体安装后仍不可用"

# 2) Emoji 字体（彩色 NotoColorEmoji.ttf，CBDT 表）
# ⚠️ yum 包 google-noto-emoji-fonts 版本过旧（Unicode 10.0，单色/覆盖不全），
#    screenshot-guard.mjs 的 emoji 采样集含 Emoji 13.0+ 码点（如 🫡 U+1FAE1），
#    旧字体 cmap 虽有码点但 Chromium HarfBuzz 对 CBDT/CBLC 渲染不稳定 → canvas 测宽返回 tofu 宽度。
#    方案: 优先从 jsDelivr CDN 下载较新彩色版本（v2.051，1501 cmap 码位），yum 作为回退。
#    详见 scripts/download-noto-color-emoji.sh 与 noto-color-emoji-download-summary.md。
emoji_fonts="$(fc-list 2>/dev/null | grep -i 'noto color emoji' || true)"
if [[ -z "$emoji_fonts" ]]; then
  log "安装彩色 Emoji 字体（NotoColorEmoji.ttf，CBDT 彩色，Unicode 14.0+）..."
  EMOJI_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/download-noto-color-emoji.sh"
  if [[ -f "$EMOJI_SCRIPT" ]] && bash "$EMOJI_SCRIPT"; then
    : # CDN 下载成功
  else
    log "⚠️ CDN 下载失败或脚本不存在，回退 yum/apt-get（可能版本较旧）..."
    if [[ "$PKG_MGR" == "yum" ]]; then
      yum install -y google-noto-emoji-fonts >/dev/null 2>&1 || true
    elif [[ "$PKG_MGR" == "apt-get" ]]; then
      apt-get install -y fonts-noto-color-emoji >/dev/null 2>&1 || true
    fi
    fc-cache -f >/dev/null 2>&1 || true
  fi
  emoji_fonts="$(fc-list 2>/dev/null | grep -i 'noto color emoji' || true)"
  # 彩色版仍不可用则退而求其次接受任何 emoji 字体
  if [[ -z "$emoji_fonts" ]]; then
    emoji_fonts="$(fc-list 2>/dev/null | grep -i emoji || true)"
  fi
fi
[[ -n "$emoji_fonts" ]] || die "Emoji 字体不可用——请手动运行: bash <skill>/scripts/download-noto-color-emoji.sh"

# 2b) Emoji 字形覆盖校验（不只看族名存在，验证 😀 字形实际存在）
#     fc-list :charset=<hex> 返回覆盖该码点的字体列表；空 = 无字体覆盖该 emoji
emoji_glyph_1f600="$(fc-list :charset=1F600 2>/dev/null | grep -i emoji || true)"
if [[ -z "$emoji_glyph_1f600" ]]; then
  die "Emoji 字体族名存在但 😀 (U+1F600) 字形未覆盖——可能装到了符号字体或黑白精简版。请运行: bash <skill>/scripts/download-noto-color-emoji.sh"
fi
log "emoji 字形覆盖: 😀 OK"

# 2c) Emoji fontconfig 路由（仅装字体 + fc-list 校验不够；
#     fontconfig 不会自动把 emoji 码点路由到 Noto Color Emoji，
#     fc-match "sans-serif:charset=1F600" 可能返回 NotoColorEmoji（fontconfig 做
#     全链 per-codepoint 匹配），但 Chromium canvas 2D 只取链首字体，不自动
#     fall-through → 渲染豆腐块。fc-match 闸门存在假阳性，不可靠。
#     方案: 无条件写入 99-emoji-fallback.conf，将 Noto Color Emoji 以
#     mode="prepend" binding="weak" 插到 sans-serif/serif/monospace 三族链首。
#     Chromium 先试 Noto Color Emoji：emoji 码点命中 → 彩色渲染；
#     Latin/CJK 码点不在其 cmap → 跳到下一个字体（DejaVu Sans / Noto Sans CJK）。
#     binding="weak" 不覆盖主字体 metrics，文字排版不受影响。
#     注: mode="append" 不可用——Chromium 取链首 DejaVu Sans 后不 fall-through。
log "写入 99-emoji-fallback.conf（mode=prepend, binding=weak）..."
FONT_CONF_DIR="$(resolve_fontconf_dir)"
mkdir -p "$FONT_CONF_DIR"
cat > "$FONT_CONF_DIR/99-emoji-fallback.conf" <<'EMOJIEOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- Prepend Noto Color Emoji to generic families so Chromium canvas 2D
       tries it first for each codepoint. Emoji codepoints (U+1F600 etc.)
       hit Noto Color Emoji; Latin/CJK codepoints fall through to the
       next font (DejaVu Sans, Noto Sans CJK).
       binding="weak" so emoji font metrics don't override text layout metrics.
       Note: mode="append" does NOT work — Chromium canvas 2D picks the first
       matching font (DejaVu Sans) and doesn't traverse the family list
       for missing codepoints, rendering emoji as tofu. -->
  <match target="pattern">
    <test name="family"><string>sans-serif</string></test>
    <edit name="family" mode="prepend" binding="weak"><string>Noto Color Emoji</string></edit>
  </match>
  <match target="pattern">
    <test name="family"><string>serif</string></test>
    <edit name="family" mode="prepend" binding="weak"><string>Noto Color Emoji</string></edit>
  </match>
  <match target="pattern">
    <test name="family"><string>monospace</string></test>
    <edit name="family" mode="prepend" binding="weak"><string>Noto Color Emoji</string></edit>
  </match>
</fontconfig>
EMOJIEOF
fc-cache -f >/dev/null 2>&1 || true
emoji_fc_match="$(fc-match "sans-serif:charset=1F600" 2>/dev/null || true)"
log "emoji fontconfig 路由: ${emoji_fc_match}"

# 3) fontconfig 中文映射（只装字体会口口；不得命中无 CJK 的 DejaVuSans）
# 动态探测系统里真正注册的 CJK 字体族名，分别按 Sans/Serif/Mono 三类匹配，
# 写 conf 时用真实名字，避免硬编码 Noto Sans CJK SC 在无该字体的系统上失效。
# 覆盖 sans-serif/serif/monospace 三族。
detect_cjk_family() {
  # $1 = 类别关键词（如 "Sans" / "Serif" / "Mono"）
  # grep 模式加 (Sans )? 可选匹配: kind=Mono 时能匹配实际的 "Noto Sans Mono CJK SC"
  #   （旧模式 "Noto Mono CJK" 不匹配 → grep 返回 1 → set -e 静默退出）
  # 内部命令替换均加 || true: 防 grep 无匹配时 set -e + var=$(cmd) 触发静默退出
  # 优先 SC（简体）变体: fc-list 输出顺序不定，head -1 可能取到 TC/KR/JP 变体，
  #   对 lang=zh-CN 页面是错误字体选择（简体字会用繁体/韩文写法）
  local kind="$1" all sc
  all="$(fc-list :lang=zh family 2>/dev/null | head -40 | tr ',' '\n' \
    | grep -iE "Noto (Sans )?${kind} CJK|Noto(Sans)?${kind}CJK|Droid Sans ${kind}|WenQuanYi|YaHei|Heiti|PingFang|Source Han ${kind}" \
    || true)"
  sc="$(printf '%s\n' "$all" | grep -iE 'SC|Simplified' | head -1 || true)"
  printf '%s' "${sc:-$(printf '%s\n' "$all" | head -1)}"
}
cjk_sans="$(detect_cjk_family Sans || true)"
cjk_serif="$(detect_cjk_family Serif || true)"
cjk_mono="$(detect_cjk_family Mono || true)"
# Mono/Serif 类 CJK 字体少见，回退到 Sans（大多数 CJK Sans 自带等宽西文区与衬线字形）
[[ -z "$cjk_mono" ]] && cjk_mono="$cjk_sans"
[[ -z "$cjk_serif" ]] && cjk_serif="$cjk_sans"
# 全族兜底：若探测失败，用 fc-list :lang=zh 首个 family
if [[ -z "$cjk_sans" ]]; then
  cjk_sans="$(fc-list :lang=zh family 2>/dev/null | head -1 | cut -d',' -f1 || true)"
  cjk_serif="${cjk_serif:-$cjk_sans}"
  cjk_mono="${cjk_mono:-$cjk_sans}"
fi
[[ -z "$cjk_sans" ]] && die "未探测到任何 CJK 字体族名——请检查 google-noto-cjk-fonts 是否安装成功"

match_file="$(fc_match_file 'sans-serif:lang=zh' || true)"
need_conf=0
# 检测: 中文映射到了非 CJK 字体（DejaVu Sans 无 CJK；NotoColorEmoji 虽有少量 CJK 码点
# 但不是中文字体，是 emoji fontconfig prepend 的副作用——99-emoji-fallback.conf 把
# Noto Color Emoji 插到 sans-serif 链首后，fc-match 'sans-serif:lang=zh' 可能返回它）
if [[ "$match_file" == *DejaVuSans.ttf* ]]; then
  need_conf=1
elif [[ "$match_file" == *Emoji* || "$match_file" == *emoji* ]]; then
  need_conf=1
elif [[ -z "$match_file" ]]; then
  need_conf=1
fi

if [[ "$need_conf" == "1" ]]; then
  log "fontconfig 未把中文映射到 CJK 字体，写入 99-cjk-fallback.conf 三族兜底→ sans:${cjk_sans} serif:${cjk_serif} mono:${cjk_mono} ..."
  FONT_CONF_DIR="$(resolve_fontconf_dir)"
  mkdir -p "$FONT_CONF_DIR"
  cat > "$FONT_CONF_DIR/99-cjk-fallback.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="lang" compare="contains" qual="any"><string>zh</string></test>
    <test name="family" compare="contains" qual="any"><string>sans-serif</string></test>
    <edit name="family" mode="prepend" binding="strong"><string>${cjk_sans}</string></edit>
  </match>
  <match target="pattern">
    <test name="lang" compare="contains" qual="any"><string>zh</string></test>
    <test name="family" compare="contains" qual="any"><string>serif</string></test>
    <edit name="family" mode="prepend" binding="strong"><string>${cjk_serif}</string></edit>
  </match>
  <match target="pattern">
    <test name="lang" compare="contains" qual="any"><string>zh</string></test>
    <test name="family" compare="contains" qual="any"><string>monospace</string></test>
    <edit name="family" mode="prepend" binding="strong"><string>${cjk_mono}</string></edit>
  </match>
</fontconfig>
EOF
  fc-cache -f >/dev/null 2>&1 || true
  match_file="$(fc_match_file 'sans-serif:lang=zh' || true)"
fi
[[ "$match_file" == *DejaVuSans.ttf* ]] && die "fontconfig 中文仍映射到 DejaVu Sans（无 CJK）——请手动核对 99-cjk-fallback.conf 里填写的字体族名（当前探测到: sans=${cjk_sans} serif=${cjk_serif} mono=${cjk_mono}）"
[[ "$match_file" == *Emoji* || "$match_file" == *emoji* ]] && die "fontconfig 中文仍映射到 emoji 字体（${match_file}）——99-emoji-fallback.conf 的 prepend 把 Noto Color Emoji 插到 sans-serif 链首，覆盖了 CJK 路由。请检查 99-cjk-fallback.conf 是否正确写入（当前探测到: sans=${cjk_sans} serif=${cjk_serif} mono=${cjk_mono}）"
if [[ -z "$match_file" || "$match_file" == *"Pattern format error"* || "$match_file" == *"Pattern error"* || "$match_file" == *"expected '{'"* ]]; then
  die "fontconfig 中文映射异常（fc-match 输出为空或解析失败: 「${match_file}」）——请检查 fontconfig 配置与 CJK 字体族名（当前探测到: sans=${cjk_sans} serif=${cjk_serif} mono=${cjk_mono}）"
fi
log "fontconfig 中文 → $match_file"

# 4) 图表/像素校验依赖（numpy/pillow）——优先 --user/$HOME
if ! python3 -c "import numpy, PIL" >/dev/null 2>&1; then
  log "安装 numpy/pillow（优先 --user/$HOME）..."; pip_user_install python3 numpy pillow || pip_user_install python3 numpy pillow || true
fi
python3 -c "import numpy, PIL" >/dev/null 2>&1 || die "numpy/pillow 仍不可用（架构图/pixel 校验需要）"

# 5) 刷新字体缓存并清旧索引，确保新字体生效
fc-cache -f >/dev/null 2>&1 || true
rm -rf ~/.cache/fontconfig 2>/dev/null || true
rm -rf ~/.cache/matplotlib 2>/dev/null || true

# 6) playwright（截图/封面/图表均依赖；HCE/EulerOS 需手装系统依赖，见 work-preparation.md）
#    ⚠️ 必须在此处 fail-stop，而非非阻塞告警：若先写标记再装 playwright，
#    并行启动的 screenshot_guard.py 会看到 font-gate-ok 就绪标记直接调用 playwright，
#    此时依赖未装完 → ModuleNotFoundError → 回退人工补装 + 重试（实测 ~62s 浪费）。
ensure_playwright python3 \
  || die "playwright 不可用——截图/封面/图表均依赖它，请按 SKILL.md Step 5 / work-preparation.md 补齐后再跑本脚本"

# 6b) 为所有其他可用 Python 解释器补装依赖（防多解释器 site-packages 不互通）
ALL_PY_BINS="$(ensure_deps_all_pythons python3)"

# 7) 写结构化门禁标记（字体+fontconfig+依赖+playwright 全部就绪后）
printf 'ok=true\ngate=preflight\nplatform=linux\ncjk_match=%s\nemoji=ok\nfontconfig=ok\ndeps=numpy,pillow,playwright\npython_bins=%s\nts=%s\n' "$match_file" "$ALL_PY_BINS" "$(date -u +%FT%TZ)" > "$MARKER"
log "✅ preflight（字体+fontconfig+依赖+playwright）通过，已写入 $MARKER"
exit 0
