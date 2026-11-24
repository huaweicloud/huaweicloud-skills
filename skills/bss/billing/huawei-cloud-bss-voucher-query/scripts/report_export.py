#!/usr/bin/env python3
"""Visual report export for the BSS voucher query skill.

Takes the **same in-memory result** that `list_coupons.py` prints on screen
(no second query) and writes it to a local report file:

- ``xlsx`` — a minimal but Excel / LibreOffice compatible OOXML workbook built
  with the standard library only (``zipfile`` + hand-written SpreadsheetML,
  inline UTF-8 strings, real numeric cells for amounts, auto column widths).
  Four worksheets: 代金券明细 / 临期明细 / 企业项目用量 / 导出信息.
- ``html`` — one self-contained, offline-openable HTML file: detail tables,
  per-enterprise-project 面额/余额/已用 bar chart and a voucher status
  distribution chart. Chart.js is inlined from ``assets/chart.umd.min.js``
  (Chart.js v4.4.0, MIT, https://www.chartjs.org) so the file works with no
  network access.

Both formats are written to a temporary file first and then renamed, so a
failure never leaves a half-written report behind.

Usage (through the skill CLI):

    python3 scripts/list_coupons.py --export xlsx,html [--out-dir DIR] [...]

Environment overrides (tests only):
    VOUCHER_QUERY_REPORT_NOW   frozen "YYYYmmdd_HHMMSS" timestamp for filenames
"""

import json
import os
import re
import tempfile
import zipfile
from datetime import datetime
from html import escape as _html_escape

FORMATS = ("xlsx", "html")
FORMAT_LABELS = {"xlsx": "Excel 工作簿", "html": "自包含 HTML 图表"}

DEFAULT_EXPIRING_DAYS = 30
FILENAME_PREFIX = "bss-voucher-report"
MAX_COL_WIDTH = 60
MIN_COL_WIDTH = 8

SHEET_DETAIL = "代金券明细"
SHEET_EXPIRING = "临期明细"
SHEET_USAGE = "企业项目用量"
SHEET_META = "导出信息"

# SpreadsheetML style indexes (see _STYLES_XML).
STYLE_DEFAULT = 0
STYLE_HEADER = 1
STYLE_MONEY = 2
STYLE_RATE = 3
STYLE_INT = 4

HEADER_LABELS = {
    "coupon_id": "代金券ID",
    "coupon_code": "券码",
    "statusText": "状态",
    "couponTypeText": "类型",
    "plan_name": "促销计划名称",
    "face_value": "面额",
    "balance": "余额",
    "currency": "币种",
    "valid_time": "生效时间",
    "expire_time": "到期时间",
    "active_time": "激活时间",
    "order_id": "订单ID",
    "lock_order_id": "锁定订单ID",
    "project_id": "企业项目ID",
    "project_name": "企业项目名称",
    "project_ids": "企业项目集合",
    "promotion_plan_id": "促销计划ID",
    "customer_id": "客户ID",
    "source_id": "来源ID",
    "useLimits": "使用限制",
}

# Preferred column order for the detail sheet (union of returned fields is
# appended afterwards, mirroring the on-screen table behaviour).
DETAIL_COLUMNS = [
    "coupon_id", "coupon_code", "statusText", "couponTypeText", "plan_name",
    "face_value", "balance", "currency", "valid_time", "expire_time",
    "active_time", "order_id", "project_id", "project_name",
    "promotion_plan_id", "customer_id", "source_id",
]

MONEY_FIELDS = ("face_value", "balance", "total_face", "total_balance", "total_used")


class ExportError(Exception):
    """A report export could not be produced (bad format / unwritable dir)."""


# --------------------------------------------------------------------------- #
# format handling
# --------------------------------------------------------------------------- #
def parse_formats(spec):
    """Parse ``--export`` ("xlsx", "html", "xlsx,html") into an ordered list."""
    if spec is None:
        return []
    text = str(spec).strip()
    if not text:
        return []
    formats = []
    for chunk in re.split(r"[,;\s]+", text):
        if not chunk:
            continue
        key = chunk.strip().lower().lstrip(".")
        if key not in FORMATS:
            raise ExportError(
                "未知导出格式 %r：仅支持 %s（可组合，如 --export xlsx,html）。"
                % (chunk, " / ".join(FORMATS))
            )
        if key not in formats:
            formats.append(key)
    return formats


def _safe_region(region):
    text = re.sub(r"[^0-9A-Za-z._-]+", "-", str(region or "unknown")).strip("-")
    return text or "unknown"


def _stamp(now=None):
    override = os.environ.get("VOUCHER_QUERY_REPORT_NOW")
    if override:
        return override
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def build_report_paths(out_dir, region, formats, now=None, reserved=()):
    """Return {format: absolute path}; never overwrites an existing file."""
    stamp = _stamp(now)
    base = "%s_%s_%s" % (FILENAME_PREFIX, _safe_region(region), stamp)
    paths = {}
    taken = set(reserved)
    for fmt in formats:
        index = 0
        while True:
            name = base if index == 0 else "%s_%d" % (base, index)
            candidate = os.path.abspath(os.path.join(out_dir, "%s.%s" % (name, fmt)))
            if not os.path.exists(candidate) and candidate not in taken:
                break
            index += 1
        taken.add(candidate)
        paths[fmt] = candidate
    return paths


def ensure_out_dir(out_dir):
    """Validate (and create if needed) the export directory; return abs path."""
    path = os.path.abspath(out_dir or ".")
    if os.path.exists(path) and not os.path.isdir(path):
        raise ExportError("导出目录不是目录：%s" % path)
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError as exc:
            raise ExportError("导出目录不存在且无法创建：%s（%s）" % (path, exc))
    if not os.access(path, os.W_OK):
        raise ExportError("导出目录不可写：%s，请用 --out-dir 指定可写目录。" % path)
    return path


def _atomic_write(path, writer):
    """Write via a temp file in the same dir, then rename (no half files)."""
    directory = os.path.dirname(path) or "."
    handle = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            prefix=".bss-report-", suffix=os.path.splitext(path)[1], dir=directory)
        handle = os.fdopen(fd, "wb")
        writer(handle)
        handle.close()
        handle = None
        os.replace(tmp_path, path)
        tmp_path = None
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass
    except OSError as exc:
        raise ExportError("报表写入失败：%s（%s）" % (path, exc))
    finally:
        if handle is not None:
            handle.close()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# --------------------------------------------------------------------------- #
# shared data shaping
# --------------------------------------------------------------------------- #
def _num(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def detail_columns(coupons):
    """Union of returned fields, preferred columns first (like the table)."""
    present = set()
    for coupon in coupons:
        if isinstance(coupon, dict):
            present.update(coupon.keys())
    columns = [key for key in DETAIL_COLUMNS if key in present]
    columns.extend(sorted(present - set(columns)))
    return columns


def detail_rows(coupons):
    columns = detail_columns(coupons)
    rows = []
    for coupon in coupons:
        rows.append({key: coupon.get(key) for key in columns})
    return columns, rows


def status_distribution(coupons):
    """Count vouchers per status label, ordered by count desc then label."""
    buckets = {}
    for coupon in coupons:
        if not isinstance(coupon, dict):
            continue
        label = coupon.get("statusText")
        if not label or label == "-":
            label = "未知"
        buckets[label] = buckets.get(label, 0) + 1
    return sorted(buckets.items(), key=lambda item: (-item[1], item[0]))


def _money_text(value):
    return "-" if value is None else "%.2f" % value


# --------------------------------------------------------------------------- #
# xlsx
# --------------------------------------------------------------------------- #
def _xml_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _col_letter(index):
    """1 -> A, 27 -> AA."""
    letters = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _ref(col_index, row_index):
    return "%s%d" % (_col_letter(col_index), row_index)


def _repr_num(value):
    text = "%.10g" % value
    return text


def _cell_xml(ref, kind, value):
    if kind == "header":
        return '<c r="%s" t="inlineStr" s="%d"><is><t>%s</t></is></c>' % (
            ref, STYLE_HEADER, _xml_escape(_display(value)))
    if kind in ("money", "rate", "int", "number"):
        number = _num(value)
        if number is not None:
            style = {"money": STYLE_MONEY, "rate": STYLE_RATE,
                     "int": STYLE_INT, "number": STYLE_DEFAULT}[kind]
            attr = ' s="%d"' % style if style else ""
            if kind == "int":
                text = str(int(number))
            elif kind == "rate":
                text = _repr_num(number)
            else:
                text = _repr_num(number)
            return '<c r="%s"%s><v>%s</v></c>' % (ref, attr, text)
    return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (
        ref, _xml_escape(_display(value)))


def _display_width(text):
    width = 0
    for char in text:
        width += 2 if ord(char) > 0x2E7F else 1
    return width


def _column_widths(header, rows):
    widths = []
    for index, title in enumerate(header):
        best = _display_width(_display(title))
        for row in rows:
            if index < len(row):
                best = max(best, _display_width(_display(row[index])))
        widths.append(min(max(best + 2, MIN_COL_WIDTH), MAX_COL_WIDTH))
    return widths


def _sheet_xml(header_kinds, rows_kinds, widths):
    """Serialize one worksheet (header row + data rows)."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>',
    ]
    if widths:
        parts.append("<cols>")
        for index, width in enumerate(widths, start=1):
            parts.append(
                '<col min="%d" max="%d" width="%.1f" customWidth="1"/>'
                % (index, index, width))
        parts.append("</cols>")
    parts.append("<sheetData>")
    all_rows = [header_kinds] + rows_kinds
    for row_index, cells in enumerate(all_rows, start=1):
        parts.append('<row r="%d">' % row_index)
        for col_index, (kind, value) in enumerate(cells, start=1):
            parts.append(_cell_xml(_ref(col_index, row_index), kind, value))
        parts.append("</row>")
    parts.append("</sheetData>")
    parts.append("</worksheet>")
    return "".join(parts)


_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="170" formatCode="0.00"/><numFmt numFmtId="171" formatCode="0.0%"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2F5597"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="5">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center"/></xf>
<xf numFmtId="170" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="171" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _content_types_xml(sheet_count):
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.worksheet+xml"/>' % index
        for index in range(1, sheet_count + 1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.styles+xml"/>'
        + overrides + "</Types>")


_ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/></Relationships>')


def _workbook_xml(sheet_names):
    sheets = "".join(
        '<sheet name="%s" sheetId="%d" r:id="rId%d"/>'
        % (_xml_escape(name), index, index)
        for index, name in enumerate(sheet_names, start=1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>" + sheets + "</sheets></workbook>")


def _workbook_rels_xml(sheet_count):
    rels = "".join(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet%d.xml"/>' % (index, index)
        for index in range(1, sheet_count + 1))
    rels += (
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>' % (sheet_count + 1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + rels + "</Relationships>")


def _detail_sheet(coupons):
    columns, rows = detail_rows(coupons)
    header = [(("header"), HEADER_LABELS.get(key, key)) for key in columns]
    body = []
    for row in rows:
        cells = []
        for key in columns:
            value = row.get(key)
            if key in MONEY_FIELDS and _num(value) is not None:
                cells.append((("money"), value))
            else:
                cells.append((("text"), _display(value)))
        body.append(cells)
    widths = _column_widths([value for _, value in header],
                            [[value for _, value in cells] for cells in body])
    return _sheet_xml(header, body, widths)


def _usage_sheet(usage_rows):
    header = [
        ("header", "企业项目ID"), ("header", "企业项目名称"), ("header", "代金券数"),
        ("header", "面额合计"), ("header", "余额合计"), ("header", "已用金额"),
        ("header", "使用率"),
    ]
    body = []
    for row in usage_rows or []:
        body.append([
            ("text", _display(row.get("project_id"))),
            ("text", _display(row.get("project_name"))),
            ("int", row.get("count")),
            ("money", row.get("total_face")),
            ("money", row.get("total_balance")),
            ("money", row.get("total_used")),
            ("rate", row.get("usage_rate")),
        ])
    widths = _column_widths([value for _, value in header],
                            [[value for _, value in cells] for cells in body])
    return _sheet_xml(header, body, widths)


def _meta_sheet(meta, formats, counts):
    header = [("header", "项目"), ("header", "值")]
    items = [
        ("报表生成时间", meta.get("generated_at", "")),
        ("Region", meta.get("region", "")),
        ("筛选条件", meta.get("filters_text") or "无"),
        ("视图", meta.get("view", "")),
        ("代金券条数（明细）", counts.get("detail")),
        ("临期明细条数", counts.get("expiring")),
        ("已过期券条数", counts.get("expired")),
        ("核销口径面额合计", "%.2f" % (meta.get("total_face") or 0.0)),
        ("核销口径余额合计", "%.2f" % (meta.get("total_balance") or 0.0)),
        ("核销口径已用合计", "%.2f" % (meta.get("total_used") or 0.0)),
        ("导出格式", " / ".join(FORMAT_LABELS[fmt] for fmt in formats)),
        ("数据来源", meta.get("source", "")),
        ("报表说明", "明细与屏幕输出同源（同一次查询的内存结果），金额单位为券面币种；"
                     "企业项目归属通过代金券订单关联只读解析，未归属券计入 \"-\"。"),
    ]
    body = []
    for label, value in items:
        if isinstance(value, int):
            body.append([("text", label), ("int", value)])
        else:
            body.append([("text", label), ("text", _display(value))])
    widths = _column_widths([value for _, value in header],
                            [[value for _, value in cells] for cells in body])
    return _sheet_xml(header, body, widths)


def write_xlsx(path, data):
    """Write the four-sheet workbook for `data` (see collect_report_data)."""
    coupons = data.get("coupons") or []
    expiring_rows = data.get("expiring_rows") or []
    usage_rows = data.get("usage_rows") or []
    meta = data.get("meta") or {}
    formats = data.get("formats") or ["xlsx"]

    sheets = [
        (SHEET_DETAIL, _detail_sheet(coupons)),
        (SHEET_EXPIRING, _detail_sheet(expiring_rows)),
        (SHEET_USAGE, _usage_sheet(usage_rows)),
        (SHEET_META, _meta_sheet(meta, formats, {
            "detail": len(coupons),
            "expiring": len(expiring_rows),
            "expired": meta.get("expired_count") or 0,
        })),
    ]

    def writer(handle):
        with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
            archive.writestr("_rels/.rels", _ROOT_RELS_XML)
            archive.writestr("xl/workbook.xml",
                             _workbook_xml([name for name, _ in sheets]))
            archive.writestr("xl/_rels/workbook.xml.rels",
                             _workbook_rels_xml(len(sheets)))
            archive.writestr("xl/styles.xml", _STYLES_XML)
            for index, (_, sheet_xml) in enumerate(sheets, start=1):
                archive.writestr("xl/worksheets/sheet%d.xml" % index, sheet_xml)

    _atomic_write(path, writer)


# --------------------------------------------------------------------------- #
# html
# --------------------------------------------------------------------------- #
HTML_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
       background: #f5f7fa; color: #1a1a2e; padding: 20px; }
.report-header { background: linear-gradient(135deg, #2f5597 0%, #4a7bd0 100%); color: #fff;
                 border-radius: 12px; padding: 26px 28px; margin-bottom: 18px; }
.report-header h1 { font-size: 22px; margin-bottom: 10px; }
.report-header .meta { font-size: 13px; opacity: .92; line-height: 1.9; }
.report-header .meta span { margin-right: 18px; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 14px; margin-bottom: 18px; }
.summary-card { background: #fff; border-radius: 12px; padding: 18px;
                box-shadow: 0 2px 8px rgba(0,0,0,.06); text-align: center; }
.summary-card .label { font-size: 12px; color: #8a94a6; margin-bottom: 6px; }
.summary-card .value { font-size: 24px; font-weight: 700; color: #2f5597; }
.summary-card .sub { font-size: 12px; color: #8a94a6; margin-top: 4px; }
.section { background: #fff; border-radius: 12px; padding: 22px;
           box-shadow: 0 2px 8px rgba(0,0,0,.06); margin-bottom: 18px; }
.section h2 { font-size: 16px; margin-bottom: 14px; padding-left: 10px;
              border-left: 4px solid #2f5597; }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.chart-box { position: relative; height: 320px; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th { background: #eef2f8; padding: 8px 10px; text-align: left; font-weight: 600;
     border-bottom: 2px solid #dde4ef; position: sticky; top: 0; }
td { padding: 7px 10px; border-bottom: 1px solid #f0f2f5; color: #444; }
tr:hover td { background: #f8fafd; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.table-scroll { max-height: 520px; overflow: auto; }
.empty { color: #8a94a6; font-size: 13px; padding: 10px 0; }
.note { font-size: 12px; color: #8a94a6; margin-top: 10px; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 10px;
        background: #eef2f8; color: #2f5597; font-size: 11.5px; }
"""

HTML_SCRIPT = """
(function () {
  var report = __REPORT_DATA__;
  if (typeof Chart === "undefined") { return; }
  var bar = document.getElementById("usageChart");
  if (bar && report.usage.length) {
    new Chart(bar, {
      type: "bar",
      data: {
        labels: report.usage.map(function (row) { return row.label; }),
        datasets: [
          { label: "面额", data: report.usage.map(function (r) { return r.face; }),
            backgroundColor: "#2f5597" },
          { label: "余额", data: report.usage.map(function (r) { return r.balance; }),
            backgroundColor: "#4a7bd0" },
          { label: "已用", data: report.usage.map(function (r) { return r.used; }),
            backgroundColor: "#e8a33d" }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { title: { display: true, text: "企业项目 面额 / 余额 / 已用（元）" } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
  var pie = document.getElementById("statusChart");
  if (pie && report.status.length) {
    new Chart(pie, {
      type: "doughnut",
      data: {
        labels: report.status.map(function (row) { return row.label; }),
        datasets: [{
          data: report.status.map(function (row) { return row.count; }),
          backgroundColor: ["#2f5597", "#4a7bd0", "#e8a33d", "#7c8fa8",
                            "#9b59b6", "#27ae60", "#e74c3c", "#16a085"]
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { title: { display: true, text: "代金券状态分布（张）" },
                   legend: { position: "bottom" } }
      }
    });
  }
})();
"""


def _chart_asset_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "chart.umd.min.js")


def _read_chart_js():
    path = _chart_asset_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise ExportError(
            "缺少本地图表资源 assets/chart.umd.min.js（%s），无法生成自包含 HTML。" % exc)


def _json_for_script(payload):
    return (json.dumps(payload, ensure_ascii=False)
            .replace("</", "<\\/").replace("<", "\\u003c"))


def _html_table(columns, rows):
    if not columns:
        return '<div class="empty">（无数据）</div>'
    head = "".join("<th>%s</th>" % _html_escape(str(HEADER_LABELS.get(key, key)))
                   for key in columns)
    body = []
    for row in rows:
        cells = []
        for key in columns:
            value = row.get(key)
            text = _display(value)
            if key in MONEY_FIELDS and _num(value) is not None:
                cells.append('<td class="num">%s</td>' % _html_escape(_money_text(_num(value))))
            else:
                cells.append("<td>%s</td>" % _html_escape(text))
        body.append("<tr>%s</tr>" % "".join(cells))
    return ('<div class="table-scroll"><table><thead><tr>%s</tr></thead>'
            "<tbody>%s</tbody></table></div>" % (head, "".join(body)))


def _usage_html_table(usage_rows):
    if not usage_rows:
        return '<div class="empty">（无数据）</div>'
    head = "".join("<th>%s</th>" % title for title in (
        "企业项目ID", "企业项目名称", "代金券数", "面额合计", "余额合计",
        "已用金额", "使用率"))
    body = []
    for row in usage_rows:
        body.append(
            "<tr><td>%s</td><td>%s</td><td class=\"num\">%s</td>"
            "<td class=\"num\">%.2f</td><td class=\"num\">%.2f</td>"
            "<td class=\"num\">%.2f</td><td class=\"num\">%.1f%%</td></tr>" % (
                _html_escape(_display(row.get("project_id"))),
                _html_escape(_display(row.get("project_name"))),
                _html_escape(str(row.get("count") or 0)),
                row.get("total_face") or 0.0,
                row.get("total_balance") or 0.0,
                row.get("total_used") or 0.0,
                (row.get("usage_rate") or 0.0) * 100,
            ))
    return ('<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            % (head, "".join(body)))


def write_html(path, data):
    """Write a self-contained (Chart.js inlined) HTML report for `data`."""
    coupons = data.get("coupons") or []
    expiring_rows = data.get("expiring_rows") or []
    usage_rows = data.get("usage_rows") or []
    meta = data.get("meta") or {}
    chart_js = _read_chart_js()

    columns, rows = detail_rows(coupons)
    exp_columns, exp_rows = detail_rows(expiring_rows)

    usage_chart = [
        {"label": (row.get("project_name") or row.get("project_id") or "-"),
         "face": round(row.get("total_face") or 0.0, 2),
         "balance": round(row.get("total_balance") or 0.0, 2),
         "used": round(row.get("total_used") or 0.0, 2)}
        for row in usage_rows
    ]
    status_chart = [{"label": label, "count": count}
                    for label, count in status_distribution(coupons)]
    payload = {"usage": usage_chart, "status": status_chart}

    cards = [
        ("代金券条数", str(len(coupons)), "明细视图"),
        ("面额合计", _money_text(meta.get("total_face")), "核销口径"),
        ("余额合计", _money_text(meta.get("total_balance")), "核销口径"),
        ("已用合计", _money_text(meta.get("total_used")), "面额 - 余额"),
        ("临期券数", str(len(expiring_rows)), meta.get("expiring_label") or "临期视图"),
    ]
    card_html = "".join(
        '<div class="summary-card"><div class="label">%s</div>'
        '<div class="value">%s</div><div class="sub">%s</div></div>'
        % (_html_escape(label), _html_escape(value), _html_escape(sub))
        for label, value, sub in cards)

    meta_spans = "".join(
        "<span>%s: %s</span>" % (_html_escape(label), _html_escape(_display(value)))
        for label, value in (
            ("Region", meta.get("region", "")),
            ("生成时间", meta.get("generated_at", "")),
            ("视图", meta.get("view", "")),
            ("筛选条件", meta.get("filters_text") or "无"),
        ))

    html = []
    html.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                "<title>BSS 代金券报表 - %s</title>\n<style>%s</style>\n</head>\n<body>"
                % (_html_escape(meta.get("region", "")), HTML_CSS))
    html.append(
        '<div class="report-header"><h1>BSS 代金券报表（企业项目维度）</h1>'
        '<div class="meta">%s</div></div>' % meta_spans)
    html.append('<div class="summary-grid">%s</div>' % card_html)
    html.append(
        '<div class="section"><h2>企业项目 面额 / 余额 / 已用</h2>'
        '<div class="charts"><div class="chart-box"><canvas id="usageChart"></canvas></div>'
        '<div class="chart-box"><canvas id="statusChart"></canvas></div></div>'
        '<div class="note">图表数据与下方表格、xlsx 报表同源（同一次查询结果），'
        '金额单位为券面币种；未归属企业项目的券计入 “-”。</div></div>')
    html.append('<div class="section"><h2>企业项目用量分析</h2>%s'
                '<div class="note">使用率 = 已用 / 面额；数据来自代金券面额与余额的本地聚合。</div></div>'
                % _usage_html_table(usage_rows))
    html.append('<div class="section"><h2>代金券明细（%d 条）</h2>%s</div>'
                % (len(rows), _html_table(columns, rows)))
    html.append('<div class="section"><h2>临期明细（%d 条）</h2>%s'
                '<div class="note">已过期的券共 %d 张，明细视图可在导出信息中查看。</div></div>'
                % (len(exp_rows), _html_table(exp_columns, exp_rows),
                   meta.get("expired_count") or 0))
    html.append("<script>%s</script>" % chart_js)
    html.append("<script>%s</script>"
                % HTML_SCRIPT.replace("__REPORT_DATA__", _json_for_script(payload)))
    html.append("</body>\n</html>\n")
    content = "".join(html)

    def writer(handle):
        handle.write(content.encode("utf-8"))

    _atomic_write(path, writer)


# --------------------------------------------------------------------------- #
# entry point used by list_coupons.main()
# --------------------------------------------------------------------------- #
def export_report(data, formats, out_dir, now=None):
    """Export `data` in every requested format; returns [{format, path, ...}]."""
    if not formats:
        return []
    directory = ensure_out_dir(out_dir)
    paths = build_report_paths(directory, data.get("meta", {}).get("region"),
                               formats, now=now)
    results = []
    written = []
    try:
        for fmt in formats:
            path = paths[fmt]
            data["formats"] = formats
            if fmt == "xlsx":
                write_xlsx(path, data)
                records = len(data.get("coupons") or [])
            else:
                write_html(path, data)
                records = len(data.get("coupons") or [])
            written.append(path)
            results.append({"format": fmt, "label": FORMAT_LABELS[fmt],
                            "path": path, "records": records})
    except Exception:
        for path in written:
            try:
                os.remove(path)
            except OSError:
                pass
        raise
    return results