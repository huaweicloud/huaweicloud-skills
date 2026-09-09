#!/usr/bin/env python3
"""
build_task_url.py — 根据 region 和 task_id 生成 OptVerse 控制台 URL
支持：直接打印 URL / 自动打开浏览器

用法:
    python scripts/build_task_url.py --region cn-east-3 --task-id xxx
    python scripts/build_task_url.py --region cn-east-3 --task-id xxx --open   # 直接打开浏览器

测试环境：注入环境变量（无默认值，强制显式声明）：
    export TEST_ENV_REGION=<your-test-region>
    export TEST_ENV_DOMAIN=<your-test-console-domain>
    python scripts/build_task_url.py -r <your-test-region> --task-id xxx

domain 解析规则（按优先级）：
    1. 若 region 与注入的 TEST_ENV_REGION 一致 → TEST_ENV_DOMAIN（测试环境）
    2. 若 region 在 REGION_TO_DOMAIN 映射表中 → 映射的 domain
    3. 上述都不匹配 → DEFAULT_DOMAIN（默认 console.huaweicloud.com）

依赖: 无需第三方库
"""
import argparse
import os
import sys
import webbrowser
import platform
import shutil
import subprocess


# region → console 域名映射表（正式域；测试域通过 TEST_ENV_REGION 注入，不在此处）
REGION_TO_DOMAIN = {
    "cn-east-3": "console.huaweicloud.com",
    # 在此添加新的正式 region → domain 映射
}

# 未识别 region 的统一默认域
DEFAULT_DOMAIN = "console.huaweicloud.com"


def detect_display():
    """
    检测当前环境是否有图形桌面。
    返回: (has_display: bool, reason: str)
    """
    system = platform.system()

    if system == "Windows":
        try:
            session_name = os.environ.get("SESSIONNAME", "Console")
            if session_name == "Services" or session_name == "":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq explorer.exe"],
                    capture_output=True, text=True, timeout=5
                )
                if "explorer.exe" not in result.stdout:
                    return False, "Windows 服务会话（无桌面）"
            return True, "Windows 桌面会话"
        except Exception:
            return True, "Windows（检测异常，假设有桌面）"

    if system == "Darwin":
        return True, "macOS（图形桌面）"

    if system == "Linux":
        display = os.environ.get("DISPLAY", "")
        if not display:
            ssh_conn = os.environ.get("SSH_CONNECTION", "")
            if ssh_conn:
                return False, "Linux 无 DISPLAY（SSH 无 X11 转发）"
            return False, "Linux 无 DISPLAY（无图形环境）"
        return True, f"Linux DISPLAY={display}"

    return True, f"{system}（默认有桌面）"


def open_url(url):
    """打开 URL，优先使用系统原生命令，fallback 到 webbrowser。"""
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(url)  # type: ignore
        elif system == "Darwin":
            subprocess.run(["open", url], check=True, timeout=10)
        else:
            for cmd in ["xdg-open", "gnome-open", "kfmclient"]:
                if shutil.which(cmd):
                    subprocess.run([cmd, url], check=True, timeout=10)
                    return
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


def get_console_domain(region: str) -> str:
    """根据 region 返回控制台域名。

    解析优先级：
      1. region 与注入的 TEST_ENV_REGION 一致 → TEST_ENV_DOMAIN（测试环境，**无默认值**）
      2. region 在 REGION_TO_DOMAIN 中 → 映射的 domain（正式域）
      3. 上述都不匹配 → DEFAULT_DOMAIN（统一走 console.huaweicloud.com）
    """
    # 1. 测试域：环境变量注入（无默认值）
    test_region = os.environ.get("TEST_ENV_REGION")
    test_domain = os.environ.get("TEST_ENV_DOMAIN")
    if test_region and test_domain and region == test_region:
        return test_domain

    # 2. 正式域映射
    if region in REGION_TO_DOMAIN:
        return REGION_TO_DOMAIN[region]

    # 3. 默认域（任何未识别的 region 统一走 console.huaweicloud.com）
    return DEFAULT_DOMAIN


def build_task_url(region: str, task_id: str) -> str:
    domain = get_console_domain(region)
    region_clean = region.replace("region=", "").strip()
    return f"https://{domain}/optverse/?region={region_clean}#/ai4s/task-detail?id={task_id}"


def build_algorithm_url(region: str, algorithm_id: str) -> str:
    domain = get_console_domain(region)
    region_clean = region.replace("region=", "").strip()
    return f"https://{domain}/optverse/?region={region_clean}#/ai4s/algorithm-design-project?algorithmId={algorithm_id}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="生成 OptVerse 控制台 URL，可选直接打开浏览器"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task-id", dest="task_id", help="演化任务 ID (evolve_task_id)")
    group.add_argument("--algorithm-id", dest="algorithm_id", help="算法项目 ID (algorithm_id)")

    parser.add_argument("--region", "-r", required=True,
                        help="区域，如 cn-east-3（正式域）；测试域需先 export TEST_ENV_REGION + TEST_ENV_DOMAIN")
    parser.add_argument("--open", "-o", action="store_true",
                        help="直接使用默认浏览器打开 URL（仅 Linux/macOS/Windows）")
    parser.add_argument("--algorithm", action="store_true",
                        help="当传入 --algorithm-id 时，明确指定为算法项目 URL")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="静默模式：不打印 URL，只打开浏览器（需配合 --open）")

    return parser.parse_args()


def is_test_env(region: str) -> bool:
    """判断是否为测试环境：基于环境变量 TEST_ENV_REGION（无默认值）。"""
    test_region = os.environ.get("TEST_ENV_REGION")
    return bool(test_region and region == test_region)


def main():
    args = parse_args()

    region = args.region
    url = build_task_url(region, args.task_id) if args.task_id else build_algorithm_url(region, args.algorithm_id)

    is_test = is_test_env(region)
    env_label = "🧪 测试环境" if is_test else "🏭 正式环境"

    if not args.quiet:
        print(f"{env_label}")
        print(f"🔗 {url}")
        print()

    if args.open:
        has_display, reason = detect_display()
        print(f"🖥️  图形桌面检测: {reason}", file=sys.stderr)

        if not has_display:
            print(f"⚠️  当前无图形桌面环境，跳过自动打开浏览器", file=sys.stderr)
            print(f"   请手动访问: {url}", file=sys.stderr)
            return 1

        print(f"🌐 正在打开浏览器...", file=sys.stderr)
        open_url(url)
        print(f"✅ 已打开", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())