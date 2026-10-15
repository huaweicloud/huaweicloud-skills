"""Huawei Cloud voucher assistant — pure-local analysis layer.

This module contains NO network / cloud dependencies. Every function takes
structured input (dicts / lists) and returns structured output, so it can be
unit-tested offline and reused by any data-source adapter.
"""


def analyze_voucher_coverage(voucher_balance, target_price):
    """Return whether voucher balance covers the target price.

    Args:
        voucher_balance: available voucher amount (>= 0).
        target_price: price of the target service/order (>= 0).

    Returns:
        dict with: coverage ("full" | "partial" | "none"),
        voucher_applied, shortfall, cash_required.
    """
    voucher_balance = float(voucher_balance)
    target_price = float(target_price)

    if target_price <= 0:
        return {
            "coverage": "full",
            "voucher_applied": 0.0,
            "shortfall": 0.0,
            "cash_required": 0.0,
        }

    if voucher_balance >= target_price:
        return {
            "coverage": "full",
            "voucher_applied": target_price,
            "shortfall": 0.0,
            "cash_required": 0.0,
        }

    if voucher_balance > 0:
        shortfall = round(target_price - voucher_balance, 2)
        return {
            "coverage": "partial",
            "voucher_applied": voucher_balance,
            "shortfall": shortfall,
            "cash_required": shortfall,
        }

    return {
        "coverage": "none",
        "voucher_applied": 0.0,
        "shortfall": round(target_price, 2),
        "cash_required": round(target_price, 2),
    }


def recommend_discount_plan(voucher_balance, target_price, alternatives=None):
    """Recommend lower-spec alternatives and a voucher+cash combo plan.

    Args:
        voucher_balance: available voucher amount.
        target_price: price of the originally chosen spec.
        alternatives: list of lower-spec options, each:
            {"service": str, "spec": str, "price": float}.

    Returns:
        dict with combo_plan and alternatives (sorted by price asc).
    """
    voucher_balance = float(voucher_balance)
    target_price = float(target_price)
    alternatives = alternatives or []

    coverage = analyze_voucher_coverage(voucher_balance, target_price)

    combo_plan = {
        "coverage": coverage["coverage"],
        "voucher_applied": coverage["voucher_applied"],
        "cash_required": coverage["cash_required"],
        "total_price": round(target_price, 2),
    }

    ranked = []
    for alt in alternatives:
        alt_price = float(alt.get("price", 0))
        alt_cov = analyze_voucher_coverage(voucher_balance, alt_price)
        ranked.append({
            "service": alt.get("service", ""),
            "spec": alt.get("spec", ""),
            "price": alt_price,
            "voucher_applied": alt_cov["voucher_applied"],
            "cash_required": alt_cov["cash_required"],
            "fully_covered": alt_cov["coverage"] == "full",
        })
    ranked.sort(key=lambda x: (not x["fully_covered"], x["cash_required"], x["price"]))

    return {
        "combo_plan": combo_plan,
        "alternatives": ranked,
    }

_CYCLE_WEIGHT = {
    "每日": 30,
    "每周": 4,
    "每月": 1,
    "仅一次": 1,
}


def recommend_tasks(tasks, top_n=5):
    """根据成长中心任务列表推荐值得优先做的任务。

    打分逻辑：score = points × cycle_weight，其中 cycle_weight 按
    周期折算月潜力（每日×30、每周×4、每月×1、仅一次×1）。

    Args:
        tasks: 任务列表，每项含 {"task_id", "task_name", "points",
               "cycle", "category", ...}（来自 list_tasks 查询）。
        top_n: 返回前 N 个推荐，默认 5。

    Returns:
        dict with:
        - "recommendations": 按得分降序排列的任务列表，每项含
          task_id, task_name, points, cycle, category, score,
          monthly_potential, reason。
        - "summary": {"total_tasks", "total_monthly_potential"}。
    """
    scored = []
    for t in tasks:
        points = int(t.get("points", 0) or 0)
        cycle = t.get("cycle", "")
        weight = _CYCLE_WEIGHT.get(cycle, 1)
        score = points * weight
        monthly_potential = score

        if cycle == "每日" and points > 0:
            reason = "日常任务：每日可做，月潜力 %d 积分" % monthly_potential
        elif cycle == "仅一次" and points >= 50:
            reason = "一次性高收益：建议优先完成，%d 积分" % points
        elif cycle == "每周" and points > 0:
            reason = "周常任务：每周可做，月潜力 %d 积分" % monthly_potential
        elif score > 0:
            reason = "%s：单次 %d 积分，月潜力 %d 积分" % (cycle, points, monthly_potential)
        else:
            reason = "无积分奖励"

        scored.append({
            "task_id": t.get("task_id"),
            "task_name": t.get("task_name", ""),
            "points": points,
            "cycle": cycle,
            "category": t.get("category", ""),
            "score": score,
            "monthly_potential": monthly_potential,
            "reason": reason,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    total_monthly = sum(s["monthly_potential"] for s in scored)

    return {
        "recommendations": scored[:top_n],
        "summary": {
            "total_tasks": len(scored),
            "total_monthly_potential": total_monthly,
        },
    }