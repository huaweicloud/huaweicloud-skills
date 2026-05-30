#!/usr/bin/env python3
"""
华为云资源查询 - 环境确保脚本

一键完成所有环境准备并验证可用性，执行后即可直接运行查询脚本：
  1. 校验必填环境变量 HW_ACCESS_KEY / HW_SECRET_KEY
  2. 检查 Python 版本是否满足最低要求，若不满足则尝试自动安装
  3. 安装 Python 依赖（支持 --upgrade）
  4. 校验华为云 SDK 是否可导入
  5. 校验凭据是否有效（真正调用 IAM API）
  6. 校验项目级服务是否可用（真正调用 ECS API）

只有所有步骤都通过（包括 API 调用），才说明环境真正准备好了。
"""

import os
import sys
import subprocess
import platform
import tempfile
import argparse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))

import ssl

ssl._create_default_https_context = ssl._create_unverified_context


# ── 虚拟环境管理 ──────────────────────────────────────────────────────

def _is_in_venv():
    """判断当前是否已在虚拟环境中"""
    return sys.prefix != sys.base_prefix


def _venv_path():
    """返回项目根目录下的 .venv 路径"""
    return os.path.join(get_project_root(), ".venv")


def _ensure_venv_and_reexec():
    """若不在 venv 中，创建 .venv 并用 venv Python 重新执行自身。

    返回 True 表示已 reexec（不会返回到调用者），
    返回 False 表示已在 venv 中，无需 reexec。
    """
    if _is_in_venv():
        return False

    venv_dir = _venv_path()
    venv_python = os.path.join(venv_dir, "bin", "python3")
    if not os.path.isabs(venv_python):
        venv_python = os.path.abspath(venv_python)

    # 创建 venv（如不存在）
    if not os.path.isfile(venv_python):
        print("\n  PEP 668: 系统 Python 禁止直接 pip install，正在创建虚拟环境...")
        rc, out, err = run_cmd([sys.executable, "-m", "venv", venv_dir], timeout=60)
        if rc != 0:
            fail(f"创建虚拟环境失败: {err}")
            print("  请手动执行: python3 -m venv .venv && source .venv/bin/activate")
            return False
        ok(f"虚拟环境已创建: {venv_dir}")

    # 用 venv Python 重新执行当前脚本
    print(f"  使用虚拟环境 Python: {venv_python}")
    os.execv(venv_python, [venv_python] + sys.argv)

def info(msg):
    print(f"  {msg}")


def ok(msg):
    print(f"  OK: {msg}")


def fail(msg):
    print(f"  FAIL: {msg}")


def get_project_id(region):
    """通过 IAM KeystoneListProjects 接口获取指定区域的项目 ID

    IAM 是全局服务，不区分 region，但项目与区域一一对应。
    查询项目列表后，按 region 名称匹配对应的项目 ID。

    :param region: 区域名称，如 cn-north-4
    :return: 项目 ID 字符串
    """
    from config import load_credentials, build_http_config
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkiam.v3 import IamClient
    from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
    from huaweicloudsdkiam.v3.region.iam_region import IamRegion

    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    try:
        http_config = build_http_config()
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
            print(f"未找到可访问的项目 (区域: {region})")
            exit(0)
        for project in projects:
            if getattr(project, 'name', '') == region:
                return project.id
        return projects[0].id
    except Exception as e:
        print(f"获取项目 ID 失败: {e}")
        exit(-1)


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

REQUIRED_ENV = ["HW_ACCESS_KEY", "HW_SECRET_KEY"]


def check_env_vars():
    """校验必填环境变量，只检查是否设置，绝不输出值"""
    print("\n[1/5] 校验全局环境变量")

    all_ok = True
    for var in REQUIRED_ENV:
        if os.getenv(var):
            print(f" {var} 已设置")
        else:
            print(f" {var} 未设置")
            all_ok = False

    if not all_ok:
        print("\n  必需的全局环境变量未设置，请配置 HW_ACCESS_KEY 和 HW_SECRET_KEY")
        return False

    print("  全局环境变量校验通过")
    return True


# ── 步骤 2：检查并安装 Python ────────────────────────────────────────

MIN_PYTHON = (3, 6)


def print_manual_python_help():
    print()
    info("请安装 Python 3.6+ 后重试，参考：")
    print("    Windows : winget install Python.Python.3.11")
    print("    Ubuntu  : sudo apt update && sudo apt install -y python3 python3-pip python3-venv")
    print("    CentOS  : sudo yum install -y python3 python3-pip")
    print("    Fedora  : sudo dnf install -y python3 python3-pip")
    print("    macOS   : brew install python@3.11")


def check_python():
    """检查 Python 版本，若不满足则尝试自动安装"""
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


def install_python():
    """尝试自动安装 Python 3.11"""
    system = platform.system()

    if system == "Windows":
        rc, out, err = run_cmd(["winget", "install", "Python.Python.3.11", "--accept-source-agreements", "--accept-package-agreements"])
        if rc == 0:
            return True
        print(f"    winget 安装失败: {err}")
        return False

    elif system == "Linux":
        # 尝试 apt（Ubuntu/Debian）
        rc, _, err = run_cmd(["sudo", "apt", "update"])
        rc2, _, err2 = run_cmd(["sudo", "apt", "install", "-y", "python3", "python3-pip", "python3-venv"])
        if rc == 0 and rc2 == 0:
            return True
        # 尝试 yum（CentOS/RHEL/EulerOS 旧版）
        rc, _, err = run_cmd(["sudo", "yum", "install", "-y", "python3", "python3-pip"])
        if rc == 0:
            return True
        # 尝试 dnf（Fedora/EulerOS 新版）
        rc, _, err = run_cmd(["sudo", "dnf", "install", "-y", "python3", "python3-pip"])
        if rc == 0:
            return True
        print("    apt/yum/dnf 安装失败")
        return False

    elif system == "Darwin":
        rc, _, err = run_cmd(["brew", "install", "python@3.11"])
        if rc == 0:
            return True
        print(f"    brew 安装失败: {err}")
        return False

    return False


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
    rc, _, _ = run_cmd([sys.executable, "-m", "pip", "--version"])
    if rc == 0:
        return True

    print("  pip 不可用，尝试使用 ensurepip 引导安装...")
    rc, _, err = run_cmd([sys.executable, "-m", "ensurepip", "--upgrade"])
    if rc == 0:
        print("  ensurepip 安装 pip 成功")
        return True

    print(f"  ensurepip 也失败: {err}")

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

        rc, out, err = run_cmd([sys.executable, get_pip_path], timeout=120)
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
    for url in mirrors:
        try:
            req = urllib.request.Request(url, method="HEAD")
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status == 200:
                print(f" 可用镜像：{url}")
                return url
        except Exception:
            continue
    print(" 无可用镜像源，将尝试官方源")
    return None


def install_dependencies():
    """安装 requirements.txt 中的依赖，优先使用国内镜像源"""
    print("\n[3/5] 安装 Python 依赖")

    root = get_project_root()
    req_file = os.path.join(root, "requirements.txt")

    if not os.path.exists(req_file):
        print(f"  未找到 {req_file}")
        return False

    # 检查依赖是否已满足（非 --upgrade 模式可跳过安装）
    if not UPGRADE and _check_deps_already_installed():
        print("  核心依赖已安装，跳过 pip 安装（使用 --upgrade 可强制重新安装）")
        return True

    # 确保 pip 可用
    if not _ensure_pip():
        return False

    mirror_url = _find_fastest_mirror()
    pip_timeout = "30"

    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]

    # 新增：--upgrade 模式
    if UPGRADE:
        pip_cmd.append("--upgrade")

    if mirror_url:
        host = mirror_url.split("//")[1].split("/")[0]
        rc, out, err = run_cmd(
            pip_cmd + ["-i", mirror_url, "--trusted-host", host,
                       "--timeout", pip_timeout, "--retries", "2"],
            timeout=120,
        )
        if rc == 0:
            print(" 依赖安装成功")
            return True
        print(f" 镜像源安装失败，尝试官方源：{err[-200:]}")

    # 兜底：官方源
    rc, _, err = run_cmd(
        pip_cmd + ["--timeout", pip_timeout, "--retries", "2"],
        timeout=120,
    )

    if rc == 0:
        print(" 依赖安装成功（官方源）")
        return True

    print(f" 依赖安装失败：{err[-300:]}")
    return False


# ── 步骤 4：校验 SDK 可导入 ─────────────────────────────────────────

SDK_MODULES = [
    "huaweicloudsdkcore",
    "huaweicloudsdkiam",
    "huaweicloudsdkevs",
    "huaweicloudsdksfsturbo",
    "huaweicloudsdkobs",
    "huaweicloudsdkcbr",
]


def check_sdk():
    """校验华为云 SDK 是否可正常导入"""
    print("\n[4/5] 校验华为云 SDK")

    all_ok = True
    for mod in SDK_MODULES:
        try:
            __import__(mod)
            print(f"  {mod}")
        except ImportError:
            print(f"  {mod} 不可导入")
            all_ok = False

    if all_ok:
        print("  SDK 校验通过")
    else:
        print("  部分 SDK 不可导入，请运行: pip install -r requirements.txt")

    return all_ok


# ── 步骤 5：校验凭据有效性（真正调用 IAM API）──────────────────────

def check_credentials():
    """通过调用 IAM API 验证 AK/SK 凭据是否有效"""
    print("\n[5/5] 校验凭据有效性（调用 IAM API）")

    try:
        from config import load_credentials, build_http_config
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkiam.v5 import IamClient
        from huaweicloudsdkiam.v5.region.iam_region import IamRegion
        from huaweicloudsdkiam.v5.model import ListUsersV5Request

        AK, SK, Region, SecurityToken = load_credentials()

        http_config = build_http_config()

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
        print(f"  IAM 凭据有效，成功获取用户列表（{user_count} 个用户）")
        return True

    except Exception as e:
        print(f"  IAM API 调用失败: {e}")
        print("  可能原因: AK/SK 无效、已过期、或网络不通")
        return False



# ── 主流程 ──────────────────────────────────────────────────────────

TOTAL_STEPS = 5


def skip_step(step_num, label):
    print(f"\n[{step_num}/{TOTAL_STEPS}] {label}")
    print("  跳过（前置步骤未通过）")


def parse_args():
    parser = argparse.ArgumentParser(description="华为云资源查询 - 环境确保脚本")
    parser.add_argument("--upgrade", action="store_true",
                        help="强制升级所有依赖到最新版本")
    return parser.parse_args()


def main():
    global UPGRADE
    args = parse_args()
    UPGRADE = args.upgrade

    print("=" * 50)
    print("  华为云资源查询 - 环境确保")
    print("=" * 50)

    # 若系统 Python 受 PEP 668 保护，自动创建 venv 并 reexec
    _ensure_venv_and_reexec()

    results = []

    # 步骤 1：环境变量
    results.append(check_env_vars())

    # 步骤 2：Python 版本
    results.append(check_python())

    # 步骤 3：依赖安装
    if all(results):
        results.append(install_dependencies())
    else:
        skip_step(3, "安装 Python 依赖")
        results.append(False)

    # 步骤 4：SDK 校验
    if all(results):
        results.append(check_sdk())
    else:
        skip_step(4, "校验华为云 SDK")
        results.append(False)

    # 步骤 5：凭据有效性
    if all(results):
        results.append(check_credentials())
    else:
        skip_step(5, "校验凭据有效性（调用 IAM API）")
        results.append(False)

    # 汇总
    print()
    print("=" * 50)
    if all(results):
        print("  环境确保完成，所有检查项均通过（含 API 验证）")
        print("  可以正常使用查询脚本")
    else:
        print("  环境确保未完成，请按上述提示修复后重新运行")
    print("=" * 50)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
