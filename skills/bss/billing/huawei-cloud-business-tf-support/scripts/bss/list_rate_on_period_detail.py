import argparse
import json
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListRateOnPeriodDetailRequest
from huaweicloudsdkbss.v2.model import RateOnPeriodReq
from huaweicloudsdkbss.v2.model import PeriodProductInfo
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

PERIOD_TYPE_MAP = {0: "天", 2: "月", 3: "年", 4: "小时"}
PERIOD_TYPE_NAMES = {v: k for k, v in PERIOD_TYPE_MAP.items()}

DISCOUNT_TYPE_MAP = {
    605: "商务授权折扣",
    606: "伙伴授予折扣",
    607: "伙伴设置折扣",
}

SIZE_MEASURE_ID_MAP = {15: "Mbps", 17: "GB", 14: "个"}

PERIOD_PRESETS = {
    "ecs": {
        "cloud_service_type": "hws.service.type.ec2",
        "resource_type": "hws.resource.type.vm",
        "spec_suffix": ".linux",
        "help": "ECS云服务器，spec如s6.small.1/s7.medium.2/c6.large.2(自动加.linux)",
    },
    "evs": {
        "cloud_service_type": "hws.service.type.ebs",
        "resource_type": "hws.resource.type.volume",
        "need_resource_size": True,
        "default_size": 10,
        "default_size_measure_id": 17,
        "help": "EVS云硬盘，spec如SATA/SAS/SSD/GPSSD/ESSD/GPSSD2.storage，默认10GB",
    },
    "eip-bw": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "need_resource_size": True,
        "default_size": 1,
        "default_size_measure_id": 15,
        "help": "EIP按带宽计费，spec: 19_bgp(动态BGP)/19_sbgp(静态BGP)/19_share(共享带宽)，默认1Mbps",
    },
    "eip-ip": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.ip",
        "help": "EIP公网IP，spec: 5_bgp(动态BGP)/5_sbgp(静态BGP)",
    },
    "elb": {
        "cloud_service_type": "hws.service.type.elb",
        "resource_type": "hws.resource.type.elbv3",
        "help": "ELB独享型负载均衡，spec如l4.flavor.elb.s1.small(共享型免费不询价)",
    },
    "nat": {
        "cloud_service_type": "hws.service.type.natgateway",
        "resource_type": "hws.resource.type.natgateway",
        "help": "NAT网关，spec如nat.spec.small/medium/large",
    },
    "obs": {
        "cloud_service_type": "hws.service.type.obs",
        "resource_type": "hws.resource.type.obs",
        "help": "OBS对象存储，spec如obs.standard/obs.warm/obs.cold",
    },
    "sfs": {
        "cloud_service_type": "hws.service.type.sfsturbo",
        "resource_type": "hws.resource.type.sfsturbo",
        "need_resource_size": True,
        "default_size": 500,
        "default_size_measure_id": 17,
        "help": "SFS Turbo，spec如sfs.turbo.standard/sfs.turbo.performance，默认500GB",
    },
    "bms": {
        "cloud_service_type": "hws.service.type.baremetal",
        "resource_type": "hws.resource.type.pm",
        "spec_suffix": ".linux",
        "help": "裸金属服务器，spec如physical.ks1.2xlarge(带demand表示不支持询价)",
    },
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="查询包年/包月产品询价，最简用法: --preset <云服务> --resource_spec <规格>",
    )
    parser.add_argument("--project_id", required=True, help="项目ID")
    parser.add_argument("--preset", required=True,
                        help="云服务别名，如ecs/evs/eip-bw/eip-ip/elb/nat/obs/sfs/vpn/bms")
    parser.add_argument("--resource_spec", nargs="+", required=True,
                        help="资源规格编码(支持多个)")
    parser.add_argument("--region", default="cn-north-4", help="区域(默认cn-north-4)")
    parser.add_argument("--available_zone", help="可用区标识")
    parser.add_argument("--period_type", nargs="+", default=["月"],
                        help="周期类型: 天/月/年/小时(默认月)，也可传数字0/2/3/4")
    parser.add_argument("--period_num", type=int, nargs="+", default=[1],
                        help="周期数(默认1)")
    parser.add_argument("--subscription_num", type=int, nargs="+", default=[1],
                        help="订购数量(默认1)")
    parser.add_argument("--resource_size", type=int, nargs="+",
                          help="资源容量(线性产品如EVS/带宽，preset已含默认值)")
    parser.add_argument("--size_measure_id", type=int, nargs="+",
                          help="容量度量标识(15=Mbps 17=GB 14=个，preset已含默认值)")
    parser.add_argument("--fee_installment_mode", help="分期模式: HALF_PAY/ZERO_PAY/NA(仅CloudPond)")
    parser.add_argument("--sort", choices=["price", "spec"], default=None,
                            help="排序: price=按官网价升序 spec=按规格名排序")
    parser.add_argument("--show_discount", action="store_true",
                            help="显示可选折扣询价明细(默认仅显示官网价)")
    parser.add_argument("--json", action="store_true", dest="json_output",
                            help="以JSON格式输出结果")
    parser.add_argument("--compare_period", nargs="+",
                            help="跨周期比价(传多个周期如 月 年，自动逐周期询价并对比)")
    return parser


def parse_period_type(val):
    if val.isdigit():
        return int(val)
    return PERIOD_TYPE_NAMES.get(val)


def apply_preset(args):
    if args.preset not in PERIOD_PRESETS:
        print(f"不支持 '{args.preset}' 的包年包月询价")
        exit(0)
    p = PERIOD_PRESETS[args.preset]
    args.cloud_service_type = [p["cloud_service_type"]]
    args.resource_type = [p["resource_type"]]
    if p.get("spec_suffix"):
        args.resource_spec = [
            s + p["spec_suffix"] if not s.endswith(p["spec_suffix"]) else s
            for s in args.resource_spec
        ]
    if p.get("need_resource_size") and not args.resource_size:
        args.resource_size = [p["default_size"]]
    if p.get("need_resource_size") and not args.size_measure_id:
        args.size_measure_id = [p["default_size_measure_id"]]


def validate_args(args):
    count = len(args.resource_spec)
    if args.resource_size and not args.size_measure_id:
        print("指定 --resource_size 时，必须同时指定 --size_measure_id")
        exit(1)
    if args.size_measure_id and not args.resource_size:
        print("指定 --size_measure_id 时，必须同时指定 --resource_size")
        exit(1)
    for name, val in [
        ("resource_size", args.resource_size),
        ("size_measure_id", args.size_measure_id),
        ("period_num", args.period_num),
        ("subscription_num", args.subscription_num),
    ]:
        if val and len(val) != 1 and len(val) != count:
            print(f"--{name} 数量必须为1或与 --resource_spec 数量({count})一致")
            exit(1)
    resolved = []
    for pt in args.period_type:
        r = parse_period_type(pt)
        if r is None:
            print(f"无效的period_type: '{pt}'，支持: 天/月/年/小时 或 0/2/3/4")
            exit(1)
        resolved.append(r)
    args.period_type = resolved


def expand_param(val, count):
    if len(val) == 1:
        return val * count
    return val


def build_product_infos(args, count, override_period_type=None, override_period_num=None):
    info_ids = [str(i + 1) for i in range(count)]
    cloud_service_types = expand_param(args.cloud_service_type, count)
    resource_types = expand_param(args.resource_type, count)
    resource_specs = args.resource_spec
    regions = [args.region] * count
    period_types = [override_period_type] * count if override_period_type else expand_param(args.period_type, count)
    period_nums = [override_period_num] * count if override_period_num else expand_param(args.period_num, count)
    subscription_nums = expand_param(args.subscription_num, count)
    available_zone = args.available_zone
    resource_sizes = expand_param(args.resource_size, count) if args.resource_size else [None] * count
    size_measure_ids = expand_param(args.size_measure_id, count) if args.size_measure_id else [None] * count
    fee_installment_mode = args.fee_installment_mode

    infos = []
    for i in range(count):
        info = PeriodProductInfo()
        info.id = info_ids[i]
        info.cloud_service_type = cloud_service_types[i]
        info.resource_type = resource_types[i]
        info.resource_spec = resource_specs[i]
        info.region = regions[i]
        info.period_type = period_types[i]
        info.period_num = period_nums[i]
        info.subscription_num = subscription_nums[i]
        if available_zone:
            info.available_zone = available_zone
        if resource_sizes[i] is not None:
            info.resource_size = resource_sizes[i]
        if size_measure_ids[i] is not None:
            info.size_measure_id = size_measure_ids[i]
        if fee_installment_mode:
            info.fee_installment_mode = fee_installment_mode
        infos.append(info)
    return infos


def create_bss_client():
    http_config = build_http_config()
    creds = GlobalCredentials(AK, SK)
    if SecurityToken:
        creds = creds.with_security_token(SecurityToken)
    return BssClient.new_builder() \
        .with_http_config(http_config) \
        .with_credentials(creds) \
        .with_region(BssRegion.CN_NORTH_1) \
        .build()


def do_inquiry(args, count, override_period_type=None, override_period_num=None):
    product_infos = build_product_infos(args, count, override_period_type, override_period_num)
    body = RateOnPeriodReq()
    body.project_id = args.project_id
    body.product_infos = product_infos

    client = create_bss_client()
    request = ListRateOnPeriodDetailRequest()
    request.body = body
    return client.list_rate_on_period_detail(request)


def safe_decimal(val):
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def format_price(val, width=14):
    s = f"{val:.2f}"
    return s.rjust(width)


def period_label(period_type, period_num):
    pt_name = PERIOD_TYPE_MAP.get(period_type, str(period_type))
    return f"{period_num}{pt_name}"


def extract_official_results(response, specs, period_type, period_num, period_label_str=""):
    results = []
    currency = getattr(response, 'currency', '') or 'CNY'
    owr = getattr(response, 'official_website_rating_result', None)
    if not owr:
        return results, currency

    total_owa = safe_decimal(getattr(owr, 'official_website_amount', None))
    total_measure_id = getattr(owr, 'measure_id', None)
    total_installment_owa = getattr(owr, 'installment_official_website_amount', None)
    total_installment_period_type = getattr(owr, 'installment_period_type', None)
    product_results = getattr(owr, 'product_rating_results', []) or []

    for i, pr in enumerate(product_results):
        spec = specs[i] if i < len(specs) else f"product_{i+1}"
        owa = safe_decimal(getattr(pr, 'official_website_amount', None))
        pid = getattr(pr, 'product_id', '') or ''
        pr_measure_id = getattr(pr, 'measure_id', None)
        pr_installment_owa = getattr(pr, 'installment_official_website_amount', None)
        pr_installment_period_type = getattr(pr, 'installment_period_type', None)
        results.append({
            "spec": spec,
            "period_label": period_label_str or period_label(period_type, period_num),
            "period_type": period_type,
            "period_num": period_num,
            "product_id": pid,
            "official_amount": owa,
            "measure_id": pr_measure_id,
            "installment_official_amount": pr_installment_owa,
            "installment_period_type": pr_installment_period_type,
            "currency": currency,
        })
    return results, currency


def extract_discount_results(response, specs, period_type, period_num, period_label_str=""):
    results = []
    currency = getattr(response, 'currency', '') or 'CNY'
    optional_discounts = getattr(response, 'optional_discount_rating_results', []) or []

    for od in optional_discounts:
        discount_id = getattr(od, 'discount_id', '') or ''
        discount_name = getattr(od, 'discount_name', '') or ''
        discount_type = getattr(od, 'discount_type', 0)
        best_offer = getattr(od, 'best_offer', 0)
        total_amount = safe_decimal(getattr(od, 'amount', None))
        total_owa = safe_decimal(getattr(od, 'official_website_amount', None))
        total_da = safe_decimal(getattr(od, 'discount_amount', None))
        od_measure_id = getattr(od, 'measure_id', None)
        od_installment_owa = getattr(od, 'installment_official_website_amount', None)
        od_installment_oda = getattr(od, 'installment_official_discount_amount', None)
        od_installment_amt = getattr(od, 'installment_amount', None)
        od_installment_period_type = getattr(od, 'installment_period_type', None)

        product_results = getattr(od, 'product_rating_results', []) or []
        product_details = []
        for i, pr in enumerate(product_results):
            spec = specs[i] if i < len(specs) else f"product_{i+1}"
            pr_measure_id = getattr(pr, 'measure_id', None)
            pr_installment_owa = getattr(pr, 'installment_official_website_amount', None)
            pr_installment_oda = getattr(pr, 'installment_official_discount_amount', None)
            pr_installment_amt = getattr(pr, 'installment_amount', None)
            pr_installment_period_type = getattr(pr, 'installment_period_type', None)
            product_details.append({
                "spec": spec,
                "amount": safe_decimal(getattr(pr, 'amount', None)),
                "official_amount": safe_decimal(getattr(pr, 'official_website_amount', None)),
                "discount_amount": safe_decimal(getattr(pr, 'discount_amount', None)),
                "product_id": getattr(pr, 'product_id', '') or '',
                "measure_id": pr_measure_id,
                "installment_official_amount": pr_installment_owa,
                "installment_discount_amount": pr_installment_oda,
                "installment_amount": pr_installment_amt,
                "installment_period_type": pr_installment_period_type,
            })

        results.append({
            "discount_id": discount_id,
            "discount_name": discount_name,
            "discount_type": discount_type,
            "discount_type_name": DISCOUNT_TYPE_MAP.get(discount_type, "未知"),
            "best_offer": best_offer,
            "period_label": period_label_str or period_label(period_type, period_num),
            "total_amount": total_amount,
            "total_official_amount": total_owa,
            "total_discount_amount": total_da,
            "measure_id": od_measure_id,
            "installment_official_amount": od_installment_owa,
            "installment_discount_amount": od_installment_oda,
            "installment_amount": od_installment_amt,
            "installment_period_type": od_installment_period_type,
            "currency": currency,
            "products": product_details,
        })
    return results


def render_table(results, discount_results, sort=None, show_discount=False):
    if not results:
        print("询价结果为空")
        return

    if sort == "price":
        results.sort(key=lambda x: x["official_amount"])
    elif sort == "spec":
        results.sort(key=lambda x: x["spec"])

    currency = results[0].get("currency", "CNY")

    print(f"{'resource_spec':<30} {'period':<10} {'official_price(' + currency + ')':>20} {'measure_id':<10} {'product_id':<40}")
    print("-" * 115)
    for r in results:
        mid = str(r["measure_id"]) if r["measure_id"] is not None else ""
        print(f"{r['spec']:<30} {r['period_label']:<10} {format_price(r['official_amount']):>20} {mid:<10} {r['product_id']:<40}")

    if show_discount and discount_results:
        print(f"\n{'='*60}")
        print("可选折扣询价明细:")
        print(f"{'='*60}")
        for d in discount_results:
            best_mark = " [最优]" if d["best_offer"] == 1 else ""
            print(f"\n  折扣: {d['discount_type_name']} - {d['discount_name']}{best_mark}")
            print(f"  周期: {d['period_label']}")
            print(f"  折后总价: {d['total_amount']} {currency}  官网价: {d['total_official_amount']} {currency}  优惠额: {d['total_discount_amount']} {currency}  金额单位: {d['measure_id']}")
            if d["products"]:
                print(f"  {'spec':<28} {'折后价':>14} {'官网价':>14} {'优惠额':>14} {'measure_id':>10} {'product_id':<36}")
                print(f"  {'-'*118}")
                for p in d["products"]:
                    p_mid = str(p["measure_id"]) if p["measure_id"] is not None else ""
                    print(f"  {p['spec']:<28} {format_price(p['amount']):>14} {format_price(p['official_amount']):>14} {format_price(p['discount_amount']):>14} {p_mid:>10} {p['product_id']:<36}")


def render_json(results, discount_results, show_discount=False):
    output = []
    for r in results:
        entry = {
            "spec": r["spec"],
            "period_label": r["period_label"],
            "period_type": r["period_type"],
            "period_num": r["period_num"],
            "product_id": r["product_id"],
            "official_amount": str(r["official_amount"]),
            "measure_id": r["measure_id"],
            "installment_official_amount": r["installment_official_amount"],
            "installment_period_type": r["installment_period_type"],
            "currency": r["currency"],
        }
        output.append(entry)
    if show_discount and discount_results:
        for d in discount_results:
            d_copy = {
                "discount_id": d["discount_id"],
                "discount_name": d["discount_name"],
                "discount_type": d["discount_type"],
                "discount_type_name": d["discount_type_name"],
                "best_offer": d["best_offer"],
                "period_label": d["period_label"],
                "total_amount": str(d["total_amount"]),
                "total_official_amount": str(d["total_official_amount"]),
                "total_discount_amount": str(d["total_discount_amount"]),
                "measure_id": d["measure_id"],
                "installment_official_amount": d["installment_official_amount"],
                "installment_discount_amount": d["installment_discount_amount"],
                "installment_amount": d["installment_amount"],
                "installment_period_type": d["installment_period_type"],
                "currency": d["currency"],
                "products": [],
            }
            for p in d["products"]:
                d_copy["products"].append({
                    "spec": p["spec"],
                    "amount": str(p["amount"]),
                    "official_amount": str(p["official_amount"]),
                    "discount_amount": str(p["discount_amount"]),
                    "product_id": p["product_id"],
                    "measure_id": p["measure_id"],
                    "installment_official_amount": p["installment_official_amount"],
                    "installment_discount_amount": p["installment_discount_amount"],
                    "installment_amount": p["installment_amount"],
                    "installment_period_type": p["installment_period_type"],
                })
            output.append({"discount": d_copy})
    print(json.dumps(output, indent=2, ensure_ascii=False))


def render_summary(results, discount_results, response, show_discount=False):
    owr = getattr(response, 'official_website_rating_result', None)
    if owr:
        total_owa = safe_decimal(getattr(owr, 'official_website_amount', None))
        total_measure_id = getattr(owr, 'measure_id', None)
        currency = getattr(response, 'currency', '') or 'CNY'
        pt = results[0]["period_type"] if results else 2
        pn = results[0]["period_num"] if results else 1
        measure_str = f", 金额单位={total_measure_id}" if total_measure_id is not None else ""
        print(f"\n汇总: 官网总价={total_owa} {currency} (周期={period_label(pt, pn)}){measure_str}")
    if show_discount and discount_results:
        best = [d for d in discount_results if d["best_offer"] == 1]
        if best:
            b = best[0]
            print(f"最优折扣: {b['discount_type_name']}({b['discount_name']}) 折后总价={b['total_amount']} {b['currency']}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.region is not None:
        global Region
        Region = args.region

    apply_preset(args)
    validate_args(args)

    product_count = len(args.resource_spec)
    show_discount = args.show_discount

    try:
        if args.compare_period:
            all_results = []
            all_discounts = []
            for pt_str in args.compare_period:
                pt = parse_period_type(pt_str)
                if pt is None:
                    print(f"无效的周期: '{pt_str}'，支持: 天/月/年/小时 或 0/2/3/4")
                    continue
                try:
                    resp = do_inquiry(args, product_count, override_period_type=pt)
                    pl = period_label(pt, args.period_num[0])
                    official, currency = extract_official_results(resp, args.resource_spec, pt, args.period_num[0], pl)
                    all_results.extend(official)
                    if show_discount:
                        discounts = extract_discount_results(resp, args.resource_spec, pt, args.period_num[0], pl)
                        all_discounts.extend(discounts)
                except Exception as e:
                    for spec in args.resource_spec:
                        all_results.append({
                            "spec": spec, "period_label": period_label(pt, args.period_num[0]),
                            "period_type": pt, "period_num": args.period_num[0],
                            "product_id": "", "official_amount": None, "measure_id": None,
                            "installment_official_amount": None, "installment_period_type": None,
                            "currency": "CNY", "error": str(e),
                        })
            valid = [r for r in all_results if r.get("official_amount") is not None]
            invalid = [r for r in all_results if r.get("official_amount") is None]
            if args.json_output:
                render_json(valid, all_discounts, show_discount=show_discount)
            else:
                render_table(valid, all_discounts, sort=args.sort, show_discount=show_discount)
                if invalid:
                    print(f"\n询价失败({len(invalid)}条):")
                    for r in invalid:
                        print(f"  {r['spec']} @ {r['period_label']}: {r.get('error', '未知错误')}")
        else:
            resp = do_inquiry(args, product_count)
            pt = args.period_type[0]
            pn = args.period_num[0]
            official, currency = extract_official_results(resp, args.resource_spec, pt, pn)
            discounts = []
            if show_discount:
                discounts = extract_discount_results(resp, args.resource_spec, pt, pn)
            if args.json_output:
                render_json(official, discounts, show_discount=show_discount)
            else:
                render_table(official, discounts, sort=args.sort, show_discount=show_discount)
                render_summary(official, discounts, resp, show_discount=show_discount)

        exit(0)
    except Exception as e:
        err_str = str(e)
        if "CBC.99006006" in err_str:
            preset_hint = ""
            if args.preset:
                preset_hint = f"\n提示: preset '{args.preset}' 的参数可能在该区域不支持，请检查 --resource_spec 是否正确"
            print(f"询价失败: 产品未发现(请检查参数是否正确){preset_hint}")
        elif "CBC.99006055" in err_str:
            print(f"询价失败: 询价结果超过金额最大限制")
        elif "CBC.0151" in err_str:
            print(f"询价失败: 拒绝访问(请检查IAM权限billing:contract:viewDiscount)")
        elif "CBC.0250" in err_str:
            print(f"询价失败: 请求频率超限(请降低调用频率)")
        else:
            print(f"询价失败")
        exit(1)


if __name__ == "__main__":
    main()
