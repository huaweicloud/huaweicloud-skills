#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出所有 EIP 及其详细信息
基于华为云 Python SDK v2

Usage:
    python3 list_eips.py --region cn-north-4
    python3 list_eips.py --status BINDING
    python3 list_eips.py --idle-only
"""

import os
import sys
from datetime import datetime
from typing import List, Optional

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
        print("  export HUAWEI_CLOUD_REGION=cn-north-4")
        sys.exit(1)
    
    credentials = BasicCredentials(ak=ak, sk=sk)
    client = EipClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EipRegion.value_of(region)) \
        .build()
    
    return client, region

def list_all_eips(client):
    """获取所有 EIP 列表（返回原始数据供其他脚本使用）"""
    from huaweicloudsdkeip.v2 import ListPublicipsRequest
    
    request = ListPublicipsRequest()
    request.limit = 1000
    
    response = client.list_publicips(request)
    return response.publicips if hasattr(response, 'publicips') else []

def list_eips(region_filter: Optional[str] = None, status_filter: Optional[str] = None, idle_only: bool = False):
    """列出所有 EIP"""
    client, region = get_client()
    
    if region_filter:
        region = region_filter
    
    color_print(Colors.BLUE, "=" * 60)
    color_print(Colors.BLUE, f"  EIP 列表查询（区域：{region}）")
    color_print(Colors.BLUE, "=" * 60)
    print()
    
    try:
        eips = list_all_eips(client)
        
        if not eips:
            color_print(Colors.YELLOW, "⚠️  当前区域没有找到 EIP 资源")
            return
        
        # 过滤和统计
        filtered_eips = []
        idle_count = 0
        binding_count = 0
        total_bandwidth = 0
        
        for eip in eips:
            # 状态过滤
            if status_filter and eip.status != status_filter:
                continue
            
            # 闲置过滤
            is_idle = (eip.status == 'DOWN' or eip.status == 'ELB')
            if idle_only and not is_idle:
                continue
            
            filtered_eips.append(eip)
            
            if is_idle:
                idle_count += 1
            else:
                binding_count += 1
            
            if hasattr(eip, 'bandwidth_size') and eip.bandwidth_size:
                total_bandwidth += eip.bandwidth_size
        
        # 输出结果
        color_print(Colors.GREEN, f"📊 找到 {len(filtered_eips)} 个 EIP")
        print()
        
        for i, eip in enumerate(filtered_eips, 1):
            is_idle = (eip.status == 'DOWN' or eip.status == 'ELB')
            status_color = Colors.RED if is_idle else Colors.GREEN
            status_text = "IDLE" if is_idle else eip.status
            
            print(f"[{i}] {Colors.BOLD}{eip.public_ip_address}{Colors.RESET}")
            print(f"    EIP ID:      {eip.id}")
            print(f"    状态：       {status_color}{status_text}{Colors.RESET}")
            print(f"    带宽大小：   {eip.bandwidth_size if hasattr(eip, 'bandwidth_size') else 'N/A'} Mbps")
            print(f"    计费模式：   {eip.bandwidth_charge_mode if hasattr(eip, 'bandwidth_charge_mode') else 'N/A'}")
            
            if hasattr(eip, 'port_id') and eip.port_id:
                print(f"    绑定资源：   {eip.port_id}")
            else:
                print(f"    绑定资源：   {Colors.YELLOW}未绑定{Colors.RESET}")
            
            if hasattr(eip, 'create_time') and eip.create_time:
                print(f"    创建时间：   {eip.create_time}")
            
            print()
        
        # 汇总统计
        color_print(Colors.BLUE, "-" * 60)
        color_print(Colors.BOLD, "📈 汇总统计:")
        print(f"  总 EIP 数：     {len(filtered_eips)}")
        print(f"  闲置 EIP:      {Colors.RED}{idle_count}{Colors.RESET}")
        print(f"  使用中 EIP:    {Colors.GREEN}{binding_count}{Colors.RESET}")
        print(f"  总带宽：       {total_bandwidth} Mbps")
        color_print(Colors.BLUE, "-" * 60)
        
    except Exception as e:
        color_print(Colors.RED, f"❌ 查询失败：{str(e)}")
        sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='列出所有华为云 EIP')
    parser.add_argument('--region', type=str, default=None, help='区域（默认：HUAWEI_CLOUD_REGION 或 cn-north-4）')
    parser.add_argument('--status', type=str, default=None, help='状态过滤（BINDING, DOWN, ELB, etc.）')
    parser.add_argument('--idle-only', action='store_true', help='仅显示闲置 EIP')
    parser.add_argument('--summary', action='store_true', help='仅输出统计数据（CSV 格式：总数，闲置数，总带宽）')
    
    args = parser.parse_args()
    
    # 如果是 summary 模式，输出 CSV 格式
    if args.summary:
        try:
            client, region = get_client()
            eips = list_all_eips(client)
            
            total_count = len(eips)
            idle_count = sum(1 for e in eips if hasattr(e, 'status') and e.status in ['DOWN', 'ELB'])
            total_bandwidth = sum(e.bandwidth_size for e in eips if hasattr(e, 'bandwidth_size') and e.bandwidth_size)
            
            # 输出 CSV 格式：总数，闲置数，总带宽
            print(f"{total_count},{idle_count},{total_bandwidth}")
        except Exception:
            print("0,0,0")
        return
    
    list_eips(
        region_filter=args.region,
        status_filter=args.status,
        idle_only=args.idle_only
    )

if __name__ == '__main__':
    main()
