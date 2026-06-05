import os
import urllib3
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig

# 抑制因 ignore_ssl_verification 产生的 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
