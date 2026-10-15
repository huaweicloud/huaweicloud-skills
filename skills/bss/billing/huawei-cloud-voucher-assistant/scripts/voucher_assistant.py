"""Huawei Cloud voucher assistant — command-line entry point.

用法:
    python scripts/voucher_assistant.py <action> [options]

action 见 SKILL.md「Action Reference」；抵扣 action 缺省仅预览，
须带 --confirm 才会执行。

数据源：
  BSS 开放 API（AK/SK 签名）— 查代金券余额/明细，需 HW_ACCESS_KEY + HW_SECRET_KEY
  成长中心前端 API（fwdo 匿名）— 查公开任务列表，零配置
  未配置 AK/SK 时，代金券查询 action 返回提示信息。分析类 action 离线可用。
"""


import argparse
import json

from analyzer import analyze_voucher_coverage, recommend_discount_plan, recommend_tasks


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_list_vouchers(args):
    from data.coupon_api import get_adapter
    adapter = get_adapter()
    if adapter is None:
        _out({"error": "代金券数据源未配置，需 AK/SK（BSS）"})
        return
    balance = adapter.get_balance()
    vouchers = adapter.list_vouchers()
    _out({"balance": balance, "vouchers": vouchers})


def cmd_list_tasks(args):
    from data.growth_api import get_adapter
    adapter = get_adapter()
    tasks = adapter.list_point_tasks()
    _out({"tasks": tasks})


def cmd_recommend_tasks(args):
    from data.growth_api import get_adapter
    adapter = get_adapter()
    tasks = adapter.list_point_tasks()
    top_n = int(args.top_n) if args.top_n else 5
    _out(recommend_tasks(tasks, top_n=top_n))


def cmd_list_voucher_applicable_services(args):
    from data.coupon_api import load_applicable_services
    services = load_applicable_services()
    _out({"services": services, "source": "references/voucher-taxonomy.md"})


def cmd_analyze_voucher_coverage(args):
    balance = float(args.balance) if args.balance is not None else 0.0
    price = float(args.price)
    _out(analyze_voucher_coverage(balance, price))


def cmd_recommend_discount_plan(args):
    balance = float(args.balance) if args.balance is not None else 0.0
    price = float(args.price)
    alternatives = []
    if args.alt:
        for item in args.alt:
            service, spec, p = item.split(":")
            alternatives.append({"service": service, "spec": spec, "price": float(p)})
    _out(recommend_discount_plan(balance, price, alternatives))


def cmd_apply_voucher(args):
    amount = float(args.amount) if args.amount is not None else 0.0
    out = {"order_ref": args.order_ref, "amount": amount, "executed": False}
    if not args.confirm:
        out["message"] = "未提供 --confirm，仅预览"
        _out(out)
        return
    from data.coupon_api import get_adapter
    adapter = get_adapter()
    if adapter is None:
        out["message"] = "代金券数据源未配置，需 AK/SK（BSS），未能执行"
        _out(out)
        return
    try:
        res = adapter.apply_voucher(args.order_ref, amount)
        out.update({"executed": True, "result": res})
    except NotImplementedError:
        out["message"] = "代金券抵扣数据源待接入（需 BSS 订单系统），未能执行"
    _out(out)


ACTIONS = {
    "list_vouchers": cmd_list_vouchers,
    "list_tasks": cmd_list_tasks,
    "recommend_tasks": cmd_recommend_tasks,
    "list_voucher_applicable_services": cmd_list_voucher_applicable_services,
    "analyze_voucher_coverage": cmd_analyze_voucher_coverage,
    "recommend_discount_plan": cmd_recommend_discount_plan,
    "apply_voucher": cmd_apply_voucher,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Huawei Cloud voucher assistant")
    parser.add_argument("action", choices=sorted(ACTIONS))
    parser.add_argument("--balance", help="代金券余额 (分析类, 数据源未接入时手动传入)")
    parser.add_argument("--price", help="目标价格 (分析类)")
    parser.add_argument("--alt", action="append", help="低规格替代 service:spec:price，可多次")
    parser.add_argument("--order-ref", help="订单引用 (抵扣)")
    parser.add_argument("--amount", help="抵扣金额")
    parser.add_argument("--confirm", action="store_true", help="确认执行抵扣")
    parser.add_argument("--top-n", help="推荐任务返回数量 (recommend_tasks, 默认 5)")

    args = parser.parse_args(argv)
    handler = ACTIONS[args.action]
    try:
        handler(args)
    except Exception as e:  # noqa: BLE001
        _out({"error": str(e)})


if __name__ == "__main__":
    main()