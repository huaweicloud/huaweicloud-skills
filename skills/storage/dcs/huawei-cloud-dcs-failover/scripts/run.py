#!/usr/bin/env python3
"""
DCS master-slave failover drill — unified entry point.

Runs the three-phase pipeline: prepare -> execute -> report

Usage:
  # Full pipeline (performs real failover)
  python3 run.py

  # Prepare only
  python3 run.py --phase prepare

  # Execute failover only (requires prior prepare)
  python3 run.py --phase execute [--force]

  # Generate report only (requires prior execution result)
  python3 run.py --phase report
"""

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")

sys.path.insert(0, SCRIPT_DIR)
from config import EXPERIMENTS_DIR, TEMPLATES_DIR, clean_templates

CONFIG_DIR = EXPERIMENTS_DIR


def run_phase(phase, config_dir=None, force=False):
    """Run a single phase."""
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
        if force:
            cmd.append("--force")
    elif phase == "report":
        cmd.extend(["--config-dir", config_dir])

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="DCS 主备倒换演练 — 统一入口（prepare → execute → report）"
    )
    parser.add_argument(
        "--phase",
        choices=["prepare", "execute", "report", "all"],
        default="all",
        help="执行阶段（默认 all = 完整流水线）",
    )
    parser.add_argument("--force", action="store_true", help="跳过 prepare 检测出的严重风险拦截（需人工确认风险）")
    parser.add_argument("--config-dir", default=None, help="配置目录路径（默认: experiments/）")
    args = parser.parse_args()

    config_dir = os.path.abspath(args.config_dir or CONFIG_DIR)

    # Scan templates/ before each run, keep at most 5 newest reports (purge old ones)
    clean_templates(max_keep=5)

    phases = []
    if args.phase == "all":
        phases = ["prepare", "execute", "report"]
    else:
        phases = [args.phase]

    print(f"\n{'='*60}")
    print(f"  DCS 主备倒换演练工具")
    print(f"  阶段: {' → '.join(phases)}")
    print(f"  模式: 实际执行{'（已确认放行跳过风险拦截）' if args.force else ''}")
    print(f"{'='*60}")

    for phase in phases:
        ok = run_phase(phase, config_dir, args.force)
        if not ok:
            print(f"\n[ERROR] 阶段 {phase} 失败，终止流水线。")
            sys.exit(1)

        if phase == "prepare":
            print(f"\n[INFO] 配置目录: {config_dir}")

    print(f"\n{'='*60}")
    print(f"  全部阶段完成！")
    print(f"{'='*60}")

    if "report" in phases:
        import glob
        report_dir = TEMPLATES_DIR
        reports = sorted(glob.glob(os.path.join(report_dir, "failover_report_*.html")))
        if reports:
            print(f"\n  报告文件: {reports[-1]}")
    if "prepare" in phases:
        print(f"  配置目录: {config_dir}")


if __name__ == "__main__":
    main()
