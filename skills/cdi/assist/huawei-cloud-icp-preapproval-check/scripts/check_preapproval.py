import argparse
import hashlib
import html
import json
import os
import platform
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

MAX_RULES_BYTES = 5 * 1024 * 1024
MAX_SCOPE_CHARS = 50_000
MIN_PYTHON = (3, 8)
SOURCE_HOST = "support.huaweicloud.com"
TEMPLATE_HOST = "res-static.hc-cdn.cn"
PROVINCES = frozenset(
    {
        "北京",
        "天津",
        "河北",
        "山西",
        "内蒙古",
        "辽宁",
        "吉林",
        "黑龙江",
        "上海",
        "江苏",
        "浙江",
        "安徽",
        "福建",
        "江西",
        "山东",
        "河南",
        "湖北",
        "湖南",
        "广东",
        "广西",
        "海南",
        "重庆",
        "四川",
        "贵州",
        "云南",
        "西藏",
        "陕西",
        "甘肃",
        "青海",
        "宁夏",
        "新疆",
    }
)
PROVINCE_SOURCES = frozenset({"未提供", "用户提供", "执照识别"})
MATCH_MODES = frozenset({"literal", "manual", "category-manual"})
IGNORED_TERM_CLASSIFICATIONS = frozenset({"description", "manual", "exclusion"})
FORWARD_EXCLUSION_MARKERS = ("不包括", "不涉及", "不提供", "不含")
SUFFIX_EXCLUSION_MARKER = "除外"
NON_CLAUSE_MARKER = "非"
NON_CLAUSE_PREFIXES = frozenset("（([{；;。.!！?？\r\n：:")
NON_CLAUSE_ENTITY_SUFFIXES = (
    "广播电台",
    "电视台",
    "出版单位",
    "新闻单位",
    "媒体",
)
CLAUSE_TERMINATORS = frozenset("；;。.!！?？\r\n")
BRACKET_PAIRS = {"（": "）", "(": ")", "【": "】", "[": "]"}
BROAD_PROVINCE_TERMS = frozenset({"药"})
NON_PROGRAM_AUDIOVISUAL_PATTERNS = (re.compile(r"视频\s*监控"),)
NATIONWIDE_NON_RULE_PHRASES = ("图书管理服务",)
PROVINCE_SCOPED_SCOPE_PHRASES = (
    ("摄像及视频制作服务", frozenset({"江西", "上海", "山西", "辽宁"})),
)
PROVINCE_RULE_TERM_ALIASES = (
    ("PROV-171", "道路运输", ("道路货物运输",)),
)
PROVINCE_SUPPRESSED_CATEGORIES = MappingProxyType(
    {
        "吉林": frozenset({"MEDICAL"}),
        "四川": frozenset({"MEDICAL"}),
    }
)
GENERIC_PROVINCE_TEMPLATE_NAME = re.compile(
    r"(?:不涉及前置审批(?:项)?承诺书|不涉及相关审批的承诺书)$"
)


class RuleError(Exception):
    pass


class InputError(Exception):
    pass


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    url: str
    host: str
    page_updated_at: str
    checked_at: str


@dataclass(frozen=True)
class IgnoredTerm:
    term: str
    classification: str
    source_excerpt: str
    reason: str


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    source_locator: str
    source_excerpt: str


@dataclass(frozen=True)
class TermAudit:
    source_terms: Tuple[str, ...]
    ignored_terms: Tuple[IgnoredTerm, ...]
    source_locator: str
    source_excerpt: str
    source_references: Tuple[SourceReference, ...]


@dataclass(frozen=True)
class SourceCoverage:
    source_id: str
    source_locator: str
    classification: str
    rule_ids: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Category:
    category_id: str
    label: str
    preapproval_type: str
    materials: Tuple[str, ...]
    authority: str
    business_check: str
    notes: str
    explicit_terms: Tuple[str, ...]
    review_terms: Tuple[str, ...]
    order: int
    audit: TermAudit


@dataclass(frozen=True)
class RuleTemplate:
    name: str
    url: str


@dataclass(frozen=True)
class PolicyTemplateRef:
    rule_id: str
    template_name: str


@dataclass(frozen=True)
class ContextualMatchGroup:
    source_tokens: Tuple[str, ...]
    shared_suffix: str
    prefixes: Tuple[str, ...]
    allow_ordinal_marker: bool


@dataclass(frozen=True)
class ProvinceRule:
    rule_id: str
    province: str
    approval_label: str
    category_ids: Tuple[str, ...]
    keywords_raw: str
    filing_type: str
    templates: Tuple[RuleTemplate, ...]
    match_mode: str
    match_terms: Tuple[str, ...]
    contextual_match_groups: Tuple[ContextualMatchGroup, ...]
    source_id: str
    source_order: int
    audit: TermAudit


@dataclass(frozen=True)
class ProvincePolicyRule:
    rule_id: str
    province: str
    approval_label: str
    category_ids: Tuple[str, ...]
    materials: Tuple[str, ...]
    template_refs: Tuple[PolicyTemplateRef, ...]
    policy_text: str
    required_action: str
    match_mode: str
    match_terms: Tuple[str, ...]
    source_id: str
    source_order: int
    audit: TermAudit


@dataclass(frozen=True)
class GenericNotInvolved:
    consultation_note: Tuple[str, ...]
    statement: Tuple[str, ...]
    submission: str


@dataclass(frozen=True)
class RuleBook:
    schema_version: int
    version: str
    checked_at: str
    scope_note: str
    sources: Tuple[Source, ...]
    categories: Mapping[str, Category]
    province_rules: Tuple[ProvinceRule, ...]
    province_policy_rules: Tuple[ProvincePolicyRule, ...]
    unlisted_template_provinces: Tuple[str, ...]
    generic_not_involved: GenericNotInvolved
    disclaimer: str
    source_coverage: Tuple[SourceCoverage, ...]


@dataclass(frozen=True)
class CategoryMatch:
    category: Category
    level: str
    company_keywords: Tuple[str, ...]
    scope_keywords: Tuple[str, ...]

    @property
    def keywords(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(self.company_keywords + self.scope_keywords))


@dataclass(frozen=True)
class ProvinceRuleMatch:
    rule: ProvinceRule
    company_matched_terms: Tuple[str, ...]
    scope_matched_terms: Tuple[str, ...]
    needs_manual_confirmation: bool
    company_template_exclusion_terms: Tuple[str, ...] = ()
    scope_template_exclusion_terms: Tuple[str, ...] = ()

    @property
    def matched_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(self.company_matched_terms + self.scope_matched_terms)
        )

    @property
    def template_exclusion_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                self.company_template_exclusion_terms
                + self.scope_template_exclusion_terms
            )
        )

    @property
    def category_id(self) -> Optional[str]:
        return self.rule.category_ids[0] if self.rule.category_ids else None


@dataclass(frozen=True)
class ProvincePolicyMatch:
    rule: ProvincePolicyRule
    company_matched_terms: Tuple[str, ...]
    scope_matched_terms: Tuple[str, ...]
    needs_manual_confirmation: bool

    @property
    def matched_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(self.company_matched_terms + self.scope_matched_terms)
        )


@dataclass(frozen=True)
class MaterialCategoryPath:
    category_id: Optional[str]
    category_label: str
    matched_terms: Tuple[str, ...]
    materials: Tuple[str, ...]
    authority: str
    templates: Tuple[Tuple[str, str], ...]
    template_exclusion_terms: Tuple[str, ...] = ()
    review_only: bool = False
    province_terms: Tuple[str, ...] = ()
    national_review_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MaterialRow:
    preapproval_type: str
    paths: Tuple[MaterialCategoryPath, ...]

    @property
    def matched_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                term
                for path in self.paths
                for term in path.matched_terms
            )
        )

    @property
    def template_exclusion_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                term
                for path in self.paths
                for term in path.template_exclusion_terms
            )
        )

    @property
    def province_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                term for path in self.paths for term in path.province_terms
            )
        )

    @property
    def national_review_terms(self) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                term
                for path in self.paths
                for term in path.national_review_terms
            )
        )

    @property
    def review_only(self) -> bool:
        return bool(self.paths) and all(path.review_only for path in self.paths)


@dataclass(frozen=True)
class CheckResult:
    book: RuleBook
    company_name: str
    original_scope: str
    province: Optional[str]
    province_source: str
    matches: Tuple[CategoryMatch, ...]
    province_rules: Tuple[ProvinceRuleMatch, ...]
    province_policies: Tuple[ProvincePolicyMatch, ...]


def _required_string(value, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleError("规则字段为空或类型错误：{}".format(path))
    return value.strip()


def _string_allow_empty(value, path: str) -> str:
    if not isinstance(value, str):
        raise RuleError("规则字段类型错误：{}".format(path))
    return value.strip()


def _string_tuple(value, path: str, allow_empty: bool = False) -> Tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RuleError("规则字段必须是文本数组：{}".format(path))
    result = tuple(item.strip() for item in value if item.strip())
    if not allow_empty and not result:
        raise RuleError("规则字段不能为空数组：{}".format(path))
    if len(result) != len(set(result)):
        raise RuleError("规则字段包含重复值：{}".format(path))
    return result


def _positive_integer(value, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise RuleError("规则字段必须是正整数：{}".format(path))
    return value


def _iso_date(value, path: str) -> str:
    result = _required_string(value, path)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", result):
        raise RuleError("规则日期必须为 YYYY-MM-DD：{}".format(path))
    return result


def _safe_url(value, host: str, path: str, document: bool = False) -> str:
    result = _required_string(value, path)
    parsed = urlparse(result)
    if parsed.scheme != "https" or parsed.hostname != host or parsed.username or parsed.password:
        if host == SOURCE_HOST:
            raise RuleError("资料来源必须是华为云官方文档：{}".format(result))
        raise RuleError("模板 URL 必须是华为云页面列出的 CDN 地址：{}".format(result))
    if document and not re.search(r"\.(?:doc|docx)$", parsed.path, re.IGNORECASE):
        raise RuleError("模板 URL 不是 Word 文档：{}".format(result))
    return result


def _load_json(path: Path):
    path = Path(path)
    descriptor = None
    chunks = []
    try:
        initial = os.lstat(str(path))
        if stat.S_ISLNK(initial.st_mode):
            raise RuleError("规则文件不得是符号链接")
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        descriptor = os.open(str(path), flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise RuleError("规则文件必须是普通文件")
        if opened.st_size > MAX_RULES_BYTES:
            raise RuleError("规则文件过大")
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_RULES_BYTES - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RULES_BYTES:
                raise RuleError("规则文件过大")
            chunks.append(chunk)
        final = os.fstat(descriptor)
        if (
            total != opened.st_size
            or final.st_size != opened.st_size
            or final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_mtime_ns != opened.st_mtime_ns
        ):
            raise RuleError("规则文件在读取期间发生变化")
    except RuleError:
        raise
    except OSError as exc:
        raise RuleError("无法读取规则文件：{}".format(exc)) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    try:
        raw = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RuleError("规则文件不是有效的 UTF-8 JSON：{}".format(exc)) from exc
    if not isinstance(raw, dict):
        raise RuleError("规则文件顶层必须是对象")
    return raw


def _required_match_key_string(value, path: str) -> str:
    result = _required_string(value, path)
    if not _match_key(result):
        raise RuleError("{} 归一化后为空".format(path))
    return result


def _match_key_string_tuple(
    value, path: str, allow_empty: bool = False
) -> Tuple[str, ...]:
    result = _string_tuple(value, path, allow_empty=allow_empty)
    for index, item in enumerate(result):
        if not _match_key(item):
            raise RuleError("{}[{}] 归一化后为空".format(path, index))
    return result


def _contextual_match_groups(item: dict, prefix: str):
    raw_groups = item.get("contextual_match_groups", [])
    if not isinstance(raw_groups, list):
        raise RuleError(
            "{}.contextual_match_groups 必须是数组".format(prefix)
        )
    groups = []
    positive_source_tokens = []
    required_fields = {
        "source_tokens",
        "shared_suffix",
        "prefixes",
        "allow_ordinal_marker",
    }
    for index, raw_group in enumerate(raw_groups):
        group_prefix = "{}.contextual_match_groups[{}]".format(prefix, index)
        if not isinstance(raw_group, dict) or set(raw_group) != required_fields:
            raise RuleError(
                "{} 必须精确包含上下文匹配字段".format(group_prefix)
            )
        raw_source_tokens = raw_group.get("source_tokens")
        source_tokens = _match_key_string_tuple(
            raw_source_tokens, group_prefix + ".source_tokens"
        )
        if len(source_tokens) != len(raw_source_tokens):
            raise RuleError("{}.source_tokens 不得包含空值".format(group_prefix))
        shared_suffix = _required_match_key_string(
            raw_group.get("shared_suffix"), group_prefix + ".shared_suffix"
        )
        raw_prefixes = raw_group.get("prefixes")
        prefixes = _match_key_string_tuple(
            raw_prefixes, group_prefix + ".prefixes"
        )
        if len(prefixes) != len(raw_prefixes):
            raise RuleError("{}.prefixes 不得包含空值".format(group_prefix))
        if len({_match_key(term) for term in source_tokens}) != len(source_tokens):
            raise RuleError(
                "{}.source_tokens 归一化后包含重复值".format(group_prefix)
            )
        if len({_match_key(term) for term in prefixes}) != len(prefixes):
            raise RuleError(
                "{}.prefixes 归一化后包含重复值".format(group_prefix)
            )
        allow_ordinal_marker = raw_group.get("allow_ordinal_marker")
        if not isinstance(allow_ordinal_marker, bool):
            raise RuleError(
                "{}.allow_ordinal_marker 必须是布尔值".format(group_prefix)
            )

        source_values = set(source_tokens)
        if not any(shared_suffix in source_token for source_token in source_values):
            raise RuleError(
                "{}.shared_suffix 不在 source_tokens 中".format(group_prefix)
            )
        for candidate_prefix in prefixes:
            if (
                candidate_prefix not in source_values
                and candidate_prefix + shared_suffix not in source_values
            ):
                raise RuleError(
                    "{}.prefixes 中的 {} 无法由来源词证明".format(
                        group_prefix, candidate_prefix
                    )
                )

        groups.append(
            ContextualMatchGroup(
                source_tokens=source_tokens,
                shared_suffix=shared_suffix,
                prefixes=prefixes,
                allow_ordinal_marker=allow_ordinal_marker,
            )
        )
        positive_source_tokens.extend(source_tokens)
    return tuple(groups), tuple(positive_source_tokens)


def _legacy_term_audit(positive_terms: Sequence[str]) -> TermAudit:
    return TermAudit(
        source_terms=tuple(positive_terms),
        ignored_terms=(),
        source_locator="legacy-v1",
        source_excerpt="legacy-v1",
        source_references=(),
    )


def _term_audit(
    item,
    prefix: str,
    positive_terms: Sequence[str],
    known_source_ids: Sequence[str],
) -> TermAudit:
    source_terms = _match_key_string_tuple(
        item.get("source_terms"), prefix + ".source_terms", allow_empty=True
    )
    source_locator = _required_match_key_string(
        item.get("source_locator"), prefix + ".source_locator"
    )
    source_excerpt = _required_string(
        item.get("source_excerpt"), prefix + ".source_excerpt"
    )
    raw_references = item.get("source_references")
    source_references = []
    if raw_references is not None:
        if not isinstance(raw_references, list) or not raw_references:
            raise RuleError("{}.source_references 必须是非空数组".format(prefix))
        seen_references = set()
        for reference_index, reference in enumerate(raw_references):
            reference_prefix = "{}.source_references[{}]".format(
                prefix, reference_index
            )
            if not isinstance(reference, dict) or set(reference) != {
                "source_id",
                "source_locator",
                "source_excerpt",
            }:
                raise RuleError("{} 必须精确包含三个来源字段".format(reference_prefix))
            source_id = _required_match_key_string(
                reference.get("source_id"), reference_prefix + ".source_id"
            )
            if source_id not in known_source_ids:
                raise RuleError("{} 引用不存在的来源：{}".format(reference_prefix, source_id))
            source_locator_value = _required_match_key_string(
                reference.get("source_locator"), reference_prefix + ".source_locator"
            )
            identity = (source_id, source_locator_value)
            if identity in seen_references:
                raise RuleError("{}.source_references 包含重复原始 locator".format(prefix))
            seen_references.add(identity)
            source_references.append(
                SourceReference(
                    source_id=source_id,
                    source_locator=source_locator_value,
                    source_excerpt=_required_string(
                        reference.get("source_excerpt"),
                        reference_prefix + ".source_excerpt",
                    ),
                )
            )

    raw_ignored = item.get("ignored_terms")
    if not isinstance(raw_ignored, list):
        raise RuleError("规则字段必须是数组：{}.ignored_terms".format(prefix))
    ignored_terms = []
    for index, ignored in enumerate(raw_ignored):
        ignored_prefix = "{}.ignored_terms[{}]".format(prefix, index)
        if not isinstance(ignored, dict):
            raise RuleError("{} 必须是对象".format(ignored_prefix))
        classification = _required_string(
            ignored.get("classification"), ignored_prefix + ".classification"
        )
        if classification not in IGNORED_TERM_CLASSIFICATIONS:
            raise RuleError(
                "{}.classification 无效：{}".format(ignored_prefix, classification)
            )
        term = _required_match_key_string(
            ignored.get("term"), ignored_prefix + ".term"
        )
        ignored_source_excerpt = _required_string(
            ignored.get("source_excerpt"), ignored_prefix + ".source_excerpt"
        )
        if term not in ignored_source_excerpt:
            raise RuleError(
                "{}.source_excerpt 未包含 ignored term：{}".format(
                    ignored_prefix, term
                )
            )
        ignored_terms.append(
            IgnoredTerm(
                term=term,
                classification=classification,
                source_excerpt=ignored_source_excerpt,
                reason=_required_string(
                    ignored.get("reason"), ignored_prefix + ".reason"
                ),
            )
        )

    source_keys = {}
    for term in source_terms:
        key = _match_key(term)
        if key in source_keys:
            raise RuleError(
                "{}.source_terms 归一化后包含重复词：{}".format(prefix, term)
            )
        source_keys[key] = term

    classified_keys = {}
    for term in positive_terms:
        key = _match_key(term)
        if key in classified_keys:
            raise RuleError("{} 术语重复分类：{}".format(prefix, term))
        classified_keys[key] = term
    for ignored in ignored_terms:
        key = _match_key(ignored.term)
        if key in classified_keys:
            raise RuleError("{} 术语重复分类：{}".format(prefix, ignored.term))
        classified_keys[key] = ignored.term

    extra_positive = [
        term for term in positive_terms if _match_key(term) not in source_keys
    ]
    if extra_positive:
        raise RuleError(
            "{} 正向词不在 source_terms 中：{}".format(
                prefix, "、".join(extra_positive)
            )
        )
    extra_ignored = [
        ignored.term
        for ignored in ignored_terms
        if _match_key(ignored.term) not in source_keys
    ]
    if extra_ignored:
        raise RuleError(
            "{}.ignored_terms 不在 source_terms 中：{}".format(
                prefix, "、".join(extra_ignored)
            )
        )
    unclassified = [
        term for key, term in source_keys.items() if key not in classified_keys
    ]
    if unclassified:
        raise RuleError(
            "{}.source_terms 存在未分类术语：{}".format(
                prefix, "、".join(unclassified)
            )
        )

    audit_excerpts = tuple(
        reference.source_excerpt for reference in source_references
    ) or (source_excerpt,)
    for term in tuple(positive_terms) + tuple(
        ignored.term for ignored in ignored_terms
    ) + source_terms:
        if not any(term in excerpt for excerpt in audit_excerpts):
            raise RuleError(
                "{}.{} 未包含术语：{}".format(
                    prefix,
                    "source_references" if source_references else "source_excerpt",
                    term,
                )
            )
    for index, ignored in enumerate(ignored_terms):
        if not any(
            ignored.source_excerpt in excerpt
            for excerpt in audit_excerpts
        ):
            raise RuleError(
                "{}.ignored_terms[{}].source_excerpt 未包含在规则 source_excerpt/source_references 中：{}".format(
                    prefix, index, ignored.source_excerpt
                )
            )

    return TermAudit(
        source_terms=source_terms,
        ignored_terms=tuple(ignored_terms),
        source_locator=source_locator,
        source_excerpt=source_excerpt,
        source_references=tuple(source_references),
    )


def _source_coverage(
    raw_coverage, source_ids: Sequence[str], rule_ids: Sequence[str]
) -> Tuple[SourceCoverage, ...]:
    if not isinstance(raw_coverage, list):
        raise RuleError("source_coverage 必须是数组")
    known_sources = set(source_ids)
    known_rules = set(rule_ids)
    seen_locators = set()
    coverage = []
    for index, item in enumerate(raw_coverage):
        prefix = "source_coverage[{}]".format(index)
        if not isinstance(item, dict):
            raise RuleError("{} 必须是对象".format(prefix))
        source_id = _required_match_key_string(
            item.get("source_id"), prefix + ".source_id"
        )
        if source_id not in known_sources:
            raise RuleError("{} 引用不存在的来源：{}".format(prefix, source_id))
        source_locator = _required_match_key_string(
            item.get("source_locator"), prefix + ".source_locator"
        )
        locator_key = (source_id, source_locator)
        if locator_key in seen_locators:
            raise RuleError(
                "source_coverage 包含重复的 source_locator：{} / {}".format(
                    source_id, source_locator
                )
            )
        seen_locators.add(locator_key)

        classification = _required_string(
            item.get("classification"), prefix + ".classification"
        )
        if classification not in {"rule", "non-rule"}:
            raise RuleError(
                "{}.classification 无效：{}".format(prefix, classification)
            )
        item_rule_ids = _match_key_string_tuple(
            item.get("rule_ids"), prefix + ".rule_ids", allow_empty=True
        )
        reason_value = item.get("reason")
        if not isinstance(reason_value, str):
            raise RuleError("规则字段为空或类型错误：{}.reason".format(prefix))
        reason = reason_value.strip()
        if classification == "rule":
            if not item_rule_ids:
                raise RuleError("{} rule 分类必须提供 rule_ids".format(prefix))
            missing_rule_ids = [
                rule_id for rule_id in item_rule_ids if rule_id not in known_rules
            ]
            if missing_rule_ids:
                raise RuleError(
                    "{} 引用不存在的规则：{}".format(
                        prefix, "、".join(missing_rule_ids)
                    )
                )
        else:
            if item_rule_ids:
                raise RuleError("{} non-rule 分类不得提供 rule_ids".format(prefix))
            if not reason:
                raise RuleError("{} non-rule 分类必须提供 reason".format(prefix))
        coverage.append(
            SourceCoverage(
                source_id=source_id,
                source_locator=source_locator,
                classification=classification,
                rule_ids=item_rule_ids,
                reason=reason,
            )
        )
    return tuple(coverage)


def _rule_templates(item: dict, prefix: str, schema_version: int) -> Tuple[RuleTemplate, ...]:
    legacy_fields = ("template_name", "template_url")
    has_legacy = any(field in item for field in legacy_fields)
    has_templates = "templates" in item
    if schema_version == 1:
        if has_templates:
            raise RuleError("schema_version 1 不得使用 {}.templates".format(prefix))
        return (
            RuleTemplate(
                name=_required_string(
                    item.get("template_name"), prefix + ".template_name"
                ),
                url=_safe_url(
                    item.get("template_url"),
                    TEMPLATE_HOST,
                    prefix + ".template_url",
                    document=True,
                ),
            ),
        )

    if has_templates and has_legacy:
        raise RuleError("{} 不得同时使用 templates 与旧模板字段".format(prefix))
    raw_templates = item.get("templates")
    if not isinstance(raw_templates, list):
        raise RuleError("{}.templates 必须是数组".format(prefix))
    # A current Huawei matrix row can explicitly have no downloadable
    # commitment letter. Keep the rule for keyword/manual review while
    # representing that state with an empty template list.
    if not raw_templates:
        return ()
    templates = []
    seen = set()
    for index, raw_template in enumerate(raw_templates):
        template_prefix = "{}.templates[{}]".format(prefix, index)
        if not isinstance(raw_template, dict):
            raise RuleError("{} 必须是对象".format(template_prefix))
        if set(raw_template) != {"name", "url"}:
            raise RuleError("{} 只允许 name 和 url 字段".format(template_prefix))
        template = RuleTemplate(
            name=_required_string(raw_template.get("name"), template_prefix + ".name"),
            url=_safe_url(
                raw_template.get("url"),
                TEMPLATE_HOST,
                template_prefix + ".url",
                document=True,
            ),
        )
        identity = (_match_key(template.name), _match_key(template.url))
        if identity in seen:
            raise RuleError("{}.templates 包含重复模板".format(prefix))
        seen.add(identity)
        templates.append(template)
    return tuple(templates)


def _policy_template_refs(
    item: dict,
    prefix: str,
    category_ids: Sequence[str],
    province: str,
    province_rules_by_id: Mapping[str, ProvinceRule],
) -> Tuple[PolicyTemplateRef, ...]:
    has_refs = "template_refs" in item
    has_legacy = "template_rule_ids" in item
    if has_refs and has_legacy:
        raise RuleError(
            "{}.template_refs 与 template_rule_ids 不得同时出现".format(prefix)
        )

    if has_refs:
        raw_refs = item.get("template_refs")
        if not isinstance(raw_refs, list):
            raise RuleError("{}.template_refs 必须是对象数组".format(prefix))
        if not raw_refs:
            raise RuleError("{}.template_refs 必须是非空对象数组".format(prefix))
        refs = []
        seen = set()
        for index, raw_ref in enumerate(raw_refs):
            ref_prefix = "{}.template_refs[{}]".format(prefix, index)
            if not isinstance(raw_ref, dict) or set(raw_ref) != {
                "rule_id",
                "template_name",
            }:
                raise RuleError(
                    "{} 必须是对象且精确包含 rule_id 和 template_name".format(
                        ref_prefix
                    )
                )
            rule_id = _required_match_key_string(
                raw_ref.get("rule_id"), ref_prefix + ".rule_id"
            )
            template_name = _required_match_key_string(
                raw_ref.get("template_name"), ref_prefix + ".template_name"
            )
            identity = (rule_id, template_name)
            if identity in seen:
                raise RuleError("{}.template_refs 包含重复 pair".format(prefix))
            seen.add(identity)
            owner = province_rules_by_id.get(rule_id)
            if owner is None:
                raise RuleError(
                    "{}.template_refs 引用的规则 {} 不存在".format(prefix, rule_id)
                )
            if owner.province != province:
                raise RuleError(
                    "{}.template_refs 不得跨省引用规则：{}".format(prefix, rule_id)
                )
            matching_templates = [
                template
                for template in owner.templates
                if template.name == template_name
            ]
            if not matching_templates:
                raise RuleError(
                    "{}.template_refs 引用的模板 {}（模板不存在）".format(
                        prefix, template_name
                    )
                )
            if len(matching_templates) > 1:
                raise RuleError(
                    "{}.template_refs 引用的模板 {} 在规则 {} 中不唯一".format(
                        prefix, template_name, rule_id
                    )
                )
            linked_excerpts = tuple(
                reference.source_excerpt for reference in owner.audit.source_references
            ) or (owner.audit.source_excerpt,)
            if not any(template_name in excerpt for excerpt in linked_excerpts):
                raise RuleError(
                    "{}.template_refs 引用的模板 {} 未出现在 "
                    "source_excerpt/source_references：{}".format(
                        prefix, template_name, rule_id
                    )
                )
            refs.append(PolicyTemplateRef(rule_id=rule_id, template_name=template_name))
        if refs and category_ids:
            raise RuleError(
                "{}.template_refs 仅适用于未关联全国类别的省级政策".format(prefix)
            )
        return tuple(refs)

    if not has_legacy:
        return ()
    raw_ids = item.get("template_rule_ids")
    template_rule_ids = _match_key_string_tuple(
        raw_ids, prefix + ".template_rule_ids", allow_empty=True
    )
    if template_rule_ids and category_ids:
        raise RuleError(
            "{}.template_rule_ids 仅适用于未关联全国类别的省级政策".format(prefix)
        )
    refs = []
    for rule_id in template_rule_ids:
        owner = province_rules_by_id.get(rule_id)
        if owner is None:
            raise RuleError(
                "{}.template_rule_ids 引用的规则 {} 不存在".format(prefix, rule_id)
            )
        if owner.province != province:
            raise RuleError(
                "{}.template_rule_ids 不得跨省引用规则：{}".format(prefix, rule_id)
            )
        if not owner.templates:
            raise RuleError(
                "{}.template_rule_ids 引用的规则没有模板：{}".format(prefix, rule_id)
            )
        if len(owner.templates) != 1:
            raise RuleError(
                "{}.template_rule_ids 引用的规则 {} 包含多个模板，必须唯一选择".format(
                    prefix, rule_id
                )
            )
        template = owner.templates[0]
        linked_excerpts = tuple(
            reference.source_excerpt for reference in owner.audit.source_references
        ) or (owner.audit.source_excerpt,)
        if not any(template.name in excerpt for excerpt in linked_excerpts):
            raise RuleError(
                "{}.template_rule_ids 引用的模板 {} 未出现在 "
                "source_excerpt/source_references：{}".format(
                    prefix, template.name, rule_id
                )
            )
        refs.append(PolicyTemplateRef(rule_id=rule_id, template_name=template.name))
    return tuple(refs)


def load_rules(path: Path) -> RuleBook:
    raw = _load_json(path)
    schema_version = raw.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2}:
        raise RuleError("不支持的规则 schema_version")
    version = _required_string(raw.get("version"), "version")
    checked_at = _iso_date(raw.get("checked_at"), "checked_at")
    scope_note = _required_string(raw.get("scope"), "scope")

    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise RuleError("sources 必须是非空数组")
    sources = []
    source_ids = set()
    for index, item in enumerate(raw_sources):
        if not isinstance(item, dict):
            raise RuleError("sources[{}] 必须是对象".format(index))
        prefix = "sources[{}]".format(index)
        source_id = _required_match_key_string(item.get("id"), prefix + ".id")
        if source_id in source_ids:
            raise RuleError("重复的来源编号：{}".format(source_id))
        source_ids.add(source_id)
        url = _safe_url(item.get("url"), SOURCE_HOST, prefix + ".url")
        sources.append(
            Source(
                source_id=source_id,
                title=_required_string(item.get("title"), prefix + ".title"),
                url=url,
                host=urlparse(url).hostname or "",
                page_updated_at=_iso_date(item.get("page_updated_at"), prefix + ".page_updated_at"),
                checked_at=_iso_date(item.get("checked_at"), prefix + ".checked_at"),
            )
        )

    raw_categories = raw.get("categories")
    if not isinstance(raw_categories, list) or not raw_categories:
        raise RuleError("categories 必须是非空数组")
    categories = {}
    category_orders = set()
    for index, item in enumerate(raw_categories):
        if not isinstance(item, dict):
            raise RuleError("categories[{}] 必须是对象".format(index))
        prefix = "categories[{}]".format(index)
        category_id = _required_match_key_string(item.get("id"), prefix + ".id")
        if category_id in categories:
            raise RuleError("重复的全国类别编号：{}".format(category_id))
        order = _positive_integer(item.get("order"), prefix + ".order")
        if order in category_orders:
            raise RuleError("重复的全国类别顺序：{}".format(order))
        category_orders.add(order)
        explicit_terms = _match_key_string_tuple(
            item.get("explicit_terms"), prefix + ".explicit_terms"
        )
        review_terms = _match_key_string_tuple(
            item.get("review_terms"), prefix + ".review_terms"
        )
        positive_terms = explicit_terms + review_terms
        audit = (
            _term_audit(item, prefix, positive_terms, tuple(source_ids))
            if schema_version == 2
            else _legacy_term_audit(positive_terms)
        )
        categories[category_id] = Category(
            category_id=category_id,
            label=_required_string(item.get("label"), prefix + ".label"),
            preapproval_type=_required_string(
                item.get("preapproval_type"), prefix + ".preapproval_type"
            ),
            materials=_string_tuple(item.get("materials"), prefix + ".materials"),
            authority=_required_string(item.get("authority"), prefix + ".authority"),
            business_check=_required_string(
                item.get("business_check"), prefix + ".business_check"
            ),
            notes=_required_string(item.get("notes"), prefix + ".notes"),
            explicit_terms=explicit_terms,
            review_terms=review_terms,
            order=order,
            audit=audit,
        )

    raw_province_rules = raw.get("province_rules")
    if not isinstance(raw_province_rules, list):
        raise RuleError("province_rules 必须是数组")
    province_rules = []
    province_rule_ids = set()
    source_orders = set()
    for index, item in enumerate(raw_province_rules):
        if not isinstance(item, dict):
            raise RuleError("province_rules[{}] 必须是对象".format(index))
        prefix = "province_rules[{}]".format(index)
        rule_id = _required_match_key_string(item.get("id"), prefix + ".id")
        if rule_id in province_rule_ids or rule_id in categories:
            raise RuleError("规则编号 {} 跨类型重复".format(rule_id))
        province_rule_ids.add(rule_id)
        province = _required_string(item.get("province"), prefix + ".province")
        if province not in PROVINCES:
            raise RuleError("省份规则包含非法省份：{}".format(province))
        category_ids = _match_key_string_tuple(
            item.get("category_ids"), prefix + ".category_ids", allow_empty=True
        )
        missing_categories = [value for value in category_ids if value not in categories]
        if missing_categories:
            raise RuleError("省份规则引用不存在的全国类别：{}".format("、".join(missing_categories)))
        match_mode = _required_string(item.get("match_mode"), prefix + ".match_mode")
        if match_mode not in MATCH_MODES:
            raise RuleError("省份规则包含非法 match_mode：{}".format(match_mode))
        match_terms = _match_key_string_tuple(
            item.get("match_terms"), prefix + ".match_terms", allow_empty=True
        )
        contextual_match_groups, contextual_source_tokens = (
            _contextual_match_groups(item, prefix)
            if schema_version == 2
            else ((), ())
        )
        has_literal_terms = bool(match_terms or contextual_match_groups)
        if match_mode == "literal" and not has_literal_terms:
            raise RuleError("literal 省份规则缺少正向词：{}".format(rule_id))
        if match_mode != "literal" and has_literal_terms:
            raise RuleError("人工确认省份规则不得配置正向词：{}".format(rule_id))
        source_id = _required_match_key_string(
            item.get("source_id"), prefix + ".source_id"
        )
        if source_id not in source_ids:
            raise RuleError("省份规则引用不存在的来源：{}".format(source_id))
        source_order = _positive_integer(item.get("source_order"), prefix + ".source_order")
        if source_order in source_orders:
            raise RuleError("重复的省份规则源顺序：{}".format(source_order))
        source_orders.add(source_order)
        positive_terms = match_terms + contextual_source_tokens
        audit = (
            _term_audit(item, prefix, positive_terms, tuple(source_ids))
            if schema_version == 2
            else _legacy_term_audit(match_terms)
        )
        missing_contextual_source_tokens = [
            term
            for term in contextual_source_tokens
            if term not in audit.source_terms
        ]
        if missing_contextual_source_tokens:
            raise RuleError(
                "{}.contextual_match_groups 来源词未逐字存在于 source_terms：{}".format(
                    prefix, "、".join(missing_contextual_source_tokens)
                )
            )
        province_rules.append(
            ProvinceRule(
                rule_id=rule_id,
                province=province,
                approval_label=_required_string(
                    item.get("approval_label"), prefix + ".approval_label"
                ),
                category_ids=category_ids,
                keywords_raw=_required_string(item.get("keywords_raw"), prefix + ".keywords_raw"),
                filing_type=(
                    _string_allow_empty
                    if schema_version == 2
                    else _required_string
                )(item.get("filing_type"), prefix + ".filing_type"),
                templates=_rule_templates(item, prefix, schema_version),
                match_mode=match_mode,
                match_terms=match_terms,
                contextual_match_groups=contextual_match_groups,
                source_id=source_id,
                source_order=source_order,
                audit=audit,
            )
        )

    province_rules_by_id = {rule.rule_id: rule for rule in province_rules}
    raw_policy_rules = raw.get("province_policy_rules", [])
    if not isinstance(raw_policy_rules, list):
        raise RuleError("province_policy_rules 必须是数组")
    policy_rules = []
    policy_ids = set()
    policy_orders = set()
    for index, item in enumerate(raw_policy_rules):
        if not isinstance(item, dict):
            raise RuleError("province_policy_rules[{}] 必须是对象".format(index))
        prefix = "province_policy_rules[{}]".format(index)
        rule_id = _required_match_key_string(item.get("id"), prefix + ".id")
        if (
            rule_id in policy_ids
            or rule_id in province_rule_ids
            or rule_id in categories
        ):
            raise RuleError("规则编号 {} 跨类型重复".format(rule_id))
        policy_ids.add(rule_id)
        province = _required_string(item.get("province"), prefix + ".province")
        if province not in PROVINCES:
            raise RuleError("省级政策包含非法省份：{}".format(province))
        category_ids = _match_key_string_tuple(
            item.get("category_ids"), prefix + ".category_ids", allow_empty=True
        )
        missing_categories = [value for value in category_ids if value not in categories]
        if missing_categories:
            raise RuleError("省级政策引用不存在的全国类别：{}".format("、".join(missing_categories)))
        match_mode = _required_string(item.get("match_mode"), prefix + ".match_mode")
        if match_mode not in MATCH_MODES:
            raise RuleError("省级政策包含非法 match_mode：{}".format(match_mode))
        match_terms = _match_key_string_tuple(
            item.get("match_terms"), prefix + ".match_terms", allow_empty=True
        )
        materials = _string_tuple(
            item.get("materials", []), prefix + ".materials", allow_empty=True
        )
        template_refs = _policy_template_refs(
            item,
            prefix,
            category_ids,
            province,
            province_rules_by_id,
        )
        if match_mode == "literal" and not match_terms:
            raise RuleError("literal 省级政策缺少 match_terms：{}".format(rule_id))
        if match_mode != "literal" and match_terms:
            raise RuleError("人工确认省级政策不得配置正向 match_terms：{}".format(rule_id))
        source_id = _required_match_key_string(
            item.get("source_id"), prefix + ".source_id"
        )
        if source_id not in source_ids:
            raise RuleError("省级政策引用不存在的来源：{}".format(source_id))
        source_order = _positive_integer(item.get("source_order"), prefix + ".source_order")
        if source_order in policy_orders:
            raise RuleError("重复的省级政策源顺序：{}".format(source_order))
        policy_orders.add(source_order)
        audit = (
            _term_audit(item, prefix, match_terms, tuple(source_ids))
            if schema_version == 2
            else _legacy_term_audit(match_terms)
        )
        audit_excerpts = tuple(
            reference.source_excerpt for reference in audit.source_references
        ) or (audit.source_excerpt,)
        for material in materials:
            if not any(material in excerpt for excerpt in audit_excerpts):
                raise RuleError(
                    "{}.materials 未出现在 source_excerpt/source_references：{}".format(
                        prefix, material
                    )
                )
        policy_rules.append(
            ProvincePolicyRule(
                rule_id=rule_id,
                province=province,
                approval_label=_required_string(
                    item.get("approval_label"), prefix + ".approval_label"
                ),
                category_ids=category_ids,
                materials=materials,
                template_refs=template_refs,
                policy_text=_required_string(item.get("policy_text"), prefix + ".policy_text"),
                required_action=_required_string(
                    item.get("required_action"), prefix + ".required_action"
                ),
                match_mode=match_mode,
                match_terms=match_terms,
                source_id=source_id,
                source_order=source_order,
                audit=audit,
            )
        )

    unlisted = _string_tuple(
        raw.get("unlisted_template_provinces"), "unlisted_template_provinces"
    )
    if any(province not in PROVINCES for province in unlisted):
        raise RuleError("未列模板省份配置包含非法省份")
    listed = {rule.province for rule in province_rules}
    if listed.intersection(unlisted):
        raise RuleError("同一省份不能同时出现在模板矩阵和未列清单")

    generic = raw.get("generic_not_involved")
    if not isinstance(generic, dict):
        raise RuleError("generic_not_involved 必须是对象")
    generic_not_involved = GenericNotInvolved(
        consultation_note=_string_tuple(
            generic.get("consultation_note"), "generic_not_involved.consultation_note"
        ),
        statement=_string_tuple(generic.get("statement"), "generic_not_involved.statement"),
        submission=_required_string(
            generic.get("submission"), "generic_not_involved.submission"
        ),
    )

    source_coverage = (
        _source_coverage(
            raw.get("source_coverage"),
            source_ids,
            tuple(categories) + tuple(province_rule_ids) + tuple(policy_ids),
        )
        if schema_version == 2
        else ()
    )

    ordered_categories = dict(
        sorted(categories.items(), key=lambda pair: (pair[1].order, pair[0]))
    )
    return RuleBook(
        schema_version=schema_version,
        version=version,
        checked_at=checked_at,
        scope_note=scope_note,
        sources=tuple(sources),
        categories=MappingProxyType(ordered_categories),
        province_rules=tuple(sorted(province_rules, key=lambda item: item.source_order)),
        province_policy_rules=tuple(
            sorted(policy_rules, key=lambda item: item.source_order)
        ),
        unlisted_template_provinces=unlisted,
        generic_not_involved=generic_not_involved,
        disclaimer=_required_string(raw.get("disclaimer"), "disclaimer"),
        source_coverage=source_coverage,
    )


def _match_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not character.isspace() and unicodedata.category(character) != "Cf"
    )


def _match_key_with_spans(value: str):
    key = []
    spans = []
    for index, character in enumerate(value):
        normalized = unicodedata.normalize("NFKC", character).casefold()
        for normalized_character in normalized:
            if normalized_character.isspace():
                continue
            if unicodedata.category(normalized_character) == "Cf":
                continue
            key.append(normalized_character)
            spans.append((index, index + 1))
    return "".join(key), tuple(spans)


def _paired_brackets(value: str) -> Mapping[int, int]:
    stack = []
    pairs = {}
    closing = {right: left for left, right in BRACKET_PAIRS.items()}
    for index, character in enumerate(value):
        if character in BRACKET_PAIRS:
            stack.append((character, index))
        elif character in closing and stack and stack[-1][0] == closing[character]:
            _, opening = stack.pop()
            pairs[opening] = index
    return pairs


def _first_terminator(value: str, start: int) -> int:
    return next(
        (
            index
            for index in range(start, len(value))
            if value[index] in CLAUSE_TERMINATORS
        ),
        len(value),
    )


def _previous_terminator(value: str, start: int) -> int:
    return next(
        (
            index
            for index in range(start - 1, -1, -1)
            if value[index] in CLAUSE_TERMINATORS
        ),
        -1,
    )


def _enclosing_bracket(
    position: int, pairs: Mapping[int, int]
) -> Optional[Tuple[int, int]]:
    candidates = [
        (opening, closing)
        for opening, closing in pairs.items()
        if opening < position < closing
    ]
    return max(candidates, default=None, key=lambda pair: pair[0])


def _merge_spans(
    spans: Sequence[Tuple[int, int]],
) -> Tuple[Tuple[int, int], ...]:
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _excluded_spans(value: str) -> Tuple[Tuple[int, int], ...]:
    pairs = _paired_brackets(value)
    spans = []
    for pattern in NON_PROGRAM_AUDIOVISUAL_PATTERNS:
        spans.extend(match.span() for match in pattern.finditer(value))

    for marker in FORWARD_EXCLUSION_MARKERS:
        search_from = 0
        while True:
            marker_start = value.find(marker, search_from)
            if marker_start < 0:
                break
            marker_end = marker_start + len(marker)
            span_end = _first_terminator(value, marker_end)
            enclosing = _enclosing_bracket(marker_start, pairs)
            if enclosing is not None:
                span_end = min(span_end, enclosing[1])
            spans.append((marker_start, span_end))
            search_from = marker_end

    # Treat a clause-level "非" as an exclusion marker. Restricting the
    # marker to clause or bracket boundaries avoids filtering embedded words
    # such as the "出版" in "报刊出版单位" unless the whole phrase is negated.
    search_from = 0
    while True:
        marker_start = value.find(NON_CLAUSE_MARKER, search_from)
        if marker_start < 0:
            break
        previous = marker_start - 1
        while previous >= 0 and value[previous].isspace():
            previous -= 1
        if previous < 0 or value[previous] in NON_CLAUSE_PREFIXES:
            marker_end = marker_start + len(NON_CLAUSE_MARKER)
            span_end = _first_terminator(value, marker_end)
            enclosing = _enclosing_bracket(marker_start, pairs)
            if enclosing is not None:
                span_end = min(span_end, enclosing[1])
            entity_ends = [
                candidate + len(suffix)
                for suffix in NON_CLAUSE_ENTITY_SUFFIXES
                for candidate in range(marker_end, span_end)
                if value.startswith(suffix, candidate)
            ]
            if entity_ends:
                spans.append((marker_start, max(entity_ends)))
        search_from = marker_start + len(NON_CLAUSE_MARKER)

    search_from = 0
    while True:
        marker_start = value.find(SUFFIX_EXCLUSION_MARKER, search_from)
        if marker_start < 0:
            break
        marker_end = marker_start + len(SUFFIX_EXCLUSION_MARKER)
        enclosing = _enclosing_bracket(marker_start, pairs)
        if enclosing is not None:
            span_start = enclosing[0] + 1
        else:
            span_start = _previous_terminator(value, marker_start) + 1
        spans.append((span_start, marker_end))
        search_from = marker_end
    return _merge_spans(spans)


def _mask_nationwide_non_rule_phrases(value: str) -> str:
    characters = list(value)
    for phrase in NATIONWIDE_NON_RULE_PHRASES:
        search_from = 0
        while True:
            start = value.find(phrase, search_from)
            if start < 0:
                break
            end = start + len(phrase)
            characters[start:end] = " " * len(phrase)
            search_from = end
    return "".join(characters)


def _scope_for_matching(value: str, province: Optional[str] = None) -> str:
    characters = list(_mask_nationwide_non_rule_phrases(value))
    for start, end in _excluded_spans(value):
        characters[start:end] = " " * (end - start)
    for phrase, allowed_provinces in PROVINCE_SCOPED_SCOPE_PHRASES:
        if province in allowed_provinces:
            continue
        search_from = 0
        while True:
            start = value.find(phrase, search_from)
            if start < 0:
                break
            end = start + len(phrase)
            characters[start:end] = " " * len(phrase)
            search_from = end
    return "".join(characters)


def _occurrence_spans(
    value_key: str, term_key: str
) -> Tuple[Tuple[int, int], ...]:
    spans = []
    search_from = 0
    while term_key:
        start = value_key.find(term_key, search_from)
        if start < 0:
            break
        spans.append((start, start + len(term_key)))
        search_from = start + 1
    return tuple(spans)


def _position_aware_terms(
    terms: Sequence[str], value_keys: Sequence[str]
) -> Tuple[str, ...]:
    unique_terms = tuple(dict.fromkeys(terms))
    keys = {term: _match_key(term) for term in unique_terms}
    occurrences = {
        (term, field_index): _occurrence_spans(value_key, keys[term])
        for term in unique_terms
        for field_index, value_key in enumerate(value_keys)
    }
    kept = []
    for term in unique_terms:
        term_occurrences = tuple(
            (field_index, span)
            for field_index in range(len(value_keys))
            for span in occurrences[(term, field_index)]
        )
        if not term_occurrences:
            kept.append(term)
            continue
        all_covered = all(
            any(
                len(keys[other]) > len(keys[term])
                and any(
                    other_start <= start and end <= other_end
                    for other_start, other_end in occurrences[(other, field_index)]
                )
                for other in unique_terms
            )
            for field_index, (start, end) in term_occurrences
        )
        if not all_covered:
            kept.append(term)
    return tuple(kept)


def _contextual_match_terms(group: ContextualMatchGroup) -> Tuple[str, ...]:
    terms = []
    for prefix in group.prefixes:
        term = prefix + group.shared_suffix
        terms.append(term)
        if group.allow_ordinal_marker:
            terms.append("第" + term)
    return tuple(terms)


def _matched_rule_terms(rule: ProvinceRule, value_key: str) -> Tuple[str, ...]:
    direct = [term for term in rule.match_terms if _match_key(term) in value_key]
    aliases = [
        alias
        for rule_id, source_term, rule_aliases in PROVINCE_RULE_TERM_ALIASES
        if rule.rule_id == rule_id and source_term in rule.match_terms
        for alias in rule_aliases
        if _match_key(alias) in value_key
    ]
    contextual = [
        term
        for group in rule.contextual_match_groups
        for term in _contextual_match_terms(group)
        if _match_key(term) in value_key
    ]
    candidates = tuple(
        dict.fromkeys(tuple(direct) + tuple(aliases) + tuple(contextual))
    )
    return (
        _position_aware_terms(candidates, (value_key,))
        if aliases or contextual
        else tuple(direct)
    )


def _matched_template_exclusion_terms(
    rule: ProvinceRule, value_key: str
) -> Tuple[str, ...]:
    terms = [
        item.term
        for item in rule.audit.ignored_terms
        if item.classification == "exclusion" and _match_key(item.term) in value_key
    ]
    return _position_aware_terms(terms, (value_key,))


def analyze(
    book: RuleBook,
    scope: str,
    province: Optional[str] = None,
    province_source: str = "未提供",
    company_name: Optional[str] = None,
) -> CheckResult:
    if not isinstance(scope, str) or not scope.strip():
        raise InputError("经营范围为空，请提供营业执照图片或经营范围原文")
    if len(scope) > MAX_SCOPE_CHARS:
        raise InputError("经营范围过长")
    original_scope = scope.strip()
    if not _match_key(original_scope):
        raise InputError("经营范围为空，请提供营业执照图片或经营范围原文")
    matching_province = province.strip() if isinstance(province, str) else province
    scope_key = _match_key(_scope_for_matching(original_scope, matching_province))

    if company_name is None:
        original_company_name = ""
    elif not isinstance(company_name, str) or not _match_key(company_name.strip()):
        raise InputError("单位名称为空")
    else:
        original_company_name = company_name.strip()
    company_key = _match_key(
        _mask_nationwide_non_rule_phrases(original_company_name)
    )

    if province is not None:
        if not isinstance(province, str) or province.strip() not in PROVINCES:
            raise InputError("备案省份无效：{}；请使用省级行政区名称".format(province))
        province = province.strip()
        if province_source == "未提供":
            province_source = "用户提供"
    elif province_source != "未提供":
        raise InputError("未提供备案省份时，省份来源必须为“未提供”")
    if province_source not in PROVINCE_SOURCES:
        raise InputError("省份来源无效：{}".format(province_source))

    matches = []
    matched_category_ids = set()
    suppressed_category_ids = PROVINCE_SUPPRESSED_CATEGORIES.get(
        province, frozenset()
    )
    for category in book.categories.values():
        if category.category_id in suppressed_category_ids:
            continue
        company_explicit = [
            term for term in category.explicit_terms if _match_key(term) in company_key
        ]
        company_review = [
            term for term in category.review_terms if _match_key(term) in company_key
        ]
        scope_explicit = [
            term for term in category.explicit_terms if _match_key(term) in scope_key
        ]
        scope_review = [
            term for term in category.review_terms if _match_key(term) in scope_key
        ]
        if not any((company_explicit, company_review, scope_explicit, scope_review)):
            continue
        matches.append(
            CategoryMatch(
                category=category,
                level="明确" if company_explicit or scope_explicit else "复核",
                company_keywords=_position_aware_terms(
                    company_explicit + company_review,
                    (company_key,),
                ),
                scope_keywords=_position_aware_terms(
                    scope_explicit + scope_review,
                    (scope_key,),
                ),
            )
        )
        matched_category_ids.add(category.category_id)

    province_matches = []
    province_policy_matches = []
    if province is not None:
        for rule in book.province_rules:
            if rule.province != province:
                continue
            if suppressed_category_ids.intersection(rule.category_ids):
                continue
            company_matched_terms = _matched_rule_terms(rule, company_key)
            scope_matched_terms = _matched_rule_terms(rule, scope_key)
            company_template_exclusion_terms = _matched_template_exclusion_terms(
                rule, company_key
            )
            scope_template_exclusion_terms = _matched_template_exclusion_terms(
                rule, scope_key
            )
            category_context = bool(matched_category_ids.intersection(rule.category_ids))
            actual_matched_terms = tuple(
                dict.fromkeys(company_matched_terms + scope_matched_terms)
            )
            only_broad_terms = bool(actual_matched_terms) and all(
                term in BROAD_PROVINCE_TERMS for term in actual_matched_terms
            )
            if rule.match_mode == "literal" and (
                company_matched_terms or scope_matched_terms
            ):
                province_matches.append(
                    ProvinceRuleMatch(
                        rule=rule,
                        company_matched_terms=company_matched_terms,
                        scope_matched_terms=scope_matched_terms,
                        needs_manual_confirmation=(
                            only_broad_terms and not category_context
                        ),
                        company_template_exclusion_terms=(
                            company_template_exclusion_terms
                        ),
                        scope_template_exclusion_terms=scope_template_exclusion_terms,
                    )
                )
            elif rule.match_mode in {"manual", "category-manual"} and category_context:
                province_matches.append(
                    ProvinceRuleMatch(
                        rule=rule,
                        company_matched_terms=(),
                        scope_matched_terms=(),
                        needs_manual_confirmation=True,
                        company_template_exclusion_terms=(
                            company_template_exclusion_terms
                        ),
                        scope_template_exclusion_terms=scope_template_exclusion_terms,
                    )
                )
        for rule in book.province_policy_rules:
            if rule.province != province:
                continue
            company_matched_terms = tuple(
                term for term in rule.match_terms if _match_key(term) in company_key
            )
            scope_matched_terms = tuple(
                term for term in rule.match_terms if _match_key(term) in scope_key
            )
            category_context = bool(matched_category_ids.intersection(rule.category_ids))
            if rule.match_mode == "literal" and (
                company_matched_terms or scope_matched_terms
            ):
                province_policy_matches.append(
                    ProvincePolicyMatch(
                        rule=rule,
                        company_matched_terms=company_matched_terms,
                        scope_matched_terms=scope_matched_terms,
                        needs_manual_confirmation=False,
                    )
                )
            elif rule.match_mode in {"manual", "category-manual"} and category_context:
                province_policy_matches.append(
                    ProvincePolicyMatch(
                        rule=rule,
                        company_matched_terms=(),
                        scope_matched_terms=(),
                        needs_manual_confirmation=True,
                    )
                )

    return CheckResult(
        book=book,
        company_name=original_company_name,
        original_scope=original_scope,
        province=province,
        province_source=province_source,
        matches=tuple(matches),
        province_rules=tuple(province_matches),
        province_policies=tuple(province_policy_matches),
    )


def _escape_markdown(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return re.sub(r"([\\`*{}\[\]()#+.!_|>~-])", r"\\\1", escaped)


def _escape_table_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"([\\`*{}\[\]()#+.!_>~-])", r"\\\1", escaped)
    escaped = escaped.replace("|", "&#124;")
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    return escaped.replace("\n", "<br>")


def _field_highlight_terms(result: CheckResult, field: str) -> Tuple[str, ...]:
    category_attribute = "company_keywords" if field == "company" else "scope_keywords"
    rule_attribute = (
        "company_matched_terms" if field == "company" else "scope_matched_terms"
    )
    national_category_ids = {
        item.category.category_id for item in result.matches
    }
    terms = []
    for item in result.matches:
        terms.extend(getattr(item, category_attribute))
    for item in result.province_rules:
        rule_terms = getattr(item, rule_attribute)
        if national_category_ids.intersection(item.rule.category_ids):
            rule_terms = tuple(
                term for term in rule_terms if term not in BROAD_PROVINCE_TERMS
            )
        terms.extend(rule_terms)
    for item in result.province_policies:
        terms.extend(getattr(item, rule_attribute))
    return tuple(dict.fromkeys(terms))


def _render_code_span(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if any(character in normalized for character in "|<>&\n"):
        escaped = html.escape(normalized, quote=False).replace("|", "&#124;")
        return "<code>{}</code>".format(escaped.replace("\n", "<br>"))

    longest_run = max(
        (len(match.group(0)) for match in re.finditer(r"`+", normalized)),
        default=0,
    )
    delimiter = "`" * (longest_run + 1)
    needs_padding = bool(normalized) and (
        normalized.startswith(("`", " ")) or normalized.endswith(("`", " "))
    )
    padding = " " if needs_padding else ""
    return "{}{}{}{}{}".format(
        delimiter, padding, normalized, padding, delimiter
    )


def _render_inline_code_text(
    value: str,
    terms: Sequence[str],
    excluded_spans: Sequence[Tuple[int, int]] = (),
) -> str:
    key, key_spans = _match_key_with_spans(value)
    if not key or not terms:
        return _escape_table_text(value)

    candidates = set()
    ordered_terms = sorted(
        terms,
        key=lambda term: (-len(_match_key(term)), term),
    )
    for term in ordered_terms:
        term_key = _match_key(term)
        if not term_key:
            continue
        search_from = 0
        while True:
            match_start = key.find(term_key, search_from)
            if match_start < 0:
                break
            match_end = match_start + len(term_key)
            start = key_spans[match_start][0]
            end = key_spans[match_end - 1][1]
            search_from = match_start + 1
            if any(start < excluded_end and excluded_start < end for excluded_start, excluded_end in excluded_spans):
                continue
            candidates.add((start, end))

    selected = []
    for start, end in sorted(
        candidates,
        key=lambda span: (-(span[1] - span[0]), span[0]),
    ):
        if any(start < selected_end and selected_start < end for selected_start, selected_end in selected):
            continue
        selected.append((start, end))
    selected.sort(key=lambda span: span[0])

    merged = []
    for start, end in selected:
        if merged and start == merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    selected = merged

    rendered = []
    cursor = 0
    for start, end in selected:
        rendered.append(_escape_table_text(value[cursor:start]))
        matched = value[start:end].replace("\r\n", "\n").replace("\r", "\n")
        rendered.append(
            "<br>".join(
                _render_code_span(line) if line else ""
                for line in matched.split("\n")
            )
        )
        cursor = end
    rendered.append(_escape_table_text(value[cursor:]))
    return "".join(rendered)


def _province_term_matches_category(term: str, category: Category) -> bool:
    term_key = _match_key(term)
    return bool(term_key) and any(
        _match_key(category_term) in term_key
        for category_term in category.explicit_terms + category.review_terms
    )


def _province_label_candidates(
    result: CheckResult,
    category_id: str,
) -> Tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            rule.approval_label
            for rule in result.book.province_rules
            if rule.province == result.province
            and category_id in rule.category_ids
        )
    )


def _ambiguous_national_type(category: Category) -> str:
    return "{}（全国规则，属地类型需确认）".format(
        category.preapproval_type
    )


def _terms_overlap(left: str, right: str) -> bool:
    left_key = _match_key(left)
    right_key = _match_key(right)
    return bool(left_key and right_key) and (
        left_key in right_key or right_key in left_key
    )


def _province_terms_for_field(
    result: CheckResult,
    field: str,
) -> Tuple[str, ...]:
    attribute = (
        "company_matched_terms" if field == "company" else "scope_matched_terms"
    )
    return tuple(
        dict.fromkeys(
            term
            for match in result.province_rules + result.province_policies
            for term in getattr(match, attribute)
        )
    )


def _term_fully_covered_by_province_matches(
    value_key: str,
    term: str,
    province_terms: Sequence[str],
) -> bool:
    term_spans = _occurrence_spans(value_key, _match_key(term))
    if not term_spans:
        return False
    province_spans = tuple(
        span
        for province_term in province_terms
        for span in _occurrence_spans(value_key, _match_key(province_term))
    )
    return bool(province_spans) and all(
        any(
            term_start < province_end and province_start < term_end
            for province_start, province_end in province_spans
        )
        for term_start, term_end in term_spans
    )


def _uncovered_national_terms(
    result: CheckResult,
    match: CategoryMatch,
) -> Tuple[str, ...]:
    company_key = _match_key(
        _mask_nationwide_non_rule_phrases(result.company_name)
    )
    scope_key = _match_key(
        _scope_for_matching(result.original_scope, result.province)
    )
    terms = []
    for field_terms, value_key, province_terms in (
        (
            match.company_keywords,
            company_key,
            _province_terms_for_field(result, "company"),
        ),
        (
            match.scope_keywords,
            scope_key,
            _province_terms_for_field(result, "scope"),
        ),
    ):
        for term in field_terms:
            if term in terms or _term_fully_covered_by_province_matches(
                value_key,
                term,
                province_terms,
            ):
                continue
            terms.append(term)
    return tuple(terms)


def _claimed_policy_template_refs(result: CheckResult) -> frozenset:
    return frozenset(
        (reference.rule_id, reference.template_name)
        for item in result.province_policies
        for reference in item.rule.template_refs
    )


def _explicit_policy_templates(
    result: CheckResult,
    item: ProvincePolicyMatch,
) -> Tuple[Tuple[str, str], ...]:
    rules_by_id = {rule.rule_id: rule for rule in result.book.province_rules}
    return tuple(
        dict.fromkeys(
            (template.name, template.url)
            for reference in item.rule.template_refs
            if reference.rule_id in rules_by_id
            for template in rules_by_id[reference.rule_id].templates
            if template.name == reference.template_name
        )
    )


def _generic_province_templates(
    result: CheckResult,
) -> Tuple[Tuple[str, str], ...]:
    if result.province is None:
        return ()
    return tuple(
        dict.fromkeys(
            (template.name, template.url)
            for rule in result.book.province_rules
            if rule.province == result.province
            for template in rule.templates
            if GENERIC_PROVINCE_TEMPLATE_NAME.search(template.name)
        )
    )


def _merge_material_rows(result: CheckResult) -> Tuple[MaterialRow, ...]:
    claimed_policy_template_refs = _claimed_policy_template_refs(result)
    generic_province_templates = _generic_province_templates(result)
    category_states = {}
    category_order = []

    def ensure_category(category_id: str):
        if category_id not in result.book.categories:
            return None
        if category_id not in category_states:
            category_states[category_id] = {
                "national_terms": [],
                "national_review_terms": [],
                "labels": {},
            }
            category_order.append(category_id)
        return category_states[category_id]

    def ensure_label(state, label: str):
        return state["labels"].setdefault(
            label,
            {
                "province_terms": [],
                "templates": [],
                "template_exclusion_terms": [],
                "has_review_match": False,
                "has_definite_match": False,
                "has_literal_match": False,
            },
        )

    def append_unique(values: list, additions: Sequence) -> None:
        for value in additions:
            if value not in values:
                values.append(value)

    def combine_label_states(primary, additions: Sequence):
        combined = {
            "province_terms": [],
            "templates": [],
            "template_exclusion_terms": [],
            "has_review_match": False,
            "has_definite_match": False,
            "has_literal_match": False,
        }
        for state in ((primary,) if primary is not None else ()) + tuple(additions):
            append_unique(combined["province_terms"], state["province_terms"])
            append_unique(combined["templates"], state["templates"])
            append_unique(
                combined["template_exclusion_terms"],
                state["template_exclusion_terms"],
            )
            for flag in (
                "has_review_match",
                "has_definite_match",
                "has_literal_match",
            ):
                combined[flag] = combined[flag] or state[flag]
        return combined

    for item in result.matches:
        category_id = item.category.category_id
        national_terms = _uncovered_national_terms(result, item)
        if not national_terms:
            continue
        state = ensure_category(category_id)
        append_unique(state["national_terms"], national_terms)
        append_unique(
            state["national_review_terms"],
            (
                term
                for term in national_terms
                if term in item.category.review_terms
                and term not in item.category.explicit_terms
            ),
        )
    national_category_ids = set(category_states)

    province_only = {}
    for item in result.province_rules:
        templates = tuple(
            (template.name, template.url)
            for template in item.rule.templates
            if (item.rule.rule_id, template.name)
            not in claimed_policy_template_refs
        )
        # A policy claims individual templates, not the entire owner rule. Keep
        # the ordinary rule when any unclaimed template remains; a genuinely
        # template-less rule still participates in the normal missing-template
        # rendering path.
        if item.rule.templates and not templates:
            continue
        linked = []
        unowned_terms = []
        terms_by_category = {}
        if item.rule.match_mode == "literal":
            if len(item.rule.category_ids) == 1 and ensure_category(
                item.rule.category_ids[0]
            ) is not None:
                linked = [item.rule.category_ids[0]]
                terms_by_category[linked[0]] = [
                    term
                    for term in item.matched_terms
                    if not (
                        linked[0] in national_category_ids
                        and term in BROAD_PROVINCE_TERMS
                    )
                ]
            else:
                for term in item.matched_terms:
                    owners = [
                        category_id
                        for category_id in item.rule.category_ids
                        if category_id in result.book.categories
                        and _province_term_matches_category(
                            term, result.book.categories[category_id]
                        )
                    ]
                    if not owners:
                        unowned_terms.append(term)
                    for category_id in owners:
                        terms_by_category.setdefault(category_id, []).append(term)
                for category_id in item.rule.category_ids:
                    if terms_by_category.get(category_id) and ensure_category(
                        category_id
                    ) is not None:
                        linked.append(category_id)
        else:
            linked = [
                category_id
                for category_id in item.rule.category_ids
                if category_id in national_category_ids
            ]
        if linked:
            for category_id in linked:
                state = ensure_category(category_id)
                label_state = ensure_label(state, item.rule.approval_label)
                if item.rule.match_mode == "literal":
                    label_state["has_literal_match"] = True
                if item.needs_manual_confirmation:
                    label_state["has_review_match"] = True
                else:
                    label_state["has_definite_match"] = True
                append_unique(
                    label_state["province_terms"],
                    terms_by_category.get(category_id, ()),
                )
                if item.template_exclusion_terms:
                    append_unique(
                        label_state["template_exclusion_terms"],
                        item.template_exclusion_terms,
                    )
                else:
                    append_unique(label_state["templates"], templates)
            if not unowned_terms:
                continue
        elif item.rule.match_mode == "literal" and not unowned_terms:
            unowned_terms = list(item.matched_terms)
        if not linked and not unowned_terms:
            continue

        local_path = province_only.setdefault(
            item.rule.approval_label,
            {
                "matched_terms": [],
                "templates": [],
                "template_exclusion_terms": [],
                "has_review_match": False,
                "has_definite_match": False,
            },
        )
        if item.needs_manual_confirmation:
            local_path["has_review_match"] = True
        else:
            local_path["has_definite_match"] = True
        for term in unowned_terms:
            if term not in local_path["matched_terms"]:
                local_path["matched_terms"].append(term)
        if item.template_exclusion_terms:
            for term in item.template_exclusion_terms:
                if term not in local_path["template_exclusion_terms"]:
                    local_path["template_exclusion_terms"].append(term)
        else:
            for template in templates:
                if template not in local_path["templates"]:
                    local_path["templates"].append(template)

    def make_category_path(
        category_id: str,
        label_state,
        national_terms: Sequence[str],
        province_first: bool = False,
    ) -> MaterialCategoryPath:
        category = result.book.categories[category_id]
        province_terms = tuple(
            label_state["province_terms"] if label_state is not None else ()
        )
        templates = tuple(
            label_state["templates"] if label_state is not None else ()
        )
        template_exclusion_terms = tuple(
            label_state["template_exclusion_terms"]
            if label_state is not None
            else ()
        )
        if not templates and not template_exclusion_terms:
            templates = generic_province_templates
        ordered_terms = (
            province_terms + tuple(national_terms)
            if province_first
            else tuple(national_terms) + province_terms
        )
        matched_terms = tuple(dict.fromkeys(ordered_terms))
        national_review_terms = tuple(
            term
            for term in national_terms
            if term in category_states[category_id]["national_review_terms"]
            and term not in province_terms
        )
        has_review_match = bool(
            label_state is not None and label_state["has_review_match"]
        )
        has_definite_match = bool(
            national_terms
            or (
                label_state is not None
                and label_state["has_definite_match"]
            )
        )
        return MaterialCategoryPath(
            category_id=category_id,
            category_label=_category_display_label(category.label),
            matched_terms=matched_terms,
            materials=category.materials,
            authority=category.authority,
            templates=templates,
            template_exclusion_terms=template_exclusion_terms,
            review_only=has_review_match and not has_definite_match,
            province_terms=province_terms,
            national_review_terms=national_review_terms,
        )

    category_paths = []
    for category_id in category_order:
        category = result.book.categories[category_id]
        state = category_states[category_id]
        national_terms = tuple(state["national_terms"])
        label_states = {
            label: label_state
            for label, label_state in state["labels"].items()
            if label_state["has_literal_match"]
        }
        support_states = tuple(
            label_state
            for label_state in state["labels"].values()
            if not label_state["has_literal_match"]
        )

        if len(label_states) == 1:
            label, label_state = next(iter(label_states.items()))
            label_state = combine_label_states(label_state, support_states)
            category_paths.append(
                (
                    label,
                    make_category_path(
                        category_id,
                        label_state,
                        national_terms,
                        province_first=(label != category.preapproval_type),
                    ),
                )
            )
            continue

        if len(label_states) > 1:
            national_terms_by_label = {label: [] for label in label_states}
            unresolved_national_terms = []
            for term in national_terms:
                owners = [
                    label
                    for label, label_state in label_states.items()
                    if any(
                        _terms_overlap(term, province_term)
                        for province_term in label_state["province_terms"]
                    )
                ]
                if len(owners) == 1:
                    national_terms_by_label[owners[0]].append(term)
                else:
                    unresolved_national_terms.append(term)
            for label, label_state in label_states.items():
                category_paths.append(
                    (
                        label,
                        make_category_path(
                            category_id,
                            label_state,
                            national_terms_by_label[label],
                            province_first=(label != category.preapproval_type),
                        ),
                    )
                )
            if unresolved_national_terms:
                support_state = combine_label_states(None, support_states)
                category_paths.append(
                    (
                        _ambiguous_national_type(category),
                        make_category_path(
                            category_id,
                            support_state,
                            unresolved_national_terms,
                        ),
                    )
                )
            continue

        candidates = _province_label_candidates(result, category_id)
        if len(candidates) == 1:
            display_type = candidates[0]
        elif len(candidates) > 1:
            display_type = _ambiguous_national_type(category)
        else:
            display_type = category.preapproval_type
        support_state = (
            combine_label_states(None, support_states)
            if support_states
            else None
        )
        category_paths.append(
            (
                display_type,
                make_category_path(category_id, support_state, national_terms),
            )
        )

    confirmation = "需向主管部门及华为云确认"
    province_paths = [
        (
            label,
            MaterialCategoryPath(
                category_id=None,
                category_label=label,
                matched_terms=tuple(values["matched_terms"]),
                materials=(confirmation,),
                authority=confirmation,
                templates=tuple(values["templates"]),
                template_exclusion_terms=tuple(
                    values["template_exclusion_terms"]
                ),
                review_only=(
                    values["has_review_match"]
                    and not values["has_definite_match"]
                ),
                province_terms=tuple(values["matched_terms"]),
            ),
        )
        for label, values in province_only.items()
    ]

    paths = category_paths + province_paths
    paths_by_type = {}
    for preapproval_type, path in paths:
        paths_by_type.setdefault(preapproval_type, []).append(path)
    return tuple(
        MaterialRow(preapproval_type=preapproval_type, paths=tuple(grouped_paths))
        for preapproval_type, grouped_paths in paths_by_type.items()
    )


def _category_display_label(label: str) -> str:
    return re.sub(r"（[^）]*）$", "", label)


def _render_basic_info(result: CheckResult, lines: list) -> None:
    company = _render_inline_code_text(
        result.company_name,
        _field_highlight_terms(result, "company"),
    )
    scope = _render_inline_code_text(
        result.original_scope,
        _field_highlight_terms(result, "scope"),
        excluded_spans=_excluded_spans(result.original_scope),
    )
    table = [
        "| 单位名称 | 经营范围 | 备案省份 | 规则版本 | 核对日期 |",
        "|---|---|---|---|---|",
        "| {} | {} | {} | {} | {} |".format(
            company or "未提供",
            scope,
            _escape_table_text(result.province or "未提供"),
            _escape_table_text(result.book.version),
            _escape_table_text(result.book.checked_at),
        ),
    ]
    lines.extend(["## 1. 基本信息", "\n".join(table)])


def _render_material_terms(result: CheckResult, row: MaterialRow) -> str:
    matched_terms = _position_aware_terms(
        row.matched_terms,
        (
            _match_key(result.company_name),
            _match_key(_scope_for_matching(result.original_scope)),
        ),
    )
    if not matched_terms:
        return "-"
    national_terms = {
        term
        for match in result.matches
        for term in match.keywords
    }
    province_terms = set(row.province_terms)
    return "、".join(
        "{}{}".format(
            _render_code_span(term),
            "（全国规则，需结合实际业务确认）"
            if term in national_terms and term not in province_terms
            else "",
        )
        for term in matched_terms
    )


def _render_path_values(row: MaterialRow, attribute: str) -> str:
    multiple_paths = len(row.paths) > 1
    rendered = []
    for path in row.paths:
        values = getattr(path, attribute)
        if isinstance(values, str):
            values = (values,)
        for value in values:
            prefix = (
                "{}：".format(_escape_table_text(path.category_label))
                if multiple_paths
                else ""
            )
            rendered.append("{}{}".format(prefix, _escape_table_text(value)))
    return "<br>".join(rendered)


def _missing_template_message(
    result: CheckResult,
    category_label: str,
) -> str:
    if result.province is None:
        return "未提供备案省份，无法匹配同省对应模板"
    return "未提供{}{}对应模板".format(
        _escape_table_text(result.province),
        _escape_table_text(category_label),
    )


def _render_templates(result: CheckResult, row: MaterialRow) -> str:
    multiple_paths = len(row.paths) > 1
    rendered = []
    for path in row.paths:
        prefix = (
            "{}：".format(_escape_table_text(path.category_label))
            if multiple_paths
            else ""
        )
        if path.template_exclusion_terms:
            rendered.append(
                "{}不适用：经营范围命中官网排除词 {}".format(
                    prefix,
                    "、".join(
                        _render_code_span(term)
                        for term in path.template_exclusion_terms
                    ),
                )
            )
        if not path.templates and not path.template_exclusion_terms:
            rendered.append(
                "{}{}".format(
                    prefix,
                    _missing_template_message(result, path.category_label),
                )
            )
        if not path.templates:
            continue
        for name, url in path.templates:
            rendered.append(
                "{}[{}]({})".format(prefix, _escape_markdown(name), url)
            )
    return "<br>".join(rendered)


def _category_context_terms(
    result: CheckResult,
    category_ids: Sequence[str],
) -> Tuple[str, ...]:
    category_id_set = set(category_ids)
    return tuple(
        dict.fromkeys(
            term
            for item in result.matches
            if item.category.category_id in category_id_set
            for term in item.keywords
        )
    )


def _policy_material_row(
    result: CheckResult,
    item: ProvincePolicyMatch,
) -> MaterialRow:
    confirmation = "需向主管部门及华为云确认"
    explicit_templates = _explicit_policy_templates(result, item)
    matched_terms = item.matched_terms or _category_context_terms(
        result, item.rule.category_ids
    )
    company_key = _match_key(result.company_name)
    scope_key = _match_key(_scope_for_matching(result.original_scope))
    paths = []
    for category_id in item.rule.category_ids:
        category = result.book.categories[category_id]
        templates = []
        exclusion_terms = []
        for rule in result.book.province_rules:
            if (
                rule.province != result.province
                or category_id not in rule.category_ids
            ):
                continue
            exclusions = _matched_template_exclusion_terms(
                rule, company_key
            ) + _matched_template_exclusion_terms(rule, scope_key)
            if exclusions:
                for term in exclusions:
                    if term not in exclusion_terms:
                        exclusion_terms.append(term)
                continue
            for template in rule.templates:
                value = (template.name, template.url)
                if value not in templates:
                    templates.append(value)
        paths.append(
            MaterialCategoryPath(
                category_id=category_id,
                category_label=_category_display_label(category.label),
                matched_terms=matched_terms,
                materials=category.materials,
                authority=category.authority,
                templates=tuple(templates),
                template_exclusion_terms=tuple(exclusion_terms),
                province_terms=matched_terms,
            )
        )
    if not paths:
        paths.append(
            MaterialCategoryPath(
                category_id=None,
                category_label=_category_display_label(item.rule.approval_label),
                matched_terms=matched_terms,
                materials=item.rule.materials or (confirmation,),
                authority=confirmation,
                templates=explicit_templates,
                province_terms=matched_terms,
            )
        )
    return MaterialRow(
        preapproval_type="{}（{}专项复核）".format(
            _category_display_label(item.rule.approval_label),
            result.province or "省级",
        ),
        paths=tuple(paths),
    )


def _render_materials(result: CheckResult, lines: list) -> None:
    table = [
        "| 前置审批类型 | 命中关键词 | 审批文件 | 批复单位 | 不涉及承诺书 | 提示 |",
        "|---|---|---|---|---|---|",
    ]
    rows = _merge_material_rows(result)
    if not rows and not result.province_policies:
        table.append(
            "| 未命中当前华为云备案规则中的关键词 | - | - | - | - | - |"
        )
    for row in rows:
        if all(path.category_id is None for path in row.paths):
            prompt = (
                "涉及：向主管部门及华为云确认需办理的类型、编号和文件。<br>"
                "不涉及：按审核意见提交承诺书或备注。"
            )
        elif row.template_exclusion_terms and not any(
            path.templates for path in row.paths
        ):
            prompt = (
                "涉及：填写审批号并上传许可证。<br>"
                "不涉及：经营范围命中官网排除词，不能使用该承诺书，"
                "请向主管部门及华为云确认处理方式。"
            )
        elif row.review_only:
            prompt = (
                "仅命中宽泛词，需核实实际业务。<br>"
                "涉及：填写审批号并上传许可证。<br>"
                "不涉及：先向批复单位确认，再按审核意见提交承诺书或备注。"
            )
        else:
            prompt = (
                "涉及：填写审批号并上传许可证。<br>"
                "不涉及：先向批复单位确认，再按审核意见提交承诺书或备注。"
            )
        table.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                _escape_table_text(row.preapproval_type),
                _render_material_terms(result, row),
                _render_path_values(row, "materials"),
                _render_path_values(row, "authority"),
                _render_templates(result, row),
                prompt,
            )
        )
    for item in result.province_policies:
        row = _policy_material_row(result, item)
        prompt = "<br>".join(
            _escape_table_text(value)
            for value in (item.rule.policy_text, item.rule.required_action)
        )
        table.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                _escape_table_text(row.preapproval_type),
                _render_material_terms(result, row),
                _render_path_values(row, "materials"),
                _render_path_values(row, "authority"),
                _render_templates(result, row),
                prompt,
            )
        )
    lines.extend(["## 2. 前置审批材料", "\n".join(table)])


def render_markdown(result: CheckResult) -> str:
    lines = ["# ICP 备案前置审批关键词核对结果"]
    for renderer in (_render_basic_info, _render_materials):
        renderer(result, lines)
    lines.append(
        "本结果仅依据单位名称、经营范围和华为云备案规则进行关键词初筛，"
        "不构成行政许可或法律结论，不保证备案通过。"
    )
    return "\n\n".join(lines) + "\n"


def _sha256_regular_file(path: Path, label: str, max_bytes: int) -> str:
    path = Path(path)
    descriptor = None
    digest = hashlib.sha256()
    try:
        initial = os.lstat(str(path))
        if stat.S_ISLNK(initial.st_mode):
            raise RuleError("{}不得是符号链接".format(label))
        if not stat.S_ISREG(initial.st_mode):
            raise RuleError("{}必须是普通文件".format(label))
        if initial.st_size > max_bytes:
            raise RuleError("{}过大".format(label))
        flags = os.O_RDONLY
        for name in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK"):
            flags |= getattr(os, name, 0)
        descriptor = os.open(str(path), flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise RuleError("{}必须是普通文件".format(label))
        if (
            opened.st_dev != initial.st_dev
            or opened.st_ino != initial.st_ino
            or opened.st_size != initial.st_size
        ):
            raise RuleError("{}在打开期间发生变化".format(label))
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise RuleError("{}过大".format(label))
            digest.update(chunk)
        final = os.fstat(descriptor)
        if (
            total != opened.st_size
            or final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_size != opened.st_size
            or final.st_mtime_ns != opened.st_mtime_ns
        ):
            raise RuleError("{}在读取期间发生变化".format(label))
    except RuleError:
        raise
    except OSError as exc:
        raise RuleError("无法读取{}：{}".format(label, exc)) from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    return digest.hexdigest()


def _diagnostic_record(book: RuleBook, rules_path: Path) -> dict:
    rules_path = Path(rules_path).resolve()
    script_path = Path(__file__).resolve()
    raw = _load_json(rules_path)
    raw_ride_categories = [
        item
        for item in raw.get("categories", [])
        if isinstance(item, dict) and item.get("id") == "RIDE"
    ]
    if len(raw_ride_categories) != 1:
        raise RuleError("诊断失败：categories[].id 必须唯一包含 RIDE")
    raw_ride = raw_ride_categories[0]
    if "RIDE" not in book.categories:
        raise RuleError("诊断失败：运行时 categories 缺少 RIDE")
    runtime_ride = book.categories["RIDE"]
    if runtime_ride.category_id != "RIDE":
        raise RuleError("诊断失败：Category.category_id 未映射为 RIDE")

    qinghai_rules = [
        rule
        for rule in book.province_rules
        if rule.rule_id == "PROV-080" and rule.province == "青海"
    ]
    if len(qinghai_rules) != 1:
        raise RuleError("诊断失败：未唯一找到青海 PROV-080")
    qinghai_rule = qinghai_rules[0]
    if "RIDE" not in qinghai_rule.category_ids:
        raise RuleError("诊断失败：青海 PROV-080 未关联 RIDE")

    result = analyze(
        book,
        "许可项目：网络预约出租车经营",
        province="青海",
        province_source="用户提供",
        company_name="青海北斗屋科技有限公司",
    )
    rendered = render_markdown(result)
    # The current Huawei matrix folds Qinghai's ride row into the province-wide
    # template. Keep the canary tied to the rule's single current template
    # rather than a historical display name.
    matching_templates = list(qinghai_rule.templates)
    if len(matching_templates) != 1:
        raise RuleError("诊断失败：青海 PROV-080 缺少唯一当前承诺书")
    canary_passed = all(
        value in rendered
        for value in (matching_templates[0].name, matching_templates[0].url)
    )
    if not canary_passed:
        raise RuleError("诊断失败：青海网约车结果未渲染承诺书")

    return {
        "status": "ok",
        "script_path": str(script_path),
        "rules_path": str(rules_path),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "script_sha256": _sha256_regular_file(
            script_path, "诊断脚本文件", MAX_RULES_BYTES
        ),
        "rules_sha256": _sha256_regular_file(
            rules_path, "诊断规则文件", MAX_RULES_BYTES
        ),
        "schema_version": book.schema_version,
        "rules_version": book.version,
        "raw_category_id_field": "id",
        "raw_ride_category_key": raw_ride["id"],
        "raw_ride_has_category_id_field": "category_id" in raw_ride,
        "runtime_ride_category_id": runtime_ride.category_id,
        "qinghai_rule_id": qinghai_rule.rule_id,
        "qinghai_category_ids": list(qinghai_rule.category_ids),
        "qinghai_templates": [
            {"name": template.name, "url": template.url}
            for template in qinghai_rule.templates
        ],
        "qinghai_canary_passed": canary_passed,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--rules")
    parser.add_argument("--company-name")
    parser.add_argument("--province")
    parser.add_argument("--province-source", default="未提供")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("scope", nargs="*")
    return parser


def _resolve_rules_path(args, references=None) -> Path:
    references = Path(
        references or Path(__file__).resolve().parents[1] / "references"
    )
    rules_path = Path(args.rules) if args.rules is not None else references / "huawei-rules.json"
    args.rules = str(rules_path)
    return rules_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        try:
            args = _parser().parse_args(argv)
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        if sys.version_info < MIN_PYTHON:
            print("错误：需要 Python 3.8 或更高版本", file=sys.stderr)
            return 127
        if args.diagnose:
            conflicting = (
                args.validate_only
                or args.company_name
                or args.province
                or args.scope
            )
            if conflicting:
                raise InputError("--diagnose 不能与其他操作或分析输入同时使用")
        _resolve_rules_path(args)
        book = load_rules(Path(args.rules))
        if args.diagnose:
            print(
                json.dumps(
                    _diagnostic_record(book, Path(args.rules)),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        if args.validate_only:
            listed = {rule.province for rule in book.province_rules}
            print(
                "规则校验通过：{}；{} 个全国类别、{} 条省份源规则、{} 条省级管局政策、{} 个已列省级地区。".format(
                    book.version,
                    len(book.categories),
                    len(book.province_rules),
                    len(book.province_policy_rules),
                    len(listed),
                )
            )
            return 0
        scope = " ".join(args.scope)
        if not args.company_name or not args.company_name.strip():
            raise InputError(
                "单位名称为空；请提供单位名称或上传可清晰识别的营业执照"
            )
        if not args.province:
            raise InputError(
                "备案省份为空；请提供备案省份或上传可清晰识别的营业执照"
            )
        result = analyze(
            book,
            scope,
            province=args.province,
            province_source=args.province_source,
            company_name=args.company_name,
        )
        print(render_markdown(result), end="")
        return 0
    except (RuleError, InputError) as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
