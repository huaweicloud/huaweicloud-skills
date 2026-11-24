#!/usr/bin/env python3
"""
华为云资源查询 - 环境确保脚本

一键完成所有环境准备并验证可用性，执行后即可直接运行查询脚本：
  1. 校验必填凭据 HW_ACCESS_KEY/HW_SECRET_KEY、HUAWEI_ACCESS_KEY/HUAWEI_SECRET_KEY 或 AKSK=AK/SK
  2. 检查 Python 版本是否满足最低要求，不满足则给出手动安装提示
  3. 安装 Python 依赖（支持 --upgrade）
  4. 校验华为云 SDK 是否可导入
  5. 校验凭据是否有效（真正调用 IAM API）
  6. 校验项目级服务是否可用（真正调用 ECS API）

只有所有步骤都通过（包括 API 调用），才说明环境真正准备好了。
"""

import os
import sys
import json
import time
import hashlib
import subprocess
import tempfile
import argparse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))

import ssl

ssl._create_default_https_context = ssl._create_unverified_context

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except (AttributeError, ValueError):
    pass


# ── 环境检查缓存 ──────────────────────────────────────────────────────

CACHE_FILE_NAME = ".env_check_cache"
DEFAULT_CACHE_TTL = 1800  # 秒，默认 30 分钟内复用上次通过的环境检查结果
DEFAULT_FAILURE_CACHE_TTL = 300  # 秒，失败/跳过结果只缓存 5 分钟，避免重跑放大成本

# 全局：是否强制刷新缓存
FORCE_REFRESH = False


# ── 总超时预算 ────────────────────────────────────────────────────────

DEFAULT_TOTAL_TIMEOUT = 120  # 秒，重副作用步骤的整体上限

_START_TS = float(os.getenv("HW_ENV_CHECK_START_TS") or time.time())
os.environ.setdefault("HW_ENV_CHECK_START_TS", str(_START_TS))


def get_total_timeout():
    try:
        return max(1, int(float(os.getenv("HW_ENV_CHECK_TIMEOUT", DEFAULT_TOTAL_TIMEOUT))))
    except (TypeError, ValueError):
        return DEFAULT_TOTAL_TIMEOUT


def remaining_budget():
    """返回距离总超时还剩多少秒（可能为负）。"""
    return get_total_timeout() - (time.time() - _START_TS)


def step_timeout(default):
    """单步超时：不超过剩余总预算，避免分步超时突破总超时。"""
    remaining = remaining_budget()
    if remaining <= 1:
        return 1
    return max(1, int(min(default, remaining)))


def budget_exhausted(label):
    """总预算耗尽时打印可读原因并返回 True。"""
    if remaining_budget() > 0:
        return False
    print(f"\nFAIL: 环境检查总超时（{get_total_timeout()}s）已用尽，{label}未执行", flush=True)
    print("  可能原因: 依赖镜像或网络不可达", flush=True)
    print("  处理建议: 检查网络/代理后重试，或设置 HW_ENV_CHECK_TIMEOUT=<更大的秒数>", flush=True)
    return True


def _cache_path():
    return os.path.join(get_project_root(), CACHE_FILE_NAME)


def _resolved_credentials():
    """通过 config 的统一入口解析凭据（含 HUAWEI_* / AKSK 回退）。"""
    from config import resolve_credentials
    return resolve_credentials()


def _credential_fingerprint():
    """对凭据做不可逆指纹，用于判断凭据是否变更（不落盘明文）。"""
    creds = _resolved_credentials()
    raw = "|".join([
        creds["ak"],
        creds["sk"],
        creds["security_token"],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_cache_ttl():
    try:
        ttl = int(os.getenv("HW_ENV_CHECK_TTL", DEFAULT_CACHE_TTL))
    except ValueError:
        ttl = DEFAULT_CACHE_TTL
    return max(0, ttl)


def get_failure_cache_ttl():
    """失败/跳过结果使用短 TTL，避免旧失败长期掩盖配置修复。"""
    try:
        ttl = int(os.getenv("HW_ENV_CHECK_FAIL_TTL", DEFAULT_FAILURE_CACHE_TTL))
    except ValueError:
        ttl = DEFAULT_FAILURE_CACHE_TTL
    return max(0, ttl)


def _cache_miss(reason):
    """打印缓存未命中原因并返回 None（未命中不静默）。"""
    print(f"  环境检查缓存未命中: {reason}")
    return None


def _entry_ttl(cache):
    """取缓存条目写入时的 TTL，并允许当前配置把它调小。"""
    configured = get_cache_ttl()
    if configured == 0:
        return 0
    try:
        stored = int(cache.get("ttl", configured))
    except (TypeError, ValueError):
        stored = configured
    return max(0, min(stored, configured))


def read_fresh_cache(mode=None):
    """读取并校验缓存；命中返回缓存字典，否则返回 None。

    命中条件：TTL 内、模式一致、region 一致、凭据指纹一致、解释器仍存在且与写入时一致。
    缓存绑定实际解释器 ``sys.executable``，因此宿主已在 venv 中（skill 目录无
    ``.venv``）时同样可以命中。
    """
    if get_cache_ttl() == 0:
        return _cache_miss("缓存已禁用（TTL=0）")
    path = _cache_path()
    if not os.path.isfile(path):
        return _cache_miss("无缓存文件")
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        return _cache_miss("缓存文件不可读或已损坏")

    entry_mode = cache.get("mode") or "full"
    if mode and entry_mode != mode:
        return _cache_miss(f"缓存模式不一致（缓存={entry_mode}，当前={mode}）")

    ttl = _entry_ttl(cache)
    if ttl == 0:
        return _cache_miss("缓存已禁用（TTL=0）")
    checked_at = cache.get("checked_at") or 0
    if time.time() - checked_at > ttl:
        return _cache_miss(f"缓存已过期（超过 {ttl}s）")
    if cache.get("region") != _resolved_credentials()["region"]:
        return _cache_miss("region 已变化")
    if cache.get("credential_fingerprint") != _credential_fingerprint():
        return _cache_miss("凭据指纹已变化")
    cached_python = cache.get("python") or ""
    if not cached_python or not os.path.isfile(cached_python):
        return _cache_miss("缓存记录的解释器路径已失效")
    if cached_python != sys.executable:
        return _cache_miss("当前解释器与写入缓存时不一致")
    return cache


def write_cache(project_id="", mode="full", status="ok", reason="", exit_code=0, ttl=None):
    """写入环境检查结果（成功 30 分钟，失败/跳过默认 5 分钟）。"""
    if ttl is None:
        ttl = get_cache_ttl() if status == "ok" else get_failure_cache_ttl()
    cache = {
        "checked_at": time.time(),
        "mode": mode,
        "status": status,
        "reason": reason,
        "exit_code": int(exit_code),
        "ttl": int(ttl),
        "region": _resolved_credentials()["region"],
        "credential_fingerprint": _credential_fingerprint(),
        "python": sys.executable,
        "project_id": project_id or "",
    }
    try:
        with open(_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


def print_cache_hit(cache):
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache.get("checked_at", 0)))
    mode = cache.get("mode") or "full"
    status = cache.get("status") or "ok"
    ttl = _entry_ttl(cache)
    status_label = {"ok": "通过", "skip": "跳过", "fail": "未通过"}.get(status, status)
    print("=" * 50)
    print("  华为云资源查询 - 环境确保")
    print("=" * 50)
    print()
    print(f"  命中环境检查缓存（模式: {mode}，状态: {status_label}，最近一次: {checked_at}，有效期 {ttl}s）")
    if status == "ok":
        print("  跳过依赖安装与凭证/服务 API 校验")
    else:
        reason = cache.get("reason") or ""
        for line in [part.strip() for part in reason.split(";") if part.strip()]:
            print(f"  {line}")
    project_id = cache.get("project_id") or ""
    if project_id:
        os.environ["HW_PROJECT_ID"] = project_id
        project_id_file = os.path.join(get_project_root(), ".project_id")
        try:
            with open(project_id_file, "w") as f:
                f.write(project_id)
        except Exception:
            pass
        print(f"  HW_PROJECT_ID: {project_id}")
    print()
    print("  如需强制重新检查，执行 check_env.sh --force 或设置 HW_ENV_CHECK_FORCE=1")
    print("=" * 50)


# ── 虚拟环境管理 ──────────────────────────────────────────────────────

def _is_in_venv():
    """判断当前是否已在虚拟环境中"""
    return sys.prefix != sys.base_prefix


def _venv_path():
    """返回项目根目录下的 .venv 路径"""
    return os.path.join(get_project_root(), ".venv")


def _venv_python_path(venv_dir):
    """返回平台对应的 venv 解释器路径。

    Windows 上 venv 的可执行文件位于 Scripts/python.exe，
    而 POSIX 上位于 bin/python3，需按平台分支。
    """
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python3")


def _ensure_venv_and_reexec():
    """若不在 venv 中，创建 .venv 并用 venv Python 重新执行自身。

    返回 True 表示已 reexec（不会返回到调用者），
    返回 False 表示已在 venv 中，无需 reexec。
    """
    if _is_in_venv():
        return False

    venv_dir = _venv_path()
    venv_python = _venv_python_path(venv_dir)
    if not os.path.isabs(venv_python):
        venv_python = os.path.abspath(venv_python)

    # 创建 venv（如不存在）
    if not os.path.isfile(venv_python):
        if budget_exhausted("创建虚拟环境"):
            sys.exit(3)
        print("\n  PEP 668: 系统 Python 禁止直接 pip install，正在创建虚拟环境...", flush=True)
        print(f"  该步骤最长等待 {step_timeout(60)}s", flush=True)
        rc, out, err = run_cmd([sys.executable, "-m", "venv", venv_dir], timeout=step_timeout(60))
        if rc != 0:
            fail(f"创建虚拟环境失败: {err}")
            if os.name == "nt":
                print("  请手动执行: python -m venv .venv && .venv\\Scripts\\activate")
            else:
                print("  请手动执行: python3 -m venv .venv && source .venv/bin/activate")
            return False
        ok(f"虚拟环境已创建: {venv_dir}")

    # 用 venv Python 重新执行当前脚本：以子进程方式运行（输出直通终端），
    # 拿到退出码后由本进程退出，不替换当前进程镜像。
    # HW_ENV_REEXEC_GUARD 防止 venv 判定失效时反复自我调用。
    if os.getenv("HW_ENV_REEXEC_GUARD") == "1":
        return False
    print(f"  使用虚拟环境 Python: {venv_python}", flush=True)
    env = dict(os.environ, HW_ENV_REEXEC_GUARD="1", PYTHONUNBUFFERED="1")
    sys.stdout.flush()
    sys.stderr.flush()
    rc = subprocess.run(
        [venv_python, os.path.abspath(__file__)] + sys.argv[1:],
        env=env,
    ).returncode
    sys.exit(rc)

def info(msg):
    print(f"  {msg}", flush=True)


def ok(msg):
    print(f"  OK: {msg}", flush=True)


def fail(msg):
    print(f"  FAIL: {msg}", flush=True)


def get_project_id(region):
    """通过 IAM KeystoneListProjects 接口获取指定区域的项目 ID

    IAM 是全局服务，不区分 region，但项目与区域一一对应。
    查询项目列表后，按 region 名称匹配对应的项目 ID。

    :param region: 区域名称，如 cn-north-4
    :return: 项目 ID 字符串
    """
    from config import build_http_config
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkiam.v3 import IamClient
    from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
    from huaweicloudsdkiam.v3.region.iam_region import IamRegion

    creds = _resolved_credentials()
    ak = creds["ak"]
    sk = creds["sk"]
    security_token = creds["security_token"]

    try:
        http_config = build_http_config()
        http_config.timeout = (5, 10)
        http_config.retry_times = 0
        print(f"  正在通过 IAM 解析 project_id（区域: {region}，单次超时约 10s）...", flush=True)
        credentials = BasicCredentials(ak, sk)
        if security_token:
            credentials = credentials.with_security_token(security_token)
        client = (IamClient.new_builder()
                  .with_http_config(http_config)
                  .with_credentials(credentials)
                  .with_region(IamRegion.value_of(region))
                  .build())
        request = KeystoneListProjectsRequest()
        response = client.keystone_list_projects(request)
        projects = response.projects
        if not projects:
            print(f"  未找到可访问的项目 (区域: {region})", flush=True)
            return ""
        for project in projects:
            if getattr(project, 'name', '') == region:
                return project.id
        return projects[0].id
    except Exception as e:
        print(f"  获取项目 ID 失败: {e}", flush=True)
        return ""


# ── 工具函数 ──────────────────────────────────────────────────────────

def run_cmd(cmd, timeout=None, **kwargs):
    """运行命令，返回 (returncode, stdout, stderr)

    Args:
        cmd: 命令列表
        timeout: 超时秒数，超时后终止子进程并返回失败
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"命令超时（{timeout}s）: {' '.join(cmd)}"
    except FileNotFoundError:
        return -1, "", f"命令未找到: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def get_project_root():
    """获取项目根目录（scripts 的上级目录）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── 步骤 1：校验环境变量 ─────────────────────────────────────────────

def check_env_vars():
    """校验必填凭据，只报告变量名与来源，绝不输出值"""
    print("\n[1/5] 校验全局环境变量")

    creds = _resolved_credentials()
    if creds["ak"]:
        print(f" AK 已设置（来源: {creds['ak_source']}）")
    else:
        print(" AK 未设置（尝试 HW_ACCESS_KEY / HUAWEI_ACCESS_KEY / AKSK）")
    if creds["sk"]:
        print(f" SK 已设置（来源: {creds['sk_source']}）")
    else:
        print(" SK 未设置（尝试 HW_SECRET_KEY / HUAWEI_SECRET_KEY / AKSK）")

    if not (creds["ak"] and creds["sk"]):
        print("\n  必需的全局环境变量未设置，请配置 HW_ACCESS_KEY / HW_SECRET_KEY、"
              "HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY，或 AKSK=AK/SK")
        return False

    print("  全局环境变量校验通过")
    return True


# ── 步骤 2：检查并安装 Python ────────────────────────────────────────

MIN_PYTHON = (3, 6)


def print_manual_python_help():
    print()
    info("请安装 Python 3.6+ 后重试，参考：")
    print("    Windows : winget install Python.Python.3.11")
    print("    Ubuntu  : apt-get install python3 python3-pip python3-venv（以管理员身份执行）")
    print("    CentOS  : yum install python3 python3-pip（以管理员身份执行）")
    print("    Fedora  : dnf install python3 python3-pip（以管理员身份执行）")
    print("    macOS   : brew install python@3.11")


def check_python():
    """检查 Python 版本，不满足时给出各平台的手动安装提示（不自动安装系统包）"""
    print("\n[2/5] 检查 Python 版本")

    version = sys.version_info[:2]
    version_str = f"{version[0]}.{version[1]}"

    info(f"当前 Python: {version_str}")

    if version >= MIN_PYTHON:
        ok(f"Python {version_str} >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
        return True
    fail(f"Python {version_str} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    print_manual_python_help()
    return False


# ── 轻量模式（默认；无凭证也可成功退出） ─────────────────────────────

LIGHT_SKIP_CREDENTIALS = "SKIP: credentials not configured"


def check_scripts_compile():
    """编译 scripts/ 下的入口脚本，捕获语法错误（不导入、不联网）。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    py_files = sorted(
        os.path.join(script_dir, name)
        for name in os.listdir(script_dir)
        if name.endswith(".py")
    )
    print(f"  正在编译 {len(py_files)} 个脚本（本地语法检查）...", flush=True)
    rc, out, err = run_cmd(
        [sys.executable, "-m", "py_compile"] + py_files,
        timeout=step_timeout(20),
    )
    if rc == 0:
        ok("入口脚本语法检查通过")
        return True
    fail("入口脚本存在语法错误")
    detail = err or out
    if detail:
        print("  " + detail.replace("\n", "\n  ")[-600:], flush=True)
    return False


def check_sdk_light():
    """探测 SDK 是否已安装；缺失只提示跳过，不安装、不算失败。"""
    missing = []
    for mod in SDK_MODULES:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        ok(f"{len(SDK_MODULES)} 个 SDK 模块可导入")
        return True
    shown = ", ".join(missing[:3]) + (" ..." if len(missing) > 3 else "")
    print(f"  SKIP: SDK 未安装（{shown}）；--full 会安装依赖", flush=True)
    return False


def run_light_checks():
    """默认轻量入口：仅静态检查，不创建 venv、不安装依赖、不调用云 API。"""
    print("=" * 50, flush=True)
    print("  华为云资源查询 - 轻量环境检查", flush=True)
    print("  不创建 venv、不安装依赖、不调用云 API", flush=True)
    print("=" * 50, flush=True)

    print("\n[1/3] 检查 Python 版本", flush=True)
    version = sys.version_info[:2]
    version_str = f"{version[0]}.{version[1]}"
    info(f"当前 Python: {version_str}")
    if version < MIN_PYTHON:
        fail(f"Python {version_str} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
        print_manual_python_help()
        reason = f"FAIL: Python {version_str} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
        write_cache(mode="light", status="fail", reason=reason, exit_code=1)
        return 1
    ok(f"Python {version_str} >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")

    print("\n[2/3] 编译入口脚本", flush=True)
    compile_ok = check_scripts_compile()

    print("\n[3/3] 探测华为云 SDK", flush=True)
    sdk_ok = check_sdk_light()

    skips = []
    if not sdk_ok:
        skips.append("SKIP: SDK not installed")
    creds = _resolved_credentials()
    if not (creds["ak"] and creds["sk"]):
        print(f"  {LIGHT_SKIP_CREDENTIALS}", flush=True)
        skips.append(LIGHT_SKIP_CREDENTIALS)
    else:
        print(f"  AK/SK 已设置（AK 来源: {creds['ak_source']}，SK 来源: {creds['sk_source']}；"
              "轻量模式不调用 API）", flush=True)

    exit_code = 0 if compile_ok else 3
    if exit_code != 0:
        status = "fail"
        reason = "FAIL: entry scripts failed the syntax check"
    elif skips:
        status = "skip"
        reason = "; ".join(skips)
    else:
        status = "ok"
        reason = ""

    ttl_used = get_cache_ttl() if status == "ok" else get_failure_cache_ttl()
    write_cache(mode="light", status=status, reason=reason, exit_code=exit_code)

    print()
    print("=" * 50, flush=True)
    if exit_code == 0:
        print("  轻量环境检查完成", flush=True)
        if skips:
            print("  存在跳过项；完整校验（安装依赖 + 校验凭据）请执行: bash scripts/check_env.sh --full", flush=True)
        else:
            print("  完整校验请执行: bash scripts/check_env.sh --full", flush=True)
    else:
        print("  轻量环境检查未通过：请先修复入口脚本语法错误", flush=True)
    print(f"  结果已缓存（有效期 {ttl_used}s）", flush=True)
    print("=" * 50, flush=True)
    return exit_code


# ── 步骤 3：安装依赖 ─────────────────────────────────────────────────
# 新增：支持 --upgrade 参数，用于升级已安装的包

UPGRADE = False  # 全局标记，由命令行参数设置


def _check_deps_already_installed():
    """快速检查核心依赖是否已安装，避免不必要的 pip 调用"""
    core_modules = ["huaweicloudsdkcore", "huaweicloudsdkecs", "huaweicloudsdkiam"]
    for mod in core_modules:
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def _ensure_pip():
    """确保 pip 可用，若不可用则尝试 ensurepip 引导安装"""
    rc, _, _ = run_cmd([sys.executable, "-m", "pip", "--version"],
                       timeout=step_timeout(20))
    if rc == 0:
        return True

    print("  pip 不可用，尝试使用 ensurepip 引导安装...", flush=True)
    rc, _, err = run_cmd([sys.executable, "-m", "ensurepip", "--upgrade"],
                         timeout=step_timeout(45))
    if rc == 0:
        print("  ensurepip 安装 pip 成功", flush=True)
        return True

    print(f"  ensurepip 也失败: {err}", flush=True)

    get_pip_path = os.path.join(tempfile.gettempdir(), "get-pip.py")
    urls = [
        "https://mirrors.huaweicloud.com/repository/pypi/simple/get-pip.py",
        "https://bootstrap.pypa.io/get-pip.py",
    ]

    ctx = ssl._create_unverified_context()

    for url in urls:
        info(f"尝试下载 get-pip.py: {url}")
        try:
            urllib.request.urlretrieve(url, get_pip_path, context=ctx)
        except Exception as e:
            print(f"    下载失败: {e}")
            continue

        rc, out, err = run_cmd([sys.executable, get_pip_path], timeout=step_timeout(45))
        if rc == 0:
            ok("get-pip.py 安装 pip 成功")
            return True
        print("    get-pip.py 执行失败")
        for line in (err or out).split('\n')[-5:]:
            print(f"    {line}")

    fail("无法安装 pip，请手动安装后重试")
    return False


def _find_fastest_mirror():
    """轻量探测可用镜像源，返回第一个可达的 URL"""
    mirrors = [
        "https://repo.huaweicloud.com/repository/pypi/simple",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
    ]
    print("  正在探测依赖镜像源（每个最多 5s）...", flush=True)
    for url in mirrors:
        if remaining_budget() <= 3:
            print("  总超时临近，停止镜像探测", flush=True)
            break
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req, timeout=max(1, min(5, int(remaining_budget()))))
            if resp.status == 200:
                print(f"  可用镜像：{url}", flush=True)
                return url
        except Exception:
            continue
    print("  无可用镜像源，将尝试官方源", flush=True)
    return None


def install_dependencies():
    """安装 requirements.txt 中的依赖，优先使用国内镜像源"""
    print("\n[3/5] 安装 Python 依赖", flush=True)

    root = get_project_root()
    req_file = os.path.join(root, "requirements.txt")

    if not os.path.exists(req_file):
        print(f"  未找到 {req_file}", flush=True)
        return False

    # 检查依赖是否已满足（非 --upgrade 模式可跳过安装）
    if not UPGRADE and _check_deps_already_installed():
        print("  核心依赖已安装，跳过 pip 安装（使用 --upgrade 可强制重新安装）", flush=True)
        return True

    if budget_exhausted("依赖安装"):
        return False

    print(f"  开始安装（首次可能耗时数十秒，剩余预算约 {max(0, int(remaining_budget()))}s）...",
          flush=True)

    # 确保 pip 可用
    if not _ensure_pip():
        return False

    mirror_url = _find_fastest_mirror()
    pip_timeout = "20"

    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]

    # 新增：--upgrade 模式
    if UPGRADE:
        pip_cmd.append("--upgrade")

    def _run_pip(extra_args, source_label):
        if budget_exhausted("依赖安装"):
            return False
        attempt_timeout = step_timeout(45)
        print(f"  正在从{source_label}安装依赖（最长 {attempt_timeout}s）...", flush=True)
        rc, out, err = run_cmd(pip_cmd + extra_args, timeout=attempt_timeout)
        if rc == 0:
            print(f"  依赖安装成功（{source_label}）", flush=True)
            return True
        print(f"  {source_label}安装失败：{(err or out)[-200:]}", flush=True)
        return False

    if mirror_url:
        host = mirror_url.split("//")[1].split("/")[0]
        if _run_pip(["-i", mirror_url, "--trusted-host", host,
                     "--timeout", pip_timeout, "--retries", "1"], "镜像源"):
            return True

    # 兜底：官方源
    if _run_pip(["--timeout", pip_timeout, "--retries", "1"], "官方源"):
        return True

    print("  依赖安装失败：无法访问依赖镜像或网络不可达", flush=True)
    print("  处理建议: 检查网络/代理，或预装依赖后使用 HW_ENV_CHECK_TTL 复用检查缓存", flush=True)
    return False


# ── 步骤 4：校验 SDK 可导入 ─────────────────────────────────────────

SDK_MODULES = [
    "huaweicloudsdkcore",
    "huaweicloudsdkecs",
    "huaweicloudsdkiam",
    "huaweicloudsdkims",
    "huaweicloudsdkas",
    "huaweicloudsdkbms",
    "huaweicloudsdkcce",
]


def check_sdk():
    """校验华为云 SDK 是否可正常导入"""
    print("\n[4/5] 校验华为云 SDK", flush=True)
    print(f"  正在校验 {len(SDK_MODULES)} 个 SDK 模块（本地导入，无需网络）...", flush=True)

    all_ok = True
    for mod in SDK_MODULES:
        try:
            __import__(mod)
            print(f"  {mod} 可导入", flush=True)
        except ImportError:
            print(f"  {mod} 不可导入", flush=True)
            all_ok = False

    if all_ok:
        print("  SDK 校验通过", flush=True)
    else:
        print("  部分 SDK 不可导入，请运行: pip install -r requirements.txt", flush=True)

    return all_ok


# ── 步骤 5：校验凭据有效性（真正调用 IAM API）──────────────────────

def check_credentials():
    """通过调用 IAM API 验证 AK/SK 凭据是否有效"""
    print("\n[5/5] 校验凭据有效性（调用 IAM API）", flush=True)

    try:
        from config import load_credentials, build_http_config
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkiam.v5 import IamClient
        from huaweicloudsdkiam.v5.region.iam_region import IamRegion
        from huaweicloudsdkiam.v5.model import ListUsersV5Request

        AK, SK, Region, SecurityToken = load_credentials()

        http_config = build_http_config()
        # 环境自检不允许长时间等待：缩短短连接超时并关闭自动重试
        http_config.timeout = (5, 10)
        http_config.retry_times = 0

        print("  正在调用 IAM API（单次超时约 10s，不等待长时间重试）...", flush=True)

        credentials = (
            GlobalCredentials(AK, SK)
            if not SecurityToken
            else GlobalCredentials(AK, SK).with_security_token(SecurityToken)
        )

        client = (
            IamClient.new_builder()
            .with_http_config(http_config)
            .with_credentials(credentials)
            .with_region(IamRegion.value_of("cn-north-1"))
            .build()
        )

        # 调用 IAM API：列出用户（限制 1 条，仅验证凭据有效）
        request = ListUsersV5Request()
        request.limit = 1
        response = client.list_users_v5(request)

        user_count = len(response.users) if response.users else 0
        print(f"  IAM 凭据有效，成功获取用户列表（{user_count} 个用户）", flush=True)
        return True

    except Exception as e:
        print(f"  IAM API 调用失败: {e}", flush=True)
        print("  可能原因: AK/SK 无效、已过期、或网络不通", flush=True)
        print("  处理建议: 检查凭据与网络/代理后重试；本步骤已按短超时执行，不会长时间等待", flush=True)
        return False



# ── 主流程 ──────────────────────────────────────────────────────────

TOTAL_STEPS = 5


def skip_step(step_num, label):
    print(f"\n[{step_num}/{TOTAL_STEPS}] {label}", flush=True)
    print("  跳过（前置步骤未通过）", flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="华为云资源查询 - 环境确保脚本")
    parser.add_argument("--light", action="store_true",
                        help="仅做轻量静态检查（不创建 venv、不安装依赖），无凭证时 exit 0")
    parser.add_argument("--full", action="store_true",
                        help="执行完整严格校验（安装依赖并校验凭证）；缺凭证 exit 2")
    parser.add_argument("--upgrade", action="store_true",
                        help="强制升级所有依赖到最新版本")
    parser.add_argument("--force", action="store_true",
                        help="强制重新执行全部检查（忽略环境检查缓存）")
    parser.add_argument("--ttl", type=int, default=None,
                        help=f"环境检查缓存有效期（秒），默认 {DEFAULT_CACHE_TTL}；0 表示禁用缓存")
    return parser.parse_args()


def run_full_checks():
    """严格模式：安装依赖、校验 SDK 并调用 IAM 验证凭据；失败结果写短 TTL 缓存。"""
    # 缓存命中则走快速路径（成功/失败都复用，避免重复创建 venv 与安装依赖）
    if not FORCE_REFRESH:
        cache = read_fresh_cache(mode="full")
        if cache:
            print_cache_hit(cache)
            return int(cache.get("exit_code", 0) or 0)

    # 轻量前置：缺少凭证时立即返回，避免无谓的 venv 创建与依赖安装
    creds = _resolved_credentials()
    if not (creds["ak"] and creds["sk"]):
        reason = ("FAIL: 未设置 AK/SK；请先配置 HW_ACCESS_KEY / HW_SECRET_KEY、"
                  "HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY，或 AKSK=AK/SK")
        print(reason, file=sys.stderr)
        write_cache(mode="full", status="fail", reason=reason, exit_code=2)
        return 2

    # 若系统 Python 受 PEP 668 保护，自动创建 venv 并 reexec
    _ensure_venv_and_reexec()

    print("=" * 50, flush=True)
    print("  华为云资源查询 - 环境确保", flush=True)
    print(f"  总超时预算: {get_total_timeout()}s（可用 HW_ENV_CHECK_TIMEOUT 调整）", flush=True)
    print("=" * 50, flush=True)

    results = []

    # 步骤 1：环境变量
    results.append(check_env_vars())

    # 步骤 2：Python 版本
    results.append(check_python())

    # 步骤 3：依赖安装
    if all(results):
        if budget_exhausted("依赖安装"):
            results.append(False)
        else:
            results.append(install_dependencies())
    else:
        skip_step(3, "安装 Python 依赖")
        results.append(False)

    # 步骤 4：SDK 校验
    if all(results):
        if budget_exhausted("SDK 校验"):
            results.append(False)
        else:
            results.append(check_sdk())
    else:
        skip_step(4, "校验华为云 SDK")
        results.append(False)

    # 步骤 5：凭据有效性
    if all(results):
        if budget_exhausted("凭据校验"):
            results.append(False)
        else:
            results.append(check_credentials())
    else:
        skip_step(5, "校验凭据有效性（调用 IAM API）")
        results.append(False)

    # 汇总
    print()
    print("=" * 50, flush=True)
    if all(results):
        print("  环境确保完成，所有检查项均通过（含 API 验证）", flush=True)
        print("  可以正常使用查询脚本", flush=True)

        # 自动获取 project_id 并导出到环境变量（可选步骤，预算不足时跳过）
        region = _resolved_credentials()["region"]
        project_id = ""
        if remaining_budget() > 5:
            project_id = get_project_id(region)
        else:
            print("  剩余预算不足，跳过 project_id 自动解析（可显式设置 HW_PROJECT_ID）", flush=True)
        if project_id:
            os.environ["HW_PROJECT_ID"] = project_id
            print(f"  HW_PROJECT_ID 已自动获取: {project_id}", flush=True)
            # 写入到临时文件供 shell 读取
            project_id_file = os.path.join(get_project_root(), ".project_id")
            with open(project_id_file, "w") as f:
                f.write(project_id)

        # 写入环境检查缓存，后续调用走快速路径
        write_cache(project_id, mode="full", status="ok", exit_code=0)
        print(f"  环境检查结果已缓存（有效期 {get_cache_ttl()}s）", flush=True)
        print("=" * 50, flush=True)
        return 0

    reason = "FAIL: 环境确保未完成（依赖镜像/网络不可达、SDK 未安装或凭据无效）"
    print("  环境确保未完成（exit 3），请按上述提示修复后重新运行", flush=True)
    print("  常见原因: 依赖镜像/网络不可达、SDK 未安装或凭据无效", flush=True)
    print("=" * 50, flush=True)
    write_cache(mode="full", status="fail", reason=reason, exit_code=3)
    print(f"  失败结果已缓存（有效期 {get_failure_cache_ttl()}s，--force 可立即重查）", flush=True)
    return 3


def main():
    global UPGRADE, FORCE_REFRESH
    args = parse_args()
    UPGRADE = args.upgrade
    FORCE_REFRESH = args.force or os.getenv("HW_ENV_CHECK_FORCE", "") == "1" or args.upgrade
    if args.ttl is not None:
        os.environ["HW_ENV_CHECK_TTL"] = str(args.ttl)

    if args.light and not args.full:
        if not FORCE_REFRESH:
            cache = read_fresh_cache(mode="light")
            if cache:
                print_cache_hit(cache)
                return int(cache.get("exit_code", 0) or 0)
        return run_light_checks()

    return run_full_checks()


if __name__ == "__main__":
    sys.exit(main())
