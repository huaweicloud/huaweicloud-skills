"""华为云 BSS（费用中心）开放 API 客户端（AK/SK 签名，零依赖）。

通过 SDK-HMAC-SHA256 签名访问 BSS 开放 API，查询代金券余额/明细。
AK/SK 从环境变量读取：HW_ACCESS_KEY/HW_SECRET_KEY 或 HUAWEICLOUD_SDK_AK/HUAWEICLOUD_SDK_SK。
Domain ID 从环境变量读取：HW_DOMAIN_ID（BSS 全局服务需 X-Domain-Id 头）。
"""


import datetime
import hashlib
import hmac
import json
import os
from urllib import error as urlerror
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 15
BSS_HOST = "bss.myhuaweicloud.com"
BSS_BASE = "https://" + BSS_HOST


class BssError(Exception):
    """BSS API 错误。"""
    pass


def _sha256_hex(data):
    """SHA256 哈希，返回十六进制小写。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256_hex(key, msg):
    """HMAC-SHA256，返回十六进制小写。"""
    if isinstance(key, str):
        key = key.encode("utf-8")
    if isinstance(msg, str):
        msg = msg.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _canonical_query(params):
    """构造规范化的 query string（参数名字典序排序 + URL 编码）。"""
    if not params:
        return ""
    parts = []
    for k in sorted(params.keys()):
        v = params[k]
        parts.append("%s=%s" % (quote(str(k), safe=""), quote(str(v), safe="")))
    return "&".join(parts)


class BssClient:
    """华为云 BSS 开放 API 客户端（AK/SK 签名）。

    Args:
        ak: Access Key ID（或环境变量 HW_ACCESS_KEY / HUAWEICLOUD_SDK_AK）。
        sk: Secret Access Key（或环境变量 HW_SECRET_KEY / HUAWEICLOUD_SDK_SK）。
        domain_id: 租户 ID（或环境变量 HW_DOMAIN_ID）。
        base_url: API 基址，默认 https://bss.myhuaweicloud.com。
    """

    def __init__(self, ak=None, sk=None, domain_id=None, base_url=None):
        self.ak = (
            ak
            or os.environ.get("HW_ACCESS_KEY")
            or os.environ.get("HUAWEICLOUD_SDK_AK", "")
        )
        self.sk = (
            sk
            or os.environ.get("HW_SECRET_KEY")
            or os.environ.get("HUAWEICLOUD_SDK_SK", "")
        )
        self.domain_id = (
            domain_id
            or os.environ.get("HW_DOMAIN_ID", "")
        )
        self.base_url = (base_url or BSS_BASE).rstrip("/")
        if not self.ak or not self.sk:
            raise BssError(
                "缺少 AK/SK：请设置环境变量 "
                "HW_ACCESS_KEY/HW_SECRET_KEY 或 "
                "HUAWEICLOUD_SDK_AK/HUAWEICLOUD_SDK_SK"
            )

    def _sign_and_request(self, method, path, params=None, body=None,
                          timeout=DEFAULT_TIMEOUT):
        """构造 SDK-HMAC-SHA256 签名请求并发送。

        BSS 为全局服务，有 domain_id 时加入 X-Domain-Id 头并参与签名。
        """
        host = self.base_url.split("://", 1)[1].split("/", 1)[0]
        query = _canonical_query(params or {})
        url = self.base_url + path
        if query:
            url += "?" + query

        if body is not None:
            payload = json.dumps(body).encode("utf-8")
        else:
            payload = b""

        now = datetime.datetime.utcnow()
        date_str = now.strftime("%Y%m%dT%H%M%SZ")

        content_type = "application/json"
        signed_names = ["content-type", "host", "x-sdk-date"]
        header_vals = {
            "content-type": content_type,
            "host": host,
            "x-sdk-date": date_str,
        }
        if self.domain_id:
            signed_names.append("x-domain-id")
            header_vals["x-domain-id"] = self.domain_id
        signed_names.sort()
        canonical_headers = "".join(
            "%s:%s\n" % (h, header_vals[h]) for h in signed_names
        )
        signed_headers_str = ";".join(signed_names)
        hashed_payload = _sha256_hex(payload)
        # APIGW 归一化规则要求 canonical_uri 以尾部斜杠结尾（官方 SDK signer 一致），
        # 否则真实 BSS 环境签名校验失败返回 HTTP 401 APIGW.0301。
        canonical_uri = quote(path, safe="/")
        if not canonical_uri.endswith("/"):
            canonical_uri += "/"

        canonical_request = "%s\n%s\n%s\n%s\n%s\n%s" % (
            method.upper(),
            canonical_uri,
            query,
            canonical_headers,
            signed_headers_str,
            hashed_payload,
        )

        algorithm = "SDK-HMAC-SHA256"
        hashed_canonical_request = _sha256_hex(canonical_request)
        string_to_sign = "%s\n%s\n%s" % (
            algorithm, date_str, hashed_canonical_request,
        )
        signature = _hmac_sha256_hex(self.sk, string_to_sign)

        headers = {
            "Host": host,
            "Content-Type": content_type,
            "X-Sdk-Date": date_str,
            "Authorization": (
                "SDK-HMAC-SHA256 Access=%s, SignedHeaders=%s, Signature=%s"
                % (self.ak, signed_headers_str, signature)
            ),
        }
        if self.domain_id:
            headers["X-Domain-Id"] = self.domain_id

        req = Request(url, data=payload if payload else None, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urlerror.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise BssError("HTTP %s: %s" % (e.code, raw[:500]))
        except urlerror.URLError as e:
            raise BssError("网络错误：%s" % e.reason)

        try:
            return json.loads(raw)
        except ValueError:
            raise BssError("响应非 JSON：%s" % raw[:500])

    def list_coupons(self, coupon_type=None, status=None, offset=0, limit=100):
        """查询优惠券/代金券列表。对应 GET /v2/promotions/benefits/coupons。

        Args:
            coupon_type: 优惠券类型：1=代金券 2=折扣券 3=产品券 4=现金券，
                None=全部（不筛选）。注意接口合法值从 1 起，0 会触发 CBC.0100。
            status: 优惠券状态：1=未激活 2=待使用 3=已使用 4=已过期 5=已回收，
                None=全部（不筛选）。
            offset: 偏移量，默认 0。
            limit: 每页条数，默认 100。

        返回后端原始响应（count + user_coupons 列表）。
        """
        if coupon_type is not None and coupon_type not in (1, 2, 3, 4):
            raise BssError(
                "coupon_type 合法值为 1=代金券/2=折扣券/3=产品券/4=现金券，"
                "当前 %r" % (coupon_type,)
            )
        if status is not None and status not in (1, 2, 3, 4, 5):
            raise BssError(
                "status 合法值为 1=未激活/2=待使用/3=已使用/4=已过期/5=已回收，"
                "当前 %r" % (status,)
            )
        params = {"offset": offset, "limit": limit}
        if status is not None:
            params["status"] = status
        if coupon_type is not None:
            params["coupon_type"] = coupon_type
        return self._sign_and_request(
            "GET", "/v2/promotions/benefits/coupons", params=params,
        )

    def list_balances(self):
        """查询客户账户余额（含代金券余额）。

        对应 GET /v2/accounts/customer-accounts/balances。
        返回后端原始响应。
        """
        return self._sign_and_request(
            "GET", "/v2/accounts/customer-accounts/balances",
        )