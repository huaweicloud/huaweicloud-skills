import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListStoredValueCardsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询储值卡列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--status", type=int, default=1, help="状态。1：可使用；2：已用完。默认查询可使用(1)，传0时查询所有状态")
parser.add_argument("--card_id", type=str, help="储值卡ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="查询的储值卡的数量，默认值为50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    request = ListStoredValueCardsRequest()
    if args.card_id:
        request.card_id = args.card_id
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    status_list = [1, 2] if args.status == 0 else [args.status]
    all_cards = []
    for s in status_list:
        request.status = s
        response = client.list_stored_value_cards(request)
        cards = getattr(response, 'stored_value_cards', []) or []
        all_cards.extend(cards)

    if not all_cards:
        print(f"没有找到储值卡记录 (区域: {Region})")
        exit(0)

    output = "card_id\tcard_name\tstatus\tface_value\tbalance\teffective_time\texpire_time\n"
    for card in all_cards:
        card_id = getattr(card, 'card_id', '')
        card_name = getattr(card, 'card_name', '')
        status = getattr(card, 'status', '')
        face_value = getattr(card, 'face_value', '')
        balance = getattr(card, 'balance', '')
        effective_time = getattr(card, 'effective_time', '')
        expire_time = getattr(card, 'expire_time', '')
        output += f"{card_id}\t{card_name}\t{status}\t{face_value}\t{balance}\t{effective_time}\t{expire_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_stored_value_cards 查询失败: {e}")
    exit(1)
