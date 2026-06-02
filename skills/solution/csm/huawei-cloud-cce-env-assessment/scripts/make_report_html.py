#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the final cloud-native assessment report HTML (one-to-one correspondence with the PDF output of make_report.py).

Design notes:
- UTF-8 + lang=zh-CN, preventing Chinese mojibake
- Chinese fonts are provided via CSS system-ui / PingFang / Microsoft YaHei / Noto CJK; no external TTF required
- radar.png / stair.png are embedded as base64, so the single HTML file is self-contained and distributable
- Section order, table columns, and color scheme are identical to the PDF
"""
import os, json, re, datetime, base64, html, openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL  = os.path.join(ROOT, "templates", "report_template.md")
XLSX = os.path.join(ROOT, "artifacts", "cloud-native-summary.xlsx")
META = os.path.join(ROOT, "data", "score_meta.json")
CLUSTER_META_PATH = os.path.join(ROOT, "data", "cluster_meta.json")
RADAR = os.path.join(ROOT, "artifacts", "radar.svg")
STAIR = os.path.join(ROOT, "artifacts", "stair.svg")
# Backward compatibility: if only old PNG exists, will fall back to png later
RADAR_PNG = os.path.join(ROOT, "artifacts", "radar.png")
STAIR_PNG = os.path.join(ROOT, "artifacts", "stair.png")
OUT   = os.path.join(ROOT, "artifacts", "cloud-native-report.html")

# === Cluster/application configuration: prefer cluster_meta.json, then env vars, then defaults ===
_cluster_meta = {}
if os.path.exists(CLUSTER_META_PATH):
    try:
        _cluster_meta = json.load(open(CLUSTER_META_PATH, "r", encoding="utf-8"))
    except Exception as _e:
        print(f"cluster_meta load warn: {_e}")

def _cfg(key, env_keys, default=""):
    val = _cluster_meta.get(key)
    if val:
        return val
    for ek in env_keys:
        if os.environ.get(ek):
            return os.environ[ek]
    return default

CLUSTER_NAME = _cfg("cluster_name", ["CCE_NAME", "CLUSTER_NAME"], "ha-dify-app-cluster")
REGION       = _cfg("region",       ["CCE_Region", "CCE_REGION", "REGION"], "cn-north-4")
APP_NAME     = _cfg("app_name",     ["APP_NAME"], "")
REPO_URL     = _cfg("dockerfile_repo_url", ["Dockerfile_REPO_URL", "DOCKERFILE_REPO_URL"], "")
K8S_VERSION  = _cluster_meta.get("k8s_version") or ""
CATEGORY     = _cluster_meta.get("category") or _cluster_meta.get("type") or "CCE"
FLAVOR       = _cluster_meta.get("flavor") or ""
NODE_COUNT   = _cluster_meta.get("node_count") or 0
NODE_AZS     = _cluster_meta.get("node_az_set") or []
BIZ_WL       = _cluster_meta.get("biz_workloads") or []
INGRESSES    = _cluster_meta.get("ingresses") or []
OVERSIZE_IMGS = _cluster_meta.get("oversize_images") or []

APP_LABEL    = APP_NAME if APP_NAME else "业务"
SCAN_DATE    = os.environ.get("SCAN_DATE") or datetime.datetime.now().strftime("%Y-%m-%d")
CLUSTER_TITLE = f"{CLUSTER_NAME}（华为云 {CATEGORY}）" if CATEGORY else CLUSTER_NAME
AZ_TEXT      = "/".join(NODE_AZS) if NODE_AZS else "未知 AZ"
FLAVOR_TEXT  = FLAVOR or "未知规格"
K8S_TEXT     = f"K8s {K8S_VERSION}" if K8S_VERSION else "K8s 版本未知"
WL_COUNT     = len(BIZ_WL)
_wl_names    = sorted({w.get("name", "") for w in BIZ_WL if w.get("name")})
WL_SUMMARY   = f"{WL_COUNT} 个工作负载" + (f"（{'/'.join(_wl_names[:8])}{'…' if len(_wl_names) > 8 else ''}）" if _wl_names else "")

# === Utility functions ===
def esc(s):
    return html.escape(str(s if s is not None else ""))

def img_b64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def read_svg(path):
    """Read SVG file text (stripping the XML header so it can be embedded in the HTML body)."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        s = f.read()
    # Strip <?xml ?>, <!DOCTYPE ?> declarations (not needed when embedded in body)
    s = re.sub(r"<\?xml[^>]*\?>\s*", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>\s*", "", s)
    return s.strip()

def render_chart(svg_path, png_path, alt):
    """Prefer inline SVG; fall back to a base64 <img> if only the PNG is available."""
    svg = read_svg(svg_path)
    if svg:
        return f'<div class="chart">{svg}</div>'
    png_b64 = img_b64(png_path)
    if png_b64:
        return f'<div class="chart"><img src="data:image/png;base64,{png_b64}" alt="{esc(alt)}" /></div>'
    return f'<p><i>未找到图表：{esc(svg_path)} 或 {esc(png_path)}</i></p>'

# === CSS (self-contained, no external links) ===
CSS = """
:root {
  --c-h1: #1F4E78;
  --c-h2: #2E74B5;
  --c-h3: #305496;
  --c-h4: #444444;
  --c-thead: #305496;
  --c-row-alt: #F2F2F2;
  --c-label-bg: #EAEEF5;
  --c-border: #BBBBBB;
  --c-mut: #888888;
  --c-cover-sub: #A23B72;
  --c-v-full: #70AD47;
  --c-v-most: #5B9BD5;
  --c-v-part: #FFC000;
  --c-v-none: #C00000;
  --c-v-na:   #A6A6A6;
  --c-p0: #C00000;
  --c-p1: #ED7D31;
  --c-p2: #FFC000;
  --c-pother: #7F7F7F;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: #f5f5f5;
  color: #222;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑",
               "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
               sans-serif;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  word-break: break-word;
}
.page {
  max-width: 1080px;
  margin: 20px auto;
  background: white;
  padding: 40px 56px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border-radius: 6px;
}
h1, h2, h3, h4 { font-weight: 600; line-height: 1.35; }
h1 { color: var(--c-h1); font-size: 26px; margin: 36px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--c-h1); }
h2 { color: var(--c-h2); font-size: 20px; margin: 28px 0 12px; padding-left: 10px; border-left: 4px solid var(--c-h2); }
h3 { color: var(--c-h3); font-size: 17px; margin: 22px 0 10px; }
h4 { color: var(--c-h4); font-size: 15px; margin: 16px 0 8px; }
p  { margin: 8px 0; }
ul, ol { margin: 8px 0 12px 24px; padding: 0; }
li { margin: 4px 0; }

.cover {
  text-align: center;
  padding: 80px 20px 40px;
  border-bottom: 1px dashed #ccc;
  margin-bottom: 24px;
}
.cover .title { font-size: 36px; color: var(--c-h1); font-weight: 700; margin-bottom: 32px; }
.cover .meta  { font-size: 16px; margin: 6px 0; color: #444; }
.cover .score { font-size: 20px; font-weight: 600; color: var(--c-cover-sub); margin-top: 24px; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0 18px;
  table-layout: fixed;
}
table th, table td {
  border: 1px solid var(--c-border);
  padding: 8px 10px;
  vertical-align: top;
  text-align: left;
  word-break: break-word;
  overflow-wrap: break-word;
}
table thead th {
  background: var(--c-thead);
  color: white;
  text-align: center;
  font-weight: 600;
}
table.striped tbody tr:nth-child(even) td { background: var(--c-row-alt); }

table.kv th { background: var(--c-label-bg); color: #222; width: 22%; text-align: left; }
table.kv tbody tr:nth-child(even) td { background: white; }

table.item-detail th { background: var(--c-label-bg); color: #222; width: 16%; text-align: left; font-weight: 600; }
table.item-detail td { font-size: 13px; }

table.advice th { background: var(--c-p0); color: white; text-align: center; }
table.advice.p1 th { background: var(--c-p1); }
table.advice.p2 th { background: var(--c-p2); color: #222; }
table.advice.pother th { background: var(--c-pother); }
table.advice td { font-size: 12.5px; }
table.advice tbody tr:nth-child(even) td { background: #F8F8F8; }

.col-num { width: 6%;  text-align: center; }
.col-dim { width: 12%; }
.col-met { width: 20%; }
.col-cur { width: 32%; }
.col-adv { width: 30%; }

.item-card { margin: 14px 0 22px; }
.item-head {
  font-weight: 600;
  font-size: 14.5px;
  padding: 6px 10px;
  background: #FAFBFC;
  border-left: 4px solid var(--c-h3);
  border-radius: 2px;
  margin-bottom: 4px;
}
.verdict-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 3px;
  color: white;
  font-size: 12.5px;
  margin-left: 6px;
}
.v-full { background: var(--c-v-full); }
.v-most { background: var(--c-v-most); }
.v-part { background: var(--c-v-part); color: #222; }
.v-none { background: var(--c-v-none); }
.v-na   { background: var(--c-v-na); }

.chart {
  margin: 12px 0 20px;
  text-align: center;
}
.chart svg {
  max-width: 100%;
  height: auto;
  display: inline-block;
}
.chart img {
  max-width: 100%;
  height: auto;
  border: 1px solid #eee;
  border-radius: 4px;
}

.footer {
  margin-top: 50px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  color: var(--c-mut);
  font-size: 12px;
  text-align: center;
}

@media print {
  body { background: white; }
  .page { box-shadow: none; max-width: 100%; margin: 0; padding: 0; border-radius: 0; }
  h1, h2, h3 { page-break-after: avoid; }
  table, .item-card, .chart { page-break-inside: avoid; }
  .page-break { page-break-before: always; }
}
"""


# === Markdown rendering (consistent with PDF version rules: heading / list / table / paragraph) ===
def _normalize_md_line(raw):
    if raw is None:
        return ("blank", "")
    s = raw.replace("\t", " ").strip()
    if not s:
        return ("blank", "")
    m = re.match(r"^[-*]\s+(.*)$", s)
    if m:
        return ("list", m.group(1).strip())
    return ("text", s)

def md_to_html(md):
    out = []
    lines = md.splitlines()
    i = 0
    in_list = False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if stripped.startswith("### "):
            close_list()
            out.append(f"<h3>{esc(stripped[4:].strip())}</h3>")
        elif stripped.startswith("## "):
            close_list()
            out.append(f"<h2>{esc(stripped[3:].strip())}</h2>")
        elif stripped.startswith("# "):
            close_list()
            out.append(f"<h1>{esc(stripped[2:].strip())}</h1>")
        elif stripped.startswith("|") and i+1 < len(lines) and re.match(r"^\|[\s:|\-]+\|$", lines[i+1].strip()):
            close_list()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            body = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                body.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<table class="striped"><thead><tr>' +
                       "".join(f"<th>{esc(c)}</th>" for c in header) +
                       "</tr></thead><tbody>")
            for row in body:
                out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
            continue
        else:
            kind, text = _normalize_md_line(raw)
            if kind == "blank":
                close_list()
            elif kind == "list":
                if not in_list:
                    out.append("<ul>")
                    in_list = True
                out.append(f"<li>{esc(text)}</li>")
            else:
                close_list()
                out.append(f"<p>{esc(text)}</p>")
        i += 1
    close_list()
    return "\n".join(out)

# === Parse template to get chapters 1, 2 ===
with open(TPL, "r", encoding="utf-8") as f:
    tpl_text = f.read()
def slice_section(text, start_marker, end_marker=None):
    i = text.index(start_marker)
    j = text.index(end_marker, i) if end_marker else len(text)
    return text[i:j].strip()
chap1 = slice_section(tpl_text, "## 1. 云原生技术介绍", "## 2. 云原生设计方法")
chap2 = slice_section(tpl_text, "## 2. 云原生设计方法", "## 3. 现状分析")

# === Load assessment data ===
meta = json.load(open(META, "r", encoding="utf-8"))
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb.active
rows = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r or r[0] is None: continue
    rows.append({
        "num": r[0], "dim": (r[1] or "").replace("\n", "/"), "level": r[2],
        "metric": r[3], "target": r[4], "method": r[5], "desc": r[6],
        "verdict": r[7], "score": r[8], "full": r[9], "basis": r[10],
    })


# === Remediation advice mapping (fully consistent with make_report.py) ===
ADV = {
    18: "为所有工作负载配置 preStop 钩子 + terminationGracePeriodSeconds；entrypoint.sh 改为 'exec' 调用业务进程；如使用服务注册中心需在停止时主动注销。",
    23: f"{APP_LABEL}-plugin-daemon (或类似有状态插件组件) 如使用 hostPath 本地路径，请改为对象存储（OBS）或共享文件存储（SFS Turbo），将插件包元数据写入 PostgreSQL/Redis。",
    25: "升级集群规格至 cce.s2.medium 或更高，或使用 Turbo HA 控制面规格，提供至少 3 个 Master 节点高可用。",
    26: f"扩容节点池跨 {'/'.join(NODE_AZS) if NODE_AZS else '多 AZ'} 至少 2 个 AZ，每 AZ ≥ 1 节点；通过 nodepool 的 az='random' 自动分散。",
    27: f"为业务工作负载添加 nodeSelector/nodeAffinity，按用途划分节点池（例如 {APP_LABEL}-api 调度到通用池，sandbox 调度到高隔离池）。",
    28: f"为 {APP_LABEL}-api / {APP_LABEL}-worker / {APP_LABEL}-web 配置 HPA（CPU 60% / Mem 70%）；定时业务可加 cronhpa-controller 实现定时扩缩。",
    29: "为节点池开启 CCE Autoscaler 插件，设置 min/max 节点数，按 Pending Pod / 节点资源利用率自动扩缩。",
    32: "改造 Python 应用日志格式为 JSON（python-json-logger）；改造 Node.js 日志为 pino/winston JSON 输出；统一携带 trace_id、api_id、上下文字段。",
    34: "在 AOM 控制台创建告警规则：节点 CPU>80%、节点 Mem>85%、Pod 重启率>0、PVC 满载、Ingress 5xx 率等；配置 ActionRule 通过 SMN topic 推送邮件/短信/钉钉。",
    36: "为所有 Deployment 添加 spec.template.spec.securityContext: runAsUser=1000, runAsNonRoot=true, fsGroup=1000；明确禁止 privileged。",
    41: f"为 {APP_LABEL} 命名空间创建专用 ServiceAccount + Role（最小权限）+ RoleBinding；为 argocd/tekton 等控制器审计 ClusterRoleBinding，按 RBAC 最小化裁剪。",
    42: f"为业务 Ingress 配置 tls 段并绑定 CCM 证书；通过 SCM 申请合法证书或使用 cert-manager 自动签发。",
    43: "节点安全组收敛：tcp/22 仅放通堡垒机/办公网段；tcp+udp/30000-32767 NodePort 段全部关闭（已经无 NodePort，可直接删除）；保留 ELB 回源段。",
}
ADV_P1 = {
    2: f"针对大镜像（参考 cluster_meta.json 中 oversize_images）做镜像瘦身：清理 build cache、合并相同 RUN、改用 distroless 或更精简基础镜像、按需安装运行时依赖。",
    9: "将 ubuntu/squid:latest、searxng/searxng:latest 改为固定版本（squid:5.7、searxng:2024.x），并通过 SWR 镜像同步到内网仓库。",
    10: "在企业 SWR 中维护统一的安全基础镜像（如 base-python:3.12-secure / base-node:22-secure），所有业务镜像 FROM 该基线，集中打补丁。",
    14: f"调整 request:limit 比例：核心 {APP_LABEL}-api/{APP_LABEL}-worker 设置 1:1.5~1:2 以保稳定；sandbox 等可放宽到 1:3；避免 1:5+ 的高超分。",
    15: "在 ArgoCD/Tekton 流水线中强制镜像 tag 来源于 git commit-sha；杜绝任何环境直接 `latest`；增加上线前镜像签名校验。",
    19: f"为 {APP_LABEL}-sandbox 增加 livenessProbe；为所有面向流量的 Deployment（{APP_LABEL}-api/web）增加 readinessProbe（启动到注册到 Service 的过渡保护）；启动慢的 plugin-daemon 增加 startupProbe。",
    22: f"单副本业务（参考 cluster_meta.json 中 single_replica_biz）请评估是否需要冗余；如可冗余，副本数 ≥2，并配合 PodDisruptionBudget。",
    24: "扩展到多 AZ 后，启用 topologySpreadConstraints 的 topologyKey=topology.kubernetes.io/zone，并叠加 podAntiAffinity（preferredDuringScheduling）。",
    38: f"hostPath 用法虽非系统敏感目录，但仍不利于跨节点迁移；改为 PVC（基于 SFS Turbo）或 emptyDir + 对象存储。",
}
ADV_P2 = {
    7: "建议改为 ENTRYPOINT 直接 exec form：`ENTRYPOINT [\"gunicorn\", ...]`，省去 bash 包装；如需逻辑判断保留 entrypoint.sh，至少确保 `set -e` + `exec` 一致。",
    14: "（同 P1）requests:limits 比例进一步细化到 1:1 ~ 1:1.5。",
}
ADV_OTHER = {
    37: "本次未取得镜像漏洞扫描结果：共享版 SWR 不支持漏洞扫描 API，请在 SWR 控制台为 cna-demo 命名空间开启镜像安全扫描，或集成 Trivy/Anchore 到 Tekton 流水线，把扫描结果作为 P0 关卡。",
}

VERDICT_CLASS = {
    "完全满足": "v-full",
    "基本满足": "v-most",
    "部分满足": "v-part",
    "未满足":   "v-none",
    "不适用":   "v-na",
    "未评估":   "v-na",
}


# === Build section HTML ===
parts = []

# Cover
parts.append(f"""<section class="cover">
  <div class="title">云原生评估报告</div>
  <div class="meta">评估对象：{esc(CLUSTER_TITLE)}</div>
  <div class="meta">应用：{esc(APP_LABEL)}{(' (' + esc(REPO_URL) + ')') if REPO_URL else ''}</div>
  <div class="meta">评估时间：{esc(SCAN_DATE)}</div>
  <div class="score">综合得分：<b>{esc(meta['overall'])} / 5</b>（{esc(meta['stage'])}）</div>
</section>""")

# Render chapters 1, 2 directly from template
parts.append('<div class="page-break"></div>')
parts.append(md_to_html(chap1))
parts.append('<div class="page-break"></div>')
parts.append(md_to_html(chap2))

# 3. Current State Analysis
parts.append('<div class="page-break"></div>')
parts.append("<h1>3. 现状分析</h1>")

# 3.1
parts.append("<h2>3.1 被扫描对象信息</h2>")
_az_label = ("单 AZ" if len(NODE_AZS) <= 1 else f"{len(NODE_AZS)} 个 AZ") + (f" ({AZ_TEXT})" if NODE_AZS else "")
_scale = f"{CATEGORY} {FLAVOR_TEXT} / {NODE_COUNT} 节点 / {_az_label} / {K8S_TEXT}"
_img_count = len({img for w in BIZ_WL for img in w.get("images", [])})
_img_text = f"业务镜像 {_img_count} 个" + (f"，其中 {len(OVERSIZE_IMGS)} 个超 500MB" if OVERSIZE_IMGS else "")
basic_tbl = [
    ("扫描对象", f"{CLUSTER_NAME}" + (f" ({APP_LABEL} 应用集群)" if APP_NAME else "")),
    ("扫描时间", SCAN_DATE),
    ("集群规模", _scale),
    ("应用数量", WL_SUMMARY or "未采集到业务工作负载"),
    ("镜像数量", _img_text),
]
parts.append('<table class="kv"><tbody>')
for k, v in basic_tbl:
    parts.append(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>")
parts.append("</tbody></table>")

# 3.2 Group by dimension
parts.append("<h2>3.2 云原生评估分析详情</h2>")
DIMS_ORDER = ["服务化", "韧性", "弹性", "自动化", "可观测性", "安全性"]
DIM_FIX = {"安全": "安全性"}
groups = {d: [] for d in DIMS_ORDER}
for r in rows:
    dim_raw = (r["dim"] or "").replace("\n", "/").replace("、", "/").strip()
    pcs = [p.strip() for p in dim_raw.split("/") if p.strip()]
    pcs = [DIM_FIX.get(p, p) for p in pcs]
    for p in pcs:
        if p in groups:
            groups[p].append(r)

for idx, dim in enumerate(DIMS_ORDER, 1):
    items = groups[dim]
    if not items:
        continue
    parts.append(f"<h3>3.2.{idx} {esc(dim)}（{len(items)} 项）</h3>")
    total = sum(it["score"] or 0 for it in items if it["verdict"] != "不适用")
    fullt = sum(it["full"] or 0 for it in items if it["verdict"] != "不适用")
    score5 = round(total/fullt*5, 2) if fullt else 0
    parts.append(f"<p>维度得分：{total} / {fullt}　（5 分制：{score5}）</p>")
    for it in items:
        verdict = it["verdict"] or "未评估"
        klass = VERDICT_CLASS.get(verdict, "v-na")
        parts.append('<div class="item-card">')
        parts.append(
            f'<div class="item-head">评估项 #{esc(it["num"])}　{esc(it["metric"])}'
            f'<span class="verdict-tag {klass}">{esc(verdict)} {esc(it["score"])}/{esc(it["full"])}</span>'
            f'</div>'
        )
        parts.append('<table class="item-detail"><tbody>')
        for k, v in [
            ("量化目标", it["target"]),
            ("验收方式", it["method"]),
            ("级别",    it["level"]),
            ("打分依据", it["basis"]),
        ]:
            parts.append(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>")
        parts.append("</tbody></table>")
        parts.append("</div>")


# 3.3 Overall Score + Radar Chart + Stair Chart
parts.append('<div class="page-break"></div>')
parts.append("<h2>3.3 成熟度评估</h2>")

# 3.3.1
parts.append("<h3>3.3.1 综合评分</h3>")
v = meta["verdict_count"]
score_tbl = [
    ("综合得分（5 分制）", f"{meta['overall']} / 5"),
    ("原始总分", f"{meta['total_score']} / {meta['total_full']}"),
    ("成熟度阶段", meta["stage"]),
    ("完全满足项数", str(v.get("完全满足", 0))),
    ("基本满足项数", str(v.get("基本满足", 0))),
    ("部分满足项数", str(v.get("部分满足", 0))),
    ("未满足项数",   str(v.get("未满足",   0))),
]
parts.append('<table class="kv"><tbody>')
for k, val in score_tbl:
    parts.append(f"<tr><th>{esc(k)}</th><td>{esc(val)}</td></tr>")
parts.append("</tbody></table>")

# 3.3.2 Dimension Scores
parts.append("<h3>3.3.2 各维度评估结果</h3>")
parts.append('<table class="striped"><thead><tr><th>维度</th><th>得分（5 分制）</th></tr></thead><tbody>')
for d, s in meta["dim_scores"].items():
    parts.append(f"<tr><td>{esc(d)}</td><td>{esc(s)}</td></tr>")
parts.append("</tbody></table>")

# Charts (base64 inlined)
# Charts (prefer inline SVG; fall back to base64 PNG if not found)
parts.append("<h4>雷达图：</h4>")
parts.append(render_chart(RADAR, RADAR_PNG, "雷达图"))
parts.append("<h4>阶梯图：</h4>")
parts.append(render_chart(STAIR, STAIR_PNG, "阶梯图"))

# Footer
parts.append(f'<div class="footer">云原生评估报告 · {esc(CLUSTER_NAME)} · {esc(SCAN_DATE)}</div>')

# === Output HTML ===
body_html = "\n".join(parts)
doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>云原生评估报告 - {esc(CLUSTER_NAME)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="page">
{body_html}
  </div>
</body>
</html>
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)
print(f"HTML saved: {OUT}  ({os.path.getsize(OUT)} bytes)")
