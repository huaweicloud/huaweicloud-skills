import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ListClustersRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数（ListClusters 接口不支持分页，超出部分需 --all 展示）

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--detail", type=str, help="是否返回集群详细信息，取值 true 或 false，不传则仅返回基本信息")
parser.add_argument("--status", type=str, help="集群状态过滤，例如 Available、Unavailable、ScalingUp、ScalingDown、Creating、Deleting、Error、Freezed")
parser.add_argument("--type", type=str, help="集群类型过滤，可选值：VirtualMachine（普通集群，含 CCE Turbo）、ARM64、Autopilot")
parser.add_argument("--version", type=str, help="集群版本过滤，例如 v1.28、v1.29")
parser.add_argument("--all", action="store_true", help=f"展示全部集群，默认最多展示 {PAGE_SIZE} 个")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

Region = args.region


# 渲染
def render(clusters, total_count, has_more):
    if not clusters:
        print("没有找到 CCE 集群")
        return

    output = "id\tname\tstatus\ttype\tversion\tflavor\tcategory\tcreated\n"
    for cluster in clusters:
        metadata = getattr(cluster, 'metadata', None)
        spec = getattr(cluster, 'spec', None)
        status = getattr(cluster, 'status', None)
        cid = getattr(metadata, 'uid', '') if metadata else ''
        name = getattr(metadata, 'name', '') if metadata else ''
        created = getattr(metadata, 'creation_timestamp', '') if metadata else ''
        phase = getattr(status, 'phase', '') if status else ''
        ctype = getattr(spec, 'type', '') if spec else ''
        version = getattr(spec, 'version', '') if spec else ''
        flavor = getattr(spec, 'flavor', '') if spec else ''
        category = getattr(spec, 'category', '') if spec else ''
        output += f"{cid}\t{name}\t{phase}\t{ctype}\t{version}\t{flavor}\t{category}\t{created}\n"

    # 汇总信息
    showing_count = len(clusters)
    if has_more:
        output += f"\n共 {total_count} 个 CCE 集群，当前展示前 {showing_count} 个（ListClusters 接口不支持分页）"
        output += "\n可加 --all 展示全部，或使用 --status / --type / --version 缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个 CCE 集群"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)

    client = CceClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CceRegion.value_of(Region)).build()
    if not client:
        print("无法获取 CCE 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListClustersRequest()
    if args.detail:
        request.detail = args.detail
    if args.status:
        request.status = args.status
    if args.type:
        request.type = args.type
    if args.version:
        request.version = args.version

    response = client.list_clusters(request)
    clusters = response.items or []
    display_clusters = clusters if args.all else clusters[:PAGE_SIZE]

    # 渲染结果
    render(display_clusters, len(clusters), len(clusters) > len(display_clusters))
except Exception as e:
    print(f"cce.clusters 查询失败: {e}")
    exit(1)
