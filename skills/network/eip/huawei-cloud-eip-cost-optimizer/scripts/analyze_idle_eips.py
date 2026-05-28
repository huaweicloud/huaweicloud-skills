#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找闲置 EIP 并生成分析报告（仅分析，不执行释放操作）
Usage: python3 analyze_idle_eips.py [--region cn-north-4] [--min-idle-days 7]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from huaweicloudsdkeip.v2 import EipClient, ListPublicipsRequest
from huaweicloudsdkeip.v2.region.eip_region import EipRegion
from huaweicloudsdkcore.auth.credentials import BasicCredentials

def get_credentials():
    """从环境变量获取 AK/SK"""
    ak = os.environ.get('HUAWEI_CLOUD_AK')
    sk = os.environ.get('HUAWEI_CLOUD_SK')
    region = os.environ.get('HUAWEI_CLOUD_REGION', 'cn-north-4')
    
    if not ak or not sk:
        print("❌ 错误：未找到华为云凭证")
        print("请设置环境变量:")
        print("  export HUAWEI_CLOUD_AK=<your-ak>")
        print("  export HUAWEI_CLOUD_SK=<your-sk>")
        print("  export HUAWEI_CLOUD_REGION=cn-north-4  # 可选，默认 cn-north-4")
        sys.exit(1)
    
    return BasicCredentials(ak=ak, sk=sk), region

def list_eips(client, region):
    """列出所有 EIP"""
    request = ListPublicipsRequest()
    request.limit = 100
    
    try:
        response = client.list_publicips(request)
        return response.publicips if response.publicips else []
    except Exception as e:
        print(f"❌ 查询 EIP 失败：{e}")
        return []

def find_idle_eips(eips, min_idle_days=0):
    """找出闲置 EIP（未绑定的）"""
    idle_eips = []
    for eip in eips:
        # 检查绑定状态：port_id 为 None 或空表示未绑定
        port_id = getattr(eip, 'port_id', None)
        status = getattr(eip, 'status', 'UNKNOWN')
        
        # 未绑定的 EIP (port_id 为 None 或空字符串)
        if port_id is None or port_id == '':
            # 计算闲置天数
            create_time = getattr(eip, 'create_time', None)
            idle_days = calculate_idle_days(create_time) if create_time else -1
            
            # 只有闲置天数 >= 阈值才加入列表
            if idle_days >= 0 and idle_days >= min_idle_days:
                idle_eips.append(eip)
    
    return idle_eips

def calculate_idle_days(create_time_str):
    """计算闲置天数（从创建时间开始）"""
    try:
        # 解析 ISO 格式时间：2024-01-15T10:30:00Z
        if 'T' in create_time_str:
            create_time = datetime.fromisoformat(create_time_str.replace('Z', '+00:00'))
        else:
            create_time = datetime.strptime(create_time_str, '%Y-%m-%d %H:%M:%S')
        
        now = datetime.now(create_time.tzinfo) if create_time.tzinfo else datetime.now()
        delta = now - create_time
        return delta.days
    except Exception:
        return -1  # 无法计算

def print_eip_table(eips, title="EIP 列表", min_idle_days=0):
    """打印 EIP 表格"""
    print("\n" + "=" * 120)
    print(f"{title} (区域：{os.environ.get('HUAWEI_CLOUD_REGION', 'cn-north-4')}, 闲置阈值：≥{min_idle_days}天)")
    print("=" * 120)
    print(f"{'EIP ID':<40} {'IP 地址':<16} {'带宽 ID':<20} {'状态':<10} {'端口绑定':<12} {'创建时间':<20} {'闲置天数'}")
    print("-" * 120)
    
    for eip in eips:
        eip_id = getattr(eip, 'id', 'N/A')[:36]
        ip = getattr(eip, 'public_ip_address', 'N/A')
        bw_id = getattr(eip, 'bandwidth_id', 'N/A')[:16] if getattr(eip, 'bandwidth_id', None) else 'N/A'
        status = getattr(eip, 'status', 'N/A')
        port_id = getattr(eip, 'port_id', 'N/A')
        create_time = getattr(eip, 'create_time', 'N/A')[:19] if getattr(eip, 'create_time', None) else 'N/A'
        
        # 闲置 EIP 高亮标记
        is_idle = port_id is None or port_id == ''
        marker = " ⚠️ 闲置" if is_idle else ""
        port_status = "未绑定" if is_idle else f"已绑定 ({port_id[:8]}...)"
        
        # 计算闲置天数
        idle_days = calculate_idle_days(create_time) if is_idle else 0
        idle_days_str = f"{idle_days} 天" if idle_days >= 0 else "未知"
        
        print(f"{eip_id:<40} {ip:<16} {bw_id:<20} {status:<10} {port_status:<12} {create_time:<20} {idle_days_str}{marker}")
    
    print("-" * 120)
    idle_count = len([e for e in eips if (getattr(e, 'port_id', None) is None or getattr(e, 'port_id', '') == '') and calculate_idle_days(getattr(e, 'create_time', None)) >= min_idle_days])
    print(f"总计：{len(eips)} 个 EIP, 闲置：{idle_count} 个 (阈值：≥{min_idle_days}天)")
    print("=" * 120 + "\n")

def generate_report(all_eips, idle_eips, min_idle_days=0):
    """生成分析报告"""
    print("\n" + "=" * 120)
    print(f"📊 闲置 EIP 分析报告 (闲置阈值：≥{min_idle_days}天)")
    print("=" * 120)
    
    # 成本估算（按 cn-north-4 按需价格）
    # 参考：EIP 保留费约 ¥0.02/小时/个，带宽费按实际带宽计算
    estimated_hourly_cost = len(idle_eips) * 0.02  # 仅保留费
    estimated_monthly_cost = estimated_hourly_cost * 24 * 30
    
    print(f"\n📈 资源概览:")
    print(f"  - EIP 总数：{len(all_eips)} 个")
    print(f"  - 闲置 EIP 数量：{len(idle_eips)} 个")
    print(f"  - 闲置率：{len(idle_eips)/len(all_eips)*100:.1f}%" if all_eips else "  - 闲置率：N/A")
    
    print(f"\n💰 成本估算（参考 cn-north-4 按需价格）:")
    print(f"  - 当前每小时成本：约 ¥{estimated_hourly_cost:.2f}/小时")
    print(f"  - 当前每月成本：约 ¥{estimated_monthly_cost:.2f}/月")
    print(f"  - 潜在节省：100%（如释放所有闲置 EIP）")
    
    print(f"\n⚠️  风险提示:")
    print(f"  - EIP 释放是不可逆操作，IP 地址将被回收且无法恢复")
    print(f"  - 建议先确认闲置 EIP 是否用于备用、灾备或临时业务")
    print(f"  - 释放前请通知相关业务负责人")
    
    print(f"\n💡 优化建议:")
    if len(idle_eips) == 0:
        print("  ✅ 所有 EIP 都在使用中，无需优化")
    else:
        print("  1. 【立即行动】确认闲置 EIP 的业务用途，联系负责人核实")
        print("  2. 【降低成本】对确认不用的 EIP，手动在控制台释放")
        print("  3. 【保留备用】对可能需要但暂时闲置的 EIP，可调整为最低带宽（1 Mbps）")
        print("  4. 【定期审计】建议每周运行此脚本，持续监控闲置资源")
        print("  5. 【标签管理】为 EIP 添加用途标签，便于后续识别和管理")
    
    # 详细清单
    if idle_eips:
        print(f"\n📋 闲置 EIP 详细清单:")
        for i, eip in enumerate(idle_eips, 1):
            eip_id = getattr(eip, 'id', 'N/A')
            ip = getattr(eip, 'public_ip_address', 'N/A')
            create_time = getattr(eip, 'create_time', 'N/A')[:19] if getattr(eip, 'create_time', None) else 'N/A'
            idle_days = calculate_idle_days(create_time)
            idle_days_str = f"{idle_days} 天" if idle_days >= 0 else "未知"
            
            print(f"\n  [{i}] EIP: {ip}")
            print(f"      ID: {eip_id}")
            print(f"      创建时间：{create_time}")
            print(f"      闲置时长：{idle_days_str}")
            print(f"      建议操作：{'立即释放' if idle_days > 30 else '确认用途后决定'}")
    
    print("\n" + "=" * 120)
    print("📝 报告生成时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 120 + "\n")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='查找闲置 EIP 并生成分析报告')
    parser.add_argument('--region', type=str, default=None, help='华为云区域 ID (默认从环境变量读取)')
    parser.add_argument('--min-idle-days', type=int, default=0, help='最小闲置天数阈值 (默认：0，即所有未绑定 EIP)')
    args = parser.parse_args()
    
    # 获取凭证
    credentials, region_id = get_credentials()
    
    # 命令行参数优先于环境变量
    if args.region:
        region_id = args.region
    
    min_idle_days = args.min_idle_days
    
    # 创建客户端
    client = EipClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EipRegion.value_of(region_id)) \
        .build()
    
    print(f"🔍 正在查询区域 {region_id} 的 EIP... (闲置阈值：≥{min_idle_days}天)")
    
    # 查询所有 EIP
    all_eips = list_eips(client, region_id)
    
    if not all_eips:
        print("ℹ️  未找到任何 EIP")
        return
    
    # 打印所有 EIP
    print_eip_table(all_eips, "所有 EIP", min_idle_days)
    
    # 找出闲置 EIP（根据阈值过滤）
    idle_eips = find_idle_eips(all_eips, min_idle_days)
    
    if not idle_eips:
        print(f"✅ 未发现闲置超过 {min_idle_days} 天的 EIP，所有 EIP 都在使用中或闲置时间不足")
        return
    
    # 打印闲置 EIP
    print_eip_table(idle_eips, "⚠️  闲置 EIP 列表", min_idle_days)
    
    # 生成分析报告
    generate_report(all_eips, idle_eips, min_idle_days)
    
    # 输出 JSON 格式报告（可选）
    if '--json' in sys.argv:
        report = {
            "region": region_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_eips": len(all_eips),
                "idle_eips": len(idle_eips),
                "idle_rate": len(idle_eips) / len(all_eips) * 100 if all_eips else 0,
                "estimated_monthly_cost_cny": len(idle_eips) * 0.02 * 24 * 30
            },
            "idle_eip_details": [
                {
                    "eip_id": getattr(eip, 'id', 'N/A'),
                    "public_ip": getattr(eip, 'public_ip_address', 'N/A'),
                    "bandwidth_id": getattr(eip, 'bandwidth_id', 'N/A'),
                    "create_time": getattr(eip, 'create_time', 'N/A'),
                    "idle_days": calculate_idle_days(getattr(eip, 'create_time', ''))
                }
                for eip in idle_eips
            ],
            "recommendations": [
                "确认闲置 EIP 的业务用途，联系负责人核实",
                "对确认不用的 EIP，手动在控制台释放",
                "对可能需要但暂时闲置的 EIP，可调整为最低带宽（1 Mbps）",
                "定期审计，建议每周运行此脚本",
                "为 EIP 添加用途标签，便于后续识别和管理"
            ]
        }
        print("\n📄 JSON 报告:")
        print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
