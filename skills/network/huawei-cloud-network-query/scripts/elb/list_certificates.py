import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListCertificatesRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 证书列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="证书ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="证书名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="证书描述，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="证书类型，支持多值查询，取值: server(服务器证书) client(CA证书) server_sm(服务器SM双证书)")
parser.add_argument("--domain", type=str, nargs="+", help="服务器证书所签域名，支持多值查询")
parser.add_argument("--common_name", type=str, nargs="+", help="证书的主域名，支持多值查询")
parser.add_argument("--fingerprint", type=str, nargs="+", help="证书的指纹，支持多值查询")
parser.add_argument("--scm_certificate_id", type=str, nargs="+", help="云证书管理服务(CCM)中的证书ID，支持多值查询")
parser.add_argument("--source", type=str, nargs="+", help="证书来源，支持多值查询，scm表示关联CCM证书，空值表示自有证书")
parser.add_argument("--admin_state_up", type=bool, help="证书的管理状态，true可用，false不可用")
parser.add_argument("--protection_status", type=str, nargs="+", help="修改保护状态，支持多值查询，nonProtection不保护，consoleProtection控制台修改保护")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListCertificatesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.type:
        request.type = args.type
    if args.domain:
        request.domain = args.domain
    if args.common_name:
        request.common_name = args.common_name
    if args.fingerprint:
        request.fingerprint = args.fingerprint
    if args.scm_certificate_id:
        request.scm_certificate_id = args.scm_certificate_id
    if args.source:
        request.source = args.source
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.protection_status:
        request.protection_status = args.protection_status
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    response = client.list_certificates(request)
    certificates = response.certificates

    if not certificates:
        print(f"没有找到证书 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(certificates) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(certificates[PAGE_SIZE - 1], 'id', ''))

    display_certificates = certificates[:PAGE_SIZE]

    output = f"name\tid\ttype\tdomain\tcommon_name\texpire_time\tsource\tcreated_at\n"
    for item in display_certificates:
        name = getattr(item, 'name', '')
        id = getattr(item, 'id', '')
        cert_type = getattr(item, 'type', '')
        domain = getattr(item, 'domain', '')
        common_name = getattr(item, 'common_name', '')
        expire_time = getattr(item, 'expire_time', '')
        source = getattr(item, 'source', '')
        created_at = getattr(item, 'created_at', '')
        output += f"{name}\t{id}\t{cert_type}\t{domain}\t{common_name}\t{expire_time}\t{source}\t{created_at}\n"

    if has_more:
        output += f"\n当前返回 {len(display_certificates)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_certificates)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_certificates 查询失败: {e}")
    exit(1)
