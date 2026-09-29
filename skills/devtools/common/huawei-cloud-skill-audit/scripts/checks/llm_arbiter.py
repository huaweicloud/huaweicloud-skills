#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 误报仲裁层(2026-09-28 试点验证 23/23 = 100% 后集成)。

职责: 检查器规则命中(经确定性降噪后剩余的语义歧义 finding)交给 LLM 做
二次判断: 「真实安全问题」还是「误报」。
- 单边决策: 仅 LLM 判 false_positive 才剔除; 判 true_positive / 缺失 /
  解析失败全部保留(宁严勿松, 不漏报)。
- 降级: 无 LLM 配置(无 key)/ 调用失败 -> 原样返回(纯规则模式), 不阻断审查。
- 配置(与 handler 共用同一套环境变量, 部署零新增):
    SKILL_AUDIT_LLM_ARBITER  (默认 1; 设 0 关闭)
    LLM_API_BASE   (默认 https://opengw.clouddeveloper.club/v1, 非敏感)
    LLM_API_KEY / HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY
    LLM_MODEL      (默认 deepseek-v4-flash-0731)
    LLM_TIMEOUT    (默认 240)
注意: 本模块不硬编码任何凭据; API key 只从环境变量读取。
"""
import json
import os
import re
import time
import urllib.request

_RULES_DIR = os.path.dirname(os.path.abspath(__file__))  # checks/ 下与规则 JSON 同目录
_RULE_META_CACHE = {}
_DEFAULT_BASE = "https://opengw.clouddeveloper.club/v1"


def _load_rule_meta():
    """懒加载规则 JSON 的 id -> description(三次全量扫描时仅首次加载)。"""
    if _RULE_META_CACHE:
        return _RULE_META_CACHE
    for fn in ("skillspector_rules.json", "runtime_security_rules.json",
               "skill_quality_rules.json"):
        try:
            with open(os.path.join(_RULES_DIR, fn), encoding="utf-8") as f:
                d = json.load(f)
            rules = d.get("rules") or d
            for r in rules:
                rid = r.get("id")
                if rid and rid not in _RULE_META_CACHE:
                    _RULE_META_CACHE[rid] = r.get("description", "")
        except Exception:
            pass
    return _RULE_META_CACHE


def _ctx_lines(path, line, width=3):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        return []
    lo = max(1, line - width)
    hi = min(len(lines), line + width)
    out = []
    for i in range(lo, hi + 1):
        marker = ">>" if i == line else "  "
        out.append(f"{marker} {i}| {lines[i-1]}")
    return out


def _build_prompt(batch, meta):
    """构造仲裁 prompt(试点验证过 23/23 的版本)。"""
    parts = [
        "你是代码安全审查仲裁员。安全扫描器的规则对华为云 skill 仓库产生了以下命中(issue)。",
        "请根据【命中行】与【上下文】判断每条是「真实安全问题」还是「误报」。",
        "",
        "判定原则:",
        "- true_positive(真实): 代码实际执行危险行为(实际读取/窃取凭据、拼接执行SQL、",
        "  递归删除系统/数据目录、运行时拉取执行不可信脚本、硬编码真凭据)。",
        "- false_positive(误报): 只是引用/检查/传参/示例/文档说明(变量名提及、检查文件是否存在、",
        "  把路径传给子进程、文档举例或故障说明、官方安装指引、错误消息文案、docstring/注释说明)。",
        "",
    ]
    for i, it in enumerate(batch, 1):
        parts.append(f"### {i}")
        parts.append(f"rule: {it.get('rule', '')}")
        parts.append(f"rule_desc: {meta.get(it.get('rule', ''), '')[:120]}")
        fname = str(it.get("file", ""))
        parts.append(f"file_type: {'code' if fname.endswith(('.py', '.sh')) else 'documentation'}")
        parts.append(f"file: {fname}")
        parts.append(f"line: {it.get('line')}")
        parts.append("context:")
        parts.extend(_ctx_lines(it.get("_path", ""), int(it.get("line") or 0)))
        parts.append("")
    parts.append('输出 JSON(只输出 JSON, 无其他文字): {"results": [{"idx": 1, "judgment": "true_positive|false_positive", "reason": "简短理由"}]}')
    return "\n".join(parts)


def _call_llm(prompt, api_base, api_key, model, timeout):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 4096,
    }
    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return (((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def _parse(content):
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    res = obj.get("results") if isinstance(obj, dict) else obj
    if not isinstance(res, list):
        return None
    out = {}
    for it in res:
        if isinstance(it, dict) and "idx" in it:
            out[int(it["idx"])] = (str(it.get("judgment") or "").strip().lower(),
                                   str(it.get("reason") or "")[:150])
    return out


def adjudicate_issues(issues, skill_dir, batch_size=8, timeout=None, log=None):
    """对 issues 做 LLM 误报仲裁, 返回 (kept, stats)。

    issues: list[dict], 每项至少含 rule/file/line(message 可选);
            file 为相对 skill_dir 的路径。
    skill_dir: 被扫 skill 根目录(用于读取命中行上下文)。
    kept: 仲裁后的保留列表(判 false_positive 的剔除, 其余全部保留)。
    stats: {"total": N, "removed": M, "skipped_reason": "..."}
    """
    stats = {"total": len(issues), "removed": 0, "skipped_reason": ""}
    if not issues:
        return issues, stats
    if os.environ.get("SKILL_AUDIT_LLM_ARBITER", "1") != "1":
        stats["skipped_reason"] = "SKILL_AUDIT_LLM_ARBITER=0"
        return issues, stats
    api_key = (os.environ.get("LLM_API_KEY")
               or os.environ.get("HERMES_CUSTOM_API_DEEPSEEK_COM_API_KEY", ""))
    if not api_key:
        stats["skipped_reason"] = "no LLM key"
        return issues, stats
    api_base = os.environ.get("LLM_API_BASE") or _DEFAULT_BASE
    model = os.environ.get("LLM_MODEL", "deepseek-v4-flash-0731")
    timeout = timeout or int(os.environ.get("LLM_TIMEOUT", "240"))
    meta = _load_rule_meta()

    # 为每条 issue 附加绝对路径(取上下文用)
    for it in issues:
        fname = str(it.get("file") or "")
        cand = os.path.join(skill_dir, fname.lstrip("/"))
        it["_path"] = cand if os.path.isfile(cand) else ""

    kept = []
    removed = []
    for si in range(0, len(issues), batch_size):
        batch = issues[si:si + batch_size]
        try:
            content = _call_llm(_build_prompt(batch, meta), api_base, api_key, model, timeout)
            verdicts = _parse(content)
        except Exception as e:
            if log:
                log.warning("[skill-audit-arbiter] LLM 调用失败, 该批保留原结论: %s", e)
            kept.extend(batch)
            continue
        if not verdicts:
            if log:
                log.warning("[skill-audit-arbiter] LLM 输出无法解析, 该批保留: %s", content[:120])
            kept.extend(batch)
            continue
        for i, it in enumerate(batch, 1):
            jud, reason = verdicts.get(i, ("", ""))
            if jud == "false_positive":
                removed.append(it)
                if log:
                    log.info("[skill-audit-arbiter] 仲裁为误报: %s:%s %s — %s",
                             it.get("file"), it.get("line"), it.get("rule"), reason)
            else:
                kept.append(it)
        time.sleep(0.5)

    stats["removed"] = len(removed)
    return kept, stats