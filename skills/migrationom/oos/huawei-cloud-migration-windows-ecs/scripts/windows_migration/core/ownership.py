#!/usr/bin/env python3
"""
资源属主标识与判定 — OwnerID 指纹算法。

设计（自动化 + 人工可审）：
  - 指纹派生: owner_id = base32( HMAC(migration_ak, SALT || project_id) )[:8]
              ak 缺失时退化为 SHA256(SALT || project_id)（离线仍可算）
              对同一账号/项目/密钥恒定，不可逆防伪造。
  - 三重判属主（任一命中即 owned）:
      1) Tags: owner_id tag == derived（首选，稳定）
      2) 名称: derived in resource.name（Tag 丢失/被删兜底）
      3) 会话清单: config/owned_resources.json 中精确 ID 记录
                 （本 skill 创建后即记录；含历史资源、无 Tag 名称被改资源）
  - 非属主 = 只读/复用，禁止任何更改/删除（安全红线由调用方 enforce）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ---- 固定盐与 Tag 键（发布时固化，不可中途变更，否则历史资源无法识别） ----
OWNER_SALT = "huawei-cloud-migration-windows-ecs:v1"
OWNER_TAG_KEY = "owner"
OWNER_TAG_VALUE = "huawei-cloud-migration-windows-ecs"
OWNER_ID_TAG = "owner_id"
NAME_PREFIXES = ("vpc-mig-", "subnet-mig-", "sg-mig-", "eip-mig-")

_STATE_REL = Path("config") / "owned_resources.json"


def derive_owner_id(project_id: str, ak: str = "", salt: str = OWNER_SALT,
                    owner_tag_value: str = OWNER_TAG_VALUE) -> str:
    """派生 OwnerID 指纹（8 字符，不可逆）。同参数恒定输出，跨项目天然隔离。"""
    msg = f"{salt}||{owner_tag_value}||{project_id}".encode("utf-8")
    key = (ak or "").encode("utf-8")
    if key:
        digest = hmac.new(key, msg, hashlib.sha256).digest()
    else:
        digest = hashlib.sha256(msg).digest()
    return base64.b32encode(digest[:5]).decode("ascii")[:8]


def owner_tag_pairs(owner_id: str, owner_tag_key: str = OWNER_TAG_KEY,
                    owner_tag_value: str = OWNER_TAG_VALUE) -> list:
    return [
        {"key": owner_tag_key, "value": owner_tag_value},
        {"key": OWNER_ID_TAG, "value": owner_id},
    ]


def name_with_owner(prefix: str, host: str, owner_id: str, ts: str = "",
                    name_prefixes: tuple = NAME_PREFIXES) -> str:
    """统一生成带属主指纹的资源名：<prefix>-<host[:16]>-<owner_id>[-<ts>]。

    保证总长 <= 64（华为云资源名称上限），任何 <>/敏感词占位符一律先清洗。
    """
    clean = "".join(c if (c.isalnum() or c in "_-") else "-" for c in (host or "migrate"))
    clean = clean.strip("-")[:16] or "migrate"
    base = f"{prefix}-{clean}-{owner_id}"
    if ts:
        base = f"{base}-{ts[:10]}"
    return base[:64]


def _tags_dict(resource: dict) -> dict:
    """提取资源 tags（支持 server.tags / publicip.tags / vpc.tags 等嵌套或平铺）。"""
    tags = resource.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    out = {}
    for t in tags:
        if isinstance(t, dict) and t.get("key"):
            out[t["key"]] = t.get("value", "")
    return out


# ---- 会话属主清单（config/owned_resources.json）----

def _state_path(base_dir: Path) -> Path:
    p = Path(base_dir) / _STATE_REL if base_dir else Path(_STATE_REL)
    return p


def load_owned(base_dir: Path | None = None) -> dict:
    p = _state_path(base_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("属主清单解析失败，按空处理: %s", p)
    return {"owner_id": "", "resources": {}}


def save_owned(base_dir: Path | None, data: dict) -> Path:
    p = _state_path(base_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def record_owned(base_dir: Path, rtype: str, rid: str, name: str, owner_id: str,
                 state: str = "using") -> None:
    """创建资源后记录（幂等）。rtype: vpc|subnet|sg|ecs|eip|task；state: using/free。"""
    data = load_owned(base_dir)
    data.setdefault("owner_id", owner_id)
    data.setdefault("resources", {})[rid] = {
        "type": rtype,
        "name": name,
        "owner_id": owner_id,
        "state": state,
        "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    save_owned(base_dir, data)
    logger.info("属主清单记录(%s): %s %s (%s)", state, rtype, rid, name)


def list_owned_by_type(base_dir: Path, owner_id: str, rtype: str) -> list:
    """按类型列出会话属主资源（rtype: vpc|subnet|sg|ecs|eip|task）。"""
    data = load_owned(base_dir)
    out = []
    for rid, rec in (data.get("resources") or {}).items():
        if rec.get("owner_id") == owner_id and rec.get("type") == rtype:
            out.append({"id": rid, **rec})
    return out


def remove_owned(base_dir: Path, rid: str, owner_id: str) -> bool:
    """删除清单记录（资源已回收）。仅允许匹配 owner_id 的记录。"""
    data = load_owned(base_dir)
    res = data.get("resources") or {}
    rec = res.get(rid)
    if rec and rec.get("owner_id") == owner_id:
        del res[rid]
        save_owned(base_dir, data)
        logger.info("属主清单移除: %s (%s)", rid, rec.get("name"))
        return True
    return False


def is_owned(base_dir: Path, resource: dict, derived_owner_id: str,
             rtype: str = "") -> bool:
    """三重判属主：Tags 指纹 → 名称指纹 → 会话清单 ID。"""
    rid = str(resource.get("id") or resource.get("task_id") or resource.get("vm_id") or "")
    name = str(resource.get("name") or resource.get("alias") or "")
    # 1) Tags 指纹
    tags = _tags_dict(resource)
    if tags.get(OWNER_ID_TAG) == derived_owner_id:
        return True
    # 2) 名称指纹
    if derived_owner_id and derived_owner_id in name:
        return True
    # 3) 会话清单
    if rid:
        data = load_owned(base_dir)
        rec = (data.get("resources") or {}).get(rid)
        if rec and rec.get("owner_id") == derived_owner_id:
            return True
    return False


def require_owned(base_dir: Path, resource: dict, derived_owner_id: str,
                  rtype: str = "", action: str = "") -> None:
    """红线：非属主资源禁止更改/删除。不满足直接抛异常。"""
    if not is_owned(base_dir, resource, derived_owner_id, rtype):
        from core.exceptions import SmsApiError
        rid = resource.get("id") or resource.get("name") or "?"
        raise SmsApiError(
            f"资源 {rtype or ''} {rid} 非本 skill 属主（owner_id 不匹配），"
            f"禁止执行 {action or '变更/删除'}。属主资源可全权操作；"
            "非属主资源仅允许只读复用。",
            detail={"resource": resource.get("name") or resource.get("id")},
        )
