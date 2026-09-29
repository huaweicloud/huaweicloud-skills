#!/usr/bin/env python3
"""
error_reporter.py — 错误报告与诊断

收集迁移过程中的错误，分类诊断，给出修复建议。
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ErrorReporter:
    """错误报告与诊断器"""

    # 错误分类规则
    ERROR_PATTERNS = {
        "network": {
            "keywords": ["timeout", "unreachable", "connection refused", "no route",
                        "network is unreachable", "ETIMEDOUT", "ECONNREFUSED",
                        "ssh: connect", "port", "refused"],
            "suggestion": "检查 VPN 连接状态、安全组规则、路由表配置。确认 GOST/squid 代理服务运行正常。",
        },
        "auth": {
            "keywords": ["permission denied", "authentication failed", "access denied",
                        "publickey", "password", "unauthorized", "403", "401"],
            "suggestion": "检查 SSH 密钥/密码配置、AKSK 权限、IAM 策略是否包含所需权限。",
        },
        "sms_agent": {
            "keywords": ["agent not installed", "agent offline", "agent error",
                        "sms agent", "rdAdmin", "source server not found"],
            "suggestion": "确认 SMS Agent 已正确安装并运行。检查 Agent 日志 /var/log/sms/。重启 Agent 服务。",
        },
        "disk_space": {
            "keywords": ["no space left", "disk full", "insufficient space",
                        "ENOSPC", "storage"],
            "suggestion": "清理源端/目标端磁盘空间。检查目标 ECS 系统盘和数据盘容量是否大于源端。",
        },
        "proxy": {
            "keywords": ["proxy", "squid", "gost", "3128", "forwarding",
                        "tunnel", "relay"],
            "suggestion": "检查代理 ECS 上 squid/GOST 服务状态。确认端口监听正常。查看代理服务日志。",
        },
        "vpn": {
            "keywords": ["vpn", "ipsec", "ike", "tunnel down", "phase1", "phase2"],
            "suggestion": "检查 VPN 网关和连接状态。确认 IKE 策略和 IPsec 策略匹配。查看 VPN 日志。",
        },
        "ecs": {
            "keywords": ["ecs", "flavor", "image", "quota", "insufficient",
                        "instance not found", "boot failed"],
            "suggestion": "检查 ECS 规格可用性、镜像状态、配额是否充足。确认 ECS 状态为运行中。",
        },
        "config": {
            "keywords": ["config", "parameter", "invalid", "missing", "required",
                        "excel", "column"],
            "suggestion": "检查 Excel 参数配置。确认必填字段完整、格式正确。参考参数说明文档。",
        },
    }

    def __init__(self, output_dir: str = "/root/migration-work/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.errors: List[Dict[str, Any]] = []

    def add_error(
        self,
        source_ip: str,
        phase: str,
        error_msg: str,
        context: Dict[str, Any] = None,
    ):
        """添加一个错误记录"""
        category, suggestion = self._classify(error_msg)

        error_record = {
            "source_ip": source_ip,
            "phase": phase,
            "error": error_msg,
            "category": category,
            "suggestion": suggestion,
            "context": context or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.errors.append(error_record)
        logger.error(f"[{category}] {source_ip} @ {phase}: {error_msg}")
        logger.info(f"  → 建议: {suggestion}")

    def _classify(self, error_msg: str) -> tuple:
        """分类错误并给出建议"""
        msg_lower = error_msg.lower()

        for category, rule in self.ERROR_PATTERNS.items():
            for keyword in rule["keywords"]:
                if keyword in msg_lower:
                    return category, rule["suggestion"]

        return "unknown", "查看详细日志，联系运维人员排查。"

    def get_errors_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """按分类获取错误"""
        categorized = {}
        for err in self.errors:
            cat = err["category"]
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(err)
        return categorized

    def generate_report(self) -> Dict[str, Any]:
        """生成错误报告"""
        by_category = self.get_errors_by_category()

        report = {
            "total_errors": len(self.errors),
            "by_category": {
                cat: {
                    "count": len(errs),
                    "suggestion": self.ERROR_PATTERNS.get(cat, {}).get("suggestion", ""),
                    "errors": errs,
                }
                for cat, errs in by_category.items()
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return report

    def save_report(self, filename: str = None) -> str:
        """保存错误报告到 JSON"""
        if not filename:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"error_report_{ts}.json"

        path = os.path.join(self.output_dir, filename)
        report = self.generate_report()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Error report saved: {path}")
        return path

    def print_summary(self):
        """打印错误摘要"""
        if not self.errors:
            print("\n✓ 无错误记录")
            return

        report = self.generate_report()
        print(f"\n✗ 共 {report['total_errors']} 个错误:")
        print("-" * 50)
        for cat, info in report["by_category"].items():
            print(f"\n  [{cat}] ({info['count']} 个)")
            print(f"  建议: {info['suggestion']}")
            for err in info["errors"][:3]:  # 每类最多显示3条
                print(f"    - {err['source_ip']} @ {err['phase']}: {err['error'][:60]}")
            if len(info["errors"]) > 3:
                print(f"    ... 还有 {len(info['errors']) - 3} 条")
        print("-" * 50)
