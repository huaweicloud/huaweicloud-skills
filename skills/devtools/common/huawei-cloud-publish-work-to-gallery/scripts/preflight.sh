#!/usr/bin/env bash
# preflight.sh — 渲染（截图 / 封面 / 图表）前一次性「字体 + 依赖 + 工具」门禁（fail-stop）
#
# 用法:
#   bash $SKILL_DIR/scripts/preflight.sh
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
# exit 141，主进程死亡 → gate 文件永远不写 → 调用方轮询标记文件徒劳。
# 忽略 SIGPIPE + log()/die() 加 || true 防 set -e 在 echo 写入失败时退出。
# 长耗时操作（yum/pip/Chromium 下载）另有硬超时（PIP_INSTALL_TIMEOUT/YUM_TIMEOUT/CHROMIUM_DL_TIMEOUT）
# + 心跳写 PREFLIGHT_LOG，避免整条 preflight 在受限网络上无限挂起（详见下方 start_heartbeat）。
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
# 全局重定向 stdout/stderr 到日志（在首次输出前生效）：
#   - 解决 shell 工具关闭输出管道后 echo/printf 报 `write error: Broken pipe` 噪声；
#   - 输出不会丢，agent 轮询 PREFLIGHT_LOG 即可读进度/失败原因（正常路径仍以 gate 标记判定）。
exec 1>>"$PREFLIGHT_LOG" 2>&1 || true
# log() 双写复用：stdout 已在上面重定向到日志，这里只 echo 一次（去掉显式 >>，避免日志双写）。
log() { echo "[preflight] $*" 2>/dev/null || true; }

# ---- 长耗时操作硬超时（秒，可用环境变量覆盖）----
# yum/pip/Chromium 下载在受限网络下可能无限挂起 → 每个操作单独设上限，超时自动 fail-fast，
# 并配心跳（start_heartbeat）让调用方能区分「卡死」与「龟速」。
PIP_INSTALL_TIMEOUT="${PIP_INSTALL_TIMEOUT:-90}"
# yum 首次冷启动需刷新仓库元数据 + 下载大包（如 google-noto-cjk-fonts ~100MB），
# 180s 在慢网/冷缓存下会误杀 → 默认放宽到 600s；单包停滞已由 --setopt=timeout=30 兜底。
YUM_TIMEOUT="${YUM_TIMEOUT:-600}"
CHROMIUM_DL_TIMEOUT="${CHROMIUM_DL_TIMEOUT:-450}"   # Chromium 下载总时长兜底（秒）
CHROMIUM_STALL_TIMEOUT="${CHROMIUM_STALL_TIMEOUT:-20}" # 连续无进度秒数 → 判卡死并换备用源
CHROMIUM_WATCH_INT="${CHROMIUM_WATCH_INT:-5}"        # 卡死看护轮询间隔（秒）
DL_PROBE_TIMEOUT="${DL_PROBE_TIMEOUT:-5}"
# Playwright 版本锁定：1.58.0 起 chromium 下载改用 Chrome-for-Testing(cft) 路径
#   builds/cft/<browserVersion>/...（含 linux-arm64），npmmirror 未同步该格式 → 404。
#   锁 ≤1.57.0 则走 revision 整数路径 builds/chromium/<rev>/chromium[-headless-shell]-<plat>.zip，
#   npmmirror（含 arm64，rev 1105~1234）均已同步，配合 PLAYWRIGHT_DOWNLOAD_HOST 可全速下载。
PLAYWRIGHT_PIN="${PLAYWRIGHT_PIN:-1.57.0}"

# ---- Playwright Chromium 下载候选源（按优先级顺序，全部参与探测，逐个尝试直到成功或全失败）----
# 优先级（2026-09-17 实测 + 用户拍板）：
#   旧主机 cdn.npmmirror.com 优先（200，~7s 可下）→ 新入口 registry.npmmirror.com（302→同存储，靠后）
#   → 官方备用 cdn.playwright.dev → 官方 azureedge（慢，最后兜底）
# 探测只做初筛/排序；实际下载失败（卡死/超时）由 network watch 检测并自动换下一源。
PLAYWRIGHT_SOURCES=(
  "https://cdn.npmmirror.com/binaries/playwright"
  "https://registry.npmmirror.com/-/binary/playwright"
  "https://cdn.playwright.dev"
  "https://playwright.azureedge.net"
)

# ---- 心跳：长耗时期间每 HEARTBEAT_INT 秒向 PREFLIGHT_LOG 写一行 ----
# 调用方轮询时读日志最新行：有「⏳ 心跳」/下载里程碑 → 龟速继续等；长时间无新行 → 卡死。
HEARTBEAT_PID=""
HEARTBEAT_INT="${HEARTBEAT_INT:-15}"
start_heartbeat() {
  [ -n "$HEARTBEAT_PID" ] && return 0
  local _beg
  _beg="$(date +%s 2>/dev/null || echo 0)"
  ( while :; do sleep "$HEARTBEAT_INT"; _now="$(date +%s 2>/dev/null || echo 0)"; echo "[preflight] ⏳ 运行中（已 $((_now-_beg))s，心跳保活）..." >> "$PREFLIGHT_LOG" 2>/dev/null || exit 0; done ) &
  HEARTBEAT_PID=$!
}
stop_heartbeat() {
  if [ -n "$HEARTBEAT_PID" ]; then
    kill "$HEARTBEAT_PID" 2>/dev/null || true
    HEARTBEAT_PID=""
  fi
}

die() { stop_heartbeat; echo "[preflight] ❌ $*" 2>/dev/null || true; exit 1; }

# ---- 用户优先安装原则（$HOME）：pip 加 --user，fontconfig conf 用 XDG 用户目录 ----
# 无 root 权限的 AI DevSpace / CodeArts 沙箱等环境优先写入 $HOME，避免写系统目录：
#  - pip 依赖 → --user（~/.local/lib），venv 内 --user 不可用时回退系统级
#  - fontconfig 规则 → ~/.config/fontconfig/conf.d（fontconfig 原生读取 XDG 用户目录）
_TS_SRC="https://pypi.tuna.tsinghua.edu.cn/simple"
# 缺 timeout 命令时退回不加超时（老系统尽力而为）
pip_user_install() {
  # $1 = python 解释器；其余 = 包名
  # stderr 进 PREFLIGHT_LOG（不占 stdout）：补装失败原因保留在日志里供排查
  # 每次安装由 timeout 限时（PIP_INSTALL_TIMEOUT），防止 pip 在慢源上无限挂起
  local py_bin="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$PIP_INSTALL_TIMEOUT" "$py_bin" -m pip install -q --index-url="${_TS_SRC}" --user "$@" >>"$PREFLIGHT_LOG" 2>&1 \
      && return 0
    timeout "$PIP_INSTALL_TIMEOUT" "$py_bin" -m pip install -q --index-url="${_TS_SRC}" "$@" >>"$PREFLIGHT_LOG" 2>&1
  else
    "$py_bin" -m pip install -q --index-url="${_TS_SRC}" --user "$@" >>"$PREFLIGHT_LOG" 2>&1 \
      && return 0
    "$py_bin" -m pip install -q --index-url="${_TS_SRC}" "$@" >>"$PREFLIGHT_LOG" 2>&1
  fi
}

# 带超时的 yum（防网络挂起）：--setopt=timeout=30 防单包下载停滞，timeout 给整条命令兜底上限。
# 首次冷启动（刷新仓库元数据 + 下载大包如 ~100MB 字体）可能超过 YUM_TIMEOUT → 失败自动重试一次
# （yum 复用已热元数据/缓存，第二次显著更快）。输出写入 PREFLIGHT_LOG 保留失败原因供排障。
yum_install() {
  local _attempt
  yum_speed_gate
  for _attempt in 1 2; do
    if command -v timeout >/dev/null 2>&1; then
      timeout "$YUM_TIMEOUT" yum install -y --setopt=timeout=30 ${YUM_MIRROR_ARGV[@]+"${YUM_MIRROR_ARGV[@]}"} "$@" >>"$PREFLIGHT_LOG" 2>&1 && return 0
    else
      yum install -y --setopt=timeout=30 ${YUM_MIRROR_ARGV[@]+"${YUM_MIRROR_ARGV[@]}"} "$@" >>"$PREFLIGHT_LOG" 2>&1 && return 0
    fi
    [ "$_attempt" -lt 2 ] && log "⚠️ yum install $* 失败/超时（${YUM_TIMEOUT}s），重试一次..."
  done
  return 1
}
yum_reinstall() {
  local _attempt
  yum_speed_gate
  for _attempt in 1 2; do
    if command -v timeout >/dev/null 2>&1; then
      timeout "$YUM_TIMEOUT" yum reinstall -y --setopt=timeout=30 ${YUM_MIRROR_ARGV[@]+"${YUM_MIRROR_ARGV[@]}"} "$@" >>"$PREFLIGHT_LOG" 2>&1 && return 0
    else
      yum reinstall -y --setopt=timeout=30 ${YUM_MIRROR_ARGV[@]+"${YUM_MIRROR_ARGV[@]}"} "$@" >>"$PREFLIGHT_LOG" 2>&1 && return 0
    fi
    [ "$_attempt" -lt 2 ] && log "⚠️ yum reinstall $* 失败/超时（${YUM_TIMEOUT}s），重试一次..."
  done
  return 1
}

# ---- yum 源测速 + 测速不过才切镜像（不动系统配置；YUM_MIRROR_BASEURL 为换源方案）----
# 背景: yum 走 /etc/yum.repos.d/*.repo 配置的源（系统出厂配置）；openEuler 默认官方源
#       repo.openeuler.org 国际路由可能极慢（实测 3.2KB/s，189MB 字体包无法完成）。
#       pip/Chromium 已走国内镜像（pypi.tuna / npmmirror），唯 yum 源脚本无法控制。
# 流程: ① 先对本机 yum 源做一次廉价测速；② 速度足够 → 直接用系统源；
#       ③ 速度差（慢/几乎不可用）→ 打印换源指引（stderr+日志），并尝试切镜像：
#         - 显式 YUM_MIRROR_BASEURL（镜像根，如 https://mirrors.huaweicloud.com/openeuler）→ 直接装配
#         - 未显式设置且 YUM_AUTO_MIRROR=1（默认）→ 按发行版启发式探测华为云镜像
#           （mirrors.huaweicloud.com 候选根 × 路径后缀 Range 探测命中才装配，不改任何系统文件）
#         - 镜像装配失败（显式根不可达 / 自动未探中）→ 极慢 die 快速失败并提示；偏慢提示后继续尝试系统源。
# 阈值（KB/s，可用环境变量覆盖）:
#   < YUM_SPEED_DEAD_KBPS(20)  基本不可用
#   < YUM_SPEED_SLOW_KBPS(100) 偏慢
#   >= SLOW                    正常（直接用系统源）
YUM_SPEED_DEAD_KBPS="${YUM_SPEED_DEAD_KBPS:-20}"
YUM_SPEED_SLOW_KBPS="${YUM_SPEED_SLOW_KBPS:-100}"
YUM_SPEED_PROBE_MAX="${YUM_SPEED_PROBE_MAX:-6}"    # 单 URL 测速上限（秒）
YUM_MIRROR_BASEURL="${YUM_MIRROR_BASEURL:-}"       # 换源用镜像根（不版本特化；自动拼各 repo 路径后缀）
YUM_AUTO_MIRROR="${YUM_AUTO_MIRROR:-1}"             # 速度不足时自动探测华为云镜像（0=关闭，仅提示）
YUM_AUTO_MIRROR_TIMEOUT="${YUM_AUTO_MIRROR_TIMEOUT:-4}"  # 华为云镜像单个候选根探测上限（秒，防泛洪）
HUAWEI_MIRROR_BASE="https://mirrors.huaweicloud.com"     # 华为云镜像公共根（子目录按发行版探测）
YUM_MIRROR_ARGV=()                                 # 装配好的 yum 镜像参数（--repofrompath/--disablerepo/--enablerepo）
_YUM_SPEED_DONE=0
_YUM_MIRROR_OK=0                                   # 镜像参数是否装配成功
_YUM_SPEED_MIN_KBPS=0
_YUM_SPEED_MIN_HOST=""

# 解析 /etc/yum.repos.d/*.repo 所有可用 baseurl（去注释/引号、展开 $basearch/$releasever、
# 过滤 mirrorlist 型），每行输出一个（父进程收集；改全局须在父进程侧）。
yum_baseurls() {
  local arch rel f line val
  arch="$(uname -m 2>/dev/null | tr -d '\r\n')"
  case "$arch" in
    aarch64|arm64) arch="aarch64" ;;
    *) arch="x86_64" ;;
  esac
  rel="$(grep -E '^VERSION_ID=' /etc/os-release 2>/dev/null | head -1 | cut -d= -f2- | tr -d '" ' || true)"
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    while IFS= read -r line; do
      line="${line%%#*}"
      # 注：不能用例 glob `*baseurl[[:space:]]*=*` 匹配 baseurl 行——部分 bash（如 Git for
      #     Windows/MSYS 5.x）的 case 模式下 [[:space:]] 类会失效导致永远不匹配。用 ERE 更稳。
      [[ "$line" =~ ^[[:space:]]*baseurl[[:space:]]*= ]] || continue
      val="${line#*=}"
      val="$(printf '%s' "$val" | tr -d " \t'\"")"
      val="$(printf '%s' "$val" | sed -e "s/\\\$basearch/${arch}/g" -e "s/\\\$releasever/${rel}/g" -e "s/\\\$stream//g")"
      case "$val" in
        http://*|https://*) ;;
        *) continue ;;
      esac
      case "$val" in
        *\?*) continue ;;   # mirrorlist 型 baseurl，无法拼 repomd.xml/镜像路径，跳过
      esac
      printf '%s\n' "$val"
    done < "$f"
  done < <(printf '%s\n' /etc/yum.repos.d/*.repo 2>/dev/null || true)
}

# 用 YUM_MIRROR_BASEURL 装配 yum 镜像参数（不改系统 .repo）：把每个 baseurl 的「路径后缀」
# 拼到镜像根后，经 --repofrompath 注入临时仓库，--disablerepo=* 弃用系统源、
# --enablerepo=preflight-mirror* 只从镜领取包。
# $1 = 1 → auto 模式：每个仓库后缀先 Range 探测，不可达则跳过（防单个仓库 404 拖垮整体 yum）。
build_mirror_argv() {
  local verify="${1:-0}" u s path i=0 url
  [ -n "$YUM_MIRROR_BASEURL" ] || return 0
  while IFS= read -r u; do
    s="${u#*://}"; s="${s#*/}"        # 去掉 scheme+host → /openEuler-22.03-.../x86_64/
    path="/${s}"
    if [ "$verify" == "1" ]; then
      url="${YUM_MIRROR_BASEURL%/}${path}"
      probe_url "${url}repodata/repomd.xml" "${YUM_AUTO_MIRROR_TIMEOUT:-4}" || { log "跳过镜像不可达仓库: ${url}"; continue; }
    fi
    YUM_MIRROR_ARGV+=( "--repofrompath=preflight-mirror${i},${YUM_MIRROR_BASEURL%/}${path}" )
    i=$((i+1))
  done < <(yum_baseurls)
  [ "$i" -gt 0 ] || return 0
  YUM_MIRROR_ARGV+=( "--disablerepo=*" "--enablerepo=preflight-mirror*" )
  _YUM_MIRROR_OK=1
}

# 按 os-release 发行版启发式给出华为云镜像候选子目录序（探测命中才用，非硬编码承诺）。
yum_mirror_candidates() {
  local id lc out
  id="${1:-}"
  lc="$(printf '%s' "$id" | tr '[:upper:]' '[:lower:]')"
  case "$lc" in
    *euler*)                          out="openeuler hce" ;;
    *hce*|*hceos*)                    out="hce openeuler" ;;
    *centos*|*rocky*|*alma*|*fedora*|*rhel*|*redhat*) out="centos rockylinux almalinux fedora alinux anolis" ;;
    *)                                out="" ;;
  esac
  printf '%s' "${out:-openeuler hce centos rockylinux almalinux fedora alinux}"
}

# 自动探测华为云镜像可用子目录根：取首个 baseurl 的路径后缀，按候选序逐根 Range 探测
# repodata/repomd.xml；命中返回根名（如 openeuler），全部不可达返回空。
yum_auto_mirror_root() {
  local first suffix cand
  while IFS= read -r first; do [ -n "$first" ] && break; done < <(yum_baseurls)
  [ -n "$first" ] || return 0
  suffix="${first#*://}"; suffix="${suffix#*/}"   # 保留仓库路径子串（含尾部 /）
  for cand in $(yum_mirror_candidates "${ID:-} ${NAME:-}"); do
    if probe_url "$HUAWEI_MIRROR_BASE/$cand/${suffix}repodata/repomd.xml" "${YUM_AUTO_MIRROR_TIMEOUT:-4}"; then
      printf '%s' "$cand"; return 0
    fi
  done
  return 0
}

# 对 baseurl 逐个测速（curl Range 256KB @ repodata/repomd.xml）。即使 max-time 超时，
# curl -w 仍输出实收字节与耗时 → 慢源不会被当「不可测」漏掉；只有解析/连接失败/404 才跳过。
# 汇总「最慢可达源」速度与 host。
yum_probe_speed() {
  local val u ttl sz kbps host min=0 minhost="" n=0 out
  while IFS= read -r val; do
    u="${val%/}/repodata/repomd.xml"
    out="$(curl -fsSL --connect-timeout 3 --max-time "$YUM_SPEED_PROBE_MAX" -r 0-262143 -o /dev/null -w '%{size_download} %{time_total}' "$u" 2>/dev/null || true)"
    ttl="$(printf '%s' "$out" | awk '{print $2}')"
    sz="$(printf '%s' "$out" | awk '{print $1}')"
    { [ -n "$sz" ] && [ "$sz" != "0" ]; } || continue
    kbps="$(awk -v s="$sz" -v t="${ttl:-0}" 'BEGIN{print (t>0)? int(s/t/1024) : 0}' 2>/dev/null || echo 0)"
    [ "$kbps" -le 0 ] && continue
    n=$((n+1))
    if [ "$n" -eq 1 ] || [ "$kbps" -lt "$min" ]; then
      min="$kbps"
      minhost="$(printf '%s' "$val" | sed -E 's#^[a-z]+://##; s#/.*$##' 2>/dev/null || true)"
    fi
  done < <(yum_baseurls)
  _YUM_SPEED_MIN_KBPS="${min:-0}"
  _YUM_SPEED_MIN_HOST="${minhost:-}"
}

# 换源指引（写日志 + 同步打印到 stderr 供 agent/用户直接看到；不自动改系统配置）
yum_mirror_hint() {
  local host="$1" kbps="$2" host_esc
  host_esc="$(printf '%s' "$host" | sed 's/[][.\/*^$+?{}()|]/\\&/g' 2>/dev/null || printf '%s' "$host")"
  ( echo
    echo "⚠️ yum 源速度异常（最慢源 ${host} 约 ${kbps} KB/s）——大包（如 CJK 字体 ~189MB）可能长时间无法完成。"
    echo "   preflight 会先自动尝试切华为云镜像（YUM_AUTO_MIRROR=1 默认开启；显式设置 YUM_MIRROR_BASEURL 时优先用它）。"
    echo "   镜像也不可达 / 已关闭时请手动处理（以下均不版本特化，不改系统文件）："
    echo "   ① 走镜像：重跑前 export YUM_MIRROR_BASEURL=https://mirrors.huaweicloud.com/openeuler（其它发行版换对应子目录，如 /centos）"
    echo "   ② 可逆改系统源（建议先备份）："
    echo "     cp -a /etc/yum.repos.d /etc/yum.repos.d.bak"
    echo "     sed -i 's|https\\?://${host_esc}|https://mirrors.huaweicloud.com/openeuler|g' /etc/yum.repos.d/*.repo"
    echo "     yum clean all && yum makecache"
    echo "     还原：rm -rf /etc/yum.repos.d && mv /etc/yum.repos.d.bak /etc/yum.repos.d" ) 2>/dev/null || true
}

# yum 前闸门：本进程只测速一次。流程=先测速；通过→系统源；不通过→先切镜像
# （显式 YUM_MIRROR_BASEURL 优先，否则 YUM_AUTO_MIRROR=1 自动探测华为云镜像），
# yum 命令将自动带 --repofrompath 走镜像继续；镜像均不可达→极慢 die/偏慢提示继续。
yum_speed_gate() {
  [ "$_YUM_SPEED_DONE" == "1" ] && return 0
  _YUM_SPEED_DONE=1
  command -v curl >/dev/null 2>&1 || return 0
  yum_probe_speed
  local min="${_YUM_SPEED_MIN_KBPS:-0}" host="${_YUM_SPEED_MIN_HOST:-}"
  [ "$min" -le 0 ] && return 0   # 测不出速度（不可测）→ 不拦截

  if [ "$min" -ge "$YUM_SPEED_SLOW_KBPS" ]; then
    log "yum 源测速正常（最慢 ${min} KB/s，host=${host}）"
    return 0
  fi

  # 速度不足 → 打印换源指引（stderr+日志），并尝试切镜像（显式根优先 → 自动探测华为云）
  yum_mirror_hint "$host" "$min"
  if [ -n "$YUM_MIRROR_BASEURL" ]; then
    build_mirror_argv
    if [ "$_YUM_MIRROR_OK" == "1" ]; then
      log "ℹ️ 已装配 YUM_MIRROR_BASEURL 镜像（${YUM_MIRROR_BASEURL}）→ yum 走镜像继续"
      return 0
    fi
  elif [ "$YUM_AUTO_MIRROR" == "1" ]; then
    local _root
    _root="$(yum_auto_mirror_root)"
    if [ -n "$_root" ]; then
      YUM_MIRROR_BASEURL="$HUAWEI_MIRROR_BASE/$_root"
      log "ℹ️ yum 源慢，自动切华为云镜像（${YUM_MIRROR_BASEURL}）..."
      build_mirror_argv 1
      if [ "$_YUM_MIRROR_OK" == "1" ]; then
        log "✅ 已装配华为云镜像仓库，yum 走镜像继续"
        return 0
      fi
      YUM_MIRROR_ARGV=()   # 装配失败（仓库后缀全部不可达）→ 清空回退
    fi
    log "⚠️ 华为云镜像自动探测未装配，回退手动处理..."
  fi

  if [ "$min" -lt "$YUM_SPEED_DEAD_KBPS" ]; then
    die "yum 源几乎不可用（最慢 ${min} KB/s，host=${host}，<${YUM_SPEED_DEAD_KBPS} KB/s）——自动镜像未命中，已打印换源指引：可 export YUM_MIRROR_BASEURL=<可用镜像根，如 https://mirrors.huaweicloud.com/openeuler> 后重跑（不改系统配置），或按指引改系统源。"
  fi
  log "⚠️ yum 源偏慢（最慢 ${min} KB/s，host=${host}）→ 继续尝试；如需加速可设 YUM_MIRROR_BASEURL 走镜像、开启 YUM_AUTO_MIRROR，或改系统源。"
}

# ---- 发现所有可用的 Python 3+ 解释器 ----
# 背景: 系统可能同时存在 python3 (3.9) 和 python (3.11)，site-packages 互不可见。
#       preflight 只装到一个 → agent 用另一个调用脚本时 ModuleNotFoundError。
#       方案: 发现所有 python3+ 解释器（含 PATH 内非标准命名 python3.x），依赖装到每一个，
#       gate 文件记录列表。用真实路径去重（python3 与 python 可能指向同一二进制）。
all_python_bins() {
  local bins="" seen="" cand real_path cands
  # 候选名：标准命名（覆盖 python3.8~python3.15 等常用版本号命名）
  cands="python3 python python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8"
  # 兜底扫描：PATH 内所有 python3* / python 可执行文件（不设版本上限，
  # 未来 3.16/3.20 或自定义版本号只要以 python3 开头即被收编）
  if [ "$(command -v which 2>/dev/null)" ]; then
    local _old_ifs="$IFS"
    IFS=':' read -r -a _path_dirs <<<"$PATH"
    IFS="$_old_ifs"
    for _d in "${_path_dirs[@]}"; do
      [ -n "$_d" ] && [ -d "$_d" ] || continue
      for _f in "$_d"/python3* "$_d"/python; do
        [ -x "$_f" ] && [ -f "$_f" ] || continue
        _b="$(basename "$_f")"
        case " $cands " in
          *" $_b "*) ;;  # 已列，跳过
          *) cands="$cands $_b" ;;
        esac
      done
    done
  fi
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
  # 【B】版本对齐：锁定与主解释器同版 playwright，保证各解释器共用同一 Chromium 缓存目录
  #      （Playwright 缓存 ~/.cache/ms-playwright 或 %LOCALAPPDATA%\ms-playwright 按包版本分目录）
  local pw_ver=""
  pw_ver="$("$primary" -c 'import importlib.metadata as m; print(m.version("playwright") if m.version("playwright") else "")' 2>/dev/null || true)"
  if [ -z "$pw_ver" ]; then
    pw_ver="$("$primary" -m playwright --version 2>/dev/null | sed -E 's/^[^0-9]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/' || true)"
  fi
  if [ -n "$pw_ver" ]; then log "playwright 版本对齐基准: $pw_ver（主解释器 $primary）"; fi
  for py in $all_bins; do
    py_real="$(readlink -f "$(command -v "$py")" 2>/dev/null || command -v "$py")"
    # 按真实路径判断是否与主解释器同一二进制（避免命令名不同但同路径导致重复补装）
    if [ "$py_real" = "$primary_real" ]; then
      ready="${ready:+$ready }$py"
      continue
    fi
    log "为 $py 补装 numpy/pillow/playwright（避免多解释器 site-packages 不互通）..."
    local _ok=0
    if pip_user_install "$py" numpy pillow; then
      # 主解释器有 playwright 版本 → 锁同版本；否则装 PLAYWRIGHT_PIN（默认 1.57.0，兼容 npmmirror legacy）
      if [ -n "$pw_ver" ]; then
        pip_user_install "$py" "playwright==$pw_ver" && _ok=1
      else
        pip_user_install "$py" "playwright==${PLAYWRIGHT_PIN}" && _ok=1
      fi
    fi
    if [ "$_ok" -eq 1 ]; then
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

# ---- 文件 mtime（GNU stat -c / macOS stat -f 通用）----
file_mtime() {
  if stat -c %Y "$1" >/dev/null 2>&1; then stat -c %Y "$1"
  elif stat -f %m "$1" >/dev/null 2>&1; then stat -f %m "$1"
  else echo "0"; fi
}
# ---- 文件字节数（卡死判定辅证：下载在写字节但 mtime 未更新也算有进度）----
file_size() {
  if stat -c %s "$1" >/dev/null 2>&1; then stat -c %s "$1"
  elif stat -f %z "$1" >/dev/null 2>&1; then stat -f %z "$1"
  else echo "0"; fi
}

# ---- 递归终止进程树（playwright install 会派生 node driver 子进程，需连带清理）----
killdesc() {   # TERM
  local p="$1" c
  for c in $(pgrep -P "$p" 2>/dev/null || true); do killdesc "$c"; done
  kill "$p" 2>/dev/null || true
}
killdesc9() {  # KILL
  local p="$1" c
  for c in $(pgrep -P "$p" 2>/dev/null || true); do killdesc9 "$c"; done
  kill -KILL "$p" 2>/dev/null || true
}

# ---- 安装 Chromium（仅 headless shell；卡死自动换源，日志极简）----
# 结构: 后台跑下载 + 后台“看护”子进程，父进程 wait 拿真实退出码。
#   ① --only-shell：只装 headless shell；
#   ② 看护监测 dl_log 的 mtime：下载器有进度就写日志 → mtime 变=在动；
#      连续 CHROMIUM_STALL_TIMEOUT 秒 mtime 不变=卡死 → 杀下载进程树并退出（父进程即拿非零 rc）；
#      下载正常结束 → 看护 kill -0 失败自然退出，绝不误伤成功路径（不依赖 ps，跨平台）；
#   ③ CHROMIUM_DL_TIMEOUT 作总时长兜底（防“一直有进度但永远下不完”）。
#   不输出逐 % 里程碑，省日志占用；liveness 由 start_heartbeat 心跳负责。
playwright_install() {
  local py_bin="$1" dl_log pid wd rc=0
  dl_log="$(mktemp 2>/dev/null || echo "/tmp/playwright-install-$$.log")"
  rm -f "$dl_log"
  "$py_bin" -m playwright install chromium --only-shell >"$dl_log" 2>&1 & pid=$!
  (
    local last_mt last_size now_mt now_size stalled=0 elapsed=0
    last_mt="$(file_mtime "$dl_log")"
    last_size="$(file_size "$dl_log")"
    while kill -0 "$pid" 2>/dev/null; do
      sleep "${CHROMIUM_WATCH_INT:-5}"
      elapsed=$((elapsed+CHROMIUM_WATCH_INT))
      now_mt="$(file_mtime "$dl_log")"
      now_size="$(file_size "$dl_log")"
      # 卡死判据 = mtime 与字节数都无变化：慢速下载（mtime 在动）不算卡死，
      # 反而此前只盯 mtime 会漏判「龟速但 mtime 持续变」的场景，这里双判据兜底。
      if [ "$now_mt" != "$last_mt" ] || [ "$now_size" != "$last_size" ]; then
        last_mt="$now_mt"; last_size="$now_size"; stalled=0
      else
        stalled=$((stalled+CHROMIUM_WATCH_INT))
      fi
      if [ "$stalled" -ge "${CHROMIUM_STALL_TIMEOUT:-20}" ]; then
        echo "[preflight] ⚠️ 下载疑似卡死（${stalled}s 无进度），终止并切换备用源..." >> "$PREFLIGHT_LOG" 2>/dev/null || true
        killdesc "$pid"; killdesc9 "$pid"
        exit 0
      fi
      if [ "$elapsed" -ge "${CHROMIUM_DL_TIMEOUT:-450}" ]; then
        echo "[preflight] ⚠️ 下载超时（${elapsed}s），终止并切换备用源..." >> "$PREFLIGHT_LOG" 2>/dev/null || true
        killdesc "$pid"; killdesc9 "$pid"
        exit 0
      fi
    done
  ) & wd=$!
  wait "$pid" 2>/dev/null || rc=$?
  kill "$wd" 2>/dev/null || true
  wait "$wd" 2>/dev/null || true
  rm -f "$dl_log"
  return "$rc"
}

# ---- 网络可达性探测（下载前廉价先行，避免对不可达镜像盲目下 110MB）----
# 修复（2026-09-17）：此前全量下载验证存在性——110MB 需 ~7s，5s 限时必超时（exit 28）→
# 好源被误判不可达。改用 Range 取 1KB（-r 0-1023）：5s 内必完成，206/200 即判可达；
# 同时 -L 跟随重定向（307 不再被 -f 当成功），探测结果与真实下载路径一致。
probe_url() {
  local url="$1" max_t="${2:-5}"
  if command -v curl >/dev/null 2>&1; then
    # -r 0-1023 只取首 1KB；-w %{http_code} 精确判 200/206；-L 跟随重定向
    local code
    code="$(curl -fsSL --connect-timeout "$max_t" --max-time "$max_t" -r 0-1023 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)"
    [ "$code" = "200" ] || [ "$code" = "206" ]
  elif command -v wget >/dev/null 2>&1; then
    wget -q -T "$max_t" -O /dev/null --header='Range: bytes=0-1023' "$url" >/dev/null 2>&1
  else
    return 1
  fi
}

# ---- legacy 下载路径（严格匹配 Playwright ≤1.57 revision 布局）----
# 从已装 playwright 内置 browsers.json 取 chromium(-headless-shell) 的 revision 与当前平台，
# 返回相对路径 /builds/chromium/<rev>/chromium-headless-shell-<plat>.zip，
# 供 probe_url 探测镜像是否真实存在该文件（而非 404 的 builds/browsers.json 清单）。
playwright_probe_url() {
  local py_bin="$1" plat rev
  if [[ -n "${OS:-}" && "$OS" == "Windows_NT" ]] || uname -s 2>/dev/null | grep -qiE 'MINGW|MSYS|CYGWIN'; then
    plat="win64"
  else
    case "$(uname -m 2>/dev/null)" in
      aarch64|arm64) plat="linux-arm64" ;;
      x86_64|amd64|x64) plat="linux" ;;
      *) plat="linux" ;;
    esac
  fi
  # 注意：-c 上下文没有 __file__，必须用 playwright.__file__ 定位内置 browsers.json
  rev="$("$py_bin" -c "
import json, os, playwright
p = os.path.join(os.path.dirname(playwright.__file__), 'driver', 'package', 'browsers.json')
d = json.load(open(p, encoding='utf-8'))
for b in d['browsers']:
    if b['name'] in ('chromium', 'chromium-headless-shell'):
        print(b['revision']); break
" 2>/dev/null || true)"
  [ -z "$rev" ] && rev="1200"   # 兜底：playwright==1.57.0 的 chromium revision
  printf '/builds/chromium/%s/chromium-headless-shell-%s.zip' "$rev" "$plat"
}

PLATFORM="$(uname -s)"
log "启动渲染前 preflight（$PLATFORM）"
start_heartbeat

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
    yum_install atk at-spi2-atk at-spi2-core alsa-lib pango nss nspr cups-libs \
      libXcomposite libXdamage libXext libXfixes libXrandr libXtst libXScrnSaver \
      mesa-libgbm mesa-libGL mesa-libEGL mesa-libGLES libdrm \
      || { log "⚠️ yum 安装 Chromium 系统依赖失败/超时（${YUM_TIMEOUT}s）——请按 references/work-preparation.md 的映射表手动补齐。"; }
  fi
  # 检查 Python playwright 包
  if ! "$py_bin" -c "import playwright" >/dev/null 2>&1; then
    log "playwright 包不可用，尝试 pip 安装（优先 --user/$HOME；锁定 ${PLAYWRIGHT_PIN} 以兼容 npmmirror legacy 下载布局）..."
    pip_user_install "$py_bin" "playwright==${PLAYWRIGHT_PIN}" \
      || pip_user_install "$py_bin" "playwright==${PLAYWRIGHT_PIN}" \
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
  # 3) 均不可用 → 先廉价探测各候选源，再对可达源按序 playwright install 下载
  #    Playwright 自己管路径和权限，无需手动下载/解压/symlink
  #    探测目标 = legacy 精确文件路径（playwright_probe_url），而非 builds/browsers.json（镜像多不返回该清单）
  if [[ "$_browser_ok" == "0" ]]; then
    log "Chromium 未就绪，开始下载（仅 headless shell；进度实时写 $PREFLIGHT_LOG，可据此判断卡死/龟速）..."
    local _rel _done=0 _s _host
    _rel="$(playwright_probe_url "$py_bin")"
    local _avail=()
    # 探测全部候选源（并行），收集可达源。Range 请求 5s 内必完成，不会误杀好源。
    for _s in "${PLAYWRIGHT_SOURCES[@]}"; do
      if probe_url "${_s}${_rel}" "$DL_PROBE_TIMEOUT"; then
        log "探测可达: $_s"
        _avail+=("$_s")
      else
        log "探测不可达: $_s"
      fi
    done
    if [[ "${#_avail[@]}" -gt 0 ]]; then
      # 按优先级顺序逐个尝试；下载失败/卡死（playwright_install 内部已 kill 进程并返回非 0）→ 换下一源
      for _host in "${_avail[@]}"; do
        log "使用源: $_host"
        export PLAYWRIGHT_DOWNLOAD_HOST="$_host"
        if playwright_install "$py_bin"; then
          _done=1
          log "✅ Chromium 下载完成（$_host）"
          break
        fi
        unset PLAYWRIGHT_DOWNLOAD_HOST
        log "⚠️ $_host 下载失败/卡死（≤${CHROMIUM_STALL_TIMEOUT}s 无进度即判卡死），换下一源..."
      done
      unset PLAYWRIGHT_DOWNLOAD_HOST
      if [[ "$_done" == "1" ]]; then
        : # 已达标
      else
        log "❌ 全部候选源下载失败——请手动执行: $py_bin -m playwright install chromium --only-shell，或安装系统 Chrome（yum install -y google-chrome-stable / apt-get install -y chromium-browser）。"
        return 1
      fi
    else
      log "❌ 所有候选源均在 ${DL_PROBE_TIMEOUT}s 内探测不可达（网络受限），不盲目发起 110MB 下载。手动方案：① 网络恢复后重跑 preflight；② 装系统浏览器：yum install -y chromium / google-chrome-stable；③ 手动下载 headless shell 到 PLAYWRIGHT_BROWSERS_PATH。"
      return 1
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
  stop_heartbeat
  printf 'ok=true\ngate=preflight\nplatform=windows\ncjk_match=Microsoft-YaHei(preinstalled)\nemoji=ok(preinstalled)\nfontconfig=n/a\ndeps=numpy,pillow,playwright\npython_bin=%s\npython_bins=%s\nts=%s\n' "$PYTHON_BIN" "$ALL_PY_BINS" "$(date -u +%FT%TZ 2>/dev/null || date +%FT%TZ)" > "$MARKER"
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
  stop_heartbeat
  printf 'ok=true\ngate=preflight\nplatform=macos\ncjk_match=%s\nemoji=ok\nfontconfig=ok\ndeps=numpy,pillow,playwright\npython_bin=python3\npython_bins=%s\nts=%s\n' "$match_file" "$ALL_PY_BINS" "$(date -u +%FT%TZ)" > "$MARKER"
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
    yum_install fontconfig || die "fontconfig 缺失且无法安装"
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
    yum_install google-noto-cjk-fonts || die "安装 google-noto-cjk-fonts 失败"
    # 验证字体文件实际落盘（rpm 元数据可能存在但 .ttc 文件缺失）
    # google-noto-cjk-fonts 是元包，实际 .ttc 文件在子包 google-noto-sans-cjk-ttc-fonts /
    # google-noto-serif-cjk-ttc-fonts 中；reinstall 元包不会重装子包，需显式 reinstall 子包
    if ! ls /usr/share/fonts/google-noto-cjk/*.ttc 2>/dev/null | grep -q .; then
      log "CJK 字体包已安装但 .ttc 文件缺失，尝试 reinstall 元包 + ttc 子包..."
      yum_reinstall google-noto-cjk-fonts google-noto-sans-cjk-ttc-fonts google-noto-serif-cjk-ttc-fonts || true
      fc-cache -f >/dev/null 2>&1 || true
      # 二次校验：若 ttc 子包名不同（其他发行版），尝试逐个 install
      if ! ls /usr/share/fonts/google-noto-cjk/*.ttc 2>/dev/null | grep -q .; then
        log "reinstall 后 .ttc 仍缺失，尝试单独 install ttc 子包..."
        yum_install google-noto-sans-cjk-ttc-fonts google-noto-serif-cjk-ttc-fonts || true
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
      yum_install google-noto-emoji-fonts || true
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
[[ -n "$emoji_fonts" ]] || die "Emoji 字体不可用——请手动运行: bash $SKILL_DIR/scripts/download-noto-color-emoji.sh"

# 2b) Emoji 字形覆盖校验（不只看族名存在，验证 😀 字形实际存在）
#     fc-list :charset=<hex> 返回覆盖该码点的字体列表；空 = 无字体覆盖该 emoji
emoji_glyph_1f600="$(fc-list :charset=1F600 2>/dev/null | grep -i emoji || true)"
if [[ -z "$emoji_glyph_1f600" ]]; then
  die "Emoji 字体族名存在但 😀 (U+1F600) 字形未覆盖——可能装到了符号字体或黑白精简版。请运行: bash $SKILL_DIR/scripts/download-noto-color-emoji.sh"
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
stop_heartbeat
printf 'ok=true\ngate=preflight\nplatform=linux\ncjk_match=%s\nemoji=ok\nfontconfig=ok\ndeps=numpy,pillow,playwright\npython_bin=python3\npython_bins=%s\nts=%s\n' "$match_file" "$ALL_PY_BINS" "$(date -u +%FT%TZ)" > "$MARKER"
log "✅ preflight（字体+fontconfig+依赖+playwright）通过，已写入 $MARKER"
exit 0
