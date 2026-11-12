#!/usr/bin/env python3
"""Query Huawei Cloud CCM (SCM) SSL certificates — strictly read-only.

Subcommands:
    list   GET /v3/scm/certificates        (ListCertificates)
    show   GET /v3/scm/certificates/{id}   (ShowCertificate)

``list --output <path>`` additionally renders the same query result as a Markdown
document and writes it to disk (default file name
``ccm_certificates_<region>_<timestamp>.md``). The Markdown text is also printed
to stdout, so the terminal output and the file content are identical line by line.
An empty result never creates an empty file.

Credentials are read from environment variables only and are never printed.
Authentication uses the Huawei Cloud SDK-HMAC-SHA256 AK/SK signature algorithm
(equivalent to huaweicloudsdkcore's Signer) with standard-library urllib only.

Exit codes:
    0 success (including empty result)
    2 invalid arguments / unknown status
    3 missing credentials
    4 HTTP 401/403 (invalid credentials or insufficient permission)
    5 invalid region / unreachable endpoint
    6 other SCM API error
"""

import argparse
import datetime
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ALGORITHM = "SDK-HMAC-SHA256"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DEFAULT_REGION = "cn-north-4"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 50
MAX_PAGES = 200
LIST_PATH = "/v3/scm/certificates"
SHOW_PATH = "/v3/scm/certificates/{certificate_id}"

AK_ENV_NAMES = (
    "HUAWEI_ACCESS_KEY",
    "HUAWEI_AK",
    "HUAWEI_ACCESS_KEY_ID",
    "HW_ACCESS_KEY",
    "HW_AK",
    "HWC_ACCESS_KEY",
    "HWC_AK",
)
SK_ENV_NAMES = (
    "HUAWEI_SECRET_KEY",
    "HUAWEI_SECRET_ACCESS_KEY",
    "HUAWEI_SK",
    "HW_SECRET_KEY",
    "HW_SECRET_ACCESS_KEY",
    "HW_SK",
    "HWC_SECRET_KEY",
    "HWC_SK",
)
TOKEN_ENV_NAMES = (
    "HUAWEI_SECURITY_TOKEN",
    "HW_SECURITY_TOKEN",
    "HWC_SECURITY_TOKEN",
)
REGION_ENV_NAMES = ("HUAWEI_REGION", "HW_REGION_NAME", "HWC_REGION")

STATUS_LABELS = {
    "PAID": "待申请",
    "ISSUED": "已签发",
    "CHECKING": "申请审核中",
    "CANCELCHECKING": "取消申请审核中",
    "UNPASSED": "申请未通过",
    "EXPIRED": "已过期",
    "REVOKING": "吊销审核中",
    "CANCLEREVOKING": "取消吊销审核中",
    "REVOKED": "已吊销",
    "UPLOAD": "托管中",
    "CHECKING_ORG": "待企业认证",
    "ISSUING": "待签发",
    "SUPPLEMENTCHECKING": "附加域名审核中",
    "CANCELSUPPLEMENTING": "取消附加域名审核中",
}

SORT_KEYS = ("certExpiredTime", "certStatus", "certUpdateTime")
SORT_DIRS = ("ASC", "DESC")

# Markdown export
MD_TABLE_HEADERS = (
    "证书 ID", "名称", "类型", "绑定域名", "状态", "签发时间", "到期时间", "剩余天数", "到期等级",
)
DEFAULT_OUTPUT_TEMPLATE = "ccm_certificates_{region}_{timestamp}.md"
OUTPUT_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
GENERATED_AT_FORMAT = "%Y-%m-%d %H:%M:%S %z"

REGION_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]+)+-\d+$")


class QueryError(Exception):
    """Base error carrying a readable message and a process exit code."""

    exit_code = 1


class UsageError(QueryError):
    exit_code = 2


class CredentialError(QueryError):
    exit_code = 3


class AuthError(QueryError):
    exit_code = 4


class RegionError(QueryError):
    exit_code = 5


class ApiError(QueryError):
    exit_code = 6


# ---------------------------------------------------------------------------
# Credentials / region
# ---------------------------------------------------------------------------

def _first_env(env, names):
    for name in names:
        value = str(env.get(name) or "").strip()
        if value:
            return value
    return ""


def load_credentials(env=None):
    """Read AK/SK (and optional token) from environment variables.

    Returns a dict with ak/sk/token. Raises CredentialError when AK or SK is
    missing. The error text only reports variable names, never values.
    """
    env = os.environ if env is None else env
    ak_value = _first_env(env, AK_ENV_NAMES)
    sk_value = _first_env(env, SK_ENV_NAMES)
    token = _first_env(env, TOKEN_ENV_NAMES)
    if not ak_value or not sk_value:
        raise CredentialError(
            "未找到华为云 AK/SK 凭据。请在本会话外通过环境变量配置后重试：\n"
            '  export HUAWEI_ACCESS_KEY="<your-access-key-id>"\n'
            "  read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY\n"
            '  export HUAWEI_REGION="cn-north-4"\n'
            "不要把 AK/SK 粘贴到对话或命令行；脚本不会读取、回显或记录其值。"
        )
    return {"ak": ak_value, "sk": sk_value, "token": token}


def resolve_region(cli_region=None, env=None):
    env = os.environ if env is None else env
    region = (cli_region or _first_env(env, REGION_ENV_NAMES) or DEFAULT_REGION).strip()
    if not REGION_PATTERN.match(region):
        raise UsageError(
            "region 格式非法: %s；示例: cn-north-4、cn-east-3、ap-southeast-1" % region
        )
    return region


def build_host(region, endpoint=None):
    if endpoint:
        value = str(endpoint).strip()
        if "://" in value:
            value = urllib.parse.urlparse(value).netloc
        value = value.rstrip("/")
        if not value:
            raise UsageError("--endpoint 为空或格式非法")
        return value
    if not REGION_PATTERN.match(str(region or "")):
        raise RegionError(
            "region 非法: %s；请使用形如 cn-north-4 的地域名。" % region
        )
    return "scm.%s.myhuaweicloud.com" % region


# ---------------------------------------------------------------------------
# Signing helpers (Huawei Cloud SDK-HMAC-SHA256)
# ---------------------------------------------------------------------------

def url_encode(value):
    return urllib.parse.quote(str(value), safe="~")


def canonical_query_string(query_pairs):
    """Sort (key, value) pairs and RFC3986-encode them like the official signer."""
    normalized = []
    for key, value in query_pairs or []:
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        normalized.append((str(key), str(value)))
    normalized.sort(key=lambda item: (item[0], item[1]))
    return "&".join(
        "%s=%s" % (url_encode(key), url_encode(value)) for key, value in normalized
    )


def canonical_uri(path):
    raw_path = str(path)
    if not raw_path.startswith("/"):
        raw_path = "/" + raw_path
    segments = urllib.parse.unquote(raw_path).split("/")
    encoded = "/".join(url_encode(segment) for segment in segments)
    if not encoded.endswith("/"):
        encoded += "/"
    return encoded


def _utc_timestamp(moment=None):
    moment = moment or datetime.datetime.now(datetime.timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def sign_headers(method, host, path, query_pairs, ak, sk, token=None,
                 timestamp=None, body=b""):
    """Build Host/X-Sdk-Date/SignedHeaders/Authorization for a request.

    Mirrors huaweicloudsdkcore.signer.Signer so the request is accepted by
    Huawei Cloud. Only the signature is derived from SK; the SK itself is never
    returned in headers.
    """
    stamp = timestamp or _utc_timestamp()
    headers = {"Host": host, "X-Sdk-Date": stamp}
    if token:
        headers["X-Security-Token"] = token

    lower_headers = {key.lower(): str(value).strip() for key, value in headers.items()}
    signed_headers = sorted(lower_headers)
    canonical_headers = "".join(
        "%s:%s\n" % (key, lower_headers[key]) for key in signed_headers
    )

    payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_SHA256
    canonical_request = "%s\n%s\n%s\n%s\n%s\n%s" % (
        method.upper(),
        canonical_uri(path),
        canonical_query_string(query_pairs),
        canonical_headers,
        ";".join(signed_headers),
        payload_hash,
    )
    string_to_sign = "%s\n%s\n%s" % (
        ALGORITHM,
        stamp,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    )
    signature = hmac.new(
        sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    headers["Authorization"] = "%s Access=%s, SignedHeaders=%s, Signature=%s" % (
        ALGORITHM,
        ak,
        ";".join(signed_headers),
        signature,
    )
    return headers


class ScmClient:
    """Minimal read-only SCM v3 HTTP client."""

    def __init__(self, region, credentials, endpoint=None, timeout=30):
        self.region = region
        self.ak_value = credentials["ak"]
        self.sk_value = credentials["sk"]
        self.token = credentials.get("token") or None
        self.host = build_host(region, endpoint)
        self.base_url = "https://%s" % self.host
        self.timeout = timeout

    def get(self, path, query_pairs):
        query = canonical_query_string(query_pairs)
        url = self.base_url + path + (("?" + query) if query else "")
        headers = sign_headers(
            "GET", self.host, path, query_pairs, self.ak_value, self.sk_value, token=self.token
        )
        headers["Accept"] = "application/json"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                body = b""
            raise classify_http_error(exc.code, body)
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise RegionError(
                "无法连接 SCM 端点 %s（%s）。请检查 region 是否正确、网络是否可达。"
                % (self.host, reason)
            )
        except TimeoutError:
            raise RegionError("请求 SCM 端点 %s 超时，请检查网络或稍后重试。" % self.host)
        except OSError as exc:
            raise RegionError(
                "连接 SCM 端点 %s 失败（%s）。请检查 region 与网络配置。"
                % (self.host, exc)
            )

        if not payload:
            return {}
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError("SCM 返回了无法解析的响应（非 JSON）。")


def extract_error_message(body):
    try:
        data = json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    code = str(data.get("error_code") or data.get("code") or "").strip()
    msg = str(data.get("error_msg") or data.get("message") or "").strip()
    if code and msg:
        return "%s: %s" % (code, msg)
    return msg or code


def classify_http_error(status_code, body=b""):
    """Map an HTTP error to a readable, secret-free exception."""
    detail = extract_error_message(body)
    if status_code == 401:
        return AuthError(
            "凭据无效或已过期（HTTP 401）。请在会话外更新 AK/SK 后重试。"
            + ((" 详情: " + detail) if detail else "")
        )
    if status_code == 403:
        return AuthError(
            "权限不足（HTTP 403）。需要 IAM 授权项 scm:cert:list（列表）或 "
            "scm:cert:get（详情）。请在华为云 IAM 中为当前账号补充只读权限后重试。"
            + ((" 详情: " + detail) if detail else "")
        )
    if status_code == 404:
        return ApiError("证书或接口不存在（HTTP 404）。" + ((" 详情: " + detail) if detail else ""))
    if status_code == 400:
        return ApiError(
            "请求参数或 region 不被 SCM 接受（HTTP 400）。请检查 region、状态值与过滤条件。"
            + ((" 详情: " + detail) if detail else "")
        )
    return ApiError(
        "SCM 接口返回 HTTP %s。" % status_code
        + ((" 详情: " + detail) if detail else "")
    )


# ---------------------------------------------------------------------------
# Parameter construction / normalization
# ---------------------------------------------------------------------------

def normalize_status(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    key = text.upper().replace("-", "_")
    if key in ("ALL", "*"):
        return "ALL"
    if key in STATUS_LABELS:
        return key
    raise UsageError(
        "未知证书状态: %s；可选值: %s"
        % (text, "、".join(["ALL"] + list(STATUS_LABELS)))
    )


def _param_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_list_query(name=None, status=None, expiring=None, offset=0,
                     limit=DEFAULT_PAGE_SIZE, enterprise_project_id=None,
                     include_shared=False, sort_key=None, sort_dir=None):
    pairs = []
    if name:
        pairs.append(("content", str(name).strip()))
    normalized_status = normalize_status(status)
    if normalized_status and normalized_status != "ALL":
        pairs.append(("status", normalized_status))
    if expiring is not None:
        pairs.append(("expired_days_since", str(int(expiring))))
    if enterprise_project_id:
        pairs.append(("enterprise_project_id", str(enterprise_project_id).strip()))
    if include_shared:
        pairs.append(("owned_by_self", "false"))
    if sort_key:
        if sort_key not in SORT_KEYS:
            raise UsageError("未知排序字段: %s；可选值: %s" % (sort_key, "、".join(SORT_KEYS)))
        pairs.append(("sort_key", sort_key))
    if sort_dir:
        normalized_dir = str(sort_dir).upper()
        if normalized_dir not in SORT_DIRS:
            raise UsageError("未知排序方向: %s；可选值: ASC、DESC" % sort_dir)
        pairs.append(("sort_dir", normalized_dir))
    pairs.append(("limit", str(max(10, min(MAX_PAGE_SIZE, int(limit))))))
    pairs.append(("offset", str(int(offset))))
    return pairs


def parse_certificate_date(value):
    """Parse SCM date strings to a date object; return None when unusable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.match(r"^(\d{4})[-/](\d{2})[-/](\d{2})", text)
    if not match:
        return None
    try:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def days_to_expire(expire_time, now=None):
    expiry = parse_certificate_date(expire_time)
    if expiry is None:
        return None
    today = (now or datetime.datetime.now(datetime.timezone.utc)).date()
    return (expiry - today).days


def grade_expiry(days, threshold=30, status=None):
    if days is None:
        if str(status or "").upper() == "EXPIRED":
            return "expired"
        return "unknown"
    if days < 0:
        return "expired"
    if days <= int(threshold):
        return "expiring"
    return "normal"


EXPIRY_LABELS = {
    "expired": "已过期",
    "expiring": "即将到期",
    "normal": "正常",
    "unknown": "未知",
}


def _field(raw, *names, default=None):
    for name in names:
        if name in raw and raw.get(name) not in (None, ""):
            return raw.get(name)
    return default


def normalize_certificate(raw, threshold=30, now=None):
    """Map an SCM certificate record to a stable output document."""
    raw = raw or {}
    status = _field(raw, "status")
    expire_time = _field(raw, "expire_time", "not_after")
    days = days_to_expire(expire_time, now=now)
    level = grade_expiry(days, threshold=threshold, status=status)
    return {
        "id": _field(raw, "id"),
        "name": _field(raw, "name"),
        "type": _field(raw, "type"),
        "domain": _field(raw, "domain"),
        "sans": _field(raw, "sans"),
        "status": status,
        "status_label": STATUS_LABELS.get(str(status or "").upper(), status),
        "brand": _field(raw, "brand"),
        "signature_algorithm": _field(raw, "signature_algorithm"),
        "issue_time": _field(raw, "issue_time"),
        "not_before": _field(raw, "not_before"),
        "not_after": _field(raw, "not_after"),
        "expire_time": expire_time,
        "validity_period": _field(raw, "validity_period"),
        "domain_type": _field(raw, "domain_type"),
        "domain_count": _field(raw, "domain_count"),
        "wildcard_count": _field(raw, "wildcard_count"),
        "deploy_support": _field(raw, "deploy_support"),
        "enterprise_project_id": _field(raw, "enterprise_project_id"),
        "description": _field(raw, "description"),
        "days_to_expire": days,
        "expiry_level": level,
        "expiry_label": EXPIRY_LABELS.get(level, level),
    }


def normalize_list_payload(payload, threshold=30, now=None):
    payload = payload or {}
    if isinstance(payload, list):
        records = payload
        total = len(records)
    else:
        records = payload.get("certificates") or []
        total = payload.get("total_count")
        if total is None:
            total = len(records)
    certs = [normalize_certificate(item, threshold=threshold, now=now) for item in records]
    return certs, int(total or 0)


def normalize_show_payload(payload, threshold=30, now=None):
    cert = normalize_certificate(payload, threshold=threshold, now=now)
    raw = payload or {}
    cert["order_id"] = _field(raw, "order_id")
    cert["push_support"] = _field(raw, "push_support")
    cert["revoke_reason"] = _field(raw, "revoke_reason")
    cert["validation_method"] = _field(raw, "validation_method")
    cert["multi_domain_type"] = _field(raw, "multi_domain_type")
    cert["fingerprint"] = _field(raw, "fingerprint")
    cert["shared"] = _field(raw, "shared")
    cert["application_info"] = _field(raw, "application_info")
    cert["authentification"] = _field(raw, "authentification")
    return cert


def collect_certificates(client, query_pairs, limit=None, start_offset=0,
                         threshold=30, now=None):
    """Page through ListCertificates until exhausted or the cap is reached."""
    base_pairs = [(key, value) for key, value in query_pairs
                  if key not in ("limit", "offset")]
    collected = []
    total = None
    offset = int(start_offset)
    page_size = DEFAULT_PAGE_SIZE
    pages = 0

    while pages < MAX_PAGES:
        remaining = None if limit is None else max(0, int(limit) - len(collected))
        if remaining is not None and remaining <= 0:
            break
        request_size = page_size
        if remaining is not None:
            request_size = min(page_size, max(10, remaining))
        pairs = base_pairs + [("limit", str(request_size)), ("offset", str(offset))]
        payload = client.get(LIST_PATH, pairs)
        certs, page_total = normalize_list_payload(payload, threshold=threshold, now=now)
        total = page_total if total is None else max(total, page_total)
        if not certs:
            break
        collected.extend(certs)
        offset += len(certs)
        pages += 1
        if limit is not None and len(collected) >= int(limit):
            break
        if total is not None and offset >= total:
            break

    if limit is not None:
        collected = collected[: int(limit)]
    return collected, int(total if total is not None else len(collected))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _text(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def _short_date(value):
    date = parse_certificate_date(value)
    return date.isoformat() if date else _text(value)


def _display_width(text):
    width = 0
    for char in str(text):
        width += 2 if unicodedata_east_asian_wide(char) else 1
    return width


def unicodedata_east_asian_wide(char):
    import unicodedata
    return unicodedata.east_asian_width(char) in ("W", "F")


def _truncate(text, width):
    text = str(text)
    if _display_width(text) <= width:
        return text
    result = ""
    used = 0
    for char in text:
        char_width = 2 if unicodedata_east_asian_wide(char) else 1
        if used + char_width > width - 1:
            break
        result += char
        used += char_width
    return result + "…"


def _pad(text, width):
    return text + " " * max(0, width - _display_width(text))


def render_table(certs):
    headers = ["ID", "名称", "类型", "域名", "状态", "签发时间", "到期时间", "剩余天数", "到期分级"]
    rows = []
    for cert in certs:
        days = cert.get("days_to_expire")
        rows.append([
            _text(cert.get("id")),
            _text(cert.get("name")),
            _text(cert.get("type")),
            _text(cert.get("domain")),
            _text(cert.get("status_label") or cert.get("status")),
            _short_date(cert.get("issue_time")),
            _short_date(cert.get("expire_time")),
            "-" if days is None else str(days),
            _text(cert.get("expiry_label") or cert.get("expiry_level")),
        ])

    widths = [_display_width(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = min(max(widths[index], _display_width(cell)), 34)

    def line(left, mid, right):
        return left + mid.join("─" * (width + 2) for width in widths) + right

    output = [line("┌", "┬", "┐")]
    output.append("│ " + " │ ".join(_pad(header, widths[i]) for i, header in enumerate(headers)) + " │")
    output.append(line("├", "┼", "┤"))
    if not rows:
        output.append("│ " + _pad("无匹配证书（total: 0）", sum(widths) + 3 * (len(widths) - 1)) + " │")
    for row in rows:
        output.append(
            "│ " + " │ ".join(
                _pad(_truncate(cell, widths[i]), widths[i]) for i, cell in enumerate(row)
            ) + " │"
        )
    output.append(line("└", "┴", "┘"))
    output.append("共 %d 张证书" % len(certs))
    return "\n".join(output)


def render_detail(cert):
    labels = [
        ("id", "证书 ID"),
        ("name", "证书名称"),
        ("type", "证书类型"),
        ("domain", "绑定域名"),
        ("sans", "附加域名"),
        ("status", "状态"),
        ("status_label", "状态说明"),
        ("brand", "证书品牌"),
        ("signature_algorithm", "签名算法"),
        ("issue_time", "签发时间"),
        ("not_before", "生效时间"),
        ("not_after", "失效时间"),
        ("expire_time", "到期时间"),
        ("validity_period", "有效期（月）"),
        ("domain_type", "域名类型"),
        ("domain_count", "可绑定域名数"),
        ("wildcard_count", "可绑定泛域名数"),
        ("deploy_support", "支持部署"),
        ("fingerprint", "SHA-1 指纹"),
        ("validation_method", "域名认证方式"),
        ("order_id", "订单 ID"),
        ("enterprise_project_id", "企业项目 ID"),
        ("description", "描述"),
        ("days_to_expire", "剩余天数"),
        ("expiry_level", "到期分级"),
        ("expiry_label", "到期说明"),
    ]
    lines = ["证书详情:"]
    for key, label in labels:
        value = cert.get(key)
        if key == "status" and value:
            lines.append("  %s: %s" % (label, value))
        else:
            lines.append("  %s: %s" % (label, _text(value)))
    application_info = cert.get("application_info")
    if isinstance(application_info, dict):
        lines.append("  申请信息: " + json.dumps(application_info, ensure_ascii=False, sort_keys=True))
    authentification = cert.get("authentification")
    if isinstance(authentification, list) and authentification:
        lines.append("  域名认证信息: " + json.dumps(authentification, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def escape_markdown_cell(value):
    """Render one table cell: escape pipes/backslashes, fold newlines, keep '-'.

    Markdown has no cell-spanning syntax, so CR/LF become ``<br>``; a literal
    backslash and ``|`` are escaped to keep the table structure intact.
    """
    text = _text(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    text = text.replace("\n", "<br>")
    return text.strip() or "-"


def markdown_row(cert):
    """Map one normalized certificate to the Markdown table row cells."""
    days = cert.get("days_to_expire")
    return [
        escape_markdown_cell(cert.get("id")),
        escape_markdown_cell(cert.get("name")),
        escape_markdown_cell(cert.get("type")),
        escape_markdown_cell(cert.get("domain")),
        escape_markdown_cell(cert.get("status_label") or cert.get("status")),
        escape_markdown_cell(_short_date(cert.get("issue_time"))),
        escape_markdown_cell(_short_date(cert.get("expire_time"))),
        escape_markdown_cell("-" if days is None else days),
        escape_markdown_cell(cert.get("expiry_label") or cert.get("expiry_level")),
    ]


def describe_filters(filters=None):
    """One-line human description of the applied filters, for the summary block."""
    filters = filters or {}
    status = filters.get("status")
    status_text = "全部（ALL）" if not status or status == "ALL" else str(status)
    parts = [
        "名称/域名（服务端模糊）=%s" % _text(filters.get("name")),
        "状态（服务端）=%s" % status_text,
        "到期窗口（服务端，天）=%s" % _text(filters.get("expiring")),
        "到期分级阈值（天）=%s" % _text(filters.get("expire_days")),
        "企业项目=%s" % _text(filters.get("enterprise_project_id")),
        "包含共享证书=%s" % ("是" if filters.get("include_shared") else "否"),
        "排序=%s %s" % (_text(filters.get("sort_key")), _text(filters.get("sort_dir"))),
        "条数上限=%s" % ("不限" if filters.get("limit") in (None, "") else filters.get("limit")),
        "起始偏移=%s" % _text(filters.get("offset")),
    ]
    return "；".join(parts)


def generated_at_text(moment=None):
    moment = moment or datetime.datetime.now().astimezone()
    return moment.strftime(GENERATED_AT_FORMAT)


def render_markdown(certs, region="", filters=None, total=None, threshold=30,
                    generated_at=None, title="华为云 CCM 证书清单"):
    """Render the list result as a self-contained Markdown document.

    The document carries a summary block (region, filters, generation time,
    record count) followed by the same nine columns as the terminal table, so
    the exported file and the console output stay consistent.
    """
    certs = list(certs or [])
    if total is None:
        total = len(certs)
    lines = [
        "# %s" % title,
        "",
        "| 摘要项 | 内容 |",
        "|--------|------|",
        "| Region | %s |" % escape_markdown_cell(region),
        "| 查询条件 | %s |" % escape_markdown_cell(describe_filters(filters)),
        "| 生成时间 | %s |" % escape_markdown_cell(generated_at or generated_at_text()),
        "| 记录数 | 返回 %d 张（服务端匹配 %d 张） |" % (len(certs), int(total or 0)),
        "| 到期分级 | 已过期=expired，即将到期=expiring（0～%d 天），正常=normal，未知=unknown |"
        % int(threshold),
        "",
        "| " + " | ".join(MD_TABLE_HEADERS) + " |",
        "|" + "|".join(["------"] * len(MD_TABLE_HEADERS)) + "|",
    ]
    if certs:
        for cert in certs:
            lines.append("| " + " | ".join(markdown_row(cert)) + " |")
    else:
        placeholder = ["-"] * len(MD_TABLE_HEADERS)
        placeholder[1] = "无匹配证书（共 0 条）"
        lines.append("| " + " | ".join(placeholder) + " |")
    lines.append("")
    lines.append("> 数据来源：SCM v3 `GET /v3/scm/certificates`（只读）；"
                 "共 %d 张证书。" % len(certs))
    return "\n".join(lines)


def default_output_name(region, timestamp=None):
    """``ccm_certificates_<region>_<timestamp>.md``."""
    stamp = timestamp or datetime.datetime.now().strftime(OUTPUT_TIMESTAMP_FORMAT)
    return DEFAULT_OUTPUT_TEMPLATE.format(region=region, timestamp=stamp)


def resolve_output_path(output, region, timestamp=None):
    """Resolve ``--output`` to a concrete file path.

    Accepts a file path, an existing directory, or a path ending with a
    separator (then the default file name is used inside it). A missing parent
    directory is a readable usage error rather than a traceback.
    """
    default_name = default_output_name(region, timestamp)
    raw = str(output or "").strip()
    if not raw:
        return default_name
    expanded = os.path.expanduser(raw)
    if expanded.endswith(os.sep) or os.path.isdir(expanded):
        return os.path.join(expanded, default_name)
    parent = os.path.dirname(expanded)
    if parent and not os.path.isdir(parent):
        raise UsageError(
            "导出目录不存在: %s；请先创建目录，或把 --output 指向已存在的目录/文件。"
            % parent
        )
    return expanded


def write_markdown(path, content):
    """Write UTF-8 Markdown; errors are surfaced as readable usage errors."""
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content if content.endswith("\n") else content + "\n")
    except OSError as exc:
        raise UsageError(
            "无法写入 Markdown 文件 %s（%s）；请检查路径与写权限。"
            % (path, getattr(exc, "strerror", None) or exc)
        )
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_common(parser):
    parser.add_argument("--region", default=None,
                        help="Huawei Cloud region (default: HUAWEI_REGION or cn-north-4)")
    parser.add_argument("--endpoint", default=None,
                        help="Endpoint override (default: scm.{region}.myhuaweicloud.com)")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Emit structured JSON instead of a table")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Query Huawei Cloud CCM SCM SSL certificates (read-only)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List SCM SSL certificates")
    _add_common(list_parser)
    list_parser.add_argument("--name", default=None,
                             help="Server-side fuzzy search by certificate name or domain")
    list_parser.add_argument("--status", default=None,
                             help="Server-side status filter (SCM code or alias)")
    list_parser.add_argument("--expiring", type=int, default=None,
                             help="Only certificates expiring within N days")
    list_parser.add_argument("--expire-days", type=int, default=30,
                             help="Local expiry-grade threshold in days (default: 30)")
    list_parser.add_argument("--limit", type=int, default=None,
                             help="Maximum total records to return (default: all)")
    list_parser.add_argument("--offset", type=int, default=0,
                             help="Starting offset (default: 0)")
    list_parser.add_argument("--enterprise-project-id", default=None,
                             help="Enterprise project ID (all / 0 / UUID)")
    list_parser.add_argument("--include-shared", action="store_true",
                             help="Include certificates shared with the tenant")
    list_parser.add_argument("--sort-key", default="certExpiredTime",
                             help="certExpiredTime / certStatus / certUpdateTime")
    list_parser.add_argument("--sort-dir", default="ASC", help="ASC / DESC")
    list_parser.add_argument("--output", default=None, metavar="PATH",
                             help="Export the same result as a Markdown file "
                                  "(PATH may be a file, an existing directory, or a "
                                  "path ending with '/' for the default name "
                                  "ccm_certificates_<region>_<timestamp>.md); "
                                  "markdown is echoed to stdout as well")

    show_parser = subparsers.add_parser("show", help="Show one certificate")
    _add_common(show_parser)
    show_parser.add_argument("--cert-id", required=True, help="Certificate ID")
    show_parser.add_argument("--expire-days", type=int, default=30,
                             help="Local expiry-grade threshold in days (default: 30)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if getattr(args, "output", None) and getattr(args, "as_json", False):
            raise UsageError("--output 与 --json 不能同时使用；请二选一（Markdown 导出或 JSON 输出）。")
        region = resolve_region(args.region)
        credentials = load_credentials()
        if args.command == "show" and not str(args.cert_id or "").strip():
            raise UsageError("--cert-id 不能为空")
        if args.timeout <= 0:
            raise UsageError("--timeout 必须大于 0")
        client = ScmClient(region, credentials, endpoint=args.endpoint, timeout=args.timeout)

        if args.command == "list":
            if args.limit is not None and args.limit <= 0:
                raise UsageError("--limit 必须大于 0")
            if args.expiring is not None and args.expiring < 0:
                raise UsageError("--expiring 不能为负数")
            if args.expire_days < 0:
                raise UsageError("--expire-days 不能为负数")
            query = build_list_query(
                name=args.name,
                status=args.status,
                expiring=args.expiring,
                offset=args.offset,
                enterprise_project_id=args.enterprise_project_id,
                include_shared=args.include_shared,
                sort_key=args.sort_key,
                sort_dir=args.sort_dir,
            )
            certs, total = collect_certificates(
                client, query, limit=args.limit, start_offset=args.offset,
                threshold=args.expire_days,
            )
            if args.as_json:
                print(json.dumps({
                    "region": region,
                    "total": total,
                    "returned": len(certs),
                    "filters": {
                        "name": args.name,
                        "status": normalize_status(args.status),
                        "expiring": args.expiring,
                        "enterprise_project_id": args.enterprise_project_id,
                        "include_shared": bool(args.include_shared),
                    },
                    "expiry_threshold_days": args.expire_days,
                    "certs": certs,
                }, ensure_ascii=False, indent=2))
            elif args.output:
                filters = {
                    "name": args.name,
                    "status": normalize_status(args.status),
                    "expiring": args.expiring,
                    "expire_days": args.expire_days,
                    "enterprise_project_id": args.enterprise_project_id,
                    "include_shared": bool(args.include_shared),
                    "sort_key": args.sort_key,
                    "sort_dir": args.sort_dir,
                    "limit": args.limit,
                    "offset": args.offset,
                }
                if not certs:
                    print("未查询到任何证书（total: 0），未生成 Markdown 文件。")
                    return 0
                document = render_markdown(
                    certs,
                    region=region,
                    filters=filters,
                    total=total,
                    threshold=args.expire_days,
                )
                path = resolve_output_path(args.output, region)
                write_markdown(path, document)
                print(document)
                sys.stderr.write("已导出 %d 张证书到 %s\n" % (len(certs), path))
            else:
                print(render_table(certs))
            return 0

        cert_id = str(args.cert_id).strip()
        path = SHOW_PATH.format(certificate_id=urllib.parse.quote(cert_id, safe=""))
        payload = client.get(path, [])
        cert = normalize_show_payload(payload, threshold=args.expire_days)
        if args.as_json:
            print(json.dumps({"region": region, "cert": cert}, ensure_ascii=False, indent=2))
        else:
            print(render_detail(cert))
        return 0
    except QueryError as exc:
        sys.stderr.write("错误: %s\n" % exc)
        return exc.exit_code
    except KeyboardInterrupt:
        sys.stderr.write("已取消。\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())