# AI生成
#!/usr/bin/env python3
"""华为云认证模块 - 支持 AK/SK 签名认证和 Token 认证"""

import hashlib
import hmac
import datetime
import requests
import base64
import urllib.parse

# 华为云 SDK-HMAC-SHA256 签名常量（与 huaweicloudsdkcore signer 对齐）
_EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class HuaweiCloudAuth:
    """华为云认证基类"""

    def __init__(self, region, project_id):
        self.region = region
        self.project_id = project_id
        self.endpoint = f"ecs.{region}.myhuaweicloud.com"

    def get_headers(self):
        """获取认证请求头，子类实现"""
        raise NotImplementedError


class AKSKAuth(HuaweiCloudAuth):
    """AK/SK 签名认证"""

    def __init__(self, ak, sk, region, project_id):
        super().__init__(region, project_id)
        self.ak = ak
        self.sk = sk

    @staticmethod
    def _url_encode(s):
        """URL 编码（与官方 signer 一致，safe='~'）"""
        return urllib.parse.quote(s, safe="~")

    def _sign(self, method, uri, headers, query_string=""):
        """计算 SDK-HMAC-SHA256 签名

        与 huaweicloudsdkcore.signer.Signer 对齐：
        CanonicalRequest = method + '\n' + CanonicalURI + '\n' +
                           CanonicalQueryString + '\n' + CanonicalHeaders + '\n' +
                           SignedHeaders + '\n' + HexEncode(Hash(RequestPayload))
        """
        # 1. 规范化请求头（小写 key，value trim）
        canonical_headers = {}
        signed_headers_list = []
        # 官方 signer：先按小写 key 排序（大小写敏感排序会导致 host 位置错误）
        for key, value in sorted(headers.items(), key=lambda kv: kv[0].lower()):
            lower_key = key.lower()
            canonical_headers[lower_key] = str(value).strip()
            signed_headers_list.append(lower_key)
        signed_headers = ";".join(signed_headers_list)

        # 2. CanonicalURI：路径分段 URL 编码，并以 '/' 结尾（与官方一致）
        path = uri.split("?")[0]
        segments = [seg for seg in path.split("/") if seg != ""]
        canonical_uri = "/" + "/".join(self._url_encode(seg) for seg in segments)
        if not canonical_uri.endswith("/"):
            canonical_uri += "/"

        # 3. CanonicalQueryString：按 key 排序，key/value 均 URL 编码
        if query_string:
            pairs = []
            for item in query_string.split("&"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    pairs.append(f"{self._url_encode(k)}={self._url_encode(v)}")
            pairs.sort()
            canonical_query_string = "&".join(pairs)
        else:
            canonical_query_string = ""

        # 4. CanonicalHeaders：'key:value\n' 拼接（每行带换行，尾部也带）
        canonical_headers_str = ""
        for key in sorted(canonical_headers):
            canonical_headers_str += f"{key}:{canonical_headers[key]}\n"

        # 5. Payload hash：GET 请求无 body → 空字符串哈希
        payload_hash = _EMPTY_HASH

        canonical_request = (
            f"{method.upper()}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers_str}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # 6. String to Sign
        sdk_date = headers.get("X-Sdk-Date", "")
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = (
            f"SDK-HMAC-SHA256\n"
            f"{sdk_date}\n"
            f"{hashed_canonical_request}"
        )

        # 7. 签名
        signature = hmac.new(
            self.sk.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        auth_header = (
            f"SDK-HMAC-SHA256 "
            f"Access={self.ak}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        return auth_header

    def get_headers(self, method="GET", uri="/", query_string=""):
        """获取带签名的请求头"""
        sdk_date = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        headers = {
            "Content-Type": "application/json",
            "X-Sdk-Date": sdk_date,
            "host": self.endpoint,
        }
        auth_header = self._sign(method, uri, headers, query_string)
        headers["Authorization"] = auth_header
        return headers


class TokenAuth(HuaweiCloudAuth):
    """Token 认证"""

    IAM_ENDPOINT_TEMPLATE = "iam.{region}.myhuaweicloud.com"

    def __init__(self, username, password, domain_id, region, project_id):
        super().__init__(region, project_id)
        self.username = username
        self.password = password
        self.domain_id = domain_id
        self._token = None
        self._token_expire = None

    def _get_token(self):
        """通过 IAM 获取 Token"""
        iam_endpoint = self.IAM_ENDPOINT_TEMPLATE.format(region=self.region)
        url = f"https://{iam_endpoint}/v3/auth/tokens"

        body = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.username,
                            "password": self.password,
                            "domain": {"name": self.domain_id},
                        }
                    },
                },
                "scope": {"project": {"id": self.project_id}},
            }
        }

        resp = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()

        token = resp.headers.get("X-Subject-Token")
        if not token:
            raise ValueError("Failed to get token: X-Subject-Token not found in response")

        # Token 有效期 24 小时，提前 5 分钟过期
        self._token = token
        self._token_expire = datetime.datetime.now() + datetime.timedelta(
            hours=23, minutes=55
        )

        return token

    def get_headers(self, method="GET", uri="/", query_string=""):
        """获取带 Token 的请求头"""
        if self._token is None or (
            self._token_expire and datetime.datetime.now() >= self._token_expire
        ):
            self._get_token()

        return {
            "Content-Type": "application/json",
            "X-Auth-Token": self._token,
        }


def create_auth(config):
    """根据配置创建认证实例

    Args:
        config: 包含认证信息的字典

    Returns:
        HuaweiCloudAuth 子类实例
    """
    auth_method = config.get("auth_method", "aksk").lower()
    region = config.get("region", "cn-north-4")
    project_id = config.get("project_id", "")

    if auth_method == "aksk":
        ak = config.get("ak", "")
        sk = config.get("sk", "")
        if not ak or not sk:
            raise ValueError("AK/SK 认证需要提供 ak 和 sk 配置")
        if not project_id:
            raise ValueError("需要提供 project_id 配置")
        return AKSKAuth(ak, sk, region, project_id)

    elif auth_method == "token":
        username = config.get("username", "")
        password = config.get("password", "")
        domain_id = config.get("domain_id", "")
        if not username or not password:
            raise ValueError("Token 认证需要提供 username 和 password 配置")
        if not project_id:
            raise ValueError("需要提供 project_id 配置")
        return TokenAuth(username, password, domain_id, region, project_id)

    else:
        raise ValueError(f"不支持的认证方式: {auth_method}，请使用 'aksk' 或 'token'")
