#!/usr/bin/env python3
"""
RDS 主备倒换演练 — 统一入口

一键执行三阶段流水线：prepare → execute → report

Usage:
  # 一键完整流程（需确认倒换）
  python3 run.py --yes

  # 仅准备阶段
  python3 run.py --phase prepare

  # 仅预演 execute 阶段（不实际倒换，需先运行 prepare）
  python3 run.py --phase execute

  # 准备 + 执行 + 报告
  python3 run.py --phase all --yes

  # 仅生成报告（需已有执行结果）
  python3 run.py --phase report
"""

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")
CONFIG_DIR = os.path.join(SKILL_ROOT, "experiments")


def run_phase(phase, config_dir=None, yes=False, force=False):
    """运行单个阶段"""
    script = os.path.join(SCRIPT_DIR, f"{phase}.py")
    if not os.path.isfile(script):
        print(f"[ERROR] 脚本不存在: {script}")
        return False

    print(f"\n{'='*60}")
    print(f"  阶段: {phase}")
    print(f"{'='*60}\n")

    cmd = [sys.executable, script]

    if phase == "prepare":
        cmd.extend(["--config-dir", config_dir])
    elif phase == "execute":
        cmd.extend(["--config-dir", config_dir])
        if yes:
            cmd.append("--yes")
        if force:
            cmd.append("--force")
    elif phase == "report":
        cmd.extend(["--config-dir", config_dir])

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="RDS 主备倒换演练 — 统一入口（prepare → execute → report）"
    )
    parser.add_argument(
        "--phase",
        choices=["prepare", "execute", "report", "all"],
        default="all",
        help="执行阶段（默认 all = 完整流水线）",
    )
    parser.add_argument("--yes", action="store_true", help="实际执行倒换（否则预演）")
    parser.add_argument("--force", action="store_true", help="跳过 prepare 检测出的严重风险拦截（需人工确认风险）")
    parser.add_argument("--config-dir", default=None, help="配置目录路径（默认: experiments/）")
    args = parser.parse_args()

    config_dir = os.path.abspath(args.config_dir or CONFIG_DIR)

    phases = []
    if args.phase == "all":
        # 预演模式（无 --yes）不生成报告：execute 仅产出空壳结果，报告无实际倒换数据
        phases = ["prepare", "execute", "report"] if args.yes else ["prepare", "execute"]
    else:
        phases = [args.phase]

    print(f"\n{'='*60}")
    print(f"  RDS 主备倒换演练工具")
    print(f"  阶段: {' → '.join(phases)}")
    print(f"  模式: {'实际执行' if args.yes else '预演（不实际倒换）'}{'（--force 跳过风险拦截）' if args.force else ''}")
    print(f"{'='*60}")

    for phase in phases:
        ok = run_phase(phase, config_dir, args.yes, args.force)
        if not ok:
            print(f"\n[ERROR] 阶段 {phase} 失败，终止流水线。")
            sys.exit(1)

        # prepare 完成后输出配置目录路径
        if phase == "prepare":
            print(f"\n[INFO] 配置目录: {config_dir}")

    print(f"\n{'='*60}")
    print(f"  全部阶段完成！")
    print(f"{'='*60}")

    if "report" in phases:
        import glob
        import datetime
        report_dir = os.path.join(SKILL_ROOT, "report")
        reports = sorted(glob.glob(os.path.join(report_dir, "failover_report_*.html")))
        if reports:
            print(f"\n  报告文件: {reports[-1]}")
    if "prepare" in phases:
        print(f"  配置目录: {config_dir}")


if __name__ == "__main__":
    main()
