import argparse
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListOnDemandResourceRatingsRequest
from huaweicloudsdkbss.v2.model import RateOnDemandReq
from huaweicloudsdkbss.v2.model import DemandProductInfo
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

DISCOUNT_TYPE_MAP = {
    605: "商务授权折扣",
    606: "伙伴授予折扣",
    607: "伙伴设置折扣",
}

PRESETS = {
    "ecs": {
        "cloud_service_type": "hws.service.type.ec2",
        "resource_type": "hws.resource.type.vm",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "spec_suffix": ".linux",
        "help": "ECS云服务器，spec 可通过 list_flavors.py 获取后加.linux或.win后缀",
    },
    "evs": {
        "cloud_service_type": "hws.service.type.ebs",
        "resource_type": "hws.resource.type.volume",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 10,
        "default_size_measure_id": 17,
        "help": "EVS云硬盘，spec：SATA/SAS/SSD/GPSSD/ESSD/GPSSD2.storage/GPSSD2.iops/GPSSD2.throughput，默认10GB",
    },
    "eip-bw": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 1,
        "default_size_measure_id": 15,
        "help": "EIP按带宽计费，spec: 19_bgp(动态BGP)/19_sbgp(静态BGP)/19_share(共享带宽)，默认1Mbps",
    },
    "eip-flow": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.bandwidth",
        "usage_measure_id": 10,
        "usage_factor": "upflow",
        "help": "EIP按流量计费，spec: 12_bgp(动态BGP)/12_sbgp(静态BGP)，usage_measure_id=10(GB)",
    },
    "eip-ip": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.ip",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "EIP公网IP，spec: 5_bgp(动态BGP)/5_sbgp(静态BGP)",
    },
    "vpc": {
        "cloud_service_type": "hws.service.type.vpc",
        "resource_type": "hws.resource.type.vpcep",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "VPC终端节点，spec如vpcep.spec.small/micro/medium/large",
    },
    "elb": {
        "cloud_service_type": "hws.service.type.elb",
        "resource_type": "hws.resource.type.elbv2",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "ELB负载均衡(共享型免费，独享型不支持询价)。spec: elb.share或L4_flavor.elb.s1.small",
    },
    "nat": {
        "cloud_service_type": "hws.service.type.natgateway",
        "resource_type": "hws.resource.type.natgateway",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "NAT公网网关，spec如nat.spec.small/nat.spec.medium/nat.spec.large",
    },
    "obs": {
        "cloud_service_type": "hws.service.type.obs",
        "resource_type": "hws.resource.type.obs",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "help": "OBS对象存储，spec如obs.standard/obs.warm/obs.cold",
    },
    "sfs": {
        "cloud_service_type": "hws.service.type.sfsturbo",
        "resource_type": "hws.resource.type.sfsturbo",
        "usage_measure_id": 4,
        "usage_factor": "Duration",
        "need_resource_size": True,
        "default_size": 500,
        "default_size_measure_id": 17,
        "help": "SFS Turbo文件系统，spec如sfs.turbo.standard/sfs.turbo.performance，默认500GB",
    },
}

def build_parser():
    parser = argparse.ArgumentParser(
        description="查询按需资源询价，最简用法: --preset <云服务> --resource_spec <规格>",
    )
    parser.add_argument("--project_id", required=True, help="项目ID")
    parser.add_argument("--preset", required=True,
                        help="云服务别名，如ecs/evs/eip-bw/eip-flow/eip-ip/vpc/elb/nat/obs/sfs/vpn/ces/ims/cbr")
    parser.add_argument("--resource_spec", nargs="+",
                        help="资源规格编码(支持多个)")
    parser.add_argument("--region", default="cn-north-4", help="区域(默认cn-north-4)")
    parser.add_argument("--available_zone", help="可用区标识")
    parser.add_argument("--resource_size", type=int, nargs="+",
                          help="资源容量(线性产品如EVS/带宽，preset已含默认值)")
    parser.add_argument("--size_measure_id", type=int, nargs="+",
                          help="容量度量标识(15=Mbps 17=GB 14=个，preset已含默认值)")
    parser.add_argument("--usage_value", type=float, nargs="+", default=[1],
                           help="使用量值(默认1即1小时)")
    parser.add_argument("--subscription_num", type=int, nargs="+", default=[1],
                           help="订购数量(默认1)")
    parser.add_argument("--compare_regions", nargs="+",
                            help="跨区域比价(传多个区域如cn-north-4 cn-east-2)")
    parser.add_argument("--show_discount", action="store_true",
                            help="显示折扣优惠明细")
    parser.add_argument("--json", action="store_true", dest="json_output",
                            help="以JSON格式输出结果")
    parser.add_argument("--sort", choices=["price", "spec"], default=None,
                            help="排序: price=按价格升序 spec=按规格名排序")
    return parser


def apply_preset(args):
    if args.preset not in PRESETS:
        print(f"不支持 '{args.preset}' 的按需询价")
        exit(0)
    p = PRESETS[args.preset]
    args.cloud_service_type = [p["cloud_service_type"]]
    args.resource_type = [p["resource_type"]]
    args.usage_measure_id = [p["usage_measure_id"]]
    args.usage_factor = [p.get("usage_factor", "Duration")]
    if not args.resource_spec:
        print(f"preset '{args.preset}' 需要指定 --resource_spec，可选值: {p.get('help', '')}")
        exit(0)
    if p.get("need_resource_size") and not args.resource_size:
        args.resource_size = [p["default_size"]]
    if p.get("need_resource_size") and not args.size_measure_id:
        args.size_measure_id = [p["default_size_measure_id"]]
    if p.get("spec_suffix"):
        args.resource_spec = [
            s + p["spec_suffix"] if not s.endswith(p["spec_suffix"]) else s
            for s in args.resource_spec
        ]


def validate_args(args):
    count = len(args.resource_spec)
    if args.resource_size and not args.size_measure_id:
        print("指定 --resource_size 时，必须同时指定 --size_measure_id")
        exit(0)
    if args.size_measure_id and not args.resource_size:
        print("指定 --size_measure_id 时，必须同时指定 --resource_size")
        exit(0)
    for name, val in [
        ("resource_size", args.resource_size),
        ("size_measure_id", args.size_measure_id),
        ("usage_value", args.usage_value),
        ("subscription_num", args.subscription_num),
    ]:
        if val and len(val) != 1 and len(val) != count:
            print(f"--{name} 数量必须为1或与 --resource_spec 数量({count})一致")
            exit(1)


def expand_param(val, count):
    if len(val) == 1:
        return val * count
    return val


def build_product_infos(args, count, override_region=None):
    info_ids = [str(i + 1) for i in range(count)]
    cloud_service_types = expand_param(args.cloud_service_type, count)
    resource_types = expand_param(args.resource_type, count)
    resource_specs = args.resource_spec
    regions = [override_region] * count if override_region else [args.region] * count
    available_zone = args.available_zone
    resource_sizes = expand_param(args.resource_size, count) if args.resource_size else [None] * count
    size_measure_ids = expand_param(args.size_measure_id, count) if args.size_measure_id else [None] * count
    usage_factors = expand_param(args.usage_factor, count)
    usage_values = expand_param(args.usage_value, count)
    usage_measure_ids = expand_param(args.usage_measure_id, count)
    subscription_nums = expand_param(args.subscription_num, count)

    infos = []
    for i in range(count):
        info = DemandProductInfo()
        info.id = info_ids[i]
        info.cloud_service_type = cloud_service_types[i]
        info.resource_type = resource_types[i]
        info.resource_spec = resource_specs[i]
        info.region = regions[i]
        if available_zone:
            info.available_zone = available_zone
        if resource_sizes[i] is not None:
            info.resource_size = resource_sizes[i]
        if size_measure_ids[i] is not None:
            info.size_measure_id = size_measure_ids[i]
        info.usage_factor = usage_factors[i]
        info.usage_value = usage_values[i]
        info.usage_measure_id = usage_measure_ids[i]
        info.subscription_num = subscription_nums[i]
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


def do_inquiry(args, count, override_region=None):
    product_infos = build_product_infos(args, count, override_region)
    body = RateOnDemandReq()
    body.project_id = args.project_id
    body.inquiry_precision = 1
    body.product_infos = product_infos

    client = create_bss_client()
    request = ListOnDemandResourceRatingsRequest()
    request.body = body
    return client.list_on_demand_resource_ratings(request)


def safe_decimal(val):
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def extract_results(response, specs, region_label="", show_discount=False):
    results = []
    product_rating_results = getattr(response, 'product_rating_results', []) or []
    currency = getattr(response, 'currency', '') or 'CNY'
    response_measure_id = getattr(response, 'measure_id', None)

    for i, pr in enumerate(product_rating_results):
        spec = specs[i] if i < len(specs) else f"product_{i+1}"
        amt = safe_decimal(getattr(pr, 'amount', None))
        owa = safe_decimal(getattr(pr, 'official_website_amount', None))
        da = safe_decimal(getattr(pr, 'discount_amount', None))
        pid = getattr(pr, 'product_id', '') or ''
        pr_measure_id = getattr(pr, 'measure_id', None)

        entry = {
            "id": getattr(pr, 'id', '') or str(i + 1),
            "spec": spec,
            "region": region_label,
            "product_id": pid,
            "amount": amt,
            "official_amount": owa,
            "discount_amount": da,
            "measure_id": pr_measure_id,
            "currency": currency,
        }

        if show_discount:
            discount_details = []
            for dr in (getattr(pr, 'discount_rating_results', None) or []):
                dr_measure_id = getattr(dr, 'measure_id', None)
                discount_details.append({
                    "discount_id": getattr(dr, 'discount_id', '') or '',
                    "discount_type": getattr(dr, 'discount_type', 0),
                    "discount_type_name": DISCOUNT_TYPE_MAP.get(getattr(dr, 'discount_type', 0), "未知"),
                    "discount_name": getattr(dr, 'discount_name', '') or '',
                    "amount": safe_decimal(getattr(dr, 'amount', None)),
                    "measure_id": dr_measure_id,
                })
            entry["discount_details"] = discount_details

        results.append(entry)
    return results, response_measure_id


def format_price(val, width=12):
    s = f"{val:.6f}"
    if s.rstrip('0').rstrip('.') != s:
        s = s.rstrip('0').rstrip('.')
    return s.rjust(width)


def render_table(results, sort=None, show_discount=False):
    if not results:
        print("询价结果为空")
        return

    if sort == "price":
        results.sort(key=lambda x: x["amount"])
    elif sort == "spec":
        results.sort(key=lambda x: x["spec"])

    has_region = any(r["region"] for r in results)
    currency = results[0].get("currency", "CNY")

    col_spec = "resource_spec"
    col_region = "region" if has_region else None
    col_amt = f"amount({currency}/h)"
    col_owa = f"official({currency}/h)"
    col_da = f"discount({currency}/h)"
    col_pid = "product_id"
    col_mid = "measure_id"

    columns = [col_spec]
    if has_region:
        columns.append(col_region)
    columns.extend([col_amt, col_owa, col_da, col_mid])
    columns.append(col_pid)
    if show_discount:
        columns.append("discount_detail")

    header = "\t".join(columns)
    print(header)

    for r in results:
        parts = [r["spec"]]
        if has_region:
            parts.append(r["region"])
        parts.extend([
            format_price(r["amount"]),
            format_price(r["official_amount"]),
            format_price(r["discount_amount"]),
            str(r["measure_id"]) if r["measure_id"] is not None else "",
        ])
        parts.append(r["product_id"])
        if show_discount and "discount_details" in r:
            dd = r["discount_details"]
            if dd:
                detail_strs = []
                for d in dd:
                    detail_strs.append(
                        f"{d['discount_type_name']}({d['discount_name']})=-{d['amount']}"
                    )
                parts.append("; ".join(detail_strs))
            else:
                parts.append("-")
        print("\t".join(parts))

    if sort == "price" and results:
        cheapest = results[0]
        region_info = f" (region: {cheapest['region']})" if cheapest['region'] else ""
        print(f"\n最低价: {cheapest['spec']} = {cheapest['amount']} {currency}/h{region_info}")


def render_json(results, show_discount=False):
    import json
    output = []
    for r in results:
        entry = {
            "spec": r["spec"],
            "region": r["region"] or None,
            "product_id": r["product_id"],
            "amount": str(r["amount"]),
            "official_amount": str(r["official_amount"]),
            "discount_amount": str(r["discount_amount"]),
            "measure_id": r["measure_id"],
            "currency": r["currency"],
        }
        if show_discount and "discount_details" in r:
            entry["discount_details"] = []
            for d in r["discount_details"]:
                entry["discount_details"].append({
                    "discount_id": d["discount_id"],
                    "discount_type": d["discount_type"],
                    "discount_type_name": d["discount_type_name"],
                    "discount_name": d["discount_name"],
                    "amount": str(d["amount"]),
                    "measure_id": d["measure_id"],
                })
        output.append(entry)
    print(json.dumps(output, indent=2, ensure_ascii=False))


def render_summary(results, response):
    total_amt = safe_decimal(getattr(response, 'amount', None))
    total_owa = safe_decimal(getattr(response, 'official_website_amount', None))
    total_da = safe_decimal(getattr(response, 'discount_amount', None))
    currency = getattr(response, 'currency', '') or 'CNY'
    measure_id = getattr(response, 'measure_id', None)
    measure_id_str = f", 金额单位={measure_id}" if measure_id is not None else ""

    print(f"\n汇总: 总价={total_amt} {currency}/h, "
          f"官网价={total_owa} {currency}/h, "
          f"优惠额={total_da} {currency}/h{measure_id_str}")


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
        if args.compare_regions:
            all_results = []
            for reg in args.compare_regions:
                try:
                    resp = do_inquiry(args, product_count, override_region=reg)
                    region_results, _ = extract_results(resp, args.resource_spec,
                                                    region_label=reg, show_discount=show_discount)
                    all_results.extend(region_results)
                except Exception as e:
                    err_msg = str(e)
                    for spec in args.resource_spec:
                        all_results.append({
                            "id": "", "spec": spec, "region": reg,
                            "product_id": "", "amount": None,
                            "official_amount": None, "discount_amount": None,
                            "measure_id": None, "currency": "CNY", "error": err_msg,
                        })
            valid_results = [r for r in all_results if r.get("amount") is not None]
            invalid_results = [r for r in all_results if r.get("amount") is None]
            if args.json_output:
                render_json(valid_results, show_discount=show_discount)
            else:
                render_table(valid_results, sort=args.sort, show_discount=show_discount)
                if invalid_results:
                    print(f"\n不可售区域({len(invalid_results)}条):")
                    for r in invalid_results:
                        print(f"  {r['spec']} @ {r['region']}: 不可售 ({r.get('error', '')})")
        else:
            resp = do_inquiry(args, product_count)
            results, _ = extract_results(resp, args.resource_spec, show_discount=show_discount)
            if args.json_output:
                render_json(results, show_discount=show_discount)
            else:
                render_table(results, sort=args.sort, show_discount=show_discount)
                render_summary(results, resp)

        exit(0)
    except Exception as e:
        err_str = str(e)
        if "CBC.99006006" in err_str:
            preset_hint = ""
            if args.preset:
                preset_hint = f"\n提示: preset '{args.preset}' 的参数可能在该区域不支持，请检查 --resource_spec 是否正确"
            print(f"询价失败: 产品未发现(请检查cloud_service_type/resource_type/resource_spec/region是否正确){preset_hint}")
        elif "CBC.99006050" in err_str:
            print(f"询价失败: 使用量单位错误(请检查usage_measure_id)")
        elif "CBC.99006074" in err_str:
            print(f"询价失败: 计费因子不存在(请检查usage_factor)")
        elif "CBC.99006055" in err_str:
            print(f"询价失败: 询价结果超过金额最大限制")
        elif "CBC.0151" in err_str:
            print(f"询价失败: 拒绝访问(请检查IAM权限billing:contract:viewDiscount)")
        else:
            print(f"询价失败")
        exit(1)


if __name__ == "__main__":
    main()
