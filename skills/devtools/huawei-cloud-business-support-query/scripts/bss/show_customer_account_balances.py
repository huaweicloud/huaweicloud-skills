import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ShowCustomerAccountBalancesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户账户余额")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
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

    request = ShowCustomerAccountBalancesRequest()
    response = client.show_customer_account_balances(request)

    debt_amount = getattr(response, 'debt_amount', 0)
    measure_id = getattr(response, 'measure_id', 1)
    currency = getattr(response, 'currency', 'CNY')
    account_balances = getattr(response, 'account_balances', []) or []

    if not account_balances:
        print(f"没有找到账户余额记录 (区域: {Region})")
        exit(0)

    total_amount = 0.0
    total_designated_amount = 0.0
    total_credit_amount = 0.0
    rows = []
    for balance in account_balances:
        account_id = getattr(balance, 'account_id', '')
        account_type = getattr(balance, 'account_type', '')
        type_str = {1: '余额', 2: '信用', 5: '奖励金', 7: '保证金'}.get(account_type, str(account_type))
        amount = getattr(balance, 'amount', 0)
        curr = getattr(balance, 'currency', 'CNY')
        designated_amount = getattr(balance, 'designated_amount', 0)
        credit_amount = getattr(balance, 'credit_amount', 0)
        measure_id = getattr(balance, 'measure_id', 1)
        rows.append((account_id, type_str, amount, curr, designated_amount, credit_amount, measure_id))
        total_amount += float(amount)
        total_designated_amount += float(designated_amount)
        total_credit_amount += float(credit_amount)

    debt = float(debt_amount)
    total_amount -= debt

    print(f"measure_id: {measure_id}\tcurrency: {currency}")
    print(f"{'account_id':<36}\t{'account_type':<8}\t{'amount':>12}\t{'currency':<5}\t{'designated_amount':>16}\t{'credit_amount':>14}\tmeasure_id")
    print(f"{'欠款':<36}\t{'欠款':<8}\t{-debt:>12.2f}\t{currency:<5}\t{'0':>16}\t{'0':>14}\t{measure_id}")
    for row in rows:
        print(f"{row[0]:<36}\t{row[1]:<8}\t{row[2]:>12}\t{row[3]:<5}\t{row[4]:>16}\t{row[5]:>14}\t{row[6]}")
    print(f"{'合计':<36}\t{'':8}\t{total_amount:>12.2f}\t{currency:<5}\t{total_designated_amount:>16.2f}\t{total_credit_amount:>14.2f}\t")
    exit(0)
except Exception as e:
    print(f"bss.show_customer_account_balances 查询失败: {e}")
    exit(1)
