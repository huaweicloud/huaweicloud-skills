import json
import os
import re
from datetime import datetime, timedelta
from regions import regions as region_list
from config import projectPath


def unique_history(history):
    h = map(
        lambda item: {
            "resource_id": extract_id(item),
            "region_id": item.get("region"),
            "metric": item.get("metric_expression_ch", "").split(" 原始值")[0]
        },
        history
    )
    s = set()
    f = []
    for item in list(h):
        if item["resource_id"] not in s:
            if len(item["resource_id"]) == 36:
                s.add(item["resource_id"])
                metrics = [item["metric"]] if item["metric"] else []
                f.append({
                    "resource_id": item["resource_id"],
                    "region_id": item["region_id"],
                    "alarm_num": 1,
                    "metrics": metrics
                })
        else:
            for i in f:
                if i["resource_id"] == item["resource_id"]:
                    i["alarm_num"] += 1
                    if item["metric"] and item["metric"] not in i["metrics"]:
                        i["metrics"].append(item["metric"])
                    break

    return f


def unique_history1(history):
    h = map(
        lambda item: {
            "cluster_id": extract_cluster_id_and_node_ip(item.get("alarm_inst_id")).get("cluster_id", ""),
            "node_ip": extract_cluster_id_and_node_ip(item.get("alarm_inst_id")).get("node_ip", ""),
            "region_id": item.get("region"),
            "metric": item.get("metric_expression_ch", "").split(" 原始值")[0]
        },
        history
    )
    s = set()
    f = []
    for item in list(h):
        key = (item["cluster_id"], item["node_ip"])
        if key not in s:
            if item["cluster_id"] or item["node_ip"]:
                s.add(key)
                metrics = [item["metric"]] if item["metric"] else []
                f.append({
                    "cluster_id": item["cluster_id"],
                    "node_ip": item["node_ip"],
                    "region_id": item["region_id"],
                    "alarm_num": 1,
                    "metrics": metrics
                })
        else:
            for i in f:
                if i["cluster_id"] == item["cluster_id"] and i["node_ip"] == item["node_ip"]:
                    i["alarm_num"] += 1
                    if item["metric"] and item["metric"] not in i["metrics"]:
                        i["metrics"].append(item["metric"])
                    break

    return f


def merge_metrics(f_data):
    """
    将f数据中每项的metrics合并为不重复的metric列表
    
    参数:
        f_data: unique_history函数返回的数据列表
    
    返回:
        合并后的metric列表（不重复）
    """
    all_metrics = []
    for item in f_data:
        metrics = item.get("metrics", [])
        all_metrics.extend(metrics)
    return list(dict.fromkeys(m for m in all_metrics if m))


def extract_id(item):
    resource = item.get("alarm_resource") or {}
    str_val = resource.get("resourceId")
    if str_val and len(str_val) == 36:
        return str_val

    str_val = extract_id_if_valid_length(resource.get("dimValue"))
    if str_val and len(str_val) == 36:
        return str_val
    return ""


def extract_id_if_valid_length(text):
    if not text or not isinstance(text, str):
        return ""

    separators = ['|', ',']
    parts = [text]

    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts

    for raw_part in parts:
        clean_part = raw_part.strip()
        if not clean_part:
            continue

        if '=' not in clean_part:
            continue

        key, value = clean_part.split('=', 1)

        if not re.search(r'(id|instance)', key, re.IGNORECASE):
            continue

        if len(value) == 36:
            return value

    return ""


def is_within_two_hours(time):
    time = int(time / 1000)
    ago = int((datetime.now() - timedelta(hours=2)).timestamp())
    return time >= ago

def set_json_dict(file_path, data=None, set_attrs=None):
    """
    设置JSON文件的字典数据
    
    参数:
        file_path: JSON文件路径
        data: 可选，字典类型，用于完全覆盖原文件内容
        set_attrs: 可选，字典类型，用于设置/更新现有字典的键值对
    
    返回:
        bool: 操作成功返回True，失败返回False
    
    用法示例:
        # 读取文件（不修改）
        set_json_dict("test.json")
        
        # 设置属性（文件不存在或为空时，以空字典为基础）
        set_json_dict("test.json", set_attrs={"key1": "value1"})
        
        # 覆盖整个对象
        set_json_dict("test.json", data={"new": "object"})
    """
    if data is not None and not isinstance(data, dict):
        print(f"错误: data参数必须是字典类型")
        return False
    
    if set_attrs is not None and not isinstance(set_attrs, dict):
        print(f"错误: set_attrs参数必须是字典类型")
        return False
    
    if data is None and set_attrs is None:
        return os.path.exists(file_path)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    result = json.loads(content)
                else:
                    result = {}
        except Exception:
            result = {}
    else:
        result = {}
    
    if data is not None:
        result = data
    elif set_attrs is not None:
        if not isinstance(result, dict):
            result = {}
        result.update(set_attrs)
    
    return write_data_to_json(result, file_path, overwrite=True)

def is_chinese(s):
    # \u4e00-\u9fa5 是基本汉字区块
    # 如果还需要生僻字，可以扩大范围或使用更完整的中文正则
    pattern = re.compile(r'[\u4e00-\u9fa5]')
    return bool(pattern.search(s))

def get_right_region(region):
  if is_chinese(region):
    for item in region_list:
      if item.get("name") == region:
        return item.get("id")
  else:
    return region
  raise TypeError("region不存在")


def get_chinese_region(region):
    for item in region_list:
        if item.get("id") == region:
            return item.get("name")
    return region

def extract_cluster_id_and_node_ip(text):
    """
    从文本中提取clusterId和nodeIP
    
    参数:
        text: 包含clusterId和nodeIP的文本，格式如 "clusterId=xxx|nodeIP=xxx"
    
    返回:
        dict: 包含cluster_id和node_ip的字典
    """
    result = {"cluster_id": "", "node_ip": ""}
    if not text or not isinstance(text, str):
        return result
    
    parts = text.split('|')
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            if key == "clusterId" or key == "cluster_id":
                result["cluster_id"] = value.strip()
            elif key == "nodeIP":
                result["node_ip"] = value.strip()
    
    return result


def get_service_alarms(service: str) -> list:
    """
    读取alarm_result.json文件，获取指定service的告警列表
    :param service: 服务类型（如ecs, rds等）
    :return: 过滤后的告警列表
    """
    file_path = projectPath + '/alarm_result.json'
    
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    
    alarm_history = data.get("alarm", {}).get("alarm_history", [])
    
    if not service:
        return alarm_history
    
    return [alarm for alarm in alarm_history if alarm.get("service", "").lower() == service.lower()]


def write_data_to_json(data, file_path, overwrite=True):
    """
    将数据写入指定目录的JSON文件
    
    参数:
    data: 要写入的数据（可以是字典、列表或其他可JSON序列化的对象）
    file_path: 目标JSON文件的完整路径
    overwrite: 布尔值，如果为True且文件存在，则覆盖文件；如果为False且文件存在，则不覆盖
    
    返回:
    bool: 写入成功返回True，失败返回False
    """
    try:
        # 确保目标目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 检查文件是否存在以及是否需要覆盖
        file_exists = os.path.exists(file_path)
        
        if file_exists and not overwrite:
            print(f"文件已存在且配置为不覆盖: {file_path}")
            return False
        
        # 打开文件并写入数据
        # 'w'模式会覆盖已存在的文件，如果文件不存在则创建新文件
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        
        operation = "覆盖" if file_exists else "创建"
        print(f"数据已成功{operation}到: {file_path}")
        return True
        
    except OSError as e:
        print(f"文件写入错误: {e}")
        return False
    except (TypeError, ValueError) as e:
        print(f"数据序列化错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False


