"""AS 模块公共工具函数"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion


def resolve_project_id(region, project_id=None):
    """解析项目 ID

    优先使用传入的 project_id，否则从环境变量 HW_PROJECT_ID 获取，
    最后通过 IAM KeystoneListProjects 接口按 region 自动获取。

    :param region: 区域名称，如 cn-north-4
    :param project_id: 可选的项目 ID，若提供则直接返回
    :return: 项目 ID 字符串
    """
    if project_id:
        return project_id

    env_pid = os.getenv("HW_PROJECT_ID", "")
    if env_pid:
        return env_pid

    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")

    if not ak or not sk:
        print("未配置 AK/SK，请设置环境变量 HW_ACCESS_KEY 和 HW_SECRET_KEY")
        exit(-1)

    try:
        http_config = build_http_config()
        credentials = BasicCredentials(ak, sk)
        if security_token:
            credentials = credentials.with_security_token(security_token)
        client = (IamClient.new_builder()
                  .with_http_config(http_config)
                  .with_credentials(credentials)
                  .with_region(IamRegion.value_of(region))
                  .build())
        request = KeystoneListProjectsRequest()
        request.name = region
        response = client.keystone_list_projects(request)
        projects = response.projects
        if not projects:
            print(f"未找到可访问的项目 (区域: {region})")
            exit(0)
        for project in projects:
            if getattr(project, 'name', '') == region:
                return project.id
        return projects[0].id
    except Exception as e:
        print(f"自动获取项目 ID 失败: {e}")
        print("请通过 --project_id 参数指定，或设置 HW_PROJECT_ID 环境变量")
        exit(-1)


def _build_vpc_client(region, project_id):
    """构建 VPC 客户端"""
    try:
        from huaweicloudsdkvpc.v3 import VpcClient
        from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion
    except ImportError:
        return None

    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")
    credentials = BasicCredentials(ak, sk, project_id)
    if security_token:
        credentials = credentials.with_security_token(security_token)
    http_config = build_http_config()
    return VpcClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(VpcRegion.value_of(region)).build()


def resolve_vpc_info(region, project_id, vpc_ids):
    """批量解析 VPC 名称和 CIDR

    :param region: 区域名称
    :param project_id: 项目 ID
    :param vpc_ids: VPC ID 列表
    :return: dict {vpc_id: {name, cidr}}
    """
    if not vpc_ids:
        return {}
    client = _build_vpc_client(region, project_id)
    if not client:
        return {vid: {"name": "", "cidr": ""} for vid in vpc_ids}
    try:
        from huaweicloudsdkvpc.v3 import ListVpcsRequest
        result = {}
        for vid in vpc_ids:
            req = ListVpcsRequest()
            req.id = [vid]
            resp = client.list_vpcs(req)
            vpcs = getattr(resp, 'vpcs', []) or []
            if vpcs:
                result[vid] = {"name": getattr(vpcs[0], 'name', ''), "cidr": getattr(vpcs[0], 'cidr', '')}
            else:
                result[vid] = {"name": "", "cidr": ""}
        return result
    except Exception:
        return {vid: {"name": "", "cidr": ""} for vid in vpc_ids}


def resolve_subnet_info(region, project_id, subnet_ids, vpc_id=None):
    """批量解析子网名称、CIDR、可用区等信息

    :param region: 区域名称
    :param project_id: 项目 ID
    :param subnet_ids: 子网 ID 列表
    :param vpc_id: 可选的 VPC ID，用于缩小查询范围
    :return: dict {subnet_id: {name, cidr, gateway_ip, availability_zone, available_ip_address_count}}
    """
    if not subnet_ids:
        return {}
    try:
        from huaweicloudsdkvpc.v2 import VpcClient as VpcClientV2
        from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion as VpcRegionV2
        from huaweicloudsdkvpc.v2 import ListSubnetsRequest
    except ImportError:
        return {sid: {"name": "", "cidr": "", "gateway_ip": "", "availability_zone": "", "available_ip_address_count": ""} for sid in subnet_ids}

    ak = os.getenv("HW_ACCESS_KEY", "")
    sk = os.getenv("HW_SECRET_KEY", "")
    security_token = os.getenv("HW_SECURITY_TOKEN", "")
    credentials = BasicCredentials(ak, sk, project_id)
    if security_token:
        credentials = credentials.with_security_token(security_token)
    http_config = build_http_config()

    try:
        client = VpcClientV2.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(VpcRegionV2.value_of(region)).build()
        result = {}
        req = ListSubnetsRequest()
        if vpc_id:
            req.vpc_id = vpc_id
        resp = client.list_subnets(req)
        subnets = getattr(resp, 'subnets', []) or []
        subnet_map = {getattr(s, 'id', ''): s for s in subnets}
        for sid in subnet_ids:
            s = subnet_map.get(sid)
            if s:
                result[sid] = {
                    "name": getattr(s, 'name', ''),
                    "cidr": getattr(s, 'cidr', ''),
                    "gateway_ip": getattr(s, 'gateway_ip', ''),
                    "availability_zone": getattr(s, 'availability_zone', ''),
                    "available_ip_address_count": getattr(s, 'available_ip_address_count', ''),
                }
            else:
                result[sid] = {"name": "", "cidr": "", "gateway_ip": "", "availability_zone": "", "available_ip_address_count": ""}
        return result
    except Exception:
        return {sid: {"name": "", "cidr": "", "gateway_ip": "", "availability_zone": "", "available_ip_address_count": ""} for sid in subnet_ids}


# 资源类型对应的列表查询脚本提示
_RESOURCE_LIST_HINTS = {
    "scalingGroup": "list_scaling_groups.py",
    "scalingConfiguration": "list_scaling_configs.py",
    "scalingPolicy": "list_scaling_policies.py",
    "lifecycleHook": "list_life_cycle_hooks.py",
    "warmPool": "list_warm_pool_instances.py",
}


def handle_not_found_error(error, resource_type, resource_id):
    """处理 404 资源不存在错误，输出友好提示

    :param error: 异常对象
    :param resource_type: 资源类型英文名，如 scalingGroup
    :param resource_id: 请求的资源 ID
    """
    error_str = str(error)
    is_404 = "404" in error_str or "could not be found" in error_str or "not exist" in error_str
    if is_404:
        list_script = _RESOURCE_LIST_HINTS.get(resource_type, "")
        hint = f"资源 [{resource_type}] 不存在 (ID: {resource_id})，请检查 ID 是否正确。"
        if list_script:
            hint += f"\n提示：可先运行 {list_script} 查看可用资源列表。"
        print(hint)
    else:
        print(f"查询失败: {error}")
    exit(1)
