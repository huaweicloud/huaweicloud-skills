#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_index.py - ICP备案知识库索引构建脚本（简化版）

功能：
1. 扫描kb目录下的markdown文件
2. 提取文档元信息（title, type, case_types）
3. 生成文档摘要（summary）
4. 输出 index.json

使用方法：
    python scripts/build_index.py

Author: Huawei Cloud Skills
Date: 2026-07-07
"""

import json
import yaml
import re
from pathlib import Path
from datetime import datetime


def parse_frontmatter(content: str) -> tuple:
    """解析YAML frontmatter"""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter, parts[2].strip()
            except yaml.YAMLError:
                return {}, content
    return {}, content


def extract_title(body: str, default: str) -> str:
    """提取文档标题（第一个#开头的行）"""
    match = re.search(r'^#+\s+(.+)$', body, re.MULTILINE)
    return match.group(1) if match else default


def extract_case_types(frontmatter: dict, body: str) -> list:
    """提取案例类型"""
    if 'case_types' in frontmatter:
        return frontmatter['case_types']
    # 尝试从正文中提取
    matches = re.findall(r'`([^`]+)`', body)
    return [m for m in matches[:5] if len(m) < 20]


def generate_summary(body: str, max_length: int = 200) -> str:
    """生成文档摘要"""
    # 移除代码块（包括内部的YAML）
    body = re.sub(r'```[\s\S]*?```', '', body)
    body = re.sub(r'`[^`]+`', '', body)
    # 移除标题行
    lines = [l.strip() for l in body.split('\n') if l.strip() and not l.strip().startswith('#')]
    # 移除引用行
    lines = [l for l in lines if not l.startswith('>')]
    # 移除链接语法
    text = ' '.join(lines)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    # 截断
    if len(text) > max_length:
        text = text[:max_length] + '...'
    return text if text else '无正文内容'


def scan_kb_directory(kb_dir: Path) -> list:
    """扫描知识库目录"""
    docs = []

    for subdir in ['faq', 'procedures', 'topics', 'cases']:
        subdir_path = kb_dir / subdir
        if subdir_path.exists():
            for md_file in subdir_path.glob('*.md'):
                docs.append(process_markdown(md_file, subdir))

    # 处理根目录下的markdown文件
    for md_file in kb_dir.glob('*.md'):
        if md_file.name not in ['index.json']:
            docs.append(process_markdown(md_file, 'root'))

    return docs


def process_markdown(md_file: Path, doc_type: str) -> dict:
    """处理单个markdown文件"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, body = parse_frontmatter(content)

    title = frontmatter.get('title', '') or extract_title(body, md_file.stem)
    type_val = frontmatter.get('type', doc_type)
    case_types = extract_case_types(frontmatter, body)
    summary = frontmatter.get('summary', '') or generate_summary(body)

    # 生成相对路径
    relative_path = str(md_file.relative_to(md_file.parent.parent))

    return {
        'path': relative_path.replace('\\', '/'),
        'type': type_val,
        'title': title,
        'case_types': case_types,
        'summary': summary
    }


def main():
    """主函数"""
    # 获取skill目录
    skill_dir = Path(__file__).parent.parent.resolve()
    kb_dir = skill_dir / 'kb'

    print(f"Scanning knowledge base: {kb_dir}")
    print("-" * 60)

    # 扫描目录
    docs = scan_kb_directory(kb_dir)

    # 生成索引
    index = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'total_docs': len(docs),
        'success_count': len(docs),
        'fail_count': 0,
        'docs': docs
    }

    # 保存index.json
    index_path = skill_dir / 'index.json'
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Generated index.json with {len(docs)} documents")
    print(f"Saved to: {index_path}")


if __name__ == '__main__':
    main()
