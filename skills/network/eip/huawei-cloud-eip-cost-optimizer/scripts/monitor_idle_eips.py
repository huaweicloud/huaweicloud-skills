#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闲置 EIP 监控与告警工具
基于华为云 Python SDK v2，支持：
- 定时扫描闲置 EIP
- 企业微信/钉钉 webhook 通知
- 邮件告警
- 自定义闲置阈值

Usage:
    python3 monitor_idle_eips.py --scan                    # 扫描并报告闲置 EIP
    python3 monitor_idle_eips.py --scan --wechat-webhook URL  # 发送微信通知
    python3 monitor_idle_eips.py --setup-cron              # 设置定时监控（每天 9:00）
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 颜色输出
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
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
        color_print(Colors.RED, "❌ 错误：未检测到认证信息")
        color_print(Colors.YELLOW, "请设置环境变量 HUAWEI_CLOUD_AK 和 HUAWEI_CLOUD_SK")
        sys.exit(1)
    
    credentials = BasicCredentials(ak=ak, sk=sk)
    client = EipClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EipRegion.value_of(region)) \
        .build()
    
    return client, region

def list_all_eips(client) -> List[dict]:
    """列出所有 EIP"""
    from huaweicloudsdkeip.v2 import ListPublicipsRequest
    
    try:
        request = ListPublicipsRequest()
        request.limit = 1000
        
        response = client.list_publicips(request)
        
        eips = []
        if response.publicips:
            for eip in response.publicips:
                # 解析创建时间
                created_at = getattr(eip, 'create_time', None)
                created_datetime = None
                if created_at:
                    try:
                        # 处理 ISO 格式时间戳
                        if 'T' in created_at:
                            created_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            created_datetime = datetime.strptime(created_at[:19], '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                eip_data = {
                    'id': eip.id,
                    'public_ip_address': eip.public_ip_address,
                    'status': eip.status,
                    'port_id': getattr(eip, 'port_id', None),
                    'bandwidth_size': getattr(eip, 'bandwidth_size', None),
                    'bandwidth_id': getattr(eip, 'bandwidth_id', None),
                    'created_at': created_at,
                    'created_datetime': created_datetime,
                }
                eips.append(eip_data)
        
        return eips
    
    except Exception as e:
        color_print(Colors.RED, f"查询 EIP 失败：{e}")
        return []

def identify_idle_eips(eips: List[dict], idle_days_threshold: int = 7) -> List[dict]:
    """识别闲置 EIP（未绑定且超过阈值天数）"""
    idle = []
    now = datetime.now()
    
    for eip in eips:
        port_id = eip.get('port_id')
        created_datetime = eip.get('created_datetime')
        
        # 未绑定 (port_id 为 None 或空)
        if not port_id or port_id == '':
            # 检查是否超过闲置天数阈值
            if created_datetime:
                days_since_creation = (now - created_datetime).days
                if days_since_creation >= idle_days_threshold:
                    eip['idle_days'] = days_since_creation
                    idle.append(eip)
            else:
                # 无法确定创建时间，默认视为闲置
                eip['idle_days'] = -1  # 未知
                idle.append(eip)
    
    return idle

def send_wechat_webhook(webhook_url: str, title: str, content: str, idle_eips: List[dict]) -> bool:
    """发送企业微信/钉钉 webhook 通知"""
    try:
        # 构建Markdown 消息
        markdown_content = f"## {title}\n\n"
        markdown_content += f"**扫描时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_content += f"### 📊 发现 {len(idle_eips)} 个闲置 EIP\n\n"
        
        if idle_eips:
            markdown_content += "| EIP ID | IP 地址 | 带宽 | 闲置天数 |\n"
            markdown_content += "|--------|---------|------|----------|\n"
            
            for eip in idle_eips[:10]:  # 最多显示 10 个
                eip_id = eip['id'][:8] + '...'
                ip = eip['public_ip_address']
                bw = f"{eip['bandwidth_size']} Mbps" if eip['bandwidth_size'] else 'N/A'
                idle_days = f"{eip['idle_days']} 天" if eip['idle_days'] > 0 else '未知'
                
                markdown_content += f"| {eip_id} | {ip} | {bw} | {idle_days} |\n"
            
            if len(idle_eips) > 10:
                markdown_content += f"\n... 还有 {len(idle_eips) - 10} 个闲置 EIP\n"
        
        markdown_content += f"\n{content}"
        
        # 企业微信格式
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read().decode('utf-8'))
        
        # 企业微信返回 errcode 0 表示成功
        if result.get('errcode', 0) == 0 or result.get('code', 0) == 0:
            color_print(Colors.GREEN, "✅ 微信通知发送成功")
            return True
        else:
            color_print(Colors.YELLOW, f"⚠️  微信通知返回异常：{result}")
            return False
            
    except Exception as e:
        color_print(Colors.RED, f"❌ 发送微信通知失败：{e}")
        return False

def send_email_alert(email_to: str, email_smtp: str, email_port: int, email_user: str, email_pass: str, 
                     title: str, content: str, idle_eips: List[dict]) -> bool:
    """发送邮件告警"""
    try:
        # 构建邮件内容
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .warning {{ color: #ff9800; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>📊 闲置 EIP 监控告警</h2>
            <p><strong>扫描时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="warning">发现 {len(idle_eips)} 个闲置 EIP</p>
            
            <table>
                <tr>
                    <th>EIP ID</th>
                    <th>IP 地址</th>
                    <th>带宽</th>
                    <th>状态</th>
                    <th>闲置天数</th>
                </tr>
        """
        
        for eip in idle_eips[:20]:  # 最多显示 20 个
            eip_id = eip['id'][:8] + '...'
            ip = eip['public_ip_address']
            bw = f"{eip['bandwidth_size']} Mbps" if eip['bandwidth_size'] else 'N/A'
            idle_days = f"{eip['idle_days']} 天" if eip['idle_days'] > 0 else '未知'
            
            html_content += f"""
                <tr>
                    <td>{eip_id}</td>
                    <td>{ip}</td>
                    <td>{bw}</td>
                    <td>{eip['status']}</td>
                    <td class="warning">{idle_days}</td>
                </tr>
            """
        
        html_content += f"""
            </table>
            <p><strong>建议操作</strong>:</p>
            <ul>
                <li>确认这些 EIP 是否确实不再使用</li>
                <li>如确认闲置，请及时释放以节省成本</li>
                <li>如需保留，请绑定到相应资源</li>
            </ul>
            <hr>
            <p style="color: #666; font-size: 12px;">此邮件由华为云 EIP 监控工具自动生成</p>
        </body>
        </html>
        """
        
        msg = MIMEText(html_content, 'html', 'utf-8')
        msg['Subject'] = Header(title, 'utf-8')
        msg['From'] = email_user
        msg['To'] = email_to
        
        # 发送邮件
        server = smtplib.SMTP_SSL(email_smtp, email_port)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [email_to], msg.as_string())
        server.quit()
        
        color_print(Colors.GREEN, "✅ 邮件告警发送成功")
        return True
        
    except Exception as e:
        color_print(Colors.RED, f"❌ 发送邮件告警失败：{e}")
        return False

def print_idle_eips_report(idle_eips: List[dict], region: str):
    """打印闲置 EIP 报告"""
    if not idle_eips:
        color_print(Colors.GREEN, "\n✅ 未发现闲置 EIP，所有 EIP 都在使用中")
        return
    
    print("\n" + "=" * 100)
    print(f"⚠️  闲置 EIP 监控报告 (区域：{region})")
    print("=" * 100)
    print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"发现闲置 EIP 数量：{len(idle_eips)} 个")
    print("=" * 100)
    print(f"{'EIP ID':<40} {'IP 地址':<16} {'带宽':<10} {'状态':<10} {'闲置天数':<10} {'创建时间'}")
    print("-" * 100)
    
    for eip in idle_eips:
        eip_id = eip.get('id', 'N/A')[:38]
        ip = eip.get('public_ip_address', 'N/A')
        bw_size = eip.get('bandwidth_size', 'N/A')
        status = eip.get('status', 'UNKNOWN')
        idle_days = f"{eip.get('idle_days', 'N/A')} 天" if eip.get('idle_days', -1) > 0 else "未知"
        created_at = eip.get('created_at', 'N/A')
        if created_at and created_at != 'N/A':
            created_at = created_at.replace('T', ' ').split('.')[0][:19]
        
        bw_display = f"{bw_size} Mbps" if bw_size else "N/A"
        
        print(f"{eip_id:<40} {ip:<16} {bw_display:<10} {status:<10} {idle_days:<10} {created_at}")
    
    print("-" * 100)
    
    # 估算成本浪费
    total_bandwidth = sum(eip.get('bandwidth_size', 0) or 0 for eip in idle_eips)
    color_print(Colors.YELLOW, f"\n💰 估算带宽资源浪费：{total_bandwidth} Mbps")
    color_print(Colors.RED, f"⚠️  建议及时释放或绑定这些闲置 EIP 以节省成本")
    print("=" * 100)

def setup_cron_job(webhook_url: Optional[str] = None, email: Optional[str] = None):
    """设置定时监控任务"""
    color_print(Colors.BLUE, "\n📅 设置定时监控任务...")
    
    # 生成 cron 命令
    script_path = os.path.abspath(__file__)
    cron_command = f"0 9 * * * cd {os.path.dirname(script_path)} && python3 {script_path} --scan"
    
    if webhook_url:
        cron_command += f" --wechat-webhook '{webhook_url}'"
    if email:
        cron_command += f" --email '{email}'"
    
    color_print(Colors.YELLOW, "\n📋 请手动添加以下 cron 任务：")
    print(f"\n{cron_command}\n")
    
    color_print(Colors.BLUE, "或者运行以下命令自动添加：")
    print(f"\n(crontab -l 2>/dev/null; echo '{cron_command}') | crontab -\n")
    
    # 尝试自动添加
    try:
        import subprocess
        result = subprocess.run(
            f"(crontab -l 2>/dev/null; echo '{cron_command}') | crontab -",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            color_print(Colors.GREEN, "✅ 定时任务已成功添加")
            color_print(Colors.BLUE, "📅 监控时间：每天早上 9:00 自动扫描")
        else:
            color_print(Colors.YELLOW, f"⚠️  自动添加失败：{result.stderr}")
            color_print(Colors.BLUE, "请手动执行上面的 crontab 命令")
    except Exception as e:
        color_print(Colors.YELLOW, f"⚠️  自动添加失败：{e}")
        color_print(Colors.BLUE, "请手动执行 crontab -e 添加上述任务")

def main():
    parser = argparse.ArgumentParser(description='闲置 EIP 监控与告警工具')
    parser.add_argument('--scan', action='store_true', help='扫描闲置 EIP')
    parser.add_argument('--idle-days', type=int, default=7, help='闲置天数阈值（默认：7 天）')
    parser.add_argument('--wechat-webhook', type=str, help='企业微信/钉钉 webhook URL')
    parser.add_argument('--email', type=str, help='告警邮箱地址')
    parser.add_argument('--email-smtp', type=str, default='smtp.163.com', help='SMTP 服务器（默认：smtp.163.com）')
    parser.add_argument('--email-port', type=int, default=465, help='SMTP 端口（默认：465）')
    parser.add_argument('--email-user', type=str, help='SMTP 登录用户名')
    parser.add_argument('--email-pass', type=str, help='SMTP 登录密码/授权码')
    parser.add_argument('--setup-cron', action='store_true', help='设置定时监控任务')
    
    args = parser.parse_args()
    
    # 设置定时任务模式
    if args.setup_cron:
        setup_cron_job(args.wechat_webhook, args.email)
        return
    
    # 扫描模式
    if not args.scan:
        parser.print_help()
        print("\n错误：请指定操作模式 (--scan / --setup-cron)")
        sys.exit(1)
    
    # 创建客户端
    client, region = get_client()
    
    color_print(Colors.BLUE, f"🔍 正在扫描区域 {region} 的闲置 EIP...")
    
    # 查询所有 EIP
    all_eips = list_all_eips(client)
    
    if not all_eips:
        color_print(Colors.YELLOW, "ℹ️  未找到任何 EIP")
        return
    
    # 识别闲置 EIP
    idle_eips = identify_idle_eips(all_eips, args.idle_days)
    
    # 打印报告
    print_idle_eips_report(idle_eips, region)
    
    # 发送告警通知
    if idle_eips:
        title = f"⚠️  闲置 EIP 告警 - 发现 {len(idle_eips)} 个闲置 EIP"
        content = "请及时处理闲置 EIP 以节省成本。"
        
        # 微信通知
        if args.wechat_webhook:
            send_wechat_webhook(args.wechat_webhook, title, content, idle_eips)
        
        # 邮件通知
        if args.email:
            if not args.email_user or not args.email_pass:
                color_print(Colors.RED, "❌ 发送邮件需要 --email-user 和 --email-pass 参数")
            else:
                send_email_alert(
                    args.email,
                    args.email_smtp,
                    args.email_port,
                    args.email_user,
                    args.email_pass,
                    title,
                    content,
                    idle_eips
                )
    else:
        color_print(Colors.GREEN, "\n✅ 所有 EIP 使用正常，无需告警")

if __name__ == '__main__':
    main()
