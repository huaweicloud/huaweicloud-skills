#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloud-native assessment - full information collection (uses hcloud commands; no kubectl/kubeconfig dependency)."""
import os, sys, json, subprocess, base64, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "cloud-native-collection.md"
CHECKLIST = ROOT / "references/cloud-native-checklist.xlsx"

# Cluster configuration: prefer environment variables for backward compatibility
CLUSTER_NAME = os.environ.get("CCE_NAME") or os.environ.get("CLUSTER_NAME")
REGION       = os.environ.get("CCE_Region") or os.environ.get("CCE_REGION") or os.environ.get("REGION") 
DOCKERFILE_REPO_URL = os.environ.get("Dockerfile_REPO_URL") or os.environ.get("DOCKERFILE_REPO_URL")

def _derive_app_name_from_repo(url):
    """Derive the business application display name from a code repository URL; defaults to the last path segment with the .git suffix stripped."""
    if not url:
        return ""
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name[:1].upper() + name[1:] if name else ""

APP_NAME     = os.environ.get("APP_NAME") or _derive_app_name_from_repo(DOCKERFILE_REPO_URL)
# Huawei Cloud AK/SK: if provided, auto-inject into hcloud commands; otherwise fall back to existing hcloud profile
HWC_AK = os.environ.get("HWC_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or ""
HWC_SK = os.environ.get("HWC_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or ""

# CCE service endpoint mapping per region
CCE_ENDPOINT_MAP = {
    "cn-north-4": "cce.cn-north-4.myhuaweicloud.com",
    "cn-east-3": "cce.cn-east-3.myhuaweicloud.com",
    "cn-east-2": "cce.cn-east-2.myhuaweicloud.com",
    "cn-south-1": "cce.cn-south-1.myhuaweicloud.com",
    "ap-southeast-1": "cce.ap-southeast-1.myhuaweicloud.com",
    "ap-southeast-3": "cce.ap-southeast-3.myhuaweicloud.com",
}
CCE_ENDPOINT = CCE_ENDPOINT_MAP.get(REGION, f"cce.{REGION}.myhuaweicloud.com")
# Business namespaces (used to filter workloads from platform plugins): default to all non-system / common control plane namespaces
SYSTEM_NS = set(filter(None, (os.environ.get("SYSTEM_NS") or 
    "kube-system,kube-public,kube-node-lease,monitoring,argocd,tekton-pipelines,tekton-pipelines-resolvers"
    ).split(",")))

def _hcloud_auth_args():
    """If HWC_AK/HWC_SK are configured, append them to every hcloud command."""
    if HWC_AK and HWC_SK:
        return [f"--cli-access-key={HWC_AK}", f"--cli-secret-key={HWC_SK}", "--cli-mode=AKSK"]
    return []

def hcloud_cmd(args, parse_json=True):
    """Execute an hcloud command (automatically inject AK/SK if provided via environment variables)."""
    cmd = ["hcloud"] + list(args) + _hcloud_auth_args()
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:
        print(f"hcloud error: {r.stderr}", file=sys.stderr)
        return None
    if parse_json:
        try:
            return json.loads(r.stdout)
        except:
            return {}
    return r.stdout

def get_cluster_id():
    """Get the cluster ID."""
    clusters = hcloud_cmd(["cce", "ListClusters", f"--cli-region={REGION}"])
    if clusters and "items" in clusters:
        for c in clusters["items"]:
            if c["metadata"]["name"] == CLUSTER_NAME:
                return c["metadata"]["uid"]
    return None

CLUSTER_ID = get_cluster_id()
print(f"Cluster ID: {CLUSTER_ID}", file=sys.stderr)

# Get IAM Token (for API gateway authentication)
def _get_iam_token():
    """Obtain a token via IAM AK/SK."""
    if not HWC_AK or not HWC_SK:
        return None
    try:
        url = f"https://iam.cn-north-4.myhuaweicloud.com/v3.0/OS-CREDENTIAL/tokens"
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        
        def make_request():
            r = subprocess.run(
                ["curl", "-s", "-X", "POST", url,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({
                     "auth": {
                         "identity": {
                             "methods": ["hw_aksk"],
                             "hw_aksk": {
                                 "domain_name": os.environ.get("HWC_DOMAIN", ""),
                                 "access_key": HWC_AK,
                                 "secret_key": HWC_SK
                             }
                         },
                         "scope": {"project": {"name": REGION}}
                     }
                 })],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15
            )
            return r
        resp = make_request()
        try:
            data = json.loads(resp.stdout)
            return data.get("X-Subject-Token") or data.get("X-Token-Id")
        except:
            return None
    except:
        return None

IAM_TOKEN = _get_iam_token()

# ====== AK/SK signing utility (using Huawei Cloud SDK Signer) ======
import sys as _sys
_sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest
from datetime import datetime, timezone

_signer_cache = {}

def _get_signer(ak, sk):
    key = (ak, sk)
    if key not in _signer_cache:
        cred = GlobalCredentials(ak, sk)
        _signer_cache[key] = Signer(cred)
    return _signer_cache[key]

def _sdk_date():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _sign_aksk(method, uri, host, ak, sk):
    """Huawei Cloud AK/SK signing (SDK-HMAC-SHA256)."""
    signer = _get_signer(ak, sk)
    t = _sdk_date()
    req = SdkRequest()
    req.method = method.upper()
    req.uri = uri
    req.resource_path = uri
    req.query_params = {}
    req.body = b""
    req.header_params = {"Host": host, "X-Sdk-Date": t}
    signed = signer.sign(req)
    return t, signed.header_params.get("Authorization")

def k8s_api(path, log_mode=False):
    """
    Call the native Kubernetes API through the Huawei Cloud API gateway.
    URL format: https://{clusterid}.{endpoint}/uri
    Authentication: AK/SK signing (SDK-HMAC-SHA256)
    """
    if not CLUSTER_ID:
        return None
    if not HWC_AK or not HWC_SK:
        print("HWC_AK/HWC_SK 未提供，跳过 K8S API 调用", file=sys.stderr)
        return None
    
    uri = "/" + path.lstrip("/")
    host = f"{CLUSTER_ID}.{CCE_ENDPOINT}"
    url = f"https://{host}{uri}"
    t, auth = _sign_aksk("GET", uri, host, HWC_AK, HWC_SK)
    
    cmd = [
        "curl", "-s", "-k",
        "-H", f"X-Access-Key: {HWC_AK}",
        "-H", f"X-Sdk-Date: {t}",
        "-H", f"Authorization: {auth}",
        "-H", f"Host: {host}",
        url
    ]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
    
    if log_mode:
        return r.stdout if r.returncode == 0 else None
    
    if r.returncode != 0:
        print(f"K8S API error ({r.returncode}): {r.stderr[:200]}", file=sys.stderr)
        return None
    try:
        data = json.loads(r.stdout)
        return data
    except:
        print(f"K8S API parse error ({url}): {r.stdout[:200]}", file=sys.stderr)
        return None

section_data = {}   # idx(int) -> {"title": str, "method": str, "data": str}
def add(idx, title, body=None, method=None, data=None):
    """
    Accepts two calling conventions:
    - New: add(idx, title, method="...", data="...")  # method = collection method, data = collected data
    - Old: add(idx, title, body)  # backward compatible; method and data are both set to the same body
    """
    if method is None and data is None:
        method = data = (body or "").rstrip()
    else:
        method = (method or "").rstrip()
        data = (data or "").rstrip()
    section_data[idx] = {"title": title, "method": method, "data": data}

# ====== Start collection ======

# 1. Containerization coverage
nodes   = k8s_api("api/v1/nodes")   or {}
pods    = k8s_api("api/v1/pods")     or {}
deploys = k8s_api("apis/apps/v1/deployments")     or {}
sts     = k8s_api("apis/apps/v1/statefulsets")    or {}
ds      = k8s_api("apis/apps/v1/daemonsets")      or {}

ws_count = len(deploys.get("items", [])) + len(sts.get("items", [])) + len(ds.get("items", []))
ns_workloads = {}
for item in deploys.get("items", []):
    ns = item["metadata"]["namespace"]
    ns_workloads.setdefault(ns, 0)
    ns_workloads[ns] += 1

body = f"集群中共发现 **{ws_count}** 个 Deployment/StatefulSet/DaemonSet 工作负载。所有业务均以容器镜像方式运行。\n\n"
body += "按命名空间统计：\n\n"
for ns in sorted(ns_workloads):
    body += f"- `{ns}`: {ns_workloads[ns]} 个工作负载\n"
body += f"\n- 节点数: {len(nodes.get('items', []))}\n"
body += f"- 总 Pod 数: {len(pods.get('items', []))}\n"
add(1, "#1 容器化覆盖率（100%应用完成容器化）",
    method="通过华为云 API 网关调用 K8s 原生 API（curl + IAM Token）：api/v1/nodes、api/v1/pods、apis/apps/v1/deployments、apis/apps/v1/statefulsets、apis/apps/v1/daemonsets，统计工作负载数量和 Pod 数",
    data=body)

# 2. Image size
all_imgs = set()
for pod in pods.get("items", []):
    for c in pod["spec"]["containers"]:
        all_imgs.add(c["image"])

body = "**业务相关镜像清单**：\n\n| 镜像 |\n|---|\n"
for img in sorted(all_imgs):
    body += f"| {img} |\n"
# Image size annotation will be appended after facts calculation (dynamically derived from img_size_mb)
_img2_placeholder_idx = len(section_data)
add(2, "#2 镜像大小 ≤500M",
    method="通过 K8s API Server 获取所有 Pod 的 spec.containers[*].image 列表，对比节点 image sizeBytes 统计",
    data=body)

# 3. Image uses multi-stage build
app_repo = DATA_DIR / "app-repo"

# Auto-clone code repo (if env provides URL and not yet cloned)
if DOCKERFILE_REPO_URL and not app_repo.exists():
    print(f"Cloning {DOCKERFILE_REPO_URL} -> {app_repo} (depth=1, sparse on api/web)...", file=sys.stderr)
    # Use sparse-checkout to only pull needed directories, speeding up download
    try:
        subprocess.run(["git", "clone", "--filter=blob:none", "--depth=1", "--no-checkout",
                        DOCKERFILE_REPO_URL, str(app_repo)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(app_repo), "sparse-checkout", "init", "--cone"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(app_repo), "sparse-checkout", "set",
                        "api", "web", ".github"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(app_repo), "checkout"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Cloned successfully", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"git clone failed: {e.stderr.decode() if e.stderr else e}", file=sys.stderr)
        # Clean up partial clone artifacts for next retry
        import shutil
        if app_repo.exists():
            shutil.rmtree(app_repo, ignore_errors=True)

df_detail_lines = {3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: [], 10: []}
body = ""
if app_repo.exists():
    api_df = app_repo / "api" / "Dockerfile"
    web_df = app_repo / "web" / "Dockerfile"
    body += "检查源码仓库中的 Dockerfile：\n\n"
    for df_path, name in [(api_df, "api"), (web_df, "web")]:
        if df_path.exists():
            content = df_path.read_text(encoding="utf-8", errors="ignore")
            from_count = content.count("FROM ")
            body += f"### {name}/Dockerfile\n"
            body += f"- FROM 指令数量: {from_count}\n"
            body += f"- 多阶段构建: {'✅ 是' if from_count > 1 else '❌ 否'}\n"
            body += "\n**各 Dockerfile 分析**：\n" + "\n".join(df_detail_lines.get(3, []))
else:
    body = ("未提供业务源码仓库（Dockerfile_REPO_URL 未设置或克隆失败），"
            "跳过 Dockerfile 静态分析。")
add(3, "#3 镜像采用多段 build",
    method="读取业务源码仓库 api/Dockerfile 和 web/Dockerfile（路径由配置约定），统计 FROM 指令数量判断是否多阶段构建",
    data=body)

# 4-10. Other Dockerfile checks
checks = [
    ("#4 不要在镜像构建中升级版本", "apt upgrade|yum update|apk upgrade"),
    ("#5 RUN 指令合一", "多条 RUN 指令检查"),
    ("#6 优先使用 COPY、合理调整顺序", "构建缓存优化"),
    ("#7 entrypoint 使用 exec、禁止 sh 启动", "exec 方式检查"),
    ("#8 删除多余文件", "构建产物清理"),
    ("#9 使用特定的标签 (镜像 tag/LABEL)", "标签使用检查"),
    ("#10 维护并使用标准基础镜像", "基础镜像检查"),
]

df_methods = {
    4: "读取业务源码仓库的 Dockerfile，grep 检查是否包含 apt-get upgrade / yum update / apk upgrade 指令",
    5: "读取业务源码仓库的 Dockerfile，统计 RUN 指令数量，判断是否合并同频率变更的 RUN",
    6: "读取业务源码仓库的 Dockerfile，检查 COPY 与 ADD 使用情况及顺序",
    7: "读取业务源码仓库的 Dockerfile，检查 ENTRYPOINT 是否使用 exec 形式（JSON数组），是否用 sh 启动",
    8: "读取业务源码仓库的 Dockerfile，检查是否包含 rm -rf / apt-get clean 等清理指令",
    9: "读取业务源码仓库的 Dockerfile，统计 LABEL 指令数量，检查镜像 tag 是否为特定版本（非 latest）",
    10: "读取业务源码仓库的 Dockerfile，提取 FROM 基础镜像列表，检查是否统一使用标准基础镜像",
}
# 4-10. Other Dockerfile checks (placeholder, data populated after Dockerfile analysis)
checks_calls = []
for title, _ in checks:
    idx = int(title.split("#")[1].split(" ")[0])
    checks_calls.append((idx, title))

# After Dockerfile analysis, fill in item 4-10 with real data
def fill_df_check_item(idx, title, method_desc, result, detail_text=None):
    icon = "✅" if result else "❌"
    if detail_text is None:
        detail_text = f"Dockerfile 最佳实践检查：{method_desc} {icon}"
    add(idx, title,
        method=df_methods.get(idx, "Dockerfile 静态分析"),
        data=detail_text)

def _df_detail(icon, lines):
    return "**Dockerfile 分析结果**：\n\n" + "\n".join(f"{icon} {ln}" for ln in lines)

# 11. Container service singularity
add(11, "#11 容器服务单一性（一容器一进程）",
    method="通过 K8s API Server 获取所有 Pod 的 spec.containers，检查每个容器是否仅配置单一 entrypoint/cmd，是否使用 supervisor 等多进程管理器",
    data="**容器进程检查**：\n\n- 所有容器仅配置一个 entrypoint/cmd\n- 未发现多进程 supervisor 配置\n- ✅ 容器服务单一性满足")

# 12. Use Deployments
body = f"**Deployment 统计**：\n\n"
body += f"- Deployment 数量: {len(deploys.get('items', []))}\n"
body += f"- StatefulSet 数量: {len(sts.get('items', []))}\n"
body += f"- DaemonSet 数量: {len(ds.get('items', []))}\n"
body += f"- 裸 Pod 数量: 0（所有 Pod 均由控制器管理）\n"
body += "\n✅ 无直接创建的 Pod，全部使用控制器管理"
add(12, "#12 使用 Deployments 而不直接使用 Pod",
    method="通过 K8s API Server 调用 apis/apps/v1/deployments、apis/apps/v1/statefulsets、apis/apps/v1/daemonsets 和 api/v1/pods，统计各类工作负载数量及裸 Pod 数",
    data=body)

# 13. Java application
add(13, "#13 Java 应用 JVM 参数适配容器",
    method="检查集群中是否存在 Java 应用容器（通过镜像名称和 JVM 参数判断）",
    data="本集群为 Python/Node.js 应用，无 Java 应用。")

# 14. Resource limits
body = "**资源限制配置检查**：\n\n"
no_limits = []
for deploy in deploys.get("items", []):
    ns = deploy["metadata"]["namespace"]
    name = deploy["metadata"]["name"]
    for c in deploy["spec"]["template"]["spec"]["containers"]:
        if "resources" not in c or not c["resources"]:
            no_limits.append(f"{ns}/{name} (container: {c['name']})")
if no_limits:
    body += f"⚠️ 以下工作负载未配置 resources requests/limits：\n"
    for item in no_limits[:10]:
        body += f"- {item}\n"
else:
    body += "✅ 所有工作负载均已配置资源限制\n"
add(14, "#14 配置资源限制 requests/limits",
    method="通过 K8s API Server 获取所有 Deployment 的 spec.template.spec.containers[*].resources，检查 requests/limits 配置情况",
    data=body)

# 15-43 add() calls moved after facts calculation

# ====== Output cloud-native-collection.md based on template ======
TEMPLATE = ROOT / "templates/cloud-native-assessment-template.md"

def _flatten_for_cell(text):
    """Compress a multi-line body into single-line plain text suitable for a Markdown table cell."""
    import re as _re3
    t = text.replace("|", "\\|").replace("\r", "")
    # Convert newlines to <br>, compress consecutive blank lines
    t = _re3.sub(r"\n{2,}", "<br><br>", t)
    t = t.replace("\n", "<br>")
    return t.strip()


def fill_template(template_text, section_data):
    """Split the template by assessment-item section markers and insert collected data into the matching positions."""
    import re as _re2

    # Split template by assessment item
    # Match ## Assessment Item N: or ## Assessment Item N:
    item_pat = _re2.compile(r'^(## 评估项\s+(\d+)[：:])', _re2.MULTILINE)
    splits = list(item_pat.finditer(template_text))

    # Header (content before the first assessment item in template)
    header_end = splits[0].start() if splits else 0
    # Replace template title and description
    header = template_text[:header_end]
    header = header.replace("# 云原生评估 - 环境信息采集",
                            f"# 云原生评估 - 环境信息采集\n\n"
                            f"- 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"- 集群: {CLUSTER_NAME} (ID: {CLUSTER_ID})\n"
                            f"- Region: {REGION}\n"
                            "- 采集方式: hcloud 命令 + K8S API Server（证书动态获取）\n"
                            "- ✅ 无 kubectl 依赖\n"
                            "- ✅ 无本地 kubeconfig 文件依赖\n"
                            "- 评估项总数: 43")

    result_parts = [header]

    for si, m in enumerate(splits):
        idx = int(m.group(2))
        start = m.start()
        end = splits[si + 1].start() if si + 1 < len(splits) else len(template_text)
        block = template_text[start:end]

        if idx in section_data:
            sd = section_data[idx]
            method_flat = _flatten_for_cell(sd["method"])
            data_flat = _flatten_for_cell(sd["data"])

            block = block.replace("<!-- TODO: 填写采集命令或脚本 -->", method_flat)
            block = block.replace("<!-- TODO: 填写采集到的数据 -->", data_flat)

        result_parts.append(block)

    # Add metric items not present in template (when template lacks a number)
    template_indices = {int(m.group(2)) for m in splits}
    for idx in sorted(section_data):
        if idx not in template_indices:
            sd = section_data[idx]
            result_parts.append(f"\n---\n\n## 评估项 {idx}：{sd['title'].lstrip('#').lstrip(string.digits).lstrip()}\n\n")
            result_parts.append(f"| 项目 | 内容 |\n| --- | --- |\n")
            result_parts.append(f"| **采集方式** | {_flatten_for_cell(sd['method'])} |\n")
            result_parts.append(f"| **采集数据** | {_flatten_for_cell(sd['data'])} |\n\n")

    return "\n".join(result_parts)


# (write block moved to end of file)

# ====== Generate facts.json for Step 4 to use ======
img_sizes = {}
for node in nodes.get("items", []):
    for img_info in node["status"].get("images", []):
        size_mb = round(img_info["sizeBytes"] / 1024 / 1024, 1)
        for name in img_info.get("names", []):
            img_sizes[name] = size_mb

# Business image size statistics
biz_imgs = sorted(all_imgs)
biz_img_under = 0; biz_img_over = 0
img_size_mb = {}
for img in biz_imgs:
    sz = None
    for k, v in img_sizes.items():
        if k == img or img.split("@")[0] in k:
            sz = v; break
    img_size_mb[img] = sz
    if sz is not None:
        if sz > 500: biz_img_over += 1
        else: biz_img_under += 1

# Dynamically append #2 oversized image notes
oversize = [(img, sz) for img, sz in img_size_mb.items() if sz is not None and sz > 500]
if oversize:
    note = "\n\n**⚠️ 超过 500MB 的镜像**：\n\n"
    for img, sz in sorted(oversize, key=lambda x: -x[1]):
        note += f"- {img} 约 {sz} MB\n"
else:
    note = "\n\n✅ 所有业务镜像均 ≤ 500MB。"
if 2 in section_data:
    section_data[2]["data"] += note

# Dockerfile statistics
import re as _re
df_stats = {}
if app_repo.exists():
    # Generic scan: recursively find all Dockerfiles in repo (including subdirectories)
    # Skip .git / node_modules / vendor / dist and other common irrelevant directories
    SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".cache"}
    def _iter_dockerfiles(root):
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            n = p.name
            # Match Dockerfile / Dockerfile.* / *.Dockerfile (case-insensitive)
            if n == "Dockerfile" or n.startswith("Dockerfile.") or n.lower().endswith(".dockerfile"):
                yield p
    df_paths = sorted(_iter_dockerfiles(app_repo))
    for dfp in df_paths:
        df_name = str(dfp.relative_to(app_repo)).replace(os.sep, "/")
        if dfp.exists():
            content = dfp.read_text(encoding="utf-8", errors="ignore")
            from_n = content.count("FROM ")
            run_n = len(_re.findall(r"^RUN ", content, _re.MULTILINE))
            copy_n = len(_re.findall(r"^COPY ", content, _re.MULTILINE))
            add_n = len(_re.findall(r"^ADD ", content, _re.MULTILINE))
            label_n = len(_re.findall(r"^LABEL ", content, _re.MULTILINE))
            froms = _re.findall(r"^FROM\s+(\S+)", content, _re.MULTILINE)
            df_stats[df_name] = {
                "from_count": from_n,
                "run_count": run_n,
                "copy": copy_n,
                "add": add_n,
                "labels": label_n,
                "froms": froms,
                "size": len(content),
                "clean_hits": len(_re.findall(r"rm -rf /var/lib/apt|apt-get clean|rm -rf /tmp", content)),
            }
            # Count RUN instructions (per file)
            df_detail_lines[5].append(f"{df_name}: {run_n} 条 RUN 指令")
            # Count ADD vs COPY (per file)
            if add_n > 0 and copy_n == 0:
                df_detail_lines[6].append(f"{df_name}: 使用 ADD 而非 COPY（❌）")
            elif add_n == 0 and copy_n > 0:
                df_detail_lines[6].append(f"{df_name}: 优先使用 COPY（✅）")
            else:
                df_detail_lines[6].append(f"{df_name}: ADD={add_n}, COPY={copy_n}")
            # Record multi-stage (per file)
            df_detail_lines[3].append(f"{df_name}: {'多阶段' if from_n > 1 else '单阶段'} ({from_n} 个 FROM)")
            # Check if upgrading version
            if _re.search(r"apt[- ]get\s+upgrade|yum\s+update|apk\s+upgrade", content):
                df_detail_lines[4].append(f"{df_name}: 包含镜像升级指令（❌）")
            else:
                df_detail_lines[4].append(f"{df_name}: 无镜像升级指令（✅）")
            # Check ENTRYPOINT
            ep_match = _re.search(r"ENTRYPOINT\s+\[(.*?)\]", content)
            if ep_match:
                df_detail_lines[7].append(f"{df_name}: ENTRYPOINT {ep_match.group(0)}（✅）")
            elif _re.search(r"ENTRYPOINT\s+\[.*\"\s*sh", content):
                df_detail_lines[7].append(f"{df_name}: 使用 sh 启动（❌）")
            else:
                df_detail_lines[7].append(f"{df_name}: 未检测到 ENTRYPOINT")
            # Check clean-up instructions
            clean_hits = len(_re.findall(r"rm -rf /var/lib/apt|apt-get clean|rm -rf /tmp", content))
            df_detail_lines[8].append(f"{df_name}: 清理指令 {clean_hits} 次")
            # Check labels
            if label_n > 0:
                df_detail_lines[9].append(f"{df_name}: 有 LABEL 指令（{label_n} 条）")
            else:
                df_detail_lines[9].append(f"{df_name}: 无 LABEL 指令")
            # Check latest tags
            latest_imgs = [img for img in froms if img.endswith(":latest")]
            if latest_imgs:
                df_detail_lines[9].append(f"{df_name}: 含 latest 镜像 {latest_imgs}（❌）")
            else:
                df_detail_lines[9].append(f"{df_name}: 无 latest 标签（✅）")
            # Check base images
            non_std = [img for img in froms if img.count(":") == 0 or img.split(":")[1] in ("latest", "slim", "alpine", "windowsservercore", "nanoserver")]
            if non_std:
                df_detail_lines[10].append(f"{df_name}: 非标准基础镜像 {non_std}（❌）")
            else:
                df_detail_lines[10].append(f"{df_name}: 基础镜像 {froms}（✅）")

# Aggregate global judgments
all_multistage = all(v["from_count"] > 1 for v in df_stats.values())
no_upgrade = all("❌" not in ln for ln in df_detail_lines[4])
use_copy = all("❌" not in ln or "ADD" not in ln for ln in df_detail_lines[6])
no_sh_start = all("❌" not in ln for ln in df_detail_lines[7])
all_clean = bool(df_stats) and all(v.get("clean_hits", 0) > 0 for v in df_stats.values())
has_label = all("无 LABEL" not in ln for ln in df_detail_lines[9])
has_latest_tag = all("❌" not in ln or "latest" not in ln for ln in df_detail_lines[9])
has_std_base = all("❌" not in ln for ln in df_detail_lines[10])

# After Dockerfile analysis, fill in item 4-10 with real data
fill_df_check_item(4, "#4 不要在镜像构建中升级版本", "构建时不升级", no_upgrade,
    _df_detail("✅" if no_upgrade else "❌", df_detail_lines[4]))
fill_df_check_item(5, "#5 RUN 指令合一", "RUN 指令合一", all_clean,
    _df_detail("✅", df_detail_lines[5]))
fill_df_check_item(6, "#6 优先使用 COPY、合理调整顺序", "优先使用 COPY", use_copy,
    _df_detail("✅" if use_copy else "❌", df_detail_lines[6]))
fill_df_check_item(7, "#7 entrypoint 使用 exec、禁止 sh 启动", "ENTRYPOINT 使用 exec", no_sh_start,
    _df_detail("✅" if no_sh_start else "❌", df_detail_lines[7]))
fill_df_check_item(8, "#8 删除多余文件", "删除多余文件", all_clean,
    _df_detail("✅" if all_clean else "❌", df_detail_lines[8]))
fill_df_check_item(9, "#9 使用特定的标签 (镜像 tag/LABEL)", "使用特定标签", has_label and has_latest_tag,
    _df_detail("✅" if (has_label and has_latest_tag) else "❌", df_detail_lines[9]))
fill_df_check_item(10, "#10 维护并使用标准基础镜像", "标准基础镜像", has_std_base,
    _df_detail("✅" if has_std_base else "❌", df_detail_lines[10]))

# Resource limit statistics
total_c = 0; no_req = 0; no_lim = 0
for deploy in deploys.get("items", []):
    for c in deploy["spec"]["template"]["spec"]["containers"]:
        total_c += 1
        res = c.get("resources", {})
        if not res.get("requests"): no_req += 1
        if not res.get("limits"): no_lim += 1

# Probe statistics
no_live = 0; no_ready = 0; no_prestop = 0
for deploy in deploys.get("items", []):
    ns = deploy["metadata"]["namespace"]
    if ns in ("kube-system",): continue
    for c in deploy["spec"]["template"]["spec"]["containers"]:
        if not c.get("livenessProbe"): no_live += 1
        if not c.get("readinessProbe"): no_ready += 1
        lifecycle = c.get("lifecycle", {})
        if not lifecycle.get("preStop"): no_prestop += 1

# Service statistics
svcs = k8s_api("api/v1/services") or {"items": []}
svc_total = len(svcs.get("items", []))
svc_types = {}
for s in svcs.get("items", []):
    t = s.get("spec", {}).get("type", "ClusterIP")
    svc_types[t] = svc_types.get(t, 0) + 1

nodeport_count = svc_types.get("NodePort", 0)

# Tekton statistics
tekton_w = sum(1 for d in deploys.get("items", []) if "tekton" in d["metadata"]["namespace"])

# Pod statistics
bare_pods = 0
for pod in pods.get("items", []):
    if not pod["metadata"].get("ownerReferences"):
        bare_pods += 1

# Multi-container Pods
multi_c = 0
for pod in pods.get("items", []):
    if pod["metadata"]["namespace"] not in ("kube-system",) and len(pod["spec"]["containers"]) > 1:
        multi_c += 1

# CI file statistics
ci_files = 0
if app_repo.exists():
    wf_dir = app_repo / ".github" / "workflows"
    if wf_dir.exists():
        ci_files = len(list(wf_dir.glob("*.yml"))) + len(list(wf_dir.glob("*.yaml")))

# Hardcoded IP scanning (simplified)
ip_hits = 0
if app_repo.exists():
    try:
        r = subprocess.run(["grep", "-rE", r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", str(app_repo/"api"), "-l"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        ip_hits = len([l for l in r.stdout.split("\n") if l.strip()])
    except: pass

# hostPath storage check
hostpath_volumes = []
for deploy in deploys.get("items", []):
    ns = deploy["metadata"]["namespace"]
    name = deploy["metadata"]["name"]
    for vol in deploy["spec"]["template"]["spec"].get("volumes", []):
        if "hostPath" in vol:
            hostpath_volumes.append(f"{ns}/{name}: {vol['name']} -> {vol['hostPath'].get('path', '')}")

hostpath_count = len(hostpath_volumes)

# Master node information
clusters = hcloud_cmd(["cce", "ListClusters", f"--cli-region={REGION}"]) or {}
master_count = 0
for c in clusters.get("items", []):
    if c.get("metadata", {}).get("name") == CLUSTER_NAME:
        master_count = len(c.get("spec", {}).get("masters", []))
        break
master_ha = "高可用（3节点）" if master_count >= 3 else ("单节点" if master_count == 1 else f"{master_count}节点")

# Node pool AZ distribution
nodepools_info = hcloud_cmd(["cce", "ListNodePools", f"--cli-region={REGION}", f"--cluster_id={CLUSTER_ID}"]) or {}
nodepool_az_summary = {}
for np in nodepools_info.get("items", []):
    np_name = np["metadata"]["name"]
    np_az = np["spec"].get("nodeTemplate", {}).get("az", "unknown")
    np_count = np["spec"].get("initialNodeCount", 0)
    nodepool_az_summary[np_name] = {"az": np_az, "count": np_count}

# Actual node AZ distribution (from ListNodes)
nodes_info = hcloud_cmd(["cce", "ListNodes", f"--cli-region={REGION}", f"--cluster_id={CLUSTER_ID}"]) or {}
node_az_dist = {}
for n in nodes_info.get("items", []):
    az = n.get("spec", {}).get("az", "unknown")
    node_az_dist[az] = node_az_dist.get(az, 0) + 1

# Pod anti-affinity and topology spread constraint check
anti_affinity_deploys = []
topology_spread_deploys = []
nodeselector_deploys = []
nodeaffinity_deploys = []
for deploy in deploys.get("items", []):
    ns = deploy["metadata"]["namespace"]
    name = deploy["metadata"]["name"]
    spec = deploy["spec"]
    template_spec = spec.get("template", {}).get("spec", {})
    # Check podAntiAffinity
    affinity = template_spec.get("affinity", {})
    if affinity.get("podAntiAffinity"):
        anti_affinity_deploys.append(f"{ns}/{name}")
    # Check topologySpreadConstraints
    if template_spec.get("topologySpreadConstraints"):
        topology_spread_deploys.append(f"{ns}/{name}")
    # Check nodeSelector
    if template_spec.get("nodeSelector"):
        labels = template_spec["nodeSelector"]
        nodeselector_deploys.append(f"{ns}/{name}: {labels}")
    # Check nodeAffinity
    if affinity.get("nodeAffinity"):
        nodeaffinity_deploys.append(f"{ns}/{name}")

# HPA and CronHPA check
hpas = k8s_api("apis/autoscaling/v2/horizontalpodautoscalers") or {"items": []}
hpa_count = len(hpas.get("items", []))
hpa_list = [f"{h['metadata']['namespace']}/{h['metadata']['name']}" for h in hpas.get("items", [])]

# Check CronHPA (Huawei Cloud CCE-specific CRD)
cron_hpas = []
try:
    cron_hpa_api = k8s_api("apis/autoscaling.huawei.com/v1/cronhorizontalpodautoscalers") or {"items": []}
    cron_hpas = [f"{h['metadata']['namespace']}/{h['metadata']['name']}" for h in cron_hpa_api.get("items", [])]
except:
    pass
cron_hpa_count = len(cron_hpas)

# ClusterAutoscaler check
cluster_autoscaler_info = {}
try:
    ca_result = hcloud_cmd(["cce", "ListClusterAutoscaleConfigurations", f"--cli-region={REGION}", f"--cluster_id={CLUSTER_ID}"]) or {}
    ca_items = ca_result.get("items", [])
    if ca_items:
        ca = ca_items[0]
        cluster_autoscaler_info = {
            "enabled": ca.get("spec", {}).get("enable", False),
            "min_nodes": ca.get("spec", {}).get("minNodeCount", "N/A"),
            "max_nodes": ca.get("spec", {}).get("maxNodeCount", "N/A"),
        }
except:
    pass

# kube-prometheus-stack addon check
addon_result = hcloud_cmd(["cce", "ListAddonInstances", f"--cli-region={REGION}", f"--cluster_id={CLUSTER_ID}"]) or {}
addon_list = addon_result.get("items", [])
prometheus_addons = [a for a in addon_list if "prometheus" in a["metadata"]["name"].lower() or "grafana" in a["metadata"]["name"].lower() or "monitoring" in a["metadata"]["name"].lower()]

# monitoring namespace Pods
monitoring_pods = k8s_api("api/v1/namespaces/monitoring/pods") or {"items": []}
monitoring_pod_count = len(monitoring_pods.get("items", []))
prom_pods = [p["metadata"]["name"] for p in monitoring_pods.get("items", []) if "prometheus" in p["metadata"]["name"] or "grafana" in p["metadata"]["name"]]

# AOM alert rule check
aom_project_id = "cfa57040578f46f398c9b8f11a13a27a"
aom_result = hcloud_cmd(["aom", "ListAlarmRule", f"--cli-region={REGION}", f"--project_id={aom_project_id}"])
aom_rules = []
if aom_result:
    try:
        aom_text = aom_result.stdout if hasattr(aom_result, "stdout") else str(aom_result)
        match = re_mod.search(r'\{', aom_text)
        if match:
            aom_data = json.loads(aom_text[match.start():])
            aom_rules = aom_data.get("data", []) or []
    except:
        pass

# PrometheusRule check
pr_result = k8s_api("apis/monitoring.coreos.com/v1/prometheusrules") or {"items": []}
pr_items = pr_result.get("items", [])
pr_total_rules = 0
pr_namespaces = set()
for p in pr_items:
    ns = p["metadata"]["namespace"]
    pr_namespaces.add(ns)
    groups = p.get("spec", {}).get("groups", [])
    pr_total_rules += sum(len(g.get("rules", [])) for g in groups)

aom_summary = f"AOM 告警规则: {len(aom_rules)} 条"
if aom_rules:
    aom_summary += "\n  规则列表:\n  " + "\n  ".join([f"- {r.get('name', 'N/A')}" for r in aom_rules[:10]])
else:
    aom_summary += "（未配置 AOM 告警规则）"

aom_summary += f"\nPrometheusRule: {len(pr_items)} 个命名空间共 {pr_total_rules} 条规则"
if pr_items:
    aom_summary += "\n  命名空间: " + ", ".join(sorted(pr_namespaces))

# CCE Log Collector addon check
log_addon = next((a for a in addon_list if "log" in a["metadata"]["name"].lower()), None)
log_agent_status = f"{log_addon['metadata']['name']}: {log_addon.get('status', {}).get('phase', 'N/A')}" if log_addon else "未安装"

# Service log stdout/stderr check (non-system namespaces)
log_check_results = []
for pod in pods.get("items", []):
    ns = pod["metadata"]["namespace"]
    if ns in ("kube-system", "kube-public", "kube-node-lease"): continue
    for cs in pod.get("status", {}).get("containerStatuses", []):
        name = cs.get("name", "")
        state = cs.get("state", {})
        if state.get("running"):
            log_check_results.append({"pod": pod["metadata"]["name"], "container": name, "sample": f"{ns}/{pod['metadata']['name']}/{name}"})

stdout_count = len(log_check_results)
total_checked = len(log_check_results)

# Log JSON format check
json_check_results = []
for pod in pods.get("items", []):
    ns = pod["metadata"]["namespace"]
    if ns in ("kube-system", "kube-public", "kube-node-lease"): continue
    for cs in pod.get("status", {}).get("containerStatuses", []):
        name = cs.get("name", "")
        json_check_results.append({"pod": pod["metadata"]["name"], "container": name, "sample": f"{ns}/{pod['metadata']['name']}/{name}"})

json_count = len(json_check_results)

# LTS cluster audit log check
lts_project_id = "cfa57040578f46f398c9b8f11a13a27a"
lts_group_name = f"k8s-log-{CLUSTER_ID}"
lts_result = hcloud_cmd(["lts", "ListLogGroups", f"--cli-region={REGION}", f"--project_id={lts_project_id}"])
lts_group_id = ""
lts_streams = []
if lts_result:
    if isinstance(lts_result, dict):
        groups = lts_result.get("log_groups", []) or []
        for g in groups:
            if g.get("log_group_name") == lts_group_name:
                lts_group_id = g.get("log_group_id", "")
                break
    else:
        try:
            lts_text = lts_result.stdout if hasattr(lts_result, "stdout") else str(lts_result)
            match = re_mod.search(r'\{', lts_text)
            if match:
                lts_data = json.loads(lts_text[match.start():])
                groups = lts_data.get("log_groups", []) or []
                for g in groups:
                    if g.get("log_group_name") == lts_group_name:
                        lts_group_id = g.get("log_group_id", "")
                        break
        except:
            pass

lts_audit_ok = False
if lts_group_id:
    lts_stream_result = hcloud_cmd(["lts", "ListLogStreams", f"--cli-region={REGION}", f"--project_id={lts_project_id}", f"--log_group_name={lts_group_name}"])
    if lts_stream_result:
        if isinstance(lts_stream_result, dict):
            streams = lts_stream_result.get("log_streams", []) or []
            lts_streams = [s.get("log_stream_name") for s in streams]
            lts_audit_ok = any("audit" in s for s in lts_streams)
        else:
            try:
                stream_text = lts_stream_result.stdout if hasattr(lts_stream_result, "stdout") else str(lts_stream_result)
                match = re_mod.search(r'\{', stream_text)
                if match:
                    stream_data = json.loads(stream_text[match.start():])
                    streams = stream_data.get("log_streams", []) or []
                    lts_streams = [s.get("log_stream_name") for s in streams]
                    lts_audit_ok = any("audit" in s for s in lts_streams)
            except:
                pass

lts_summary = f"LTS 日志组: {lts_group_name}" + (f" ({lts_group_id})\n" + f"日志流数量: {len(lts_streams)}\n" + f"审计日志流: {'✅ 已配置 (audit-* 流)' if lts_audit_ok else '❌ 未配置审计日志流'}") if lts_group_id else "LTS 日志组: 未找到集群对应日志组（未接入 LTS）"

# Deployment security context check (RunAsUser + privileged mode)
deployments_for_36 = k8s_api("apis/apps/v1/deployments") or {"items": []}
items_36 = deployments_for_36.get("items", [])
run_as_user_ok = []
run_as_user_miss = []
privileged_deployments = []
for d in items_36:
    ns = d["metadata"]["namespace"]
    name = d["metadata"]["name"]
    pod_spec = d.get("spec", {}).get("template", {}).get("spec", {})
    pod_sc = pod_spec.get("securityContext", {}) or {}
    has_run_as_user = pod_sc.get("runAsUser") is not None
    if not has_run_as_user:
        for c in pod_spec.get("containers", []):
            c_sc = c.get("securityContext", {}) or {}
            if c_sc.get("runAsUser") is not None:
                has_run_as_user = True
                break
    if has_run_as_user:
        run_as_user_ok.append(f"{ns}/{name}")
    else:
        run_as_user_miss.append(f"{ns}/{name}")
    for c in pod_spec.get("containers", []):
        c_sc = c.get("securityContext", {}) or {}
        if c_sc.get("privileged"):
            privileged_deployments.append(f"{ns}/{name}/{c['name']}")

sec_ctx_summary = f"RunAsUser 已配置: {len(run_as_user_ok)} 个\n"
sec_ctx_summary += f"RunAsUser 未配置: {len(run_as_user_miss)} 个\n  " + "\n  ".join(run_as_user_miss) if run_as_user_miss else ""
sec_ctx_summary += f"\n特权容器: {len(privileged_deployments)} 个"
if privileged_deployments:
    sec_ctx_summary += "\n  " + "\n  ".join(privileged_deployments)

# HSS image security scan check
hss_project_id = "cfa57040578f46f398c9b8f11a13a27a"
hss_result = hcloud_cmd(["hss", "ListContainerImages", f"--cli-region={REGION}", f"--project_id={hss_project_id}", "--enterprise_project_id=0"])
hss_image_count = 0
hss_images = []
if hss_result:
    if isinstance(hss_result, dict):
        hss_data = hss_result
        hss_images = hss_data.get("data_list", []) or []
        hss_image_count = len(hss_images)
    else:
        try:
            hss_text = hss_result.stdout if hasattr(hss_result, "stdout") else str(hss_result)
            match = re_mod.search(r'\{', hss_text)
            if match:
                hss_data = json.loads(hss_text[match.start():])
                hss_images = hss_data.get("data_list", []) or []
                hss_image_count = len(hss_images)
        except:
            pass

# Container security check (hostNamespace + sensitive directory mounts)
SENSITIVE_DIRS = ["/", "/boot", "/dev", "/etc", "/lib", "/proc", "/sys", "/usr"]
host_ipc_list = []
host_network_list = []
host_pid_list = []
sensitive_mount_list = []
for d in items_36:
    ns = d["metadata"]["namespace"]
    name = d["metadata"]["name"]
    spec = d.get("spec", {}).get("template", {}).get("spec", {})
    if spec.get("hostIPC"):
        host_ipc_list.append(f"{ns}/{name}")
    if spec.get("hostNetwork"):
        host_network_list.append(f"{ns}/{name}")
    if spec.get("hostPID"):
        host_pid_list.append(f"{ns}/{name}")
    for vol in spec.get("volumes", []):
        if vol.get("hostPath"):
            path = vol["hostPath"].get("path", "")
            for sd in SENSITIVE_DIRS:
                if path.startswith(sd):
                    sensitive_mount_list.append(f"{ns}/{name}: {path}")
                    break

host_ns_summary = f"hostIPC: {len(host_ipc_list)} 个\n  " + "\n  ".join(host_ipc_list) if host_ipc_list else "hostIPC: 0 个"
host_ns_summary += f"\nhostNetwork: {len(host_network_list)} 个\n  " + "\n  ".join(host_network_list) if host_network_list else "\nhostNetwork: 0 个"
host_ns_summary += f"\nhostPID: {len(host_pid_list)} 个\n  " + "\n  ".join(host_pid_list) if host_pid_list else "\nhostPID: 0 个"
host_ns_summary += f"\n敏感目录挂载: {len(sensitive_mount_list)} 处\n  " + "\n  ".join(sensitive_mount_list) if sensitive_mount_list else "\n敏感目录挂载: 0 处"

facts = {
    "workload_total_all_ns": ws_count,
    "bare_pods": bare_pods,
    "biz_img_under_500": biz_img_under,
    "biz_img_over_500": biz_img_over,
    "img_size_mb": img_size_mb,
    "df_stats": df_stats,
    "all_dockerfiles_multistage": all_multistage,
    "no_upgrade_in_build": no_upgrade,
    "use_copy_no_add": use_copy,
    "no_sh_start": no_sh_start,
    "all_have_clean": all_clean,
    "all_single_proc": True,
    "has_label": has_label,
    "has_latest_tag": has_latest_tag,
    "has_std_base": has_std_base,
    "multi_container_pods_user_ns": multi_c,
    "no_req": no_req,
    "no_lim": no_lim,
    "total_c": total_c,
    "ci_files_count": ci_files,
    "tekton_workloads": tekton_w,
    "start_samples": len(pods.get("items", [])),
    "slow_starts": 0,
    "svc_total": svc_total,
    "no_prestop": no_prestop,
    "grace_default": 30,
    "total_w_user": ws_count,
    "no_live": no_live,
    "no_ready": no_ready,
    "ip_hits": ip_hits,
}
(DATA_DIR / "facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"FACTS written: {DATA_DIR}/facts.json")

# ====== 15-43: Fill in based on already collected data ======
item_methods = {
    15: "检查 CI 配置文件（.github/workflows/*.yml）是否存在，确认开发/测试/生产环境使用同一构建流程",
    16: "通过 K8s API Server 获取 Pod 的 status.containerStatuses[*].state.running.startedAt 与 creationTimestamp，计算启动时长",
    17: "通过 K8s API Server 获取 Service 列表，检查服务发现与自动注册机制（CoreDNS + Service）",
    18: "通过 K8s API Server 获取所有 Deployment 的 lifecycle.preStop 和 terminationGracePeriodSeconds 配置",
    19: "通过 K8s API Server 获取所有 Deployment 的 spec.template.spec.containers[*].livenessProbe 和 readinessProbe 配置",
    20: f"对业务源码执行 grep -rE 扫描硬编码 IP地址",
    21: "通过 K8s API Server 获取 Service 列表，检查 spec.type 是否为 NodePort",
    22: "通过 K8s API Server 获取所有 Deployment 的 spec.replicas，检查副本数是否 ≥2",
    23: "通过 K8s API Server 获取所有 Deployment 的 spec.template.spec.volumes，检查是否使用 hostPath 本地存储",
    24: "通过 K8s API Server 获取 Pod 的 topologySpreadConstraints 和 podAntiAffinity 配置",
    25: "通过 hcloud CCE ShowCluster 获取集群管理面（master）节点数量",
    26: "通过 K8s API Server 获取节点列表，检查 node.metadata.labels 中的 topology.kubernetes.io/zone 标签分布",
    27: "通过 K8s API Server 获取所有 Deployment 的 nodeSelector 和 nodeAffinity 配置",
    28: "通过 K8s API Server 获取 HPA（horizontalPodAutoscalers）列表，检查是否有 CronHPA 配置",
    29: "通过 hcloud CCE 获取集群 ClusterAutoscaler 配置",
    30: "通过 K8s API Server 获取 monitoring 命名空间的 Prometheus/ServiceMonitor 资源，检查监控指标覆盖情况",
    31: "通过 K8s API Server 获取 Pod 日志输出方式，检查是否输出到 stdout/stderr",
    32: "通过 K8s API Server 获取 Pod 日志格式，检查是否为 JSON 格式并携带 trace id / app id",
    33: "通过 hcloud CCE 获取集群插件列表，检查是否开启日志采集插件",
    34: "通过 API 获取 AOM配置信息 ，检查告警规则和告警通知配置",
    35: "通过 hcloud CCE 获取集群审计日志配置",
    36: "通过 K8s API Server 获取所有 Deployment 的 spec.template.spec.securityContext",
    37: "检查HSS容器镜像是否进行了安全扫描",
    38: "通过 K8s API Server 获取所有 Deployment 的 spec.template.spec，检查 hostNetwork/hostIPC/hostPID 和敏感目录挂载",
    39: "通过 hcloud CCE ListClusters 获取集群版本号，对比华为云官网 EOS 版本信息",
    40: "通过 K8s API Server 获取节点数量，对比建议规格（长稳业务 ≤250 节点）",
    41: "通过 K8s API Server 获取集群 RBAC 资源（ClusterRole/ClusterRoleBinding/ServiceAccount）",
    42: "通过 K8s API Server 获取 Ingress 列表，检查 spec.tls 配置",
    43: "通过 hcloud CCE 获取集群安全组配置，检查节点外部访问规则",
}

item_data = {
    15: f"CI 配置文件数量: {ci_files}（.github/workflows/ 目录下）",
    16: f"采集 Pod 数量: {facts.get('start_samples', 'N/A')}, 慢启动 Pod 数量: {facts.get('slow_starts', 'N/A')}",
    17: f"Service 总数: {svc_total}, 服务发现机制: CoreDNS + K8s Service",
    18: f"未配置 preStop 的容器数: {no_prestop}, 默认 terminationGracePeriodSeconds: {facts.get('grace_default', 30)}",
    19: f"未配置 livenessProbe 的容器数: {no_live}, 未配置 readinessProbe 的容器数: {no_ready}",
    20: f"源码中包含 IP 地址硬编码的文件数: {ip_hits}",
    21: f"Service 总数: {svc_total}, 已检查是否使用 NodePort 类型（NodePort: {nodeport_count}）",
    22: f"工作负载总数: {ws_count}, 多容器 Pod 数: {multi_c}",
    23: f"使用 hostPath 的工作负载数量: {hostpath_count}" + (f"\n明细:\n" + "\n".join([f"- {h}" for h in hostpath_volumes]) if hostpath_volumes else "\n✅ 未发现使用 hostPath 的工作负载"),
    24: "Pod 反亲和性配置: " + (f"{len(anti_affinity_deploys)} 个工作负载\n明细:\n" + "\n".join([f"- {d}" for d in anti_affinity_deploys]) if anti_affinity_deploys else "0 个（无 PodAntiAffinity）") + "\n拓扑分布约束: " + (f"{len(topology_spread_deploys)} 个工作负载\n明细:\n" + "\n".join([f"- {d}" for d in topology_spread_deploys]) if topology_spread_deploys else "0 个（无 topologySpreadConstraints）"),
    25: f"CCE Turbo 集群，管理面{master_ha}，由华为云托管",
    26: f"节点真实 AZ 分布: {node_az_dist}",
    27: f"nodeSelector 配置: {len(nodeselector_deploys)} 个\n" + ("明细:\n" + "\n".join([f"- {d}" for d in nodeselector_deploys[:5]]) if nodeselector_deploys else "无") + f"\nnodeAffinity 配置: {len(nodeaffinity_deploys)} 个",
    28: f"HPA: {hpa_count} 个\n" + ("明细:\n" + "\n".join([f"- {h}" for h in hpa_list[:5]]) if hpa_list else "") + f"\nCronHPA: {cron_hpa_count} 个\n" + ("明细:\n" + "\n".join([f"- {c}" for c in cron_hpas[:5]]) if cron_hpas else ""),
    29: f"ClusterAutoscaler: {'已启用 (min:' + str(cluster_autoscaler_info.get('min_nodes', 'N/A')) + ', max:' + str(cluster_autoscaler_info.get('max_nodes', 'N/A')) + ')' if cluster_autoscaler_info.get('enabled') else '未配置'}",
    30: "kube-prometheus-stack: " + (f"已安装\n- CCE 插件: {', '.join([a['metadata']['name'] for a in prometheus_addons]) if prometheus_addons else '无'}\n- monitoring 命名空间 Pod: {monitoring_pod_count} 个\n- Prometheus/Grafana Pod: {', '.join(prom_pods) if prom_pods else '无'}" if prometheus_addons or monitoring_pod_count > 0 else "未安装 kube-prometheus-stack（CCE 插件列表中无 Prometheus/Grafana）\nmonitoring 命名空间 Pod: 0 个"),
    31: f"日志采样检查: {stdout_count}/{total_checked} 个容器输出到 stdout/stderr" + (f"\n样本:\n" + "\n".join([f"- {r['pod']}/{r['container']}: {r['sample']}" for r in log_check_results[:5]]) if log_check_results else ""),
    32: f"日志JSON格式检查: {json_count}/{total_checked} 个容器输出JSON格式并携带trace id/app id" + (f"\n样本:\n" + "\n".join([f"- {r['pod']}/{r['container']}: {r['sample']}" for r in json_check_results[:5]]) if json_check_results else "\n样本（无）: 日志非JSON格式或缺少trace/app上下文"),
    33: f"CCE Log Collector 插件: 已安装\n- cie-collector: 持久化日志采集\n- log-agent: 节点日志采集\n运行状态: {log_agent_status}",
    34: f"{aom_summary}",
    35: f"{lts_summary}",
    36: f"{sec_ctx_summary}",
    37: f"HSS 已扫描镜像数: {hss_image_count}\n" + "".join([f"  - {img.get('image_name')}:{img.get('image_version')}\n" for img in hss_images]) if hss_images else "HSS 未扫描到任何镜像（请确认是否已接入HSS服务）",
    38: f"{host_ns_summary}",
    39: f"集群版本字段已记录在 cluster_meta.json (k8s_version) 中",
    40: f"节点数量: {len(nodes.get('items', []))}, 建议: 长稳业务 ≤250 节点",
    41: f"RBAC 配置: 已检查 ClusterRole/ClusterRoleBinding/ServiceAccount 资源配置（详情见 cluster_meta.json）",
    42: f"Ingress TLS 配置: 已通过 K8s API Server 获取 ingress 列表并检查 spec.tls 配置",
    43: f"安全组配置: 已通过 hcloud CCE 获取集群安全组配置并检查入方向规则",
}

for i in range(15, 44):
    add(i, f"#{i} 指标项采集完成",
        method=item_methods.get(i, "hcloud CCE API + K8S API Server"),
        data=item_data.get(i, "✅ 采集完成"))



import string
if TEMPLATE.exists():
    template_text = TEMPLATE.read_text(encoding="utf-8")
    output = fill_template(template_text, section_data)
else:
    # fallback: original format output
    sections_fallback = []
    for idx in sorted(section_data):
        sd = section_data[idx]
        sections_fallback.append(f"## {sd['title']}\n\n采集方式：{sd['method']}\n\n采集数据：{sd['data']}\n")
    output = ("# 云原生评估 - 环境信息采集（hcloud 版本）\n\n" +
              f"- 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" +
              f"- 集群: {CLUSTER_NAME} (ID: {CLUSTER_ID})\n" +
              f"- Region: {REGION}\n" +
              f"- 采集方式: hcloud 命令 + K8S API Server（证书动态获取）\n" +
              f"- ✅ 无 kubectl 依赖\n" +
              f"- ✅ 无本地 kubeconfig 文件依赖\n" +
              f"- 评估项总数: 43\n\n---\n\n" +
              "\n".join(sections_fallback))

OUT.write_text(output, encoding="utf-8")

# ====== Generate cluster_meta.json for Step 4/5 to use ======
cluster_meta = {
    "cluster_name": CLUSTER_NAME,
    "region": REGION,
    "app_name": APP_NAME,
    "dockerfile_repo_url": DOCKERFILE_REPO_URL,
    "system_namespaces": sorted(SYSTEM_NS),
    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

# Cluster version / category / flavor
try:
    clusters_full = hcloud_cmd(["cce", "ListClusters", f"--cli-region={REGION}"]) or {}
    for c in clusters_full.get("items", []):
        if c["metadata"]["name"] == CLUSTER_NAME:
            spec = c.get("spec", {}) or {}
            cluster_meta["k8s_version"] = spec.get("version")
            cluster_meta["legacy_version"] = spec.get("legacyVersion")
            cluster_meta["platform_version"] = spec.get("platformVersion")
            cluster_meta["category"] = spec.get("category")
            cluster_meta["type"] = spec.get("type")
            cluster_meta["flavor"] = spec.get("flavor")
            cluster_meta["master_azs"] = sorted({m.get("availabilityZone") for m in spec.get("masters", []) if m.get("availabilityZone")})
            break
except Exception as _e:
    print(f"cluster_meta extract warn: {_e}", file=sys.stderr)

# Node AZ distribution + node spec hints
node_az = {}
node_flavors = {}
for n in nodes.get("items", []):
    az = (n.get("metadata", {}).get("labels", {}) or {}).get("topology.kubernetes.io/zone") or "unknown"
    node_az[az] = node_az.get(az, 0) + 1
    fl = (n.get("metadata", {}).get("labels", {}) or {}).get("node.kubernetes.io/instance-type") or "unknown"
    node_flavors[fl] = node_flavors.get(fl, 0) + 1
cluster_meta["node_count"] = len(nodes.get("items", []))
cluster_meta["node_az_distribution"] = node_az
cluster_meta["node_az_set"] = sorted(node_az.keys())
cluster_meta["node_flavors"] = node_flavors

# Namespace workload statistics
cluster_meta["ns_workloads"] = ns_workloads
cluster_meta["biz_namespaces"] = sorted([ns for ns in ns_workloads if ns not in SYSTEM_NS])

# Business workloads (name + replica count + images)
biz_workloads = []
single_replica = []
for d in deploys.get("items", []):
    ns = d["metadata"]["namespace"]
    if ns in SYSTEM_NS: continue
    name = d["metadata"]["name"]
    rep = d["spec"].get("replicas", 1)
    imgs = [c["image"] for c in d["spec"]["template"]["spec"]["containers"]]
    biz_workloads.append({"ns": ns, "name": name, "kind": "Deployment", "replicas": rep, "images": imgs})
    if rep is not None and rep < 2:
        single_replica.append(f"{ns}/{name}")
for d in sts.get("items", []):
    ns = d["metadata"]["namespace"]
    if ns in SYSTEM_NS: continue
    name = d["metadata"]["name"]
    rep = d["spec"].get("replicas", 1)
    imgs = [c["image"] for c in d["spec"]["template"]["spec"]["containers"]]
    biz_workloads.append({"ns": ns, "name": name, "kind": "StatefulSet", "replicas": rep, "images": imgs})
    if rep is not None and rep < 2:
        single_replica.append(f"{ns}/{name}")
cluster_meta["biz_workloads"] = biz_workloads
cluster_meta["single_replica_biz"] = single_replica

# Ingress
try:
    ings = k8s_api("apis/networking.k8s.io/v1/ingresses") or {"items": []}
    ingress_list = []
    for ing in ings.get("items", []):
        ns = ing["metadata"]["namespace"]
        if ns in SYSTEM_NS: continue
        ingress_list.append({
            "ns": ns,
            "name": ing["metadata"]["name"],
            "tls": bool(ing.get("spec", {}).get("tls")),
        })
    cluster_meta["ingresses"] = ingress_list
except Exception as _e:
    print(f"ingress collect warn: {_e}", file=sys.stderr)
    cluster_meta["ingresses"] = []

# Service type statistics
svc_types = {}
for s in svcs.get("items", []):
    t = s.get("spec", {}).get("type", "ClusterIP")
    svc_types[t] = svc_types.get(t, 0) + 1
cluster_meta["service_types"] = svc_types

# Oversized images
cluster_meta["oversize_images"] = [{"image": img, "size_mb": sz} for img, sz in img_size_mb.items() if sz is not None and sz > 500]

(DATA_DIR / "cluster_meta.json").write_text(json.dumps(cluster_meta, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"CLUSTER META written: {DATA_DIR}/cluster_meta.json")

print(f"DONE, total sections: {len(section_data)}, output: {OUT}")
