#!/usr/bin/env python3
"""
report.py — 迁移报告生成

生成迁移结果报告:
  - HTML 报告 (可视化)
  - JSON 报告 (机器可读)
  - CSV 汇总 (Excel 可打开)
  - 控制台摘要
"""

import os
import csv
import json
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ReportGenerator:
    """迁移报告生成器"""

    def __init__(self, output_dir: str = "/root/migration-work/reports"):
        """
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ──────────────────────────────────────────────────────
    #  控制台摘要
    # ──────────────────────────────────────────────────────

    @staticmethod
    def console_summary(summary: Dict[str, Any]) -> str:
        """生成控制台摘要文本"""
        stats = summary.get("stats", {})
        lines = [
            "",
            "=" * 60,
            "  迁移结果汇总",
            "=" * 60,
            f"  总数:     {stats.get('total', 0)}",
            f"  成功:     {stats.get('success', 0)}",
            f"  失败:     {stats.get('failed', 0)}",
            f"  跳过:     {stats.get('skipped', 0)}",
            f"  耗时:     {summary.get('duration', 0):.1f}s",
            f"  时间:     {summary.get('timestamp', '')}",
            "=" * 60,
        ]

        # 逐条结果
        results = summary.get("results", [])
        if results:
            lines.append("")
            lines.append("  逐条结果:")
            lines.append("-" * 60)
            for r in results:
                source_ip = r.get("source_ip", "N/A")
                status = "✓" if r.get("success") else "✗"
                error = r.get("error", "")[:50] if not r.get("success") else ""
                duration = r.get("duration", 0)
                lines.append(f"  {status} {source_ip:20s} {duration:8.1f}s  {error}")
            lines.append("-" * 60)

        # 步骤追踪详情
        lines.append("")
        lines.append("  步骤追踪详情 (耗时/阻塞/问题):")
        lines.append("-" * 60)
        for r in results:
            source_ip = r.get("source_ip", "N/A")
            st = r.get("step_tracking")
            if not st:
                lines.append(f"  {source_ip}: 无步骤追踪数据")
                continue
            lines.append(f"  {source_ip}:")
            for step in st.get("steps", []):
                step_name = step.get("name", "")
                step_dur = step.get("duration", 0)
                step_status = step.get("status", "")
                icon = "✓" if step_status == "success" else "✗" if step_status == "failed" else "○"
                line = f"    {icon} {step_name:40s} {step_dur:8.1f}s"
                blockings = step.get("blockings", [])
                issues = step.get("issues", [])
                if blockings:
                    line += f"  阻塞:{len(blockings)}"
                if issues:
                    line += f"  问题:{len(issues)}"
                lines.append(line)
                for b in blockings:
                    bdesc = b.get("description", str(b)) if isinstance(b, dict) else str(b)
                    lines.append(f"      ⚠ 阻塞: {bdesc[:60]}")
                for i in issues:
                    idesc = i.get("description", str(i)) if isinstance(i, dict) else str(i)
                    lines.append(f"      ! 问题: {idesc[:60]}")
        lines.append("-" * 60)

        text = "\n".join(lines)
        print(text)
        return text

    # ──────────────────────────────────────────────────────
    #  JSON 报告
    # ──────────────────────────────────────────────────────

    def save_json(self, summary: Dict[str, Any], filename: str = None) -> str:
        """保存 JSON 报告"""
        if not filename:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"migration_report_{ts}.json"

        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON report saved: {path}")
        return path

    # ──────────────────────────────────────────────────────
    #  CSV 报告
    # ──────────────────────────────────────────────────────

    def save_csv(self, summary: Dict[str, Any], filename: str = None) -> str:
        """保存 CSV 报告"""
        if not filename:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"migration_report_{ts}.csv"

        path = os.path.join(self.output_dir, filename)

        results = summary.get("results", [])
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "源端IP", "目标ECS_ID", "任务名称", "状态",
                "耗时(秒)", "阶段", "错误信息", "SMS任务ID", "源端ID",
                "步骤追踪_步骤数", "步骤追踪_总耗时", "步骤追踪_阻塞数", "步骤追踪_问题数",
                "步骤追踪_详情",
            ])

            for r in results:
                st = r.get("step_tracking") or {}
                steps = st.get("steps", [])
                step_count = len(steps)
                step_total_dur = sum(s.get("duration", 0) for s in steps)
                blocker_count = sum(len(s.get("blockings", [])) for s in steps)
                issue_count = sum(len(s.get("issues", [])) for s in steps)
                step_details = "; ".join(
                    f"{s.get('name','')}({s.get('duration',0):.1f}s,{s.get('status','')})"
                    for s in steps
                )
                writer.writerow([
                    r.get("source_ip", ""),
                    r.get("target_server_id", ""),
                    r.get("task_name", ""),
                    "成功" if r.get("success") else "失败",
                    r.get("duration", 0),
                    r.get("phase", ""),
                    r.get("error", ""),
                    r.get("task_id", ""),
                    r.get("source_id", ""),
                    step_count,
                    round(step_total_dur, 1),
                    blocker_count,
                    issue_count,
                    step_details,
                ])

        logger.info(f"CSV report saved: {path}")
        return path

    # ──────────────────────────────────────────────────────
    #  HTML 报告
    # ──────────────────────────────────────────────────────

    def save_html(self, summary: Dict[str, Any], filename: str = None) -> str:
        """保存 HTML 报告"""
        if not filename:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"migration_report_{ts}.html"

        path = os.path.join(self.output_dir, filename)

        stats = summary.get("stats", {})
        results = summary.get("results", [])

        # 计算成功率
        total = stats.get("total", 0)
        success = stats.get("success", 0)
        success_rate = (success / total * 100) if total > 0 else 0

        # 生成 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>迁移结果报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ padding: 15px 25px; border-radius: 8px; color: white; }}
        .card.total {{ background: #2196F3; }}
        .card.success {{ background: #4CAF50; }}
        .card.failed {{ background: #f44336; }}
        .card.skipped {{ background: #FF9800; }}
        .card .num {{ font-size: 28px; font-weight: bold; }}
        .card .label {{ font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .ok {{ color: #4CAF50; }}
        .fail {{ color: #f44336; }}
        .progress {{ background: #e0e0e0; border-radius: 4px; height: 20px; margin: 10px 0; }}
        .progress-bar {{ background: #4CAF50; height: 100%; border-radius: 4px; }}
        .step-section {{ margin-top: 30px; }}
        .step-section h2 {{ color: #333; border-bottom: 2px solid #2196F3; padding-bottom: 5px; }}
        .host-steps {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 4px; }}
        .host-steps h3 {{ color: #2196F3; margin: 0 0 8px 0; }}
        .step-row {{ display: flex; align-items: center; gap: 10px; padding: 4px 0; border-bottom: 1px solid #eee; }}
        .step-name {{ flex: 1; }}
        .step-dur {{ color: #666; font-size: 13px; }}
        .step-badge {{ padding: 2px 8px; border-radius: 3px; font-size: 12px; color: white; }}
        .step-badge.blocker {{ background: #f44336; }}
        .step-badge.issue {{ background: #FF9800; }}
        .blocker-text {{ color: #f44336; font-size: 12px; padding-left: 20px; }}
        .issue-text {{ color: #FF9800; font-size: 12px; padding-left: 20px; }}
    </style>
</head>
<body>
    <h1>私网环境 VMware → ECS 迁移结果报告</h1>
    <p>生成时间: {summary.get('timestamp', '')} | 总耗时: {summary.get('duration', 0):.1f}s</p>

    <div class="summary">
        <div class="card total"><div class="num">{total}</div><div class="label">总数</div></div>
        <div class="card success"><div class="num">{success}</div><div class="label">成功</div></div>
        <div class="card failed"><div class="num">{stats.get('failed', 0)}</div><div class="label">失败</div></div>
        <div class="card skipped"><div class="num">{stats.get('skipped', 0)}</div><div class="label">跳过</div></div>
    </div>

    <div class="progress">
        <div class="progress-bar" style="width: {success_rate:.0f}%"></div>
    </div>
    <p>成功率: {success_rate:.1f}%</p>

    <table>
        <tr>
            <th>源端 IP</th>
            <th>目标 ECS</th>
            <th>状态</th>
            <th>阶段</th>
            <th>耗时(s)</th>
            <th>错误信息</th>
        </tr>
"""
        for r in results:
            status_class = "ok" if r.get("success") else "fail"
            status_text = "✓ 成功" if r.get("success") else "✗ 失败"
            error = r.get("error", "")
            if len(error) > 80:
                error = error[:80] + "..."
            html += f"""        <tr>
            <td>{r.get('source_ip', '')}</td>
            <td>{r.get('target_server_id', '')[:20]}...</td>
            <td class="{status_class}">{status_text}</td>
            <td>{r.get('phase', '')}</td>
            <td>{r.get('duration', 0)}</td>
            <td>{error}</td>
        </tr>
"""

        # 步骤追踪详情 section
        html += """    </table>

    <div class="step-section">
        <h2>步骤追踪详情 (耗时 / 阻塞 / 问题)</h2>
"""
        for r in results:
            source_ip = r.get("source_ip", "N/A")
            st = r.get("step_tracking")
            if not st:
                html += f"""        <div class="host-steps">
            <h3>{source_ip}</h3>
            <p>无步骤追踪数据</p>
        </div>
"""
                continue
            html += f"""        <div class="host-steps">
            <h3>{source_ip}</h3>
"""
            for step in st.get("steps", []):
                step_name = step.get("name", "")
                step_dur = step.get("duration", 0)
                step_status = step.get("status", "")
                icon = "✓" if step_status == "success" else "✗" if step_status == "failed" else "○"
                blockings = step.get("blockings", [])
                issues = step.get("issues", [])
                html += f"""            <div class="step-row">
                <span>{icon}</span>
                <span class="step-name">{step_name}</span>
                <span class="step-dur">{step_dur:.1f}s</span>
"""
                if blockings:
                    html += f'                <span class="step-badge blocker">阻塞 {len(blockings)}</span>\n'
                if issues:
                    html += f'                <span class="step-badge issue">问题 {len(issues)}</span>\n'
                html += "            </div>\n"
                for b in blockings:
                    bdesc = b.get("description", str(b)) if isinstance(b, dict) else str(b)
                    html += f'            <div class="blocker-text">⚠ {bdesc}</div>\n'
                for i in issues:
                    idesc = i.get("description", str(i)) if isinstance(i, dict) else str(i)
                    html += f'            <div class="issue-text">! {idesc}</div>\n'
            html += "        </div>\n"

        html += """    </div>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML report saved: {path}")
        return path

    # ──────────────────────────────────────────────────────
    #  生成所有格式
    # ──────────────────────────────────────────────────────

    def generate_all(self, summary: Dict[str, Any]) -> Dict[str, str]:
        """生成所有格式的报告

        Returns:
            {"json": path, "csv": path, "html": path}
        """
        self.console_summary(summary)
        return {
            "json": self.save_json(summary),
            "csv": self.save_csv(summary),
            "html": self.save_html(summary),
        }
