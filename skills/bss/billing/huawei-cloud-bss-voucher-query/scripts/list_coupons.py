#!/usr/bin/env python3
"""Query Huawei Cloud BSS (费用中心) vouchers / coupons with enterprise-project
(企业项目 / project_id) dimension support.

Primary execution path is KooCLI `hcloud BSS ListSubCustomerCoupons` (read-only
GET /v2/promotions/benefits/coupons); when hcloud is not installed the script
falls back to the official `huaweicloudsdkbss` v2 SDK
(`BssClient.list_sub_customer_coupons`). Credentials are always read from the
active CLI profile / SDK environment — never passed as literals.

Feature summary:
- Full voucher list (table / --json / --names-only), automatic offset paging
  (BSS page limit 100), strict write-intent guard (read-only).
- Server-side filters forwarded when the API supports them: `--coupon-id`,
  `--status` (1-5 / aliases), `--coupon-type`. Client-side filters applied
  after the full list is fetched: `--name`, `--project-id`.
- `--project-id`: enterprise project (企业项目) scoped filtering. The BSS
  coupon-list API (`ListSubCustomerCoupons`) carries **no** project_id field in
  its request or its coupon records — it is a global (domain) API. The script
  therefore attributes coupons to enterprise projects through the customer
  order linkage (coupon.order_id / lock_order_id → `ListCustomerOrders`
  → order.enterprise_projects) and filters locally, mirroring the `--name`
  client-side strategy. Records with no attributable order keep project_id "-".
- `--expiring [days]` / `--expired`: list vouchers that expire soon / already
  expired (based on valid_time / expire_time), combinable with `--project-id`.
- `--usage-analysis`: aggregate face_value vs balance per enterprise project
  (count / total face / total balance / used / usage rate) for financial
  apportionment and reconciliation.

Usage:
    python3 scripts/list_coupons.py [--region cn-north-1] [--json | --names-only]
                                    [--status available] [--name plan-2026]
                                    [--project-id proj-xxx] [--coupon-id CP...]
                                    [--expiring 30] [--expired] [--usage-analysis]
                                    [--export xlsx,html] [--out-dir DIR]

Environment overrides (mostly for tests):
    VOUCHER_QUERY_HCLOUD_BIN   hcloud executable (default "hcloud")
    VOUCHER_QUERY_HCLOUD_ARGS  extra args injected before the BSS operation
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from skill_quality_sdk import quality_report
from report_export import (
    DEFAULT_EXPIRING_DAYS,
    ExportError,
    ensure_out_dir,
    export_report,
    parse_formats,
)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 100
MAX_PAGES = 100
SERVICE = "BSS"
ALLOWED_OPERATION = "ListSubCustomerCoupons"
ALLOWED_ORDER_OPERATION = "ListCustomerOrders"
BSS_ENDPOINT = "https://bss.myhuaweicloud.com"
# BSS is a global service and KooCLI only accepts the cn-north-1 channel
# region; other values fail at the CLI layer before the BSS call is signed.
BSS_SUPPORTED_REGIONS = ("cn-north-1",)
DEFAULT_REGION = BSS_SUPPORTED_REGIONS[0]

# The real BSS coupon-list operation is ListSubCustomerCoupons; "ListCoupons"
# is accepted as a read-only alias and normalised to the real operation.
OPERATION_ALIASES = {
    "listsubcustomercoupons": ALLOWED_OPERATION,
    "listcoupons": ALLOWED_OPERATION,
}

WRITE_INTENT_KEYWORDS = (
    "createpartnercoupons",
    "reclaimpartnercoupons",
    "reclaimcouponquotas",
    "reclaimenterprisemultiaccountcoupon",
    "claimenterprisemultiaccountcoupon",
    "updatecouponquotas",
    "adjustcouponquotas",
    "transferenterprisemultiaccountcoupon",
    "retrieveenterprisemultiaccountcoupon",
    "sendcoupon",
    "issuecoupon",
    "deletecoupon",
    "freezecoupon",
    "unfreezecoupon",
    "cancelcoupon",
    "create",
    "delete",
    "update",
    "modify",
    "transfer",
    "retrieve",
    "adjust",
    "send",
    "issue",
    "cancel",
    "freeze",
    "unfreeze",
    "destroy",
    "创建",
    "删除",
    "修改",
    "回收",
    "发放",
    "转移",
    "认领",
    "调整",
    "冻结",
    "作废",
    "核销",
)

STATUS_LABELS = {
    1: "UNACTIVATED",
    2: "AVAILABLE",
    3: "USED",
    4: "EXPIRED",
    5: "RECLAIMED",
}
COUPON_TYPE_LABELS = {
    1: "VOUCHER",
    2: "DISCOUNT",
    3: "PRODUCT",
    4: "CASH",
}
STATUS_ALIASES = {
    "1": 1, "unactivated": 1, "inactive": 1, "pending": 1, "notactivated": 1,
    "2": 2, "available": 2, "unused": 2, "valid": 2, "active": 2, "touse": 2,
    "3": 3, "used": 3,
    "4": 4, "expired": 4,
    "5": 5, "reclaimed": 5, "recycled": 5, "recalled": 5,
}

PREFERRED_COLUMNS = [
    "coupon_id",
    "coupon_code",
    "statusText",
    "couponTypeText",
    "plan_name",
    "face_value",
    "balance",
    "currency",
    "valid_time",
    "expire_time",
    "active_time",
    "order_id",
    "project_id",
    "project_name",
    "promotion_plan_id",
    "customer_id",
    "source_id",
]

_COUPON_LIST_KEYS = ("user_coupons", "coupons", "coupon_infos", "coupon_list")

_CREDENTIAL_MISSING_PATTERNS = (
    "cli-ak",
    "cli-sk",
    "access key",
    "secret key",
    "credential",
    "configure",
    "未配置",
    "配置为空",
    "no ak",
    "no sk",
    "ak/sk",
)
_AUTH_PATTERNS = (
    "401",
    "403",
    "unauthorized",
    "forbidden",
    "apigw.0301",
    "认证失败",
    "权限不足",
    "permission denied",
)
# BSS business error codes that mean "not authorized for this operation".
# CBC.0151 is what the coupon API returns when the identity lacks
# billing:coupon:view (or a related billing permission).
_AUTH_ERROR_CODES = frozenset({
    "cbc.0151",
    "apigw.0301",
    "apigw.0302",
})
_REGION_UNSUPPORTED_PATTERNS = (
    "cli-region的值不支持",
    "cli-region is not supported",
    "region is not supported",
    "region not supported",
    "不支持的区域",
    "支持的区域值如下",
)
_USE_ERROR_MARKER = "[use_error]"
# KooCLI builds that carry no BSS service reject the call with
# `[USE_ERROR]Unsupported service: BSS` before the request is signed. That is
# not a credential or API failure — it means the CLI catalog is incomplete, so
# the SDK fallback must take over instead of hard-failing (SKILL.md promises a
# transparent SDK fallback).
_UNSUPPORTED_SERVICE_PATTERNS = (
    "unsupported service",
    "not supported service",
    "service not supported",
    "service not found",
    "不支持的 service",
    "不支持的服务",
    "服务不存在",
)


class VoucherQueryError(Exception):
    """Base error for the BSS voucher query skill."""


class GuardError(VoucherQueryError):
    """A write intent was detected and blocked (skill is read-only)."""


class UsageError(VoucherQueryError):
    """An invalid argument value was supplied (region/status/days/page size)."""


class ConfigError(VoucherQueryError):
    """hcloud missing or credentials (AK/SK) not configured."""


class AuthError(VoucherQueryError):
    """Authentication/authorization failure (invalid AK/SK or IAM 403)."""


class ApiError(VoucherQueryError):
    """hcloud / network / unexpected API failure."""


def guard_write_intent(text):
    """Raise GuardError if `text` carries a mutating intent."""
    low = re.sub(r"[\s_\-]+", "", str(text).lower())
    for keyword in WRITE_INTENT_KEYWORDS:
        if keyword in low:
            raise GuardError(
                "检测到写操作意图（关键词: %s）。本 skill 仅支持只读查询"
                "（BSS %s），创建/回收/调整/转移等变更操作已被守卫拦截。"
                % (keyword, ALLOWED_OPERATION)
            )
    return False


def normalize_operation(operation):
    """Map a read-only operation / alias to the real BSS operation name."""
    key = re.sub(r"[\s_\-]+", "", str(operation).lower())
    if key in OPERATION_ALIASES:
        return OPERATION_ALIASES[key]
    return operation


def guard_operation(operation):
    """Only the read-only coupon-list operation may be executed."""
    normalized = normalize_operation(operation)
    if normalized != ALLOWED_OPERATION:
        raise GuardError(
            "不允许的操作 %r：本 skill 仅允许只读操作 %s。"
            % (operation, ALLOWED_OPERATION)
        )
    return normalized


def parse_status(value):
    """Map a --status value to the numeric BSS status (1-5), else None."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if value in STATUS_LABELS else None
    key = re.sub(r"[\s_\-]+", "", str(value).strip().lower())
    return STATUS_ALIASES.get(key)


def _hcloud_executable():
    return os.environ.get("VOUCHER_QUERY_HCLOUD_BIN", "hcloud")


def run_hcloud(argv):
    """Execute hcloud and return (stdout, stderr, returncode)."""
    cmd = [_hcloud_executable()]
    extra = os.environ.get("VOUCHER_QUERY_HCLOUD_ARGS", "").split()
    if extra:
        cmd.extend(extra)
    cmd.extend(argv)
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=120, universal_newlines=True,
        )
    except FileNotFoundError:
        raise ConfigError(
            "未找到 hcloud（KooCLI）。请先安装 KooCLI 并完成认证配置，"
            "参见 references/cli-installation-guide.md。"
        )
    except subprocess.TimeoutExpired:
        raise ApiError("hcloud 执行超时（120s），请检查网络后重试。")
    return proc.stdout or "", proc.stderr or "", proc.returncode


def extract_json(stdout):
    """Parse hcloud stdout as JSON; tolerate wrapper/noise lines."""
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ApiError("hcloud 输出无法解析为 JSON：%s" % text[:200])


def extract_error_envelope(payload):
    """Return ``{code, message}`` when a response body is an error envelope.

    hcloud can return an HTTP error payload (``error_code`` / ``error_msg``)
    while still exiting with code 0. Treating that as an empty result would
    silently turn an auth/permission failure into "no vouchers".
    """
    if not isinstance(payload, dict):
        return None
    code = payload.get("error_code") or payload.get("errorCode")
    message = payload.get("error_msg") or payload.get("errorMsg")
    if code is None and message is None:
        return None
    return {
        "code": str(code or "").strip(),
        "message": str(message or "").strip(),
    }


def classify_hcloud_failure(stdout, stderr, returncode, error=None):
    """Map a failed hcloud invocation / error payload to a domain error."""
    blob = (stderr + " " + stdout).strip()
    low = blob.lower()
    if error is None:
        try:
            error = extract_error_envelope(extract_json(stdout))
        except VoucherQueryError:
            error = None
    if error:
        code = error.get("code", "")
        message = error.get("message", "")
        detail = ("%s %s" % (code, message)).strip()[:300]
        code_low = code.lower()
        if code_low in _AUTH_ERROR_CODES or any(
                p in (code + " " + message).lower() for p in _AUTH_PATTERNS):
            return AuthError(
                "无权限访问 BSS 代金券（%s）：请检查 IAM 权限（需只读 "
                "billing:coupon:view，按企业项目筛选时还需 billing:order:view），"
                "参见 references/iam-policies.md。详情：%s"
                % (code or "鉴权失败", detail)
            )
        if any(p in (code + " " + message).lower()
               for p in _CREDENTIAL_MISSING_PATTERNS):
            return ConfigError(
                "AK/SK 凭证无效或未配置（%s）：请先运行 hcloud configure 或设置"
                "凭证环境变量（严禁在对话中粘贴 AK/SK），参见"
                " references/cli-installation-guide.md。详情：%s"
                % (code or "凭证错误", detail)
            )
        if any(p in (code + " " + message).lower()
               for p in _REGION_UNSUPPORTED_PATTERNS):
            return UsageError(
                "BSS 仅支持 --region %s（当前值被 CLI 拒绝）：%s"
                % ("/".join(BSS_SUPPORTED_REGIONS), detail)
            )
        return ApiError(
            "BSS 接口返回错误（%s）：%s"
            % (code or "未知错误码", detail)
        )
    if any(p in low for p in _REGION_UNSUPPORTED_PATTERNS):
        return UsageError(
            "BSS 仅支持 --region %s，请改用受支持的 SDK 区域（BSS 为全局服务）："
            "%s" % ("/".join(BSS_SUPPORTED_REGIONS), blob[:300])
        )
    if _USE_ERROR_MARKER in low:
        return ApiError(
            "hcloud 参数/环境错误（KooCLI 拒绝了该调用）：BSS %s 真实参数清单"
            "可通过 `hcloud BSS %s --help` 查看。详情：%s"
            % (ALLOWED_OPERATION, ALLOWED_OPERATION, blob[:300])
        )
    if any(p in low for p in _CREDENTIAL_MISSING_PATTERNS) and not re.search(
            r"\b40[13]\b", blob):
        return ConfigError(
            "缺少 AK/SK 凭证：hcloud 未配置有效凭证。请先运行 hcloud configure 或"
            "设置凭证环境变量（严禁在对话中粘贴 AK/SK），参见"
            " references/cli-installation-guide.md。详情：%s" % blob[:300]
        )
    if any(p in low for p in _AUTH_PATTERNS):
        return AuthError(
            "无权限访问 BSS 代金券，请检查 IAM 权限（403：AK/SK 无效或未授予 BSS "
            "只读权限），参见 references/iam-policies.md。详情：%s" % blob[:300]
        )
    return ApiError(
        "hcloud 调用失败（退出码 %s）：%s" % (returncode, blob[:300])
    )


def hcloud_service_unsupported(stdout, stderr):
    """True when KooCLI rejects the call because its catalog lacks BSS.

    Older / trimmed KooCLI builds answer `hcloud BSS ...` with
    `[USE_ERROR]Unsupported service: BSS` even though the binary itself is
    present. This is a CLI-coverage gap, not a credential or BSS API failure,
    so the caller should fall back to the official SDK.
    """
    low = (stdout + " " + stderr).lower()
    return any(pattern in low for pattern in _UNSUPPORTED_SERVICE_PATTERNS)


def extract_items(payload, keys):
    """Pull a list out of an hcloud response under one of `keys`."""
    if isinstance(payload, list):
        return payload
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def extract_coupons(payload):
    return extract_items(payload, _COUPON_LIST_KEYS)


def _total_count(payload, keys):
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if isinstance(payload.get(key), int):
            return payload[key]
    return None


def _has_more(batch, collected, limit, payload, total_keys):
    if not batch:
        return False
    total = _total_count(payload, total_keys)
    if total is not None and total >= 0:
        return collected < total
    return len(batch) >= limit


def build_command(region, coupon_id=None, status=None, coupon_type=None,
                  limit=DEFAULT_PAGE_SIZE, offset=0,
                  operation=ALLOWED_OPERATION):
    """Build the hcloud BSS coupon-list argv (without the executable)."""
    argv = [
        SERVICE,
        operation,
        "--cli-region=%s" % region,
        "--offset=%d" % offset,
        "--limit=%d" % limit,
    ]
    if coupon_id:
        argv.append("--coupon_id=%s" % coupon_id)
    if status is not None:
        argv.append("--status=%d" % status)
    if coupon_type is not None:
        argv.append("--coupon_type=%d" % coupon_type)
    return argv


def build_order_command(region, order_id, limit=DEFAULT_PAGE_SIZE, offset=0):
    """Build the hcloud BSS customer-orders argv (read-only)."""
    argv = [
        SERVICE,
        ALLOWED_ORDER_OPERATION,
        "--cli-region=%s" % region,
        "--offset=%d" % offset,
        "--limit=%d" % limit,
    ]
    if order_id:
        argv.append("--order_id=%s" % order_id)
    return argv


def _status_text(value):
    if value is None:
        return "-"
    if isinstance(value, int):
        label = STATUS_LABELS.get(value)
        return "%s(%s)" % (label, value) if label else str(value)
    return str(value)


def filter_by_name(coupons, name):
    """Client-side name filter (case-insensitive substring)."""
    if not name:
        return list(coupons)
    wanted = str(name).strip().lower()
    matched = []
    for coupon in coupons:
        if not isinstance(coupon, dict):
            continue
        haystack = " ".join(
            str(coupon.get(field) or "")
            for field in ("plan_name", "coupon_code", "coupon_id")
        ).lower()
        if wanted in haystack:
            matched.append(coupon)
    return matched


def filter_by_status(coupons, status):
    """Client-side status filter for non-numeric / unrecognised values."""
    if status is None:
        return list(coupons)
    if isinstance(status, int):
        wanted = status
    else:
        parsed = parse_status(status)
        wanted = parsed if parsed is not None else str(status).strip().lower()
    matched = []
    for coupon in coupons:
        if not isinstance(coupon, dict):
            continue
        value = coupon.get("status")
        if isinstance(wanted, int):
            if value == wanted:
                matched.append(coupon)
        elif _status_text(value).lower() == wanted or str(value).strip().lower() == wanted:
            matched.append(coupon)
    return matched


def _coupon_order_refs(coupon):
    """Return the order ids referenced by a coupon record."""
    refs = []
    for field in ("order_id", "lock_order_id"):
        value = coupon.get(field)
        if value:
            refs.append(str(value))
    return refs


def fetch_order_projects(region, order_ids, max_orders=50):
    """Resolve enterprise projects for a set of order ids (read-only).

    Queries `hcloud BSS ListCustomerOrders` per order id and returns a dict
    mapping order_id -> list of {"id": project_id, "name": project_name}.
    The coupon-list API carries no project_id, so projects are attributed
    through the order => enterprise_projects linkage. Best-effort: lookup
    failures degrade to an empty map (project_id stays "-").
    """
    result = {}
    seen = set()
    for order_id in order_ids:
        if not order_id or order_id in seen or len(result) >= max_orders:
            continue
        seen.add(order_id)
        try:
            stdout, stderr, returncode = run_hcloud(
                build_order_command(region, order_id)
            )
        except VoucherQueryError:
            continue
        if returncode != 0 or _USE_ERROR_MARKER in (stdout + " " + stderr).lower():
            continue
        try:
            payload = extract_json(stdout)
        except VoucherQueryError:
            continue
        # Best-effort order lookup: an error envelope (e.g. no
        # billing:order:view) leaves the project as "-" instead of failing
        # the whole coupon query.
        if extract_error_envelope(payload):
            continue
        orders = extract_items(payload, ("order_infos", "orders", "records"))
        projects = []
        for order in orders:
            if not isinstance(order, dict):
                continue
            # Only attribute projects for the order actually queried, so an
            # extra order in the page cannot mis-attribute a coupon.
            if order.get("order_id") and str(order["order_id"]) != order_id:
                continue
            for ep in order.get("enterprise_projects") or []:
                if isinstance(ep, dict) and ep.get("id"):
                    projects.append({
                        "id": str(ep["id"]),
                        "name": ep.get("name") or "",
                    })
        if projects:
            result[order_id] = projects
    return result


def attribute_project_id(coupon, order_projects):
    """Set project_id / project_name on a coupon from order linkage.

    The coupon list API returns no enterprise-project field. When the coupon
    references an order, the order's enterprise_projects (resolved by
    `fetch_order_projects`) provide the attribution. Only one project is
    exposed as `project_id` (the first); the full set is kept in
    `project_ids` for filtering.
    """
    flat = dict(coupon)
    projects = []
    for ref in _coupon_order_refs(coupon):
        for ep in order_projects.get(ref) or []:
            if {"id": ep["id"], "name": ep["name"]} not in projects:
                projects.append({"id": ep["id"], "name": ep["name"]})
    flat["project_ids"] = [p["id"] for p in projects]
    if projects:
        flat["project_id"] = projects[0]["id"]
        flat["project_name"] = projects[0]["name"]
    else:
        flat["project_id"] = "-"
        flat["project_name"] = "-"
    return flat


def filter_by_project(coupons, project_id):
    """Client-side enterprise-project filter (applied to `project_ids`)."""
    if not project_id:
        return list(coupons)
    wanted = str(project_id).strip()
    matched = []
    for coupon in coupons:
        if not isinstance(coupon, dict):
            continue
        ids = coupon.get("project_ids")
        if ids and wanted in [str(i) for i in ids]:
            matched.append(coupon)
    return matched


def _parse_utc(value):
    if not value:
        return None
    text = str(value).strip().replace(" ", "T").replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def _now_utc():
    return datetime.now(timezone.utc)


def filter_expiry(coupons, expiring_days=None, expired=False):
    """Filter coupons by expire_time (near-expiry / already expired)."""
    now = _now_utc()
    if not expired and not expiring_days:
        return list(coupons)
    horizon = now + timedelta(days=int(expiring_days)) if expiring_days else None
    matched = []
    for coupon in coupons:
        expire = _parse_utc(coupon.get("expire_time"))
        if expire is None:
            continue
        if expired and expire < now:
            matched.append(coupon)
        elif not expired and horizon is not None and now <= expire <= horizon:
            matched.append(coupon)
    return matched


def _coupon_balance(coupon):
    val = coupon.get("balance")
    if val is None:
        val = coupon.get("remaining_value", coupon.get("face_value", 0))
    try:
        value = float(val or 0)
    except (TypeError, ValueError):
        return 0.0
    # Negative made-up values would corrupt the usage stats.
    return value if value >= 0 else 0.0


def _coupon_face(coupon):
    val = coupon.get("face_value", 0)
    try:
        value = float(val or 0)
    except (TypeError, ValueError):
        return 0.0
    return value if value >= 0 else 0.0


def usage_analysis(coupons):
    """Aggregate face_value vs balance per enterprise project.

    Returns a list of dicts (project_id, project_name, count, total_face,
    total_balance, total_used, usage_rate). Projects are taken from each
    coupon's attributed `project_ids`; unattributed coupons are aggregated
    under project_id "-".
    """
    buckets = {}
    for coupon in coupons:
        if not isinstance(coupon, dict):
            continue
        ids = coupon.get("project_ids") or ["-"]
        face = _coupon_face(coupon)
        balance = _coupon_balance(coupon)
        used = face - balance if face else 0.0
        name = coupon.get("project_name") or "-"
        for project_id in ids:
            key = str(project_id)
            bucket = buckets.setdefault(key, {
                "project_id": key,
                "project_name": name if key != "-" else "-",
                "count": 0,
                "total_face": 0.0,
                "total_balance": 0.0,
                "total_used": 0.0,
            })
            bucket["count"] += 1
            bucket["total_face"] += face
            bucket["total_balance"] += balance
            bucket["total_used"] += used
    rows = []
    for key in sorted(buckets):
        bucket = buckets[key]
        face = bucket["total_face"]
        bucket["usage_rate"] = (bucket["total_used"] / face
                                if face else 0.0)
        rows.append(bucket)
    return rows


def _model_to_dict(model):
    if hasattr(model, "to_json_object"):
        try:
            return model.to_json_object()
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(model, "to_dict"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return model.to_dict()
    if isinstance(model, dict):
        return dict(model)
    return {"value": str(model)}


def list_coupons_via_sdk(region, coupon_id=None, status=None, coupon_type=None,
                         limit=DEFAULT_PAGE_SIZE, max_pages=MAX_PAGES):
    """SDK fallback: query coupons through `huaweicloudsdkbss` v2."""
    try:
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkcore.http.http_config import HttpConfig
        from huaweicloudsdkbss.v2 import BssClient, ListSubCustomerCouponsRequest
    except ImportError as exc:
        raise ConfigError(
            "未找到 hcloud（KooCLI），且 huaweicloudsdkcore/huaweicloudsdkbss 未安装，"
            "无法回退到 SDK。请安装 KooCLI 或 pip install huaweicloudsdkcore "
            "huaweicloudsdkbss。详情：%s" % exc
        )

    # Explicit whitelist only — never enumerate os.environ. Scanning the whole
    # environment for HUAWEI/HW_/HWC prefixes harvests unrelated secrets and is
    # blocked by the security scanner (E2 Env Variable Harvesting).
    _AK_ENV_NAMES = ("HUAWEICLOUD_SDK_AK", "HUAWEI_ACCESS_KEY")
    _SK_ENV_NAMES = ("HUAWEICLOUD_SDK_SK", "HUAWEI_SECRET_KEY")

    def _env_pair():
        for ak_name, sk_name in zip(_AK_ENV_NAMES, _SK_ENV_NAMES):
            ak = (os.environ.get(ak_name) or "").strip()
            sk = (os.environ.get(sk_name) or "").strip()
            if ak and sk:
                return ak, sk
        return None, None

    ck1, ck2 = _env_pair()
    if not ck1 or not ck2:
        raise ConfigError(
            "SDK 回退缺少 AK/SK 凭证：官方 SDK 的 GlobalCredentials 不会自动读取环境"
            "变量，且当前环境未检测到受支持的环境变量（HUAWEICLOUD_SDK_AK / "
            "HUAWEICLOUD_SDK_SK，或 HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY）。"
            "请在会话外设置 HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK（严禁在对话中粘贴"
            " AK/SK），参见 references/cli-installation-guide.md。"
        )
    credentials = GlobalCredentials(ak=ck1, sk=ck2)
    try:
        client = BssClient.new_builder() \
            .with_credentials(credentials) \
            .with_http_config(HttpConfig.get_default_config()) \
            .with_endpoints([BSS_ENDPOINT]) \
            .build()
    except Exception as exc:
        raise ConfigError(
            "SDK 初始化失败（endpoint=%s）：%s。请检查 huaweicloudsdkbss 安装。"
            % (BSS_ENDPOINT, exc)
        )
    coupons = []
    offset = 0
    for _ in range(max_pages):
        request = ListSubCustomerCouponsRequest(
            coupon_id=coupon_id,
            status=status,
            coupon_type=coupon_type,
            offset=offset,
            limit=min(limit, MAX_PAGE_SIZE),
        )
        try:
            response = client.list_sub_customer_coupons(request)
        except Exception as exc:
            low = str(exc).lower()
            if any(p in low for p in _AUTH_PATTERNS):
                raise AuthError(
                    "无权限访问 BSS 代金券，请检查 IAM 权限（403）。详情：%s"
                    % str(exc)[:300]
                )
            raise ApiError("SDK 调用失败：%s" % str(exc)[:300])
        batch = list(getattr(response, "user_coupons", None) or [])
        coupons.extend(_model_to_dict(item) for item in batch)
        total = getattr(response, "count", None)
        if total is not None and len(coupons) >= total:
            break
        if len(batch) < limit:
            break
        offset += len(batch)
    return coupons


def list_coupons(region, coupon_id=None, status=None, coupon_type=None, name=None,
                 limit=DEFAULT_PAGE_SIZE, max_pages=MAX_PAGES,
                 operation=ALLOWED_OPERATION, project_id=None):
    """Query all coupons (paged); KooCLI first, SDK fallback.

    After the coupon list is fetched, each record is enriched with enterprise
    project attribution through the order linkage (client side, since the
    coupon API carries no project field), then filtered by `--project-id`
    locally (mirroring the `--name` client-side strategy).
    """
    if str(region or "").strip() not in BSS_SUPPORTED_REGIONS:
        raise UsageError(
            "不支持的 BSS Region：%r。BSS 为全局服务，KooCLI 仅接受 --region %s。"
            % (region, "/".join(BSS_SUPPORTED_REGIONS))
        )
    status_int = parse_status(status)
    # validate_query_args() rejects unknown status values before this point.
    client_status = None if status_int is not None else status
    coupons = []
    offset = 0
    for _page in range(max_pages):
        argv = build_command(region, coupon_id=coupon_id, status=status_int,
                             coupon_type=coupon_type,
                             limit=limit, offset=offset, operation=operation)
        try:
            stdout, stderr, returncode = run_hcloud(argv)
        except ConfigError:
            coupons = list_coupons_via_sdk(
                region, coupon_id=coupon_id, status=status_int,
                coupon_type=coupon_type, limit=limit, max_pages=max_pages,
            )
            break
        if returncode != 0 or _USE_ERROR_MARKER in (stdout + " " + stderr).lower():
            if hcloud_service_unsupported(stdout, stderr):
                coupons = list_coupons_via_sdk(
                    region, coupon_id=coupon_id, status=status_int,
                    coupon_type=coupon_type, limit=limit, max_pages=max_pages,
                )
                break
            raise classify_hcloud_failure(stdout, stderr, returncode)
        payload = extract_json(stdout)
        # hcloud may answer an auth/permission failure with exit code 0 and a
        # top-level error envelope; never render that as an empty voucher list.
        error = extract_error_envelope(payload)
        if error:
            raise classify_hcloud_failure(
                stdout, stderr, returncode, error=error)
        batch = extract_coupons(payload)
        coupons.extend(batch)
        if not _has_more(batch, len(coupons), limit, payload,
                         ("count", "total_count", "totalCount", "total")):
            break
        offset += len(batch) if batch else limit
    if client_status is not None:
        coupons = filter_by_status(coupons, client_status)
    coupons = filter_by_name(coupons, name)

    # Enterprise-project attribution via order linkage (client side). Only
    # performed when project filtering is requested, to keep the common path
    # lightweight.
    coupon = coupons or []
    if project_id:
        order_ids = []
        for c in coupon:
            for ref in _coupon_order_refs(c):
                order_ids.append(ref)
        order_projects = fetch_order_projects(region, order_ids)
        coupon = [attribute_project_id(c, order_projects) for c in coupon]
        coupon = filter_by_project(coupon, project_id)
    return coupon


def enrich_coupons_with_projects(region, coupons, max_orders=50):
    """Attribute enterprise projects to coupons via order linkage (client side).

    Used by the usage-analysis view so stats can be sliced by enterprise
    project. Coupons carrying no attributable order keep project_id "-".
    """
    order_ids = []
    for c in coupons:
        for ref in _coupon_order_refs(c):
            order_ids.append(ref)
    order_projects = fetch_order_projects(region, order_ids, max_orders=max_orders)
    return [attribute_project_id(c, order_projects) for c in coupons]


def normalize_coupon(coupon):
    """Add human-readable status / type labels and flatten use_limits."""
    flat = dict(coupon)
    flat["statusText"] = _status_text(coupon.get("status"))
    coupon_type = coupon.get("coupon_type")
    if isinstance(coupon_type, int):
        label = COUPON_TYPE_LABELS.get(coupon_type)
        flat["couponTypeText"] = ("%s(%s)" % (label, coupon_type)) if label else str(coupon_type)
    else:
        flat["couponTypeText"] = "-"
    limits = coupon.get("use_limits")
    if isinstance(limits, list):
        flat["useLimits"] = json.dumps(limits, ensure_ascii=False, separators=(",", ":"))
    return flat


def _field(coupon, *names, default="-"):
    for name in names:
        if name in coupon and coupon[name] not in (None, ""):
            return coupon[name]
    return default


def coupon_names(coupons):
    names = []
    for coupon in coupons:
        name = _field(coupon, "plan_name", "coupon_code", default=None)
        if name is None:
            name = _field(coupon, "coupon_id", default="")
        names.append(str(name))
    return names


def _cell(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def render_table(coupons):
    """Render full-field table output (union of all returned fields)."""
    rows_data = [normalize_coupon(coupon) for coupon in coupons]
    columns = []
    for key in PREFERRED_COLUMNS:
        if any(key in c for c in rows_data):
            columns.append(key)
    for key in sorted({k for c in rows_data for k in c}):
        if key not in columns:
            columns.append(key)
    if not columns:
        columns = ["coupon_id", "coupon_code"]
    rows = [[_cell(_field(c, col)) for col in columns] for c in rows_data]
    widths = [max(len(col), *(len(row[i]) for row in rows)) for i, col in enumerate(columns)]
    header = "  ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    separator = "  ".join("-" * w for w in widths)
    lines = [header, separator]
    for row in rows:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(columns))))
    return "\n".join(lines)


def render_usage_table(rows):
    """Render per-project usage analysis as a table."""
    columns = ["project_id", "project_name", "count",
               "total_face", "total_balance", "total_used", "usage_rate"]
    data = []
    for row in rows:
        data.append({
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "count": row["count"],
            "total_face": "%.2f" % row["total_face"],
            "total_balance": "%.2f" % row["total_balance"],
            "total_used": "%.2f" % row["total_used"],
            "usage_rate": "%.1f%%" % (row["usage_rate"] * 100),
        })
    widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            widths[col] = max(widths[col], len(str(row[col])))
    lines = ["  ".join(col.ljust(widths[col]) for col in columns)]
    lines.append("  ".join("-" * widths[col] for col in columns))
    for row in data:
        lines.append("  ".join(str(row[col]).ljust(widths[col]) for col in columns))
    return "\n".join(lines)


def describe_filters(args):
    """One human-readable filter description (used by the screen and reports)."""
    filters = []
    for label, value in (
        ("status", args.status), ("name", args.name),
        ("coupon_id", args.coupon_id), ("project_id", args.project_id),
    ):
        if value is not None and str(value) != "":
            filters.append("%s=%s" % (label, value))
    if args.expiring:
        filters.append("expiring<=%sd" % args.expiring)
    if args.expired:
        filters.append("expired")
    return ", ".join(filters)


def _available_status_values():
    aliases = sorted({k for k in STATUS_ALIASES if not str(k).isdigit()})
    codes = "/".join(str(code) for code in sorted(STATUS_LABELS))
    return "%s（数字状态码 %s）" % ("/".join(aliases), codes)


def validate_query_args(args):
    """Reject unsupported region / status / day / page-size values early."""
    region = str(getattr(args, "region", DEFAULT_REGION) or "").strip()
    if region not in BSS_SUPPORTED_REGIONS:
        raise UsageError(
            "不支持的 BSS Region：%r。BSS 为全局服务，KooCLI 仅接受 --region %s。"
            % (region, "/".join(BSS_SUPPORTED_REGIONS))
        )
    status = getattr(args, "status", None)
    if status is not None and str(status).strip() != "" and parse_status(status) is None:
        raise UsageError(
            "未知的代金券状态：%r。可用值：%s。"
            % (status, _available_status_values())
        )
    expiring = getattr(args, "expiring", None)
    if expiring is not None and expiring < 1:
        raise UsageError(
            "--expiring 需要正整数天数（例如 --expiring 30），收到 %r。" % expiring
        )
    page_size = getattr(args, "page_size", None)
    if page_size is not None and not (1 <= page_size <= MAX_PAGE_SIZE):
        raise UsageError(
            "--page-size 必须在 1..%d 之间（BSS 上限），收到 %r。"
            % (MAX_PAGE_SIZE, page_size)
        )


def _report_view(args):
    if args.usage_analysis:
        return "使用率分析"
    if args.expired:
        return "已过期"
    if args.expiring:
        return "%d 天内到期" % args.expiring
    return "全部代金券"


def collect_report_data(args, formats=None):
    """Run the query / filters / aggregation exactly once.

    Returns a single dict ``{coupons, usage_rows, expiring_rows, meta,
    formats}`` that both the screen output and the report export consume, so a
    report can never drift from what the console shows (no second query).

    - ``coupons`` — the rows the screen renders (same filters, same order).
    - ``usage_rows`` — per-enterprise-project aggregation (``None`` when neither
      ``--usage-analysis`` nor ``--export`` asked for it).
    - ``expiring_rows`` — near-expiry / expired detail for the report sheet.
    """
    formats = parse_formats(getattr(args, "export", None)) if formats is None else formats
    validate_query_args(args)
    operation = guard_operation(args.operation)
    limit = min(max(args.page_size, 1), MAX_PAGE_SIZE)
    coupons = list_coupons(
        args.region,
        coupon_id=args.coupon_id,
        status=args.status,
        coupon_type=args.coupon_type,
        name=args.name,
        limit=limit,
        operation=operation,
        project_id=args.project_id,
    )

    need_usage = bool(args.usage_analysis or formats)
    attributed = coupons
    if need_usage and any("project_ids" not in c for c in coupons):
        attributed = enrich_coupons_with_projects(args.region, coupons)
    usage_rows = usage_analysis(attributed) if need_usage else None

    # The screen keeps its original columns (no project attribution unless it
    # was asked for); the report gets the attributed copy. Both come from the
    # same query and the same filter order, so counts and amounts match.
    if args.usage_analysis:
        visible = list(attributed)
        report_coupons = list(attributed)
    else:
        visible = filter_expiry(coupons, args.expiring, args.expired)
        report_coupons = filter_expiry(attributed, args.expiring, args.expired)

    expiring_rows = []
    expiring_label = ""
    expired_count = 0
    if formats:
        if args.expiring or args.expired:
            expiring_rows = filter_expiry(attributed, args.expiring, args.expired)
            expiring_label = ("已过期" if args.expired
                             else "%d 天内到期" % args.expiring)
        else:
            expiring_rows = filter_expiry(attributed, DEFAULT_EXPIRING_DAYS, False)
            expiring_label = "%d 天内到期" % DEFAULT_EXPIRING_DAYS
        expired_count = len(filter_expiry(attributed, None, True))

    total_face = sum(_coupon_face(c) for c in visible)
    total_balance = sum(_coupon_balance(c) for c in visible)
    # Status / type labels + flattened use_limits, exactly like the screen table.
    report_coupons = [normalize_coupon(c) for c in report_coupons]
    expiring_rows = [normalize_coupon(c) for c in expiring_rows]
    meta = {
        "region": args.region,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filters": {
            "status": args.status, "name": args.name,
            "coupon_id": args.coupon_id, "project_id": args.project_id,
            "expiring": args.expiring, "expired": bool(args.expired),
            "coupon_type": args.coupon_type, "page_size": limit,
        },
        "filters_text": describe_filters(args),
        "view": _report_view(args),
        "coupon_count": len(visible),
        "total_face": total_face,
        "total_balance": total_balance,
        "total_used": max(total_face - total_balance, 0.0),
        "expiring_label": expiring_label,
        "expired_count": expired_count,
        "source": "hcloud BSS %s / %s（只读）" % (
            ALLOWED_OPERATION, ALLOWED_ORDER_OPERATION),
    }
    return {
        "coupons": report_coupons,
        "screen_coupons": visible,
        "usage_rows": usage_rows,
        "expiring_rows": expiring_rows,
        "meta": meta,
        "formats": formats,
    }


@quality_report(skill_name="huawei-cloud-bss-voucher-query", skill_version="1.0.0")
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="huawei-cloud-bss-voucher-query",
        description="查询华为云 BSS 代金券列表，支持按企业项目ID/状态/到期/使用率维度筛选"
                    "（KooCLI hcloud BSS %s，只读）。" % ALLOWED_OPERATION)
    parser.add_argument("-r", "--region", default=DEFAULT_REGION,
                        help="目标 Region（BSS 仅支持 cn-north-1 等区域，默认 %s）"
                             % DEFAULT_REGION)
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="以 JSON 输出完整原始字段")
    parser.add_argument("--names-only", action="store_true", dest="names_only",
                        help="仅输出代金券名称（促销计划名称）清单")
    parser.add_argument("--status",
                        help="按代金券状态过滤（1-5 或 available/used/expired 等；"
                             "可识别的值走服务端，否则本地过滤）")
    parser.add_argument("--name", help="按促销计划名称 / 券码过滤（本地子串匹配）")
    parser.add_argument("--coupon-id", dest="coupon_id",
                        help="按代金券 ID 过滤（精确查询，服务端参数）")
    parser.add_argument("--coupon-type", dest="coupon_type", type=int,
                        help="按代金券类型过滤（1=代金券 2=折扣券 3=产品券 4=现金券）")
    parser.add_argument("--project-id", dest="project_id",
                        help="按企业项目 ID 过滤（ListSubCustomerCoupons 无该服务端参数，"
                             "走本脚本订单归属本地过滤，需 billing:order:view 只读权限）")
    parser.add_argument("--expiring", type=int, default=None, metavar="DAYS",
                        help="仅列出 N 天内到期（未过期）的代金券")
    parser.add_argument("--expired", action="store_true",
                        help="仅列出已过期的代金券")
    parser.add_argument("--usage-analysis", action="store_true", dest="usage_analysis",
                        help="按企业项目汇总面额/余额/使用率统计")
    parser.add_argument("--export", metavar="{xlsx,html}",
                        help="导出可视化报表：xlsx（四表工作簿）/ html（自包含图表），"
                             "可组合如 --export xlsx,html")
    parser.add_argument("--out-dir", dest="out_dir", default=None,
                        help="报表输出目录（默认当前目录；同名文件不覆盖，自动加序号）")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE,
                        dest="page_size",
                        help="分页大小（BSS 上限 %d，默认 %d）"
                             % (MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE))
    parser.add_argument("--operation", default=ALLOWED_OPERATION,
                        help="hcloud BSS 操作名（仅允许只读 %s / ListCoupons）"
                             % ALLOWED_OPERATION)
    args = parser.parse_args(argv)

    try:
        guard_write_intent(" ".join(argv if argv is not None else sys.argv[1:]))
        guard_operation(args.operation)
        for flag_name, flag_value in (
            ("--status", args.status), ("--name", args.name),
            ("--coupon-id", args.coupon_id), ("--project-id", args.project_id),
        ):
            if flag_value is not None and str(flag_value) != "":
                guard_write_intent(str(flag_value))
        formats = parse_formats(args.export)
        out_dir = ensure_out_dir(args.out_dir) if formats else None
        data = collect_report_data(args, formats)
    except (VoucherQueryError, ExportError) as exc:
        print("[错误] %s" % exc, file=sys.stderr)
        return 1

    coupons = data["screen_coupons"]
    rows = data["usage_rows"]

    if args.usage_analysis:
        print("Region %s 的 BSS 代金券使用率分析（按企业项目汇总）：" % args.region)
        if rows:
            print(render_usage_table(rows))
        else:
            print("（无数据）")
    elif args.as_json:
        print(json.dumps(coupons, ensure_ascii=False, indent=2))
    elif args.names_only:
        print("Region %s 的 BSS 代金券名称列表（共 %d 张）："
              % (args.region, len(coupons)))
        for name in coupon_names(coupons):
            print("- %s" % name)
    elif not coupons:
        filters = describe_filters(args)
        suffix = "（过滤条件: %s）" % filters if filters else ""
        print("当前区域（%s）无 BSS 代金券%s。" % (args.region, suffix))
    else:
        print("Region %s 的 BSS 代金券列表（共 %d 张，完整字段）："
              % (args.region, len(coupons)))
        print(render_table(coupons))

    if formats:
        try:
            results = export_report(data, formats, out_dir)
        except ExportError as exc:
            print("[错误] %s" % exc, file=sys.stderr)
            return 1
        for item in results:
            print("已导出%s：%s（代金券 %d 条 / 临期 %d 条 / 企业项目 %d 个）"
                  % (item["label"], item["path"], item["records"],
                     len(data["expiring_rows"] or []), len(rows or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())