#!/usr/bin/env python3
"""HTML report generator: assembles all sections into a self-contained single file."""

import glob
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from html_template import (
    html_head, html_footer, render_header, render_summary_cards,
    render_topology, render_status_tables, render_detail_boxes,
    render_charts_section, render_conclusion,
)

logger = logging.getLogger(__name__)

# Maximum number of historical reports to keep
MAX_REPORTS = 10


def _cleanup_old_reports(output_dir: str, safe_name: str, keep: int = MAX_REPORTS) -> None:
    """Clean up old reports, keeping only the latest keep copies."""
    pattern = os.path.join(output_dir, f"巡检报告_{safe_name}_*.html")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if len(files) > keep:
        for old_file in files[keep:]:
            try:
                os.remove(old_file)
                logger.info("Cleaned old report: %s", old_file)
            except OSError as e:
                logger.warning("Failed to remove old report %s: %s", old_file, e)


def build_report(
    drill_name: str,
    judgment_result: dict[str, Any],
    instances_by_service: dict[str, list[dict]],
    metrics_by_service: dict[str, list[dict]],
    topology: list[dict],
    duration_s: float,
    start: str,
    end: str,
    output_dir: str = ".",
    runtime: dict[str, Any] | None = None,
) -> str:
    """Generate full HTML report, return output file path."""
    if runtime is None:
        runtime = {}
    timezone_offset = runtime.get("timezone_offset", 8)
    duration_minutes = runtime.get("_duration_minutes", 30)

    # Calculate statistics
    total_items = judgment_result["global"]["total_checks"]
    fail_items = 0  # query failure count (simplified)
    tz = timezone(timedelta(hours=timezone_offset))
    inspect_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # Assemble HTML
    parts = [html_head()]
    parts.append(render_header(drill_name, inspect_time, duration_s, total_items, fail_items))
    parts.append(render_summary_cards(judgment_result, instances_by_service))
    parts.append(render_topology(topology))
    parts.append(render_status_tables(judgment_result))
    parts.append(render_detail_boxes(judgment_result))

    # Chart section
    chart_html, chart_scripts = render_charts_section(
        metrics_by_service, instances_by_service, drill_name, start, end,
        duration_minutes=duration_minutes, timezone_offset=timezone_offset,
    )
    parts.append(chart_html)
    parts.append(render_conclusion(judgment_result))

    # JavaScript
    if chart_scripts:
        parts.append(f"<script>\n{chart_scripts}\n</script>")

    parts.append(html_footer())

    html_content = "\n".join(parts)

    # Write file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = drill_name.replace("/", "_").replace(" ", "_")
    filename = f"巡检报告_{safe_name}_{timestamp}.html"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Clean up old reports, keep only latest MAX_REPORTS
    _cleanup_old_reports(output_dir, safe_name)

    logger.info("Report generated: %s (%.1f KB)", filepath, len(html_content) / 1024)
    return filepath
