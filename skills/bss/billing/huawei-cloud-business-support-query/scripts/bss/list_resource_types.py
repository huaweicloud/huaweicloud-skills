#!/usr/bin/env python3
"""
华为云 BSS - 查询资源类型列表

通过华为云 BSS API（v1.0）列举资源类型，支持按服务类型编码过滤。

用法:
  完整列表:       python scripts/bss/list_resource_types.py
  按服务过滤:     python scripts/bss/list_resource_types.py -s hws.service.type.ec2

输出说明:
  总记录数        API 返回的资源类型总数
  过滤后记录数    使用 -s 过滤后的实际记录数（仅在启用了过滤时输出）
  ---
  每条记录包含:  code（编码）, name（名称）, service_type_code（所属服务编码）

注意事项:
  1. 使用 -s 过滤时，过滤是在客户端完成的（BSS API 不支持服务端过滤）
  2. 部分服务类型编码可通过 list_service_types.py 查询
  3. 每种云服务的资源类型可通过以下方式进一步查看:
     - 使用 list_on_demand_resource_ratings.py 查询按需定价
     - 使用 list_rate_on_period_detail.py 查询包年包月定价

BSS 定价参数对照表（常见云服务）：

  | 云服务           | service_type_code              | 说明           |
  |------------------|-------------------------------|----------------|
  | ECS 弹性云服务器  | hws.service.type.ec2          | 计算           |
  | EVS 云硬盘       | hws.service.type.ebs          | 存储           |
  | EIP 弹性公网IP   | hws.service.type.vpc          | ⚠️ EIP 在 BSS API 中归属于 "vpc" 服务 |
  | VPC 虚拟私有云   | hws.service.type.vpc          | 网络           |
  | ELB 弹性负载均衡 | hws.service.type.elb          | 负载均衡       |
  | NAT 网关         | hws.service.type.nat          | NAT 网关       |
  | OBS 对象存储     | hws.service.type.obs          | 对象存储       |
  | SFS 弹性文件服务 | hws.service.type.sfs          | 文件存储       |
  | VPN 虚拟专用网络 | hws.service.type.vpn          | VPN            |
  | RDS 关系型数据库 | hws.service.type.rds          | 数据库         |
  | DCS 分布式缓存   | hws.service.type.dcs          | 缓存           |
  | CCE 云容器引擎   | hws.service.type.cce          | 容器           |
  | CES 云监控       | hws.service.type.ces          | 监控           |
  | IMS 镜像服务     | hws.service.type.ims          | 镜像           |

  | 常见 resource_type_code     | 所属服务       | 说明             |
  |-----------------------------|---------------|------------------|
  | hws.resource.type.vm        | ECS           | 弹性云服务器实例  |
  | hws.resource.type.vm.cpu    | ECS           | vCPU（部分场景）  |
  | hws.resource.type.vm.mem    | ECS           | 内存（部分场景）  |
  | hws.resource.type.volume    | EVS           | 云硬盘            |
  | hws.resource.type.volume.gpssd | EVS        | 通用型SSD        |
  | hws.resource.type.ip        | EIP/VPC       | 弹性公网IP        |
  | hws.resource.type.bandwidth | EIP/VPC       | 带宽（含按带宽和按流量） |
  | hws.resource.type.bandwidth.name | EIP/VPC  | 带宽名称          |

  | resource_spec 示例                         | 说明                              |
  |-------------------------------------------|-----------------------------------|
  | s6.large.2                                | ECS 规格编码                      |
  | SSD.gpfsla.v2                             | EVS 高IO（按需）                  |
  | 10_hws.resource.type.bandwidth            | 固定带宽 10Mbps（按带宽计费）     |
  | ?_hws.resource.type.bandwidth             | ❓ 按流量计费的带宽，resource_spec 需通过 list_rate_on_period_detail 查看已有订单确认 |

修复说明（踩坑点）：
  1. 原脚本在 if args.service_type_code or args.resource_type_name 中引用了未定义的参数 resource_type_name，
     导致当不传 -s 参数时报 AttributeError: 'Namespace' object has no attribute 'resource_type_name'。
     已修复：移除该引用，仅在有 -s 参数时才输出过滤记录数。
  2. 原脚本分页逻辑中 total_count 在每轮循环中被重新赋值，
     若 total_count 首次为 0（API 返回 None），会导致循环逻辑异常。
     已优化：非首次循环时复用首次记录的 total_count。
  3. 原脚本无 -h 帮助信息输出，现已为 list_resource_types 添加完整帮助说明。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.region.bss_region import BssRegion
from huaweicloudsdkbss.v2.model import ListResourceTypesRequest
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="查询华为云资源类型列表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/bss/list_resource_types.py                       # 所有资源类型
  python scripts/bss/list_resource_types.py -s hws.service.type.ec2   # 只查 ECS 相关
  python scripts/bss/list_resource_types.py -s hws.service.type.vpc   # 查 EIP/VPC 相关

常见 service_type_code:
  hws.service.type.ec2  - ECS 弹性云服务器
  hws.service.type.ebs  - EVS 云硬盘
  hws.service.type.vpc  - VPC/EIP（注意：EIP 归属 VPC 服务）
  hws.service.type.elb  - ELB 弹性负载均衡
  hws.service.type.obs  - OBS 对象存储
        """
    )
    parser.add_argument("-s", "--service_type_code",
                        help="按服务类型编码过滤（如 hws.service.type.ec2）")
    return parser.parse_args()


def main():
    args = parse_args()

    AK, SK, Region, SecurityToken = load_credentials()

    http_config = build_http_config()

    # BSS 使用 GlobalCredentials
    credentials = (
        GlobalCredentials(AK, SK)
        if not SecurityToken
        else GlobalCredentials(AK, SK).with_security_token(SecurityToken)
    )

    client = (
        BssClient.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(BssRegion.CN_NORTH_1)
        .build()
    )

    # 分页查询，在循环内直接过滤
    filtered = []
    offset = 0
    limit = 100
    total_count = 0
    fetched = 0
    is_first_page = True

    MAX_PAGES = 1000
    for _page in range(MAX_PAGES):
        request = ListResourceTypesRequest()
        request.offset = offset
        request.limit = limit
        # 如果传了 service_type_code，直接走服务端过滤
        if args.service_type_code:
            request.service_type_code = args.service_type_code

        response = client.list_resource_types(request)
        resource_types = getattr(response, 'resource_types', None) or []

        # 在循环内直接过滤
        if args.service_type_code:
            resource_types = [r for r in resource_types if getattr(r, 'service_type_code', '') == args.service_type_code]
        filtered.extend(resource_types)

        # 分页控制
        fetched += len(getattr(response, 'resource_types', None) or [])
        current_total = getattr(response, 'total_count', None)
        if is_first_page:
            if current_total is not None:
                total_count = current_total
            else:
                total_count = fetched
            is_first_page = False
        # 如果 total_count 为 0，使用已拉取数据的长度
        effective_total = total_count if total_count > 0 else fetched

        if fetched >= effective_total:
            break

        offset += limit

    # 输出结果
    output = f"总记录数\t{total_count}\n"
    if args.service_type_code:
        output += f"过滤后记录数\t{len(filtered)}\n"

    if filtered:
        output += "\n资源类型列表:\n"
        output += "resource_type_code\tresource_type_name\tresource_type_desc\tservice_type_code\n"
        for resource in filtered:
            resource_type_code = getattr(resource, 'resource_type_code', '')
            resource_type_name = getattr(resource, 'resource_type_name', '')
            resource_type_desc = getattr(resource, 'resource_type_desc', '')
            service_type_code = getattr(resource, 'service_type_code', '')
            output += f"{resource_type_code}\t{resource_type_name}\t{resource_type_desc}\t{service_type_code}\n"

    print(output)


if __name__ == "__main__":
    main()
