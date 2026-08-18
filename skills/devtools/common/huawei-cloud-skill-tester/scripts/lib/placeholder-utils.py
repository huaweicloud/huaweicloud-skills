#!/usr/bin/env python3
# placeholder-utils.py — 共享占位符替换逻辑 (phase-3 生成 / phase-4 执行兜底共用)
# 单一维护点: 修改占位符规则只需改这里, 避免 phase-3/4 两处不同步。
#
# 用法: 在 bash heredoc python 脚本中
#   exec(open("<SCRIPT_DIR>/lib/placeholder-utils.py", encoding='utf-8').read())
# 之后即可调用 replace_placeholders(text, skill_dir)
import re
import os

_REGION = os.environ.get('HUAWEI_REGION', 'cn-north-4')


def replace_placeholders(text, skill_dir):
    """替换命令中的占位符为真实值, 返回清理后的命令字符串。

    规则:
    - --cli-region={region|cli_region|location} → --cli-region=<region值> (保留前缀)
    - 裸 {region}/{cli_region}/{location} → <region值>
    - /path/to/xxx、<your-skill>、./xxx-skill → skill_dir
    - {id}/{instance_id}/... → test-placeholder
    - [--key=value ...]/[options]/[...] 模板残渣 → 删除
    - 空 --cli-region=(后无值) → 删除; 有值的绝不删
    - 压缩连续空格
    """
    # ① 先整体处理带 --cli-region= 前缀的占位符(保留前缀!)
    text = re.sub(r'--cli-region=\{(?:region|cli_region|location)\}', '--cli-region=' + _REGION, text)
    # ② 再处理裸 region 占位符(非 cli-region 上下文)
    text = re.sub(r'\{region\}|\{cli_region\}|\{location\}', _REGION, text)
    text = re.sub(r'<region>|<cli-region>|<location>', _REGION, text)
    # 明文路径占位符 → 被测 skill 真实目录
    text = re.sub(r'/path/to/[^\s"\']*', skill_dir, text)
    text = re.sub(r'<skill[-_]?path>|<your-skill>|/your-skill[^\s"\']*|/target/skill[^\s"\']*|/skills-folder[^\s"\']*', skill_dir, text)
    # 相对路径占位符: ./my-skill / ./xxx-skill / ./skills/xxx 等
    text = re.sub(r'\./[^\s"\']*skill[^\s"\']*', skill_dir, text)
    text = re.sub(r'\{id\}|\{instance_id\}|\{server_id\}|\{vpc_id\}|\{subnet_id\}|\{flavor_id\}|\{image_id\}|\{config_id\}', 'test-placeholder', text)
    text = re.sub(r'<id>|<instance_id>|<server_id>|<vpc_id>|<subnet_id>|<flavor_id>|<image_id>|<config_id>', 'test-placeholder', text)
    # 清理 [--key=value ...] 等模板残渣
    text = re.sub(r'\s*\[--key=value[^\]]*\]', '', text)
    text = re.sub(r'\s*\[options\]', '', text)
    text = re.sub(r'\s*\[[^\]]*\.\.\.\s*\]', '', text)
    # 只清理"空的 --cli-region="(后面无值才删, 绝不删有值的)
    text = re.sub(r'--cli-region=\s*(?=\s|$)', '', text)
    # 压缩连续空格(清理占位符后可能留下双空格)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()
