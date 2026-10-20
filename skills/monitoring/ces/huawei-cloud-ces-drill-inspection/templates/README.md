# Inspection Report Output Directory

This directory stores generated HTML inspection reports. Reports are automatically output here by `inspect_cli.py inspect`.

- Report naming convention: `巡检报告_<drill_name>_YYYYMMDD_HHMMSS.html`
- Automatic cleanup: only the latest 10 reports are kept; older ones are deleted
- Chart.js is inlined in each report — fully offline-capable, no external dependencies
