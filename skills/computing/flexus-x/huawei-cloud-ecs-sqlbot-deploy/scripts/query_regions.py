#!/usr/bin/env python3
"""
华为云SQLBot部署 - 区域规格查询工具
用于查询支持的区域和X实例类型
"""

import sys
import os

# 导入配置模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import REGION_NAMES, REGION_FLAVOR_PRIORITY

def show_all_regions():
    """显示所有支持的区域"""
    print("\n" + "=" * 80)
    print("📋 华为云SQLBot部署 - 支持的区域和X实例类型")
    print("=" * 80)
    print("| Region 代码 | 区域名称 | 支持的X实例类型（优先级顺序） |")
    print("|-------------|----------|------------------------------|")
    
    for region_code, types in REGION_FLAVOR_PRIORITY.items():
        if region_code == "default":
            continue
        region_name = REGION_NAMES.get(region_code, region_code)
        print(f"| {region_code:12} | {region_name:20} | {', '.join(types):28} |")
    
    print("\n" + "=" * 80)
    print("📌 智能规格选择功能:")
    print("  ✅ 优先级选择: 脚本根据区域自动选择最合适的X实例类型")
    print("  ✅ 自动降级: 如果首选规格售罄，自动尝试下一个选项")
    print("  ✅ 多重重试: 最多尝试3个不同的规格直到成功")
    print("  ✅ 4U8G兼容: 始终选择4核8GB内存配置")
    print("  ✅ 向后兼容: 用户仍可手动指定 --flavor 参数")
    print("=" * 80)

def show_region_detail(region_code):
    """显示特定区域的详细信息"""
    if region_code not in REGION_FLAVOR_PRIORITY and region_code != "default":
        print(f"❌ 错误: 不支持的区域代码 '{region_code}'")
        print(f"使用 --list 查看所有支持的区域")
        return
    
    region_name = REGION_NAMES.get(region_code, region_code)
    types = REGION_FLAVOR_PRIORITY.get(region_code, REGION_FLAVOR_PRIORITY["default"])
    
    print(f"\n📋 区域详情: {region_code}")
    print("=" * 50)
    print(f"区域名称: {region_name}")
    print(f"Region代码: {region_code}")
    print(f"支持的X实例类型: {', '.join(types)}")
    print(f"优先级顺序: {' > '.join(types)}")
    print("\n📝 部署命令示例:")
    print(f"python3 deploy_sqlbot.py \\")
    print(f"  --ak YOUR_AK \\")
    print(f"  --sk YOUR_SK \\")
    print(f"  --project-id YOUR_PROJECT_ID \\")
    print(f"  --region {region_code} \\")
    print(f"  --notify-user-id YOUR_FEISHU_ID")
    print("\n💡 提示:")
    print(f"  1. 脚本会优先尝试 {types[0]} 系列规格")
    print(f"  2. 如果售罄，会自动尝试: {', '.join(types[1:])}")
    print(f"  3. 最多尝试 {min(3, len(types))} 个不同的规格")
    print("=" * 50)

def show_region_suggestions():
    """显示区域选择建议"""
    print("\n📊 区域选择建议")
    print("=" * 50)
    print("🇨🇳 中国大陆地区 (推荐):")
    print("  cn-north-4   华北-北京四   (x1, x1e, x1i, x2e)")
    print("  cn-east-3    华东-上海一   (x1, x1e, x1i, x2e)")
    print("  cn-south-1   华南-广州     (x1, x1e, x1i, x2e)")
    print("  cn-southwest-2 西南-贵阳一 (x1, x1e, x1i, x2e)")
    print("\n🌏 亚太地区 (推荐):")
    print("  ap-southeast-3 亚太-新加坡 (x1, x1e, x2e)")
    print("  ap-southeast-1 中国-香港   (x1, x2e)")
    print("  ap-southeast-2 亚太-曼谷   (x1, x2e)")
    print("\n🌍 其他地区:")
    print("  根据用户地理位置选择最近区域")
    print("  优先选择支持多种X实例类型的区域")
    print("  避免选择只支持单一X实例类型的区域")
    print("=" * 50)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='华为云SQLBot部署 - 区域规格查询工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  1. 查看所有支持的区域:
     python3 query_regions.py --list
  
  2. 查看特定区域详情:
     python3 query_regions.py --region cn-north-4
  
  3. 查看区域选择建议:
     python3 query_regions.py --suggest
  
  4. 查看帮助:
     python3 query_regions.py --help

支持的查询方式：
  --list, -l     显示所有支持的区域和规格
  --region REGION  显示特定区域的详细信息
  --suggest, -s    显示区域选择建议
  --help, -h       显示帮助信息
        """
    )
    
    parser.add_argument('--list', '-l', action='store_true', help='显示所有支持的区域和规格')
    parser.add_argument('--region', type=str, help='显示特定区域的详细信息')
    parser.add_argument('--suggest', '-s', action='store_true', help='显示区域选择建议')
    
    args = parser.parse_args()
    
    if args.list:
        show_all_regions()
    elif args.region:
        show_region_detail(args.region)
    elif args.suggest:
        show_region_suggestions()
    else:
        # 默认显示所有区域
        show_all_regions()
        print("\n📌 更多查询选项:")
        print("  python3 query_regions.py --list           # 显示所有区域")
        print("  python3 query_regions.py --region cn-north-4  # 显示特定区域详情")
        print("  python3 query_regions.py --suggest       # 显示区域选择建议")
        print("  python3 query_regions.py --help          # 显示帮助信息")

if __name__ == "__main__":
    main()