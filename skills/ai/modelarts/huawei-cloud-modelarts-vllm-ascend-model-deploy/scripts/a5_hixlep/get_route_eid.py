import os
import sys

def ipv4_to_modified_ipv6(ipv4_addr):
    """将IPv4地址转换为修改后的IPv6格式"""
    # 将IPv4地址转换为十六进制，去掉0x前缀，填充为8位小写十六进制
    hex_parts = []
    for part in ipv4_addr.split('.'):
        hex_part = format(int(part), '02x')  # 转换为2位小写十六进制
        hex_parts.append(hex_part)
    
    # 组合成完整的IPv4十六进制表示
    ipv4_hex = ''.join(hex_parts)
    
    # 添加前缀
    prefix = "0x000000000000008000100000"
    result = prefix + ipv4_hex[2:] + '01'
    
    return result

def process_source_dest_ips(filename):
    """处理源目标IP文件并生成对应的配置"""
    
    # 检查文件是否存在
    if not os.path.exists(filename):
        raise FileNotFoundError(f"文件不存在: {filename}")
    
    # 读取文件
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # 解析数据
    ip_pairs = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            parts = line.split()
            if len(parts) >= 2:
                src_ip = parts[0]
                dest_ip = parts[1]
                ip_pairs.append((src_ip, dest_ip))
    
    # 分析数据：找出第一列重复的IP和第二列不重复的IP
    src_ip_count = {}
    dest_ip_count = {}
    
    for src_ip, dest_ip in ip_pairs:
        src_ip_count[src_ip] = src_ip_count.get(src_ip, 0) + 1
        dest_ip_count[dest_ip] = dest_ip_count.get(dest_ip, 0) + 1
    
    # 找出重复的源IP（出现次数大于1）
    duplicate_src_ips = [ip for ip, count in src_ip_count.items() if count > 1]
    
    # 找出不重复的目标IP（出现次数等于1）
    unique_dest_ips = [ip for ip, count in dest_ip_count.items() if count == 1]
    
    print(f"发现重复的源IP: {duplicate_src_ips}")
    print(f"发现唯一的目标IP: {unique_dest_ips}")
    print(f"总共处理了 {len(ip_pairs)} 个IP对")
    
    # 重新组织数据：对于每个重复的源IP，找出与之配对的唯一目标IP
    # 按照原始文件中的对应关系
    config_pairs = []
    
    # 对于每个重复的源IP
    for src_ip in duplicate_src_ips:
        # 找出所有与该源IP配对的唯一目标IP
        for pair in ip_pairs:
            if pair[0] == src_ip and pair[1] in unique_dest_ips:
                config_pairs.append((src_ip, pair[1]))

    # 按照dest_ip的大小排序
    # 将IP地址转换为元组形式以便正确排序（例如"223.223.0.122"转换为(223,223,0,122)）
    config_pairs.sort(key=lambda x: tuple(map(int, x[1].split('.'))))
    
    print(f"生成 {len(config_pairs)} 个配置对")
    
    # 按照示例的格式组织数据
    config_data = []
    
    # 生成配置
    for i, (src_ip, dest_ip) in enumerate(config_pairs):
        config_data.append(f"pair{i}_dev_id={i}")
        config_data.append(f"pair{i}_slot_id=0")
        config_data.append(f"pair{i}_chan_num=1")
        config_data.append(f"pair{i}_chan0_local_eid={ipv4_to_modified_ipv6(src_ip)}")
        config_data.append(f"pair{i}_chan0_remote_eid={ipv4_to_modified_ipv6(dest_ip)}")
        config_data.append(f"pair{i}_chan0_flag=1")
        config_data.append("")
    
    # 添加设备数量
    if config_data:
        config_data.insert(0, f"pair_device_num={len(config_pairs)}")
    
    return config_data

def save_route_config(config_data, output_filename):
    """保存路由配置文件"""
    # 确保输出目录存在
    output_dir = os.path.dirname(output_filename)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_filename, 'w') as f:
        for line in config_data:
            f.write(line + '\n')

def main():
    input_file = "/home/source_dest_ips.txt"
    output_file = "/lib/route.conf"
    
    try:
        # 处理输入文件并生成配置
        config_data = process_source_dest_ips(input_file)
        
        # 保存输出文件
        save_route_config(config_data, output_file)
        
        print(f"成功生成配置文件: {output_file}")
        print(f"共生成 {len([x for x in config_data if x.startswith('pair') and x.endswith('dev_id')])} 个设备配置")
        
        # 打印前几个配置项作为示例
        print("\n生成的配置示例:")
        for i, line in enumerate(config_data[:10]):
            print(line)
        if len(config_data) > 10:
            print("...")
            
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()