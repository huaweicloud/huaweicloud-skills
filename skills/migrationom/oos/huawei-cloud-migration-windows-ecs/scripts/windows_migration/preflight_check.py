#!/usr/bin/env python3
"""迁移前置任务：环境变量检查。

用途：实际执行迁移编排前，先校验迁移所需环境变量是否已配置。
如果客户还未设置环境变量，本工具会明确提示缺失项，并建议按 SKILL.md
「前置任务：环境变量检查」章节完成配置后再发起迁移。

用法：
  python3 preflight_check.py --scenario public    # 公网迁移前检查
  python3 preflight_check.py --scenario private   # 私网迁移前检查
  python3 preflight_check.py --scenario public --json   # JSON 输出

退出码：
  0  = 必备环境变量齐备，可继续迁移
  2  = 存在缺失环境变量，请先配置后再迁移（不打印任何敏感值）
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from core.hostinfo import load_sources_and_proxies, ENV_NAME

# 云侧凭证环境变量（migrate.yaml 中 sms_agent 段为空时的数据来源）
CLOUD_CRED_ENVS = ("migration_Access_Key", "migration_Secret_Access_Key", "migration_domain")


def _missing(envs: dict[str, str]) -> list[str]:
    return [k for k, v in envs.items() if not v or not str(v).strip()]


def run_preflight(scenario: str) -> dict:
    """执行前置检查，返回结构化结果。不打印任何凭据值。"""
    report: dict = {"scenario": scenario, "ok": True, "missing": []}

    sources, proxies = load_sources_and_proxies()
    if scenario == "public":
        # 公网：批量模式必须提供至少一台源端；代理主机不应被误判
        required = {"Host_Information 源端主机": len(sources) > 0}
        if proxies:
            report["note"] = "公网迁移不应包含代理对象，请检查 Host_Information 是否使用了私网模板"
        for ck in CLOUD_CRED_ENVS:
            required[ck] = bool(os.environ.get(ck, ""))
    else:
        # 私网：必须有源端 + 代理
        required = {
            "Host_Information 源端主机": len(sources) > 0,
            "Host_Information 代理主机": len(proxies) > 0,
        }
        for ck in CLOUD_CRED_ENVS:
            required[ck] = bool(os.environ.get(ck, ""))

    missing = [k for k, ok in required.items() if not ok]
    if missing:
        report["ok"] = False
        report["missing"] = missing
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="迁移前置任务：环境变量检查（不打印任何敏感值）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit 0=齐备可迁移；exit 2=缺失需先配置",
    )
    parser.add_argument("--scenario", choices=["public", "private"], required=True)
    parser.add_argument("--json", dest="json_output", action="store_true")
    args = parser.parse_args()

    report = run_preflight(args.scenario)

    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report["ok"]:
            print(f"[前置检查] {args.scenario} 迁移所需环境变量已配置，可继续迁移。")
        else:
            print("[前置检查] ❌ 迁移前置任务未完成，缺少以下配置：")
            for item in report["missing"]:
                print(f"  - {item}")
            print()
            print("请先配置环境变量后再迁移（详见 SKILL.md「前置任务：环境变量检查」）：")
            print(
                "  1) export migration_Access_Key=... / migration_Secret_Access_Key=... / migration_domain=..."
            )
            print("  2) export Host_Information='[...]'  # JSON 数组主机信息（公网:源端；私网:源端+代理）")
            if "Host_Information" in " ".join(report["missing"]):
                print("  3) 确认 Host_Information 为 JSON 数组且主机字段完整")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())