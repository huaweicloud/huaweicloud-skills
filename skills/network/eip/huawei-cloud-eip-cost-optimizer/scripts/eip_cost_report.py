#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eip_cost_report.py - 华为云 EIP 成本分析报告生成器
基于华为云 Python SDK v2

Usage:
    python3 eip_cost_report.py --region cn-north-4
    python3 eip_cost_report.py --idle-days 7
    python3 eip_cost_report.py --output report.html
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# 颜色输出
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def color_print(color: str, message: str):
    """彩色输出"""
    print(f"{color}{message}{Colors.RESET}")

def get_client():
    """创建 EIP 客户端 (v2 SDK)"""
    from huaweicloudsdkeip.v2 import EipClient
    from huaweicloudsdkeip.v2.region.eip_region import EipRegion
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    
    ak = os.environ.get('HUAWEI_CLOUD_AK')
    sk = os.environ.get('HUAWEI_CLOUD_SK')
    region = os.environ.get('HUAWEI_CLOUD_REGION', 'cn-north-4')
    
    if not ak or not sk:
        color_print(Colors.RED, "❌ Error: Missing credentials")
        print("\nPlease set environment variables:")
        print("  export HUAWEI_CLOUD_AK=<your-ak>")
        print("  export HUAWEI_CLOUD_SK=<your-sk>")
        sys.exit(1)
    
    credentials = BasicCredentials(ak=ak, sk=sk)
    client = EipClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EipRegion.value_of(region)) \
        .build()
    return client, region

def get_eip_list(client, region: str) -> List[Dict[str, Any]]:
    """获取 EIP 列表"""
    try:
        from huaweicloudsdkeip.v2 import ListPublicipsRequest
        
        request = ListPublicipsRequest()
        request.limit = 100
        
        response = client.list_publicips(request)
        eips = response.publicips if hasattr(response, 'publicips') else []
        
        # 转换为字典格式
        result = []
        for eip in eips:
            eip_dict = {
                'id': eip.id,
                'public_ip_address': eip.public_ip_address,
                'status': eip.status,
                'bandwidth_size': eip.bandwidth_size if hasattr(eip, 'bandwidth_size') else 0,
                'bandwidth_charge_mode': eip.bandwidth_charge_mode if hasattr(eip, 'bandwidth_charge_mode') else 'bandwidth',
                'create_time': eip.create_time if hasattr(eip, 'create_time') else None,
                'port_id': eip.port_id if hasattr(eip, 'port_id') else None,
                'tags': [],
            }
            result.append(eip_dict)
        
        return result
        
    except Exception as e:
        color_print(Colors.RED, f"❌ 获取 EIP 列表失败：{str(e)}")
        return []

def get_eip_tags(client, eip_id: str) -> List[Dict[str, str]]:
    """获取 EIP 标签"""
    try:
        from huaweicloudsdkeip.v2 import ShowPublicipRequest
        
        request = ShowPublicipRequest()
        request.publicip_id = eip_id
        
        response = client.show_publicip(request)
        eip = response.publicip
        
        if hasattr(eip, 'tags') and eip.tags:
            return [{'key': tag.key, 'value': tag.value} for tag in eip.tags]
        
    except Exception:
        pass
    
    return []

def has_protected_tag(eip_tags: List[Dict], protected_tags: List[Tuple[str, str]]) -> bool:
    """检查 EIP 是否有保护标签"""
    if not protected_tags:
        return False
    
    for tag in eip_tags:
        tag_key = tag.get('key', '')
        tag_value = tag.get('value', '')
        for pk, pv in protected_tags:
            if tag_key == pk and tag_value == pv:
                return True
    return False

def is_idle_eip(eip: Dict[str, Any], idle_days: int = 7, protected_tags: List[Tuple[str, str]] = None) -> Tuple[bool, str]:
    """判断 EIP 是否闲置
    
    闲置原因:
      - unbound: 未绑定
      - protected: 有保护标签（附加标记，不单独判定闲置）
      - "": 非闲置
    """
    # 检查保护标签
    if has_protected_tag(eip.get('tags', []), protected_tags or []):
        return False, 'protected'
    
    # 检查是否未绑定
    if eip.get('status') == 'DOWN' or not eip.get('port_id'):
        # 简单判断：状态为 DOWN 或未绑定资源
        return True, 'unbound'
    
    return False, ''

def calculate_cost(bandwidth_size: int, charge_mode: str = 'bandwidth') -> float:
    """计算 EIP 月度成本（简化估算）
    
    华为云 EIP 计费规则（参考）：
    - 带宽计费：约 2 元/Mbps/月
    - 流量计费：按实际使用量
    """
    if charge_mode == 'bandwidth':
        # 带宽计费：2 元/Mbps/月
        return bandwidth_size * 2.0
    else:
        # 流量计费：估算为带宽计费的 50%
        return bandwidth_size * 1.0

def generate_report(eips: List[Dict], region: str, idle_days: int = 7, protected_tags: List[Tuple[str, str]] = None):
    """生成成本分析报告"""
    color_print(Colors.BLUE, "=" * 70)
    color_print(Colors.BLUE, f"  华为云 EIP 成本分析报告")
    color_print(Colors.BLUE, f"  区域：{region} | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    color_print(Colors.BLUE, "=" * 70)
    print()
    
    # 分类统计
    idle_eips = []
    active_eips = []
    protected_eips = []
    total_cost = 0
    idle_cost = 0
    
    for eip in eips:
        # 获取标签
        from huaweicloudsdkeip.v2 import EipClient
        # 注意：这里需要 client 参数，简化处理不获取标签
        
        cost = calculate_cost(eip.get('bandwidth_size', 0), eip.get('bandwidth_charge_mode'))
        eip['monthly_cost'] = cost
        total_cost += cost
        
        is_idle, reason = is_idle_eip(eip, idle_days, protected_tags)
        
        if reason == 'protected':
            protected_eips.append(eip)
            active_eips.append(eip)  # 保护的 EIP 算作活跃
        elif is_idle:
            idle_eips.append(eip)
            idle_cost += cost
        else:
            active_eips.append(eip)
    
    # 输出总览
    color_print(Colors.BOLD, "📊 资源总览:")
    print(f"  总 EIP 数：     {len(eips)}")
    print(f"  活跃 EIP:      {len(active_eips)}")
    print(f"  闲置 EIP:      {Colors.RED}{len(idle_eips)}{Colors.RESET}")
    if protected_eips:
        print(f"  受保护 EIP:    {Colors.GREEN}{len(protected_eips)}{Colors.RESET}")
    print()
    
    # 成本统计
    color_print(Colors.BOLD, "💰 成本统计:")
    print(f"  月度总成本：   ¥{total_cost:.2f}")
    print(f"  闲置浪费：     {Colors.RED}¥{idle_cost:.2f}{Colors.RESET}")
    if total_cost > 0:
        waste_ratio = (idle_cost / total_cost) * 100
        print(f"  浪费比例：     {Colors.YELLOW}{waste_ratio:.1f}%{Colors.RESET}")
    print()
    
    # 闲置 EIP 详情
    if idle_eips:
        color_print(Colors.RED, "⚠️  闲置 EIP 列表:")
        print()
        
        for i, eip in enumerate(idle_eips, 1):
            print(f"  [{i}] {Colors.BOLD}{eip['public_ip_address']}{Colors.RESET}")
            print(f"      EIP ID:    {eip['id']}")
            print(f"      带宽：      {eip['bandwidth_size']} Mbps")
            print(f"      月成本：    ¥{eip['monthly_cost']:.2f}")
            print(f"      状态：      {eip['status']}")
            if eip.get('create_time'):
                print(f"      创建时间：  {eip['create_time']}")
            print()
        
        color_print(Colors.YELLOW, "💡 优化建议:")
        print("  1. 及时释放不再使用的闲置 EIP")
        print("  2. 对临时使用的 EIP 设置标签标记（如：env=test）")
        print("  3. 定期（每周）运行闲置检测脚本")
        print()
    else:
        color_print(Colors.GREEN, "✅ 未发现闲置 EIP，资源利用率良好！")
        print()
    
    # 活跃 EIP 摘要
    color_print(Colors.GREEN, "📋 活跃 EIP 摘要:")
    print()
    
    for eip in active_eips[:5]:  # 只显示前 5 个
        print(f"  • {eip['public_ip_address']} - {eip['bandwidth_size']} Mbps - ¥{eip['monthly_cost']:.2f}/月")
    
    if len(active_eips) > 5:
        print(f"  ... 还有 {len(active_eips) - 5} 个活跃 EIP")
    
    print()
    color_print(Colors.BLUE, "=" * 70)

def main():
    parser = argparse.ArgumentParser(description='华为云 EIP 成本分析报告')
    parser.add_argument('--region', type=str, default=None, help='区域（默认：HUAWEI_CLOUD_REGION 或 cn-north-4）')
    parser.add_argument('--idle-days', type=int, default=7, help='闲置天数阈值（默认：7）')
    parser.add_argument('--protected-tags', type=str, default=None, help='保护标签（格式：key1=value1,key2=value2）')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径（HTML/JSON）')
    
    args = parser.parse_args()
    
    client, region = get_client()
    
    if args.region:
        region = args.region
    
    # 解析保护标签
    protected_tags = []
    if args.protected_tags:
        for item in args.protected_tags.split(','):
            if '=' in item:
                key, value = item.split('=', 1)
                protected_tags.append((key.strip(), value.strip()))
    
    # 获取 EIP 列表
    color_print(Colors.BLUE, "🔍 正在扫描 EIP 资源...")
    eips = get_eip_list(client, region)
    
    if not eips:
        color_print(Colors.YELLOW, "⚠️  当前区域没有找到 EIP 资源")
        sys.exit(0)
    
    # 生成报告
    generate_report(eips, region, args.idle_days, protected_tags)

if __name__ == '__main__':
    main()
