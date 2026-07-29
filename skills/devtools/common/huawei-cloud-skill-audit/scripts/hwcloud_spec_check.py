#!/usr/bin/env python3
"""华为云 SKILL.md 规范检查器 — 检查 frontmatter 字段、正文章节结构、文件大小等"""

import re
import sys
from pathlib import Path

# ── Frontmatter 必需字段定义 ──
REQUIRED_FIELDS = {
    "name": {"type": "string", "desc": "技能唯一标识，与目录名一致"},
    "description": {"type": "string", "desc": "技能描述，包含功能概要和触发词"},
    "tags": {"type": "list", "desc": "标签列表，用于搜索和分类，不大于5个"},
}

# ── Frontmatter 推荐字段定义（缺失仅 warning，不阻塞） ──
RECOMMENDED_FIELDS = {
    "version": {"type": "string", "desc": "语义化版本号"},
}

# ── 正文章节结构定义 ──
# (序号, 章节名, 必需性: required/conditional/recommended)
SECTION_STRUCTURE = [
    (1, "概述", "required"),
    (2, "前置条件", "required"),
    (3, "KooCLI命令格式标准", "conditional"),
    (4, "场景路由", "conditional"),
    (5, "核心命令", "required"),
    (6, "参数确认", "required"),
    (7, "输出格式", "recommended"),
    (8, "验证方法", "recommended"),
    (9, "最佳实践", "recommended"),
    (10, "参考文档", "required"),
    (11, "注意事项", "recommended"),
]

# 章节匹配别名（支持中英文混合标题）
SECTION_ALIASES = {
    "概述": ["概述", "Overview", "overview", "Introduction", "简介", "核心定位", "适用场景"],
    "前置条件": ["前置条件", "Prerequisites", "prerequisites", "前提条件", "Requirements", "Setup", "安装配置", "安装"],
    "KooCLI命令格式标准": ["KooCLI命令格式", "KooCLI", "命令格式标准", "CLI命令格式"],
    "场景路由": ["场景路由", "工作流", "Scenario", "Workflow", "场景"],
    "核心命令": ["核心命令", "Core Commands", "核心操作", "命令", "Usage", "使用方法", "How to Use",
               "Command Reference", "命令速查", "常用命令", "Commands", "IMAP Commands",
               "SMTP Commands", "执行流程", "完整执行流程"],
    "参数确认": ["参数确认", "Parameters", "参数配置", "参数", "Configuration", "配置",
               "项目参数", "Global Flags", "环境变量", "Environment Variables", "配置说明"],
    "输出格式": ["输出格式", "Output Format", "输出", "Output Formats"],
    "验证方法": ["验证方法", "Verification", "验证", "Verification Checklist"],
    "最佳实践": ["最佳实践", "Best Practices", "Best Practice"],
    "参考文档": ["参考文档", "References", "参考", "Reference", "See Also", "Related",
               "延伸阅读", "Related Skills", "Fix strategies", "Troubleshooting"],
    "注意事项": ["注意事项", "Notes", "Caveats", "注意", "Pitfalls", "Gotchas", "常见问题"],
}

# ── 文件大小限制 ──
MAX_SKILL_MD_LINES = 500
MAX_SKILL_DIR_SIZE_MB = 5


def parse_frontmatter(content: str):
    """解析 YAML frontmatter，返回 (metadata_dict, body_str, parse_error)"""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m:
        return {}, content, True

    fm_text = m.group(1)
    body = content[m.end():]
    meta = {}
    parse_error = False

    try:
        # 简易 YAML 解析（不依赖 PyYAML）
        current_key = None
        in_multiline = False
        multiline_value = []

        for line in fm_text.split('\n'):
            stripped = line.strip()

            # 多行值结束
            if in_multiline and not line.startswith(' ') and stripped:
                if current_key:
                    meta[current_key] = ' '.join(multiline_value).strip()
                in_multiline = False
                multiline_value = []

            # key: value
            kv_match = re.match(r'^(\w[\w-]*):\s*(.*)', stripped)
            if kv_match and not in_multiline:
                key = kv_match.group(1)
                value = kv_match.group(2).strip()
                current_key = key

                if value == '|' or value == '>':
                    in_multiline = True
                    multiline_value = []
                elif value.startswith('[') and value.endswith(']'):
                    # 列表内联格式: [a, b, c]
                    items = [x.strip().strip('"').strip("'") for x in value[1:-1].split(',')]
                    meta[key] = [x for x in items if x]
                elif value:
                    meta[key] = value.strip('"').strip("'")
                else:
                    # 可能是下一行列表
                    meta[key] = []
                continue

            # 列表项: - item
            if stripped.startswith('- ') and current_key:
                item = stripped[2:].strip().strip('"').strip("'")
                if isinstance(meta.get(current_key), list):
                    meta[current_key].append(item)
                else:
                    meta[current_key] = [item]
                continue

            # 多行值续行
            if in_multiline and line.startswith(' '):
                multiline_value.append(stripped)
                continue

    except Exception:
        parse_error = True

    return meta, body, parse_error


def check_frontmatter(skill_dir: Path, meta: dict, parse_error: bool) -> list:
    """检查 frontmatter 规范，返回 issue 列表"""
    issues = []
    skill_name = skill_dir.name

    # YAML 解析失败
    if parse_error:
        issues.append({
            "skill": skill_name, "source": "hwcloud-spec", "rule": "frontmatter.parse-error",
            "severity": "error", "category": "frontmatter.parse-error",
            "message": "SKILL.md YAML frontmatter 解析失败，请检查 --- 包裹内的 YAML 语法"
        })
        return issues

    # 必需字段检查
    for field, spec in REQUIRED_FIELDS.items():
        if field not in meta:
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": f"frontmatter.missing.{field}",
                "severity": "error", "category": f"frontmatter.missing.{field}",
                "message": f"缺少必需字段 '{field}'（{spec['desc']}）"
            })
            continue

        value = meta[field]

        # 类型检查
        if spec["type"] == "list":
            if not isinstance(value, list):
                issues.append({
                    "skill": skill_name, "source": "hwcloud-spec",
                    "rule": f"frontmatter.type.{field}",
                    "severity": "error", "category": f"frontmatter.type.{field}",
                    "message": f"字段 '{field}' 应为列表类型，当前为: {type(value).__name__}"
                })
            elif field == "tags" and len(value) > 5:
                issues.append({
                    "skill": skill_name, "source": "hwcloud-spec",
                    "rule": "frontmatter.tags-too-many",
                    "severity": "warning", "category": "frontmatter.tags-too-many",
                    "message": f"标签数量 {len(value)} 超过上限5个，建议精简"
                })

        elif spec["type"] == "string":
            if isinstance(value, list):
                issues.append({
                    "skill": skill_name, "source": "hwcloud-spec",
                    "rule": f"frontmatter.type.{field}",
                    "severity": "error", "category": f"frontmatter.type.{field}",
                    "message": f"字段 '{field}' 应为字符串类型，当前为列表"
                })

    # 推荐字段检查（缺失仅 warning）
    for field, spec in RECOMMENDED_FIELDS.items():
        if field not in meta:
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": f"frontmatter.missing.{field}",
                "severity": "warning", "category": f"frontmatter.missing.{field}",
                "message": f"缺少推荐字段 '{field}'（{spec['desc']}）"
            })
            continue

        value = meta[field]

        # 类型检查
        if spec["type"] == "string" and isinstance(value, list):
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": f"frontmatter.type.{field}",
                "severity": "warning", "category": f"frontmatter.type.{field}",
                "message": f"字段 '{field}' 应为字符串类型，当前为列表"
            })

    # name 与目录名一致性
    if "name" in meta and meta["name"] != skill_name:
        issues.append({
            "skill": skill_name, "source": "hwcloud-spec",
            "rule": "frontmatter.name-mismatch",
            "severity": "error", "category": "frontmatter.name-mismatch",
            "message": f"name 字段 '{meta['name']}' 与目录名 '{skill_name}' 不一致"
        })

    # version 语义化版本号检查
    if "version" in meta and isinstance(meta["version"], str):
        if not re.match(r'^\d+\.\d+\.\d+', meta["version"]):
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": "frontmatter.version-format",
                "severity": "warning", "category": "frontmatter.version-format",
                "message": f"version '{meta['version']}' 不符合语义化版本号格式 (如 2.0.0)"
            })

    # description 质量检查
    if "description" in meta and isinstance(meta["description"], str):
        desc = meta["description"]
        if len(desc) < 20:
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": "frontmatter.description-too-short",
                "severity": "warning", "category": "frontmatter.description-too-short",
                "message": f"description 过短（{len(desc)}字符），应包含功能概要、技术基础、适用场景、触发词"
            })

    return issues


def check_sections(skill_dir: Path, body: str) -> list:
    """检查正文章节结构，返回 issue 列表"""
    issues = []
    skill_name = skill_dir.name

    # 提取所有 ## 标题
    headings = []
    for m in re.finditer(r'^#{1,3}\s+(.+)$', body, re.MULTILINE):
        headings.append(m.group(1).strip())

    # 检查必需章节
    missing_required = []
    missing_recommended = []

    for idx, section_name, required_level in SECTION_STRUCTURE:
        aliases = SECTION_ALIASES.get(section_name, [section_name])
        found = False
        for heading in headings:
            for alias in aliases:
                if alias in heading:
                    found = True
                    break
            if found:
                break

        if not found:
            if required_level == "required":
                missing_required.append(section_name)
            elif required_level == "recommended":
                missing_recommended.append(section_name)

    for s in missing_required:
        issues.append({
            "skill": skill_name, "source": "hwcloud-spec",
            "rule": "section.missing-required",
            "severity": "error", "category": "section.missing-required",
            "message": f"缺少必需章节: '{s}'"
        })

    for s in missing_recommended:
        issues.append({
            "skill": skill_name, "source": "hwcloud-spec",
            "rule": "section.missing-recommended",
            "severity": "warning", "category": "section.missing-recommended",
            "message": f"缺少推荐章节: '{s}'"
        })

    return issues


def check_file_size(skill_dir: Path) -> list:
    """检查文件大小限制，返回 issue 列表"""
    issues = []
    skill_name = skill_dir.name

    # SKILL.md 行数
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        lines = skill_md.read_text(encoding="utf-8", errors="replace").count('\n') + 1
        if lines > MAX_SKILL_MD_LINES:
            issues.append({
                "skill": skill_name, "source": "hwcloud-spec",
                "rule": "size.skill-md-lines",
                "severity": "warning", "category": "size.skill-md-lines",
                "message": f"SKILL.md 共 {lines} 行，超过建议上限 {MAX_SKILL_MD_LINES} 行"
            })

    # 目录总大小
    total_size = sum(f.stat().st_size for f in skill_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    if size_mb > MAX_SKILL_DIR_SIZE_MB:
        issues.append({
            "skill": skill_name, "source": "hwcloud-spec",
            "rule": "size.dir-too-large",
            "severity": "warning", "category": "size.dir-too-large",
            "message": f"技能目录总大小 {size_mb:.1f}MB，超过建议上限 {MAX_SKILL_DIR_SIZE_MB}MB"
        })

    return issues


def run_hwcloud_spec_check(skill_dir: Path) -> dict:
    """对单个技能目录运行华为云规范检查，返回结果 dict"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"skill_name": skill_dir.name, "issues": [{
            "skill": skill_dir.name, "source": "hwcloud-spec", "rule": "file.missing",
            "severity": "error", "category": "file.missing",
            "message": "SKILL.md 文件不存在"
        }]}

    content = skill_md.read_text(encoding="utf-8", errors="replace")
    meta, body, parse_error = parse_frontmatter(content)

    issues = []
    issues.extend(check_frontmatter(skill_dir, meta, parse_error))
    if not parse_error:
        issues.extend(check_sections(skill_dir, body))
    issues.extend(check_file_size(skill_dir))

    return {"skill_name": skill_dir.name, "issues": issues}
