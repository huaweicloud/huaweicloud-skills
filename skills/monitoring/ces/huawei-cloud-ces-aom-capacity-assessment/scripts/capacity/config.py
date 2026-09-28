"""Config module: global configuration, region mapping, unit compatibility handling.

Boundary: only provides config lookup and data matching; no business logic, no collection, no Excel writes.
"""
from __future__ import annotations

import re
from datetime import timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Region mapping: Excel Chinese region name -> KooCLI --cli-region code
# ---------------------------------------------------------------------------
# The alias table is ordered by priority: exact match first, then contains-match
REGION_ALIASES: dict[str, str] = {
    # North China
    "华北-北京一": "cn-north-1", "北京一": "cn-north-1", "华北北京一": "cn-north-1",
    "华北-北京四": "cn-north-4", "北京四": "cn-north-4", "华北北京四": "cn-north-4",
    "华北-乌兰察布一": "cn-north-9", "乌兰察布": "cn-north-9",
    # East China
    "华东-上海一": "cn-east-3", "上海一": "cn-east-3", "华东一": "cn-east-3", "华东上海一": "cn-east-3",
    "华东-上海二": "cn-east-2", "上海二": "cn-east-2", "华东二": "cn-east-2", "华东上海二": "cn-east-2",
    "华东-青岛": "cn-east-4", "青岛": "cn-east-4",
    # South China
    "华南-广州": "cn-south-1", "广州": "cn-south-1", "华南广州": "cn-south-1",
    "华南-深圳": "cn-south-4", "深圳": "cn-south-4",
    # Southwest
    "西南-贵阳一": "cn-southwest-2", "贵阳": "cn-southwest-2", "西南贵阳一": "cn-southwest-2",
    # HK/Macau/Taiwan and overseas
    "中国-香港": "ap-southeast-1", "香港": "ap-southeast-1",
    "亚太-新加坡": "ap-southeast-3", "新加坡": "ap-southeast-3",
    "亚太-曼谷": "ap-southeast-2", "曼谷": "ap-southeast-2",
    "亚太-雅加达": "ap-southeast-4", "雅加达": "ap-southeast-4",
    "非洲-约翰内斯堡": "af-south-1", "约翰内斯堡": "af-south-1",
    "拉美-墨西哥城一": "la-north-2", "墨西哥": "la-north-2",
    "拉美-圣保罗一": "sa-brazil-1", "圣保罗": "sa-brazil-1",
}

REGION_CODE_RE = re.compile(r"^(cn|ap|af|la|sa|eu)-[a-z0-9-]+$")


def resolve_region(raw: str) -> str:
    """Resolve the Excel region cell to a KooCLI region code.

    Supports: existing region code (passed through), Chinese full name, Chinese short name, contains-match.
    Raises ValueError when unresolvable; the caller (model) confirms with the user.
    """
    if not raw or not str(raw).strip():
        raise ValueError("region is empty")
    s = str(raw).strip()
    if REGION_CODE_RE.match(s):
        return s
    if s in REGION_ALIASES:
        return REGION_ALIASES[s]
    # contains-match (e.g. "华东-上海一（主）")
    for alias, code in REGION_ALIASES.items():
        if alias in s:
            return code
    raise ValueError(f"unrecognized region: {s!r}; provide a region code (e.g. cn-east-3) or a standard Chinese region name")


def region_timezone(region_code: str):
    """Mainland China regions split day windows by UTC+8; overseas regions use UTC."""
    if region_code.startswith("cn-"):
        return timezone(timedelta(hours=8))
    return timezone.utc


# ---------------------------------------------------------------------------
# Service Chinese-name prefixes (used to strip service prefixes from metric names in Excel,
# e.g. "ECS CPU使用率" -> "CPU使用率")
# ---------------------------------------------------------------------------
SERVICE_PREFIXES: list[tuple[str, str]] = [
    ("CCE", "cce"),
    ("EFS-Turbo", "efsturbo"),
    ("TaurusDB", "taurusdb"),
    ("GeminiDB", "geminidb"),
    ("RocketMQ", "dms"),
    ("RabbitMQ", "dms"),
    ("Kafka", "dms"),
    ("Bandwidth", "bandwidth"),
    ("VPCEP", "vpcep"),
    ("NAT", "nat"),
    ("RDS", "rds"),
    ("ECS", "ecs"),
    ("ELB", "elb"),
    ("EIP", "eip"),
    ("CSS", "css"),
    ("DDS", "dds"),
    ("DWS", "dws"),
    ("DCS", "dcs"),
    ("DMS", "dms"),
    ("DC", "dc"),
    ("ER", "er"),
    ("EVS", "evs"),
    ("APIG", "apig"),
    ("DRS", "drs"),
    ("SFS", "efsturbo"),
]


def strip_service_prefix(metric: str) -> str:
    """Strip the service-name prefix from a Chinese metric name, for prefix-less matching."""
    for prefix, _ in SERVICE_PREFIXES:
        if metric.startswith(prefix):
            rest = metric[len(prefix):].strip()
            # e.g. "NAT网关注入方向带宽" style residual prefixes are further stripped
            for inner, _ in SERVICE_PREFIXES:
                if rest.startswith(inner):
                    rest = rest[len(inner):].strip()
                    break
            return rest
    return metric




# ---------------------------------------------------------------------------
# Unit normalization and conversion
# ---------------------------------------------------------------------------
# canonical family -> factor (scaled to the family base unit)
UNIT_PARSER: list[tuple[re.Pattern, str, float]] = [
    # bit data rates (including plural bits/s)
    (re.compile(r"(?i)gbits?/s|gbps|gbit"), "bits_per_sec", 1e9),
    (re.compile(r"(?i)mbits?/s|mbps|mbit"), "bits_per_sec", 1e6),
    (re.compile(r"(?i)kbits?/s|kbps|kbit"), "bits_per_sec", 1e3),
    (re.compile(r"(?i)bits?/s|bps|bits?"), "bits_per_sec", 1.0),
    # Byte data rates (including plural Bytes/s)
    (re.compile(r"(?i)gbytes?/s|gib/s|gb/s"), "bytes_per_sec", 1e9),
    (re.compile(r"(?i)mbytes?/s|mib/s|mb/s"), "bytes_per_sec", 1e6),
    (re.compile(r"(?i)kbytes?/s|kib/s|kb/s"), "bytes_per_sec", 1e3),
    (re.compile(r"(?i)bytes?/s|b/s"), "bytes_per_sec", 1.0),
    # data amounts (no rate suffix, including plural Bytes)
    (re.compile(r"(?i)gb$|gbytes?$|gib$"), "bytes", 1e9),
    (re.compile(r"(?i)mb$|mbytes?$|mib$"), "bytes", 1e6),
    (re.compile(r"(?i)kb$|kbytes?$|kib$"), "bytes", 1e3),
    (re.compile(r"(?i)bytes?$"), "bytes", 1.0),
    (re.compile(r"^%$|百分比|使用率"), "percent", 1.0),
    # note: count/min must be matched before count (otherwise swallowed as a count substring)
    (re.compile(r"(?i)count/min|counts/min"), "per_min", 1.0),
    # Count/s, Counts etc. intentionally go into the count family (peak/valley ratio is dimensionless;
    # the family is only used for multi-entry compatibility checks)
    (re.compile(r"(?i)count|连接|个|条"), "count", 1.0),
    (re.compile(r"(?i)request/s|req/s|times/s|次/s|次/秒|次每秒"), "per_sec", 1.0),
    (re.compile(r"(?i)packet/s|pps|包/s"), "packet_per_sec", 1.0),
    (re.compile(r"(?i)μs|us$|微秒"), "microsec", 1.0),
    (re.compile(r"(?i)times/min|次/min|次/分钟"), "per_sec", 1 / 60.0),
    (re.compile(r"(?i)ms|毫秒"), "ms", 1.0),
    (re.compile(r"(?i)s$|秒"), "sec", 1.0),
]


def parse_unit(unit: Optional[str]) -> Optional[tuple[str, float]]:
    """Normalize a CES unit string to (canonical_family, factor_to_base)."""
    if unit is None:
        return None
    s = str(unit).strip().rstrip("）)").strip()
    if not s:
        return None
    for pat, fam, fac in UNIT_PARSER:
        if pat.search(s):
            return fam, fac
    return None


def convert_value(value: float, raw_unit: str, display_unit: str) -> tuple[float, bool]:
    """Convert raw_unit -> display_unit (supports bit/s <-> Byte/s, 1 Byte = 8 bit).

    Returns (converted value, success). When conversion is impossible, returns the value unchanged
    with False.
    """
    if raw_unit == display_unit:
        return value, True
    src = parse_unit(raw_unit)
    dst = parse_unit(display_unit)
    if src is None or dst is None:
        return value, False
    src_fam, src_fac = src
    dst_fam, dst_fac = dst
    if src_fam == dst_fam:
        return value * (src_fac / dst_fac), True
    # cross-family: bit <-> byte (data rate, 1 Byte = 8 bit); no conversion between other families
    if {src_fam, dst_fam} == {"bits_per_sec", "bytes_per_sec"}:
        if src_fam == "bits_per_sec":
            return value * (src_fac / dst_fac) / 8.0, True
        return value * (src_fac / dst_fac) * 8.0, True
    return value, False


def units_compatible(units: list[str]) -> bool:
    """Whether multiple entry units can be unified (canonical family matching suffices; numeric values
    align by base unit).

    bit/s and Byte/s are considered the same family (both data rates, 1 Byte = 8 bit), thus compatible.
    """
    fams: set[str] = set()
    for u in units:
        p = parse_unit(u)
        if p is None:
            return False
        fam = p[0]
        fams.add("data_rate" if fam in ("bits_per_sec", "bytes_per_sec") else fam)
    return len(fams) <= 1