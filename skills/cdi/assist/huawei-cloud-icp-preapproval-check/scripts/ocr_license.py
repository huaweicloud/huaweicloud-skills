"""Local OCR fallback for Chinese business-license images.

The host agent should use its native image OCR first. This module is only a
local fallback and deliberately emits candidates and warnings instead of
making filing or legal decisions.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROVINCES = (
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
)

_SCOPE_STOP_LABELS = (
    "统一社会信用代码",
    "社会信用代码",
    "住所",
    "法定代表人",
    "负责人",
    "注册资本",
    "成立日期",
    "营业期限",
    "登记机关",
    "企业类型",
    "类型",
    "注册号",
    "许可项目",
    "一般项目",
    "经营场所",
)


class OcrError(Exception):
    """Base class for expected OCR fallback errors."""


class OcrDependencyError(OcrError):
    """Raised when the optional RapidOCR dependency is unavailable."""


class OcrInputError(OcrError):
    """Raised when the image path cannot be used."""


def _clean_line(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"[\t\r\n ]+", "", text)
    return text.strip()


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        value = _clean_line(value)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _value_after_label(line: str, labels: Sequence[str]) -> Optional[str]:
    for label in labels:
        match = re.match(r"^{}\s*[：:]?\s*(.*)$".format(re.escape(label)), line)
        if match:
            value = _clean_line(match.group(1))
            return value or None
    return None


def _contains_stop_label(line: str) -> Optional[Tuple[int, str]]:
    matches = [
        (line.find(label), label)
        for label in _SCOPE_STOP_LABELS
        if line.find(label) >= 0
    ]
    return min(matches, key=lambda item: item[0]) if matches else None


def _extract_scope(lines: Sequence[str]) -> Optional[str]:
    start = None
    first_value = None
    for index, line in enumerate(lines):
        value = _value_after_label(line, ("经营范围",))
        if value is not None:
            start = index
            first_value = value
            break
    if start is None:
        return None

    parts = []
    if first_value:
        parts.append(first_value)
    for line in lines[start + 1 :]:
        stop = _contains_stop_label(line)
        if stop is not None:
            prefix = _clean_line(line[: stop[0]])
            if prefix:
                parts.append(prefix)
            break
        cleaned = _clean_line(line)
        if cleaned:
            parts.append(cleaned)
    scope = _clean_line("".join(parts))
    return scope or None


def extract_fields(raw_lines: Iterable[str]) -> Dict[str, Any]:
    """Extract conservative business-license field candidates from OCR lines."""

    lines = _unique(raw_lines)
    company_name = next(
        (
            value
            for line in lines
            for value in [_value_after_label(line, ("企业名称", "名称"))]
            if value
        ),
        None,
    )
    scope = _extract_scope(lines)

    address = next(
        (
            value
            for line in lines
            for value in [_value_after_label(line, ("住所", "经营场所"))]
            if value
        ),
        None,
    )
    province_candidates = [
        province for province in PROVINCES if address and province in address
    ]

    warnings = []
    if company_name is None:
        warnings.append("未识别单位名称")
    if scope is None:
        warnings.append("未识别经营范围")
    if not province_candidates:
        warnings.append("未识别备案省份，请人工提供")
    elif len(province_candidates) > 1:
        warnings.append("省份候选不唯一，请人工确认备案省份")

    return {
        "company_name": company_name,
        "scope": scope,
        "province_candidates": province_candidates,
        "warnings": warnings,
    }


def _load_engine() -> Any:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        raise OcrDependencyError(
            "未安装 rapidocr_onnxruntime；请运行 "
            "python -m pip install -r requirements-ocr.txt"
        ) from exc
    return RapidOCR()


def _recognize_lines(engine: Any, image_path: Path) -> List[str]:
    try:
        output = engine(str(image_path))
    except Exception as exc:
        raise OcrInputError("OCR 无法读取图片：{}".format(exc)) from exc

    result = output[0] if isinstance(output, tuple) else output
    if not result:
        return []

    lines = []
    for item in result:
        if isinstance(item, dict):
            text = item.get("text") or item.get("rec_text")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            text = item[1]
        else:
            text = None
        if text:
            lines.append(str(text))
    return _unique(lines)


def _error_payload(code: str, message: str) -> str:
    return json.dumps(
        {"error": code, "message": message},
        ensure_ascii=False,
        sort_keys=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用本地 RapidOCR 读取营业执照图片并输出 JSON 候选字段"
    )
    parser.add_argument("--image", required=True, help="营业执照图片路径")
    parser.add_argument("--pretty", action="store_true", help="格式化 JSON 输出")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = _parser().parse_args(argv)
        image_path = Path(args.image).expanduser()
        if not image_path.exists():
            raise OcrInputError("图片文件不存在：{}".format(image_path))
        if not image_path.is_file():
            raise OcrInputError("图片路径不是普通文件：{}".format(image_path))
        if image_path.stat().st_size == 0:
            raise OcrInputError("图片文件为空：{}".format(image_path))

        engine = _load_engine()
        lines = _recognize_lines(engine, image_path)
        if not lines:
            raise OcrInputError("OCR 未识别出文字，请提供更清晰的图片")
        fields = extract_fields(lines)
        payload = {
            "engine": "rapidocr_onnxruntime",
            "image": str(image_path),
            "lines": lines,
            "raw_text": "\n".join(lines),
            **fields,
        }
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
                sort_keys=bool(args.pretty),
            )
        )
        return 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    except OcrDependencyError as exc:
        message = str(exc)
        if "requirements-ocr.txt" not in message:
            message += "；请运行 python -m pip install -r requirements-ocr.txt"
        print(_error_payload("ocr_dependency_missing", message), file=sys.stderr)
        return 2
    except OcrInputError as exc:
        code = "image_not_found" if "不存在" in str(exc) else "ocr_input_error"
        print(_error_payload(code, str(exc)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
