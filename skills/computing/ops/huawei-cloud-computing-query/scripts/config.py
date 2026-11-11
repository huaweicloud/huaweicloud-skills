import os
from urllib.parse import urlparse

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


def load_credentials():
    """从环境变量加载华为云凭据

    支持永久 AK/SK 和临时 AK/SK（含 SecurityToken）。
    设置 HW_SECURITY_TOKEN 环境变量即可启用临时凭证模式。
    """
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "cn-north-4")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    if not ak or not sk:
        print("未配置 AK/SK，请设置环境变量 HW_ACCESS_KEY 和 HW_SECRET_KEY")
        exit(-1)

    return ak, sk, region, security_token


def load_credentials_optional():
    """从环境变量加载华为云凭据（可选模式）

    用于公开接口（如 API 版本查询），不要求 AK/SK 必须存在。
    如果 AK/SK 未配置，返回空字符串，由调用方决定如何处理。
    """
    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    region = os.getenv("HW_REGION_NAME", "cn-north-4")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")
    return ak, sk, region, security_token


def _get_proxy_url():
    """获取代理 URL，优先级: HTTPS_PROXY > HTTP_PROXY"""
    proxy_url = os.getenv("HTTPS_PROXY", "")
    if proxy_url:
        return proxy_url
    proxy_url = os.getenv("HTTP_PROXY", "")
    if proxy_url:
        return proxy_url
    return ""


def build_http_config():
    """构建 HTTP 配置，代理支持环境变量

    代理 URL 来源（优先级从高到低）:
      1. HTTPS_PROXY
      2. HTTP_PROXY

    代理 URL 格式:
      - http://host:port
      - http://user:pass@host:port
    """
    from huaweicloudsdkcore.http.http_config import HttpConfig

    http_config = HttpConfig.get_default_config()
    http_config.ignore_ssl_verification = True
    http_config.timeout = (30, 60)
    http_config.retry_times = 3

    proxy_url = _get_proxy_url()
    if proxy_url:
        parsed = urlparse(proxy_url)
        http_config.proxy_protocol = parsed.scheme or "http"
        http_config.proxy_host = parsed.hostname or ""
        http_config.proxy_port = parsed.port or 8080
        http_config.proxy_user = parsed.username or ""
        http_config.proxy_password = parsed.password or ""

    return http_config


def get_project_id(region, ak=None, sk=None, security_token=None):
    """通过 IAM API 根据区域名自动获取项目 ID。
    凭据参数可选，不传则从环境变量加载。
    """
    if ak is None:
        ak = os.getenv("HW_ACCESS_KEY", "")
    if sk is None:
        sk = os.getenv("HW_SECRET_KEY", "")
    if security_token is None:
        security_token = os.getenv("HW_SECURITY_TOKEN", "")

    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkiam.v3 import IamClient
    from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
    from huaweicloudsdkiam.v3.region.iam_region import IamRegion

    http_config = build_http_config()
    credentials = BasicCredentials(ak, sk) if not security_token \
        else BasicCredentials(ak, sk).with_security_token(security_token)
    client = IamClient.new_builder() \
        .with_http_config(http_config) \
        .with_credentials(credentials) \
        .with_region(IamRegion.value_of(region)) \
        .build()

    request = KeystoneListProjectsRequest()
    request.name = region
    response = client.keystone_list_projects(request)
    projects = response.projects
    if not projects:
        return None

    for project in projects:
        if getattr(project, 'name', '') == region:
            return project.id

    return projects[0].id


# ── 错误与空结果上下文增强 ────────────────────────────────────────────

def _error_cause(text):
    """按错误文本归类常见失败原因，返回 (原因, 处理建议)。"""
    lowered = text.lower()
    # CCE 跨项目/区域不匹配：401 CCE_CM.0001 Authorize failed, Project ... not match region ...
    # 需在通用 401 之前识别，避免误导为 AK/SK 无效。
    if ("not match region" in lowered
            or ("authorize failed" in lowered and "project" in lowered)):
        return ("region 与 AK/SK 所属项目不匹配（401 Authorize failed）",
                "确认该 AK/SK 的 project 与 --region 是否一致（project/region 一一对应）；"
                "若使用 IAM 子用户，检查其是否被授权访问该区域的项目，详见 references/iam-policies.md")
    if "401" in text or "unauthorized" in lowered or "apigw.0301" in lowered:
        return ("AK/SK 无效或已过期（401 Unauthorized）", "检查 HW_ACCESS_KEY / HW_SECRET_KEY / HW_SECURITY_TOKEN 是否正确且未过期")
    if "403" in text or "forbidden" in lowered or "not authorized" in lowered:
        return ("权限不足（403 Forbidden）", "为该账号补充对应服务的只读权限（CCE 可授予系统策略 CCEReadOnlyPolicy），详见 references/iam-policies.md")
    if "404" in text or "not found" in lowered:
        return ("资源不存在（404 Not Found）", "确认资源 ID 正确，且该资源属于当前 --region 对应的项目")
    if "timeout" in lowered or "timed out" in lowered:
        return ("请求超时", "检查网络与代理（HTTPS_PROXY/HTTP_PROXY），稍后重试或缩小查询范围")
    if "connection" in lowered or "max retries" in lowered or "sslerror" in lowered or "name or service" in lowered:
        return ("网络连接失败", "检查本机网络、代理配置与华为云 Endpoint 连通性")
    if "429" in text or "throttl" in lowered or "too many requests" in lowered:
        return ("请求被流控（429）", "降低查询频率，缩小范围后重试")
    return ("未归类错误", "核对参数与 region 后重试；若持续失败请附上完整错误信息反馈")


def format_api_error(err, action, region, project_id=None, extra=None):
    """把 SDK 异常渲染为带上下文的中文错误说明。

    :param err: 原始异常
    :param action: 动作描述，例如 "CCE 节点列表查询"
    :param region: 区域
    :param project_id: 项目 ID（可选）
    :param extra: 额外上下文，例如 "集群 ID: xxx"
    """
    text = str(err) or err.__class__.__name__
    cause, suggestion = _error_cause(text)
    context = f"区域: {region}"
    if project_id:
        context += f", 项目 ID: {project_id}"
    if extra:
        context += f", {extra}"
    return (
        f"{action} 失败（{context}）\n"
        f"错误: {text}\n"
        f"原因: {cause}\n"
        f"处理建议: {suggestion}"
    )


def format_empty_result(action, region, project_id=None, extra=None, hints=None):
    """空结果时输出带上下文与排查建议的说明。"""
    context = f"区域: {region}"
    if project_id:
        context += f", 项目 ID: {project_id}"
    if extra:
        context += f", {extra}"
    lines = [f"没有找到{action}（{context}）"]
    lines.append("排查建议:")
    for hint in (hints or []):
        lines.append(f"- {hint}")
    return "\n".join(lines)
