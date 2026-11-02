import os
import urllib3
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkcore.exceptions import exceptions

from huaweicloudsdkconfig.v1 import ConfigClient
from huaweicloudsdkconfig.v1 import (
    ListBuiltInPolicyDefinitionsRequest,
    ListSchemasRequest,
    RunQueryRequest,
    QueryRunRequestBody
)
from huaweicloudsdkconfig.v1.region.config_region import ConfigRegion

# 仅在关闭 TLS 校验（HW_IGNORE_SSL_VERIFICATION=true）时抑制 InsecureRequestWarning
if os.getenv("HW_IGNORE_SSL_VERIFICATION", "").lower() in ("1", "true", "yes"):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_credentials():
    """从环境变量加载华为云凭据

    优先取 HW_ACCESS_KEY / HW_SECRET_KEY，其次 HUAWEICLOUD_AK / HUAWEICLOUD_SK
    可选: HW_SECURITY_TOKEN（临时凭证模式）
    仅需 Config ReadOnlyAccess 权限，无需过度授权。
    """
    ak = os.getenv("HW_ACCESS_KEY", "") or os.getenv("HUAWEICLOUD_AK", "")
    sk = os.getenv("HW_SECRET_KEY", "") or os.getenv("HUAWEICLOUD_SK", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    if not ak or not sk:
        print("未配置 AK/SK，请设置环境变量 HW_ACCESS_KEY/HW_SECRET_KEY（或 HUAWEICLOUD_AK/HUAWEICLOUD_SK）")
        exit(1)

    return ak, sk, security_token


def _get_proxy_url():
    """获取代理 URL，优先级: 自定义 PROXY_URL > HTTPS_PROXY > HTTP_PROXY"""
    for var in ("PROXY_URL", "HTTPS_PROXY", "HTTP_PROXY"):
        proxy_url = os.getenv(var, "")
        if proxy_url:
            return proxy_url
    return ""


def build_http_config():
    """构建 HTTP 配置，代理支持环境变量

    代理 URL 格式:
      - http://host:port
      - http://user:pass@host:port
    未配置代理时不使用代理（公网环境直连）。
    TLS 证书校验默认开启；仅当设置环境变量 HW_IGNORE_SSL_VERIFICATION=true
    （如内网代理使用自签证书）时才关闭。
    """
    http_config = HttpConfig.get_default_config()
    http_config.ignore_ssl_verification = (
        os.getenv("HW_IGNORE_SSL_VERIFICATION", "").lower() in ("1", "true", "yes")
    )
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


def generate_config_client(region="cn-north-4"):
    """构建 Config 客户端（Config 为全局服务，默认 cn-north-4）"""
    ak, sk, security_token = load_credentials()

    credentials = GlobalCredentials(ak, sk)
    if security_token:
        credentials = credentials.with_security_token(security_token)

    return (ConfigClient.new_builder()
            .with_credentials(credentials)
            .with_region(ConfigRegion.value_of(region))
            .with_http_config(build_http_config())
            .build())


def _handle_client_exception(action, e):
    """统一异常处理：打印错误码与信息，不输出任何凭据"""
    print(f"{action} 查询失败")
    print(f"Error code: {e.error_code}")
    print(f"Error message: {e.error_msg}")
    exit(1)


def list_built_in_policy_definitions():
    """查询预置合规规则列表"""
    config_client = generate_config_client()
    try:
        request = ListBuiltInPolicyDefinitionsRequest()
        request.x_language = "zh-cn"
        return config_client.list_built_in_policy_definitions(request).to_dict()
    except exceptions.ClientRequestException as e:
        _handle_client_exception("config.list_built_in_policy_definitions", e)


def list_schema(marker=None):
    """查询资源 Schema 列表（分页）"""
    config_client = generate_config_client()
    try:
        request = ListSchemasRequest()
        request.limit = 200
        if marker:
            request.marker = marker
        return config_client.list_schemas(request).to_dict()
    except exceptions.ClientRequestException as e:
        _handle_client_exception("config.list_schema", e)


def query_Config_resource_by_sql(sql):
    """通过高级查询 SQL 查询资源"""
    config_client = generate_config_client()
    try:
        request = RunQueryRequest()
        request.body = QueryRunRequestBody(expression=sql)
        return config_client.run_query(request).to_dict()
    except exceptions.ClientRequestException as e:
        _handle_client_exception("config.run_query", e)

