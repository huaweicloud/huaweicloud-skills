#!/usr/bin/env python3
"""
Agent 恢复专用入口 — 仅重建源端 Agent 的敏感参数与注册配置。

背景:
  SMS-Agent 的 AutoIt/预编译 exe 读取 .secrets.dat 后会自动删除该文件（一次性设计）。
  若直接手动执行计划任务 `schtasks /run /tn ConfigureSMSAgent` 且 secrets 已缺失，
  AutoIt 会读到空 Domain/企业项目 → 日志出现 "invalid AK or SK" → Agent 实际未注册
  （connected=False、预检 0/14），而被旧版 VerifyPhase 误判为“注册成功(需复查)”。

  正确恢复方式不是手动 /run 计划任务，而是重跑本入口：
    python3 agent_recover.py --scenario private --config config/migrate.yaml

  ConfigurePhase 会重建 .secrets.dat（写入后回读校验）、重传 exe、重建计划任务，
  再由 VerifyPhase 按“日志尾部致命错误”判定注册失败/成功。

用法:
  python3 agent_recover.py --scenario private --config config/migrate.yaml [--json]
  python3 agent_recover.py --scenario public  --config config/migrate.yaml [--json]

退出码:
  0 — 恢复成功（Agent 已重新配置并注册）
  1 — 恢复失败
  2 — 配置错误
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import ConfigLoader  # noqa: E402
from core.winrm.manager import WinRMManager  # noqa: E402
from phases.base_phase import MigrationContext  # noqa: E402
from phases.configure_phase import ConfigurePhase  # noqa: E402
from phases.verify_phase import VerifyPhase  # noqa: E402
from phases.winrm_phase import WinRMPhase  # noqa: E402
from scenarios.base_scenario import BaseScenario  # noqa: E402
from unified_migrate import setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


class AgentRecoverScenario(BaseScenario):
    """轻量恢复场景: WinRM → ConfigurePhase → VerifyPhase（不重装、不清理）。"""

    def __init__(self, config, via_gost: bool, proxy_mode: bool):
        super().__init__("Agent 恢复(重建配置)")
        self._config = config
        self._ctx = MigrationContext(
            config=config,
            winrm_manager=WinRMManager(config),
            sandbox_download_dir=config.download.sandbox_download_dir,
            source_download_dir=config.source_download_dir,
        )
        # 仅重建配置相关阶段；若源端 Agent 未安装，ConfigurePhase 会因 exe 缺失报错并提示先跑完整迁移。
        self.add_phase(WinRMPhase(via_gost=via_gost))
        self.add_phase(ConfigurePhase(proxy_mode=proxy_mode))
        self.add_phase(VerifyPhase())

    def run(self):
        return super().run(self._ctx)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent 恢复 — 重建源端 SMS-Agent 敏感参数与注册（替代手动 schtasks /run）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  # 私网（经 gost 连接源端，配置走 Squid 代理）\n"
            "  python3 agent_recover.py --scenario private --config config/migrate.yaml\n"
            "  # 公网直连\n"
            "  python3 agent_recover.py --scenario public --config config/migrate.yaml\n"
        ),
    )
    parser.add_argument(
        "--scenario", choices=["public", "private"], required=True,
        help="迁移场景: public=公网直连, private=私网代理",
    )
    parser.add_argument(
        "--config", default="config/migrate.yaml",
        help="配置文件路径 (默认: config/migrate.yaml)",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="输出 JSON 结构化结果到 stdout（供外部脚本解析）",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    try:
        config = ConfigLoader.load(config_path)
    except Exception as e:
        if args.json_output:
            sys.stdout.write(json.dumps({
                "exit_code": 2, "success": False,
                "error_type": type(e).__name__, "error": str(e),
            }, ensure_ascii=False, indent=2) + "\n")
        else:
            print(f"配置加载失败: {e}", file=sys.stderr)
        return 2

    if config.scenario != args.scenario:
        config.scenario = args.scenario

    setup_logging(config, json_mode=args.json_output)
    logger = logging.getLogger("agent_recover")

    via_gost = args.scenario == "private"
    proxy_mode = args.scenario == "private"
    logger.info("=" * 60)
    logger.info("Agent 恢复: 场景=%s | 配置=%s", args.scenario, config_path)
    logger.info("=" * 60)

    scenario = AgentRecoverScenario(config, via_gost=via_gost, proxy_mode=proxy_mode)
    result = scenario.run()

    if args.json_output:
        sys.stdout.write(json.dumps({
            "exit_code": 0 if result.success else 1,
            **result.to_dict(),
        }, ensure_ascii=False, indent=2) + "\n")
    else:
        print(result.summary())

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())