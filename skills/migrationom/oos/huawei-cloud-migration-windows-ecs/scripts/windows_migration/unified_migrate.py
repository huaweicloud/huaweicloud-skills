#!/usr/bin/env python3
"""
统一主机迁移编排入口。

用法:
  # 单台迁移（公网直连 / 私网代理）
  python3 unified_migrate.py --scenario public  --config config/migrate.yaml
  python3 unified_migrate.py --scenario private --config config/migrate.yaml

  # 批量迁移（主机信息来自环境变量 Host_Information；private 需同时在同变量提供代理主机）
  python3 unified_migrate.py --scenario public  --batch env --workers 10
  python3 unified_migrate.py --scenario private --batch env --workers 10

  # 兼容回退：批量 CSV 主机列表
  python3 unified_migrate.py --scenario public  --batch config/hosts.csv --workers 10
  python3 unified_migrate.py --scenario private --batch config/hosts.csv --workers 10

  # 私网迁移（文件服务器部署在代理主机；proxyopt.skip=false 时 Phase1 自动部署跳板机）
  # 跳板机单独就绪: python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml

  # JSON 结构化输出（供外部脚本消费）
  python3 unified_migrate.py --scenario public --config config/migrate.yaml --json

场景:
  public  — 公网迁移，直连模式，SMS-Agent 直连华为云
  private — 私网迁移，代理模式，proxyopt 分发 + SMS-Agent 经 Squid 代理

退出码:
  0   — 成功
  1   — 失败（迁移未完成）
  2   — 配置错误
  130 — 用户中断 (SIGINT)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import ConfigLoader, MigrateConfig  # noqa: E402
from core.exceptions import MigrationError  # noqa: E402
from core.callbacks import Callbacks  # noqa: E402
from core.batch_orchestrator import BatchOrchestrator  # noqa: E402
from core.private_batch_orchestrator import PrivateBatchOrchestrator  # noqa: E402
from core.hostinfo import load_sources_and_proxies, to_host_states, ENV_NAME  # noqa: E402
from scenarios.private_scenario import PrivateScenario  # noqa: E402
from scenarios.public_scenario import PublicScenario  # noqa: E402


def setup_logging(config: MigrateConfig, json_mode: bool = False) -> None:
    """配置日志（控制台 + 文件轮转）。json 模式下抑制控制台日志输出。"""
    log_cfg = config.logging
    log_dir = Path(log_cfg.dir) if log_cfg.dir else PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers = [
        RotatingFileHandler(
            log_dir / log_cfg.file,
            maxBytes=log_cfg.max_size_mb * 1024 * 1024,
            backupCount=log_cfg.backup_count,
            encoding="utf-8",
        ),
    ]
    if not json_mode:
        handlers.insert(0, logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=getattr(logging, log_cfg.level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _output_json(data: dict) -> None:
    """输出 JSON 到 stdout，单次写入，确保原子性。"""
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="统一主机迁移编排 — 公网/私网场景，支持单台和批量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单台迁移
  python3 unified_migrate.py --scenario public --config config/migrate.yaml

  # 批量迁移（100台，10并发）
  python3 unified_migrate.py --scenario public --batch config/hosts.csv --workers 10

  # JSON 结构化输出（供外部脚本解析）
  python3 unified_migrate.py --scenario public --config config/migrate.yaml --json
        """,
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
        "--batch", default=None,
        help="批量模式: env（从环境变量 Host_Information 读取 JSON 主机信息）或 CSV 路径（兼容回退）。"
             "未传 --batch 但设置了 Host_Information 时自动进入批量模式",
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="批量并发线程数 (默认: 配置文件 batch.max_workers)",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="输出 JSON 结构化结果到 stdout（供外部脚本解析）",
    )
    parser.add_argument(
        "--callback", default=None,
        help="回调脚本路径 (Python 文件，定义 build_callbacks() -> Callbacks)",
    )
    parser.add_argument(
        "--skip-preflight", dest="skip_preflight", action="store_true",
        help="跳过前置环境变量检查（默认开启；仅当所有参数已内嵌 migrate.yaml 时使用）",
    )
    args = parser.parse_args()

    # ===== 前置任务：环境变量检查 =====
    # 未设置 Host_Information / migration_* 时，先提醒客户配置环境变量，再继续迁移。
    if not args.skip_preflight:
        try:
            from preflight_check import run_preflight
            report = run_preflight(args.scenario)
        except Exception as e:  # 前置检查异常不阻塞主流程，仅告警
            logging.warning("[前置任务] 检查执行异常，已跳过: %s", e)
            report = {"ok": True}
        if not report.get("ok"):
            if args.json_output:
                _output_json({
                    "exit_code": 2,
                    "success": False,
                    "preflight": False,
                    "missing": report.get("missing", []),
                    "error": "前置任务未完成：缺少迁移环境变量，请先配置后再迁移",
                })
            else:
                print("[前置任务] ❌ 迁移前置检查未通过：请先配置环境变量，再进行迁移。", file=sys.stderr)
                for item in report.get("missing", []):
                    print(f"  - 缺少: {item}", file=sys.stderr)
                print(
                    "  配置示例见 SKILL.md「前置任务：环境变量检查」：\n"
                    "    export migration_Access_Key=... / migration_Secret_Access_Key=... / migration_domain=...\n"
                    "    export Host_Information='[...]'  # JSON 数组主机信息",
                    file=sys.stderr,
                )
                print("  如所有参数已内嵌 migrate.yaml，可加 --skip-preflight 强制跳过。", file=sys.stderr)
            return 2
        logging.info("[前置任务] 环境变量检查通过，开始迁移编排。")

    # 加载配置
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    try:
        config = ConfigLoader.load(config_path)
    except Exception as e:
        if args.json_output:
            _output_json({
                "exit_code": 2,
                "success": False,
                "error_type": type(e).__name__,
                "error": str(e),
            })
        else:
            print(f"配置加载失败: {e}", file=sys.stderr)
        return 2

    # 配置中 scenario 与命令行参数一致性检查
    if config.scenario != args.scenario:
        original = config.scenario
        config.scenario = args.scenario
        logging.warning("配置文件 scenario=%s 被命令行 --scenario=%s 覆盖",
                        original, args.scenario)

    # 设置日志（json 模式下不输出到控制台，避免污染 stdout）
    setup_logging(config, json_mode=args.json_output)
    logger = logging.getLogger("unified_migrate")

    # 加载回调（可选）
    callbacks = Callbacks()
    if args.callback:
        cb_path = Path(args.callback)
        if not cb_path.is_absolute():
            cb_path = PROJECT_ROOT / cb_path
        if not cb_path.suffix:
            cb_path = cb_path.with_suffix(".py")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("callback_module", cb_path)
            cb_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cb_module)
            if hasattr(cb_module, "build_callbacks"):
                callbacks = cb_module.build_callbacks()
                logger.info("回调脚本已加载: %s", cb_path)
        except Exception as e:
            logger.warning("回调脚本加载失败: %s — %s", cb_path, e)

    logger.info("=" * 60)
    logger.info("统一主机迁移编排")
    if args.batch:
        workers = args.workers or config.batch.max_workers
        logger.info("模式: 批量 | 场景: %s | 主机列表: %s | 并发: %d",
                    args.scenario, args.batch, workers)
    else:
        logger.info("模式: 单台 | 场景: %s | 配置: %s", args.scenario, config_path)
    logger.info("=" * 60)

    try:
        # ---- 批量模式判定 ----
        # 显式 CSV 路径 > 环境变量 Host_Information（--batch env 或未传 --batch 但环境变量存在）
        use_env = (args.batch == "env") or (args.batch is None and os.environ.get(ENV_NAME))
        if args.batch and not use_env:
            # ---- 批量模式（CSV 兼容回退）----
            batch_csv = Path(args.batch)
            if not batch_csv.is_absolute():
                batch_csv = PROJECT_ROOT / args.batch

            workers = args.workers or config.batch.max_workers
            state_file = config.batch.state_file
            if not Path(state_file).is_absolute():
                state_file = str(PROJECT_ROOT / state_file)

            if args.scenario == "private":
                # 私网批量模式 — 经跳板机 gost 多端口转发
                state_file = state_file.replace(".json", "_private.json") if "private" not in state_file else state_file
                orchestrator = PrivateBatchOrchestrator(
                    config=config,
                    hosts_csv=str(batch_csv),
                    max_workers=workers,
                    state_file=state_file,
                    callbacks=callbacks,
                )
            else:
                # 公网批量模式 — 直连 WinRM
                orchestrator = BatchOrchestrator(
                    config=config,
                    hosts_csv=str(batch_csv),
                    max_workers=workers,
                    state_file=state_file,
                    callbacks=callbacks,
                )
            result = orchestrator.run()

        elif use_env:
            # ---- 批量模式（环境变量 Host_Information）----
            hosts_info, proxies = load_sources_and_proxies()
            if not hosts_info:
                logger.error("环境变量 %s 为空或 JSON 解析失败，无法进入批量模式", ENV_NAME)
                return 2
            prefer_inner = args.scenario == "private"
            states = to_host_states(hosts_info, prefer_inner_ip=prefer_inner)
            logger.info("Host_Information 解析: %d 台源端主机, %d 台代理主机", len(states), len(proxies))

            workers = args.workers or config.batch.max_workers
            state_file = config.batch.state_file
            if not Path(state_file).is_absolute():
                state_file = str(PROJECT_ROOT / state_file)

            if args.scenario == "private":
                # 私网批量模式 — 经跳板机 gost 多端口转发；代理主机信息来自 Host_Information
                state_file = state_file.replace(".json", "_private.json") if "private" not in state_file else state_file
                orchestrator = PrivateBatchOrchestrator(
                    config=config,
                    hosts_csv="",
                    max_workers=workers,
                    state_file=state_file,
                    callbacks=callbacks,
                    hosts_info=states,
                    proxies=proxies,
                )
            else:
                orchestrator = BatchOrchestrator(
                    config=config,
                    hosts_csv="",
                    max_workers=workers,
                    state_file=state_file,
                    callbacks=callbacks,
                    hosts_info=states,
                )
            result = orchestrator.run()

        else:
            result = None

        if result is not None:

            if args.json_output:
                _output_json({
                    "exit_code": 0 if result.is_success else 1,
                    "mode": "batch",
                    **result.to_dict(),
                })
            else:
                print(result.summary())

            return 0 if result.is_success else 1

        else:
            # ---- 单台模式 ----
            if args.scenario == "public":
                scenario = PublicScenario(config)
            else:
                scenario = PrivateScenario(config)
            scenario.callbacks = callbacks

            result = scenario.run()

            if args.json_output:
                _output_json({
                    "exit_code": 0 if result.success else 1,
                    "mode": "single",
                    **result.to_dict(),
                })
            else:
                print(result.summary())

            return 0 if result.success else 1

    except KeyboardInterrupt:
        logger.info("用户中断")
        if args.json_output:
            _output_json({
                "exit_code": 130,
                "success": False,
                "error_type": "KeyboardInterrupt",
                "error": "用户中断",
            })
        return 130
    except MigrationError as e:
        logger.error("迁移异常: %s [%s]", e.message, e.error_code, exc_info=True)
        if args.json_output:
            _output_json({
                "exit_code": 1,
                "success": False,
                **e.to_dict(),
            })
        else:
            print(f"迁移失败: [{e.error_code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("执行异常: %s", e, exc_info=True)
        if args.json_output:
            _output_json({
                "exit_code": 1,
                "success": False,
                "error_type": type(e).__name__,
                "error": str(e),
            })
        else:
            print(f"执行异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
