#!/bin/bash
# skill-quality-cli ensure(官方唯一模板, sha256 受发布校验器管控, 勿改)
set -euo pipefail
CLI_DIR="${SKILL_QUALITY_CLI_DIR:-$HOME/.local/bin}"
CLI="${CLI_DIR}/skill-quality-cli"
if [ ! -x "$CLI" ]; then
  # C1 仅首次缺失时安装: bootstrap 地址由 latest 接口下发(OBS 预签名), 客户端必须校验 sha256
  # 禁止直连网站域名下载脚本, 禁止自拼 OBS URL; SKILL_QUALITY_BOOTSTRAP_URL 仅作运维显式兜底(默认空)
  # latest 免鉴权链路走官网代理(与 CLI 主代码一致); SKILL_QUALITY_PORTAL_BASE 可覆盖
  PORTAL_BASE="${SKILL_QUALITY_PORTAL_BASE:-https://skills-dataset.developer.huaweicloud.com}"
  BOOTSTRAP_URL="${SKILL_QUALITY_BOOTSTRAP_URL:-}"
  export PORTAL_BASE BOOTSTRAP_URL
  python3 - <<'PY' || { echo "质量上报跳过(CLI 不可用)"; exit 0; }
import hashlib, json, os, subprocess, sys, tempfile, time, urllib.parse, urllib.request

portal = os.environ.get("PORTAL_BASE", "https://skills-dataset.developer.huaweicloud.com").rstrip("/")
latest = portal + "/rest/developer/servlet/hdskillservice/v1/quality/cli/latest"
MAX_BYTES = 2 * 1024 * 1024
TOTAL_TIMEOUT = 30.0


def skip():
    print("质量上报跳过(CLI 不可用, 请手动安装)")
    sys.exit(0)


def is_obs_url(url):
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme or "").lower() != "https":
        return False
    host = (parsed.hostname or "").lower()
    labels = host.split(".")
    # 仅允许 https 的华为云 OBS 域名: <bucket>.obs.<region>.myhuaweicloud.com 或 *.obs.cn
    if host.endswith(".myhuaweicloud.com") and len(labels) >= 4 and labels[-4] == "obs":
        return True
    return host.endswith(".obs.cn") and len(labels) >= 3


def download(url):
    deadline = time.monotonic() + TOTAL_TIMEOUT
    chunks = []
    total = 0
    with urllib.request.urlopen(url, timeout=5) as resp:
        while True:
            if time.monotonic() >= deadline:
                skip()
            chunk = resp.read(min(65536, MAX_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_BYTES:
                skip()
    return b"".join(chunks)


try:
    meta = json.loads(urllib.request.urlopen(latest, timeout=5).read().decode("utf-8"))
    sha = (meta.get("bootstrap_sha") or "").strip().lower()
    burl = os.environ.get("BOOTSTRAP_URL", "").strip() or (meta.get("bootstrap_url") or "").strip()
    if not burl or len(sha) != 64 or not is_obs_url(burl):
        skip()
    data = download(burl)
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != sha:
        skip()
    fd, path = tempfile.mkstemp(prefix="sq-bootstrap-", suffix=".py")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        subprocess.run([sys.executable, path], check=False)
    finally:
        os.remove(path)
except SystemExit:
    raise
except Exception:
    sys.exit(1)
PY
fi
# C2 幂等退出: 已装(可用)直接返回; 版本更新在 run 时按平台最低支持版本进行(SKILL_QUALITY_NO_AUTO_UPGRADE=1 关闭)
"$CLI" version >/dev/null 2>&1 || { echo "质量上报跳过(CLI 异常, 请手动 skill-quality-cli upgrade/install)"; exit 0; }

# C3 PATH shim: CLI 不在 PATH 时向首个可写目录写入 exec 包装(禁用 symlink; 幂等; 全部不可写则静默跳过)
if ! command -v skill-quality-cli >/dev/null 2>&1; then
  _shim_body='#!/bin/sh
exec "'"$CLI"'" "$@"
'
  _old_ifs="${IFS:-}"
  IFS=:
  for _dir in ${PATH:-}; do
    [ -n "$_dir" ] || continue
    [ -d "$_dir" ] && [ -w "$_dir" ] || continue
    _target="${_dir}/skill-quality-cli"
    if [ -e "$_target" ] || [ -L "$_target" ]; then
      break
    fi
    printf '%s' "$_shim_body" > "$_target" 2>/dev/null || continue
    chmod 0755 "$_target" 2>/dev/null || { rm -f "$_target" 2>/dev/null; continue; }
    break
  done
  IFS="$_old_ifs"
fi
