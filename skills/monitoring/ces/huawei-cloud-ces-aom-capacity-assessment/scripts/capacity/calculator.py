"""Capacity computation module: 峰谷值倍数 (peak/valley multiple), 压力系数 (pressure coefficient),
预计节日上限 (expected festival ceiling), 扩容建议 (scale-out recommendation).

Boundary: only numeric computation, no data collection, no Excel writes. All formulas follow skill_overview §7.

Error wording (§7.3):
  Historical mode: 峰谷值倍数/压力系数/预计节日上限 -> "无法计算"; 扩容建议 -> "现有数据不支持给出建议"
  T-24 mode: same -> "无法预测"; 扩容建议 -> "现有数据不支持给出建议" when 资源上限 is empty, otherwise "无法预测"
  Special: incompatible multi-entry units -> 压力系数 = "多入口实例，但单位不兼容"
"""
from __future__ import annotations

from typing import Any, Optional

SCALE_THRESHOLD = 0.8

HIST = "historical"
T24 = "t24"

# Error codes
ERR_NO_ENTRANCE = "no_entrance"          # entrance instance ID missing
ERR_NO_COMMON_DATE = "no_common_date"    # entrance and target have no common date / entrance data missing
ERR_ZERO_VALLEY = "zero_valley"          # valley is 0 (divide by zero)
ERR_NO_CEILING = "no_ceiling"            # 资源上限 empty
ERR_UNIT_INCOMPAT = "unit_incompatible"  # multi-entry instance units incompatible


def _f(v: float, nd: int = 2) -> float:
    return round(float(v), nd)


def _error_words(mode: str) -> str:
    return "无法计算" if mode == HIST else "无法预测"


class AssessResult:
    def __init__(self, mode: str):
        self.mode = mode
        self.ratio: Optional[float] = None
        self.pressure: Any = None
        self.forecast: Optional[float] = None
        self.advice: Optional[str] = None
        self.errors: list[str] = []

    def as_dict(self) -> dict[str, Any]:
        ew = _error_words(self.mode)
        return {
            "errors": self.errors,
            "峰谷值倍数": self.ratio if self.ratio is not None else ew,
            "压力系数": self.pressure if self.pressure is not None else ew,
            "预计节日上限": self.forecast if self.forecast is not None else ew,
            "扩容建议": self.advice if self.advice is not None else "现有数据不支持给出建议",
        }


def peak_valley_ratio(peak: float, valley: float) -> Optional[float]:
    if valley == 0:
        return None
    return peak / valley


def _resolve_advice(
    mode: str,
    computed: bool,
    ceiling: Optional[float],
    forecast: Optional[float] = None,
    threshold: float = SCALE_THRESHOLD,
) -> str:
    """Final wording of the scale-out recommendation."""
    if computed:
        if ceiling is None or ceiling == "":
            return "现有数据不支持给出建议"
        try:
            c = float(ceiling)
        except (TypeError, ValueError):
            return "现有数据不支持给出建议"
        if c <= 0:
            return "现有数据不支持给出建议"
        return "是" if (forecast or 0) > c * threshold else "否"
    # computation failed
    if mode == T24 and ceiling is not None:
        try:
            c = float(ceiling)
            if c > 0:
                return "无法预测"
        except (TypeError, ValueError):
            pass
    return "现有数据不支持给出建议"


def assess(
    mode: str,
    target: dict[str, Any],
    entrances: list[dict[str, Any]],
    ceiling: Optional[float],
    growth: float = 1.0,
    threshold: float = SCALE_THRESHOLD,
) -> AssessResult:
    """Core capacity assessment.

    target: {"peak": float, "valley": float, "unit": str}
    entrances: [{"peak": float, "valley": float, "unit": str}, ...]
    ceiling: 资源上限 (may be None)
    growth: activity growth multiple (default 1.0)
    """
    r = AssessResult(mode)
    ew = _error_words(mode)

    if not entrances:
        r.errors.append(ERR_NO_ENTRANCE)
        r.advice = _resolve_advice(mode, False, ceiling)
        return r

    # multi-entry unit compatibility
    if len(entrances) > 1:
        from .config import units_compatible
        units = [e.get("unit") or "" for e in entrances]
        if not units_compatible(units):
            r.errors.append(ERR_UNIT_INCOMPAT)
            r.pressure = "多入口实例，但单位不兼容"  # special wording
            r.ratio = ew
            r.forecast = ew
            r.advice = _resolve_advice(mode, False, ceiling)
            return r

    tp, tv = target.get("peak"), target.get("valley")
    if tp is None or tv is None or tp == 0 or tv == 0:
        r.errors.append(ERR_ZERO_VALLEY)
        r.advice = _resolve_advice(mode, False, ceiling)
        return r

    t_ratio = peak_valley_ratio(tp, tv)
    if t_ratio is None:
        r.errors.append(ERR_ZERO_VALLEY)
        r.advice = _resolve_advice(mode, False, ceiling)
        return r

    # Entrance instances: the collection layer already guarantees the entrance and target share common dates.
    # With multiple compatible entries, compute each 峰谷值倍数 and take the arithmetic mean as the entrance
    # 峰谷值倍数 (not just the first one).
    e_ratios: list[float] = []
    for e in entrances:
        ep, ev = e.get("peak"), e.get("valley")
        if ep is None or ev is None:
            r.errors.append(ERR_NO_COMMON_DATE)
            r.advice = _resolve_advice(mode, False, ceiling)
            return r
        if ep == 0 or ev == 0:
            r.errors.append(ERR_ZERO_VALLEY)
            r.advice = _resolve_advice(mode, False, ceiling)
            return r
        er_i = peak_valley_ratio(ep, ev)
        if er_i is None:
            r.errors.append(ERR_ZERO_VALLEY)
            r.advice = _resolve_advice(mode, False, ceiling)
            return r
        e_ratios.append(er_i)
    e_ratio = sum(e_ratios) / len(e_ratios)

    pressure = t_ratio / e_ratio
    forecast = pressure * tp * (growth - 1.0) + tp

    r.ratio = _f(t_ratio)
    r.pressure = _f(pressure)
    r.forecast = _f(forecast)

    if ceiling is None or ceiling == "":
        r.errors.append(ERR_NO_CEILING)
        r.advice = _resolve_advice(mode, True, ceiling, forecast)
        return r
    try:
        c = float(ceiling)
    except (TypeError, ValueError):
        r.errors.append(ERR_NO_CEILING)
        r.advice = _resolve_advice(mode, True, ceiling, forecast)
        return r
    if c <= 0:
        r.errors.append(ERR_NO_CEILING)
        r.advice = _resolve_advice(mode, True, ceiling, forecast)
        return r
    r.advice = "是" if forecast > c * threshold else "否"
    return r