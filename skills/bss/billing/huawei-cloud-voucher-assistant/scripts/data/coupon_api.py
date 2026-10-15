"""Coupon (代金券) data-source adapter。

单数据源，工厂 get_adapter() 自动选择：
- BSS 开放 API（BssCouponAdapter，AK/SK 签名）：已有代金券账户余额/明细。
有 AK/SK 时返回 BSS 适配器，否则返回 None。
代金券抵扣需 BSS 订单系统（待接入）。分析层 (analyzer.py) 与此解耦。
"""


from abc import ABC, abstractmethod
import os
import re

from data.bss_client import BssClient, BssError


# BSS 查询优惠券列表接口参数语义（官方 SDK ListSubCustomerCouponsRequest）
# coupon_type: 1=代金券 2=折扣券 3=产品券 4=现金券（合法值从 1 起，0 触发 CBC.0100）
# status: 1=未激活 2=待使用 3=已使用 4=已过期 5=已回收
_COUPON_TYPE_VOUCHER = 1
# status=2 为「待使用」（即可用）状态，get_balance 只统计可用代金券
_STATUS_AVAILABLE = 2
_PAGE_SIZE = 100
_STATUS_LABELS = {
    1: "inactive",
    2: "available",
    3: "used",
    4: "expired",
    5: "recycled",
}


def _status_label(stat):
    """BSS 状态码 → 可读状态。未识别值返回 unknown。"""
    return _STATUS_LABELS.get(stat, "unknown")


def _fetch_all_coupons(client, coupon_type=None, status=None, page_size=_PAGE_SIZE,
                       max_pages=100):
    """按 offset/limit 分页拉取全部优惠券，返回 (count, user_coupons 列表)。

    真实 BSS 响应结构为 {"count": N, "user_coupons": [...]}，
    兼容旧响应键 coupons/records 与 total_count。
    count 缺失/为 0 时以「单页不足 page_size」作为结束信号，并设最大页数防呆。
    """
    all_items = []
    offset = 0
    total = 0
    for _ in range(max_pages):
        data = client.list_coupons(
            coupon_type=coupon_type, status=status, offset=offset, limit=page_size,
        )
        try:
            total = int(data.get("count", data.get("total_count", 0)) or 0)
        except (TypeError, ValueError):
            total = 0
        items = data.get("user_coupons", data.get("coupons", data.get("records", []))) or []
        all_items.extend(items)
        if not items or len(items) < page_size:
            break
        if total and len(all_items) >= total:
            break
        offset += len(items)
    return total, all_items


def _coupon_balance(item):
    """单张代金券余额（元）。

    老版本券（coupon_version=1）balance 为空，余额即未用面值，回退 face_value。
    """
    val = item.get("balance")
    if val is None:
        val = item.get("remaining_value", item.get("face_value", 0))
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


# 本地知识库路径（skill 根目录 references/voucher-taxonomy.md）
_KB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "references", "voucher-taxonomy.md",
)


def load_applicable_services(kb_path=None):
    """从本地知识库 references/voucher-taxonomy.md 解析代金券适用云服务列表。

    优先解析「## 适用服务」章节下的 Markdown 表格（服务/服务名称/抵扣规则）；
    表格缺失时回退到章节内的服务代码枚举文本（如 ECS / OBS / RDS）。

    Args:
        kb_path: 知识库文件路径，缺省用 skill 自带 references/voucher-taxonomy.md。

    Returns:
        list，每项 {"service", "service_name", "deduction_rule"}。
    """
    path = kb_path or _KB_PATH
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, IOError):
        return []

    lines = text.splitlines()
    services = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##"):
            in_section = "适用服务" in stripped
            continue
        if not in_section:
            continue
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 3:
                continue
            # 跳过表头/分隔行
            if cells[0].startswith("-") or "服务" in cells[0]:
                continue
            code = cells[0]
            if not re.match(r"^[A-Za-z][A-Za-z0-9]*$", code):
                continue
            services.append({
                "service": code.lower(),
                "service_name": cells[1],
                "deduction_rule": cells[2],
            })
        elif stripped.startswith("-") and not services:
            # 回退: 从枚举文本提取服务代号 (如 "ECS / OBS / RDS")
            for code in re.findall(r"\b[A-Za-z][A-Za-z0-9]+\b", stripped):
                if code.upper() in {"ECS", "OBS", "RDS", "CCE", "GaussDB"}:
                    services.append({
                        "service": code.lower(),
                        "service_name": code,
                        "deduction_rule": "满减券/折扣券一般适用；教育/活动券通常可用",
                    })
    return services


class CouponAdapter(ABC):
    """代金券账户数据源统一接口。"""

    @abstractmethod
    def get_balance(self):
        """返回可用代金券余额 (float)。"""

    @abstractmethod
    def list_vouchers(self):
        """返回代金券明细列表，每项:
        {"id", "face_value", "balance", "status", "effective", "expired"}。
        """

    @abstractmethod
    def list_applicable_services(self):
        """返回代金券适用云服务列表，每项:
        {"service", "service_name", "deduction_rule"}。
        """

    @abstractmethod
    def apply_voucher(self, order_ref, amount):
        """按订单抵扣金额，需二次校验并确认。
        返回 {"applied", "order_ref", "message"}。
        """


class BssCouponAdapter(CouponAdapter):
    """基于华为云 BSS 开放 API 的代金券适配器（AK/SK 签名）。

    可提供：已有代金券账户余额/明细（list_coupons）。
    不可提供：代金券适用服务（回退本地知识库）、抵扣（需 BSS 订单系统）。

    Args:
        client: 已构造的 BssClient；缺省用环境变量 AK/SK 构造。
        ak/sk: 可直接传入 AK/SK（或通过环境变量）。
        **client_kwargs: 透传给 BssClient。
    """

    def __init__(self, client=None, ak=None, sk=None, **client_kwargs):
        self.client = client or BssClient(ak=ak, sk=sk, **client_kwargs)

    def get_balance(self):
        """返回可用代金券总余额 (float)。对应 GET /v2/promotions/benefits/coupons。

        按 BSS 语义只统计「待使用」（status=2，即可用）代金券：
        coupon_type=1 + status=2，分页汇总每张券 balance（老版本券 balance 为空
        时回退面值 face_value）。
        """
        _, coupons = _fetch_all_coupons(
            self.client, coupon_type=_COUPON_TYPE_VOUCHER, status=_STATUS_AVAILABLE,
        )
        total = sum(_coupon_balance(c) for c in coupons)
        return round(total, 2)

    def list_vouchers(self):
        """返回已有代金券明细列表（来自 GET /v2/promotions/benefits/coupons）。

        返回每项: {"id", "face_value", "balance", "status", "effective",
                  "expired", "type", "source"}。status 语义：
                 1=未激活 2=待使用 3=已使用 4=已过期 5=已回收。
        """
        _, coupons = _fetch_all_coupons(self.client, coupon_type=_COUPON_TYPE_VOUCHER)
        vouchers = []
        for c in coupons:
            stat = c.get("status", 0)
            vouchers.append({
                "id": c.get("coupon_id", c.get("id")),
                "face_value": float(c.get("face_value", c.get("denomination", 0)) or 0),
                "balance": _coupon_balance(c),
                "status": _status_label(stat),
                "effective": c.get("valid_time", c.get("effective_time", c.get("active_time", ""))),
                "expired": c.get("expire_time", c.get("expiry_time", "")),
                "type": "代金券",
                "source": "bss-coupons",
            })
        return vouchers

    def list_applicable_services(self):
        """代金券适用云服务列表 → 读取本地知识库 references/voucher-taxonomy.md。

        BSS 不直接提供该字段，按 SKILL.md 文档由本地知识库提供。
        """
        return load_applicable_services()

    def apply_voucher(self, order_ref, amount):
        """按订单抵扣 → 需 BSS 订单系统，本适配器不提供。"""
        raise NotImplementedError(
            "代金券抵扣需 BSS 订单系统（订单创建时指定 coupon_id 自动抵扣）"
        )


def get_adapter(config=None, **client_kwargs):
    """工厂：返回 BSS 代金券适配器（AK/SK 签名）。

    有 AK/SK 时返回 BssCouponAdapter，否则返回 None。

    Args:
        config: 可选配置字典（ak/sk 等）。
        **client_kwargs: 透传给 BssClient。
    """
    ak = (
        (config and config.get("ak"))
        or os.environ.get("HW_ACCESS_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_AK", "")
    )
    sk = (
        (config and config.get("sk"))
        or os.environ.get("HW_SECRET_KEY")
        or os.environ.get("HUAWEICLOUD_SDK_SK", "")
    )
    if ak and sk:
        try:
            return BssCouponAdapter(ak=ak, sk=sk, **client_kwargs)
        except BssError:
            pass
    return None


def get_bss_adapter(ak=None, sk=None):
    """工厂：返回 BSS 适配器（AK/SK）。"""
    return BssCouponAdapter(ak=ak, sk=sk)