#!/usr/bin/env python3
"""Private, scope-bound checkpoint helpers for resumable Skill CLIs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import hcloud_common

MAX_CHECKPOINT_BYTES = 32 * 1024 * 1024


class CheckpointError(ValueError):
    """Describe one safe checkpoint rejection with a stable public error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def scope_sha256(scope: dict[str, Any]) -> str:
    """Return a deterministic digest for the cloud-read scope owned by a caller."""
    encoded = json.dumps(
        scope,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checkpoint_document(
    *,
    contract: str,
    scope: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Build one versioned, scope-bound checkpoint document."""
    return {
        "contract": contract,
        "scope_sha256": scope_sha256(scope),
        "scope": scope,
        "state": state,
    }


def write_checkpoint(
    path: Path,
    *,
    contract: str,
    scope: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Atomically write a private checkpoint and return its artifact receipt."""
    return hcloud_common.write_json_artifact(
        path,
        checkpoint_document(contract=contract, scope=scope, state=state),
    )


def load_checkpoint(
    path: Path,
    *,
    contract: str,
    scope: dict[str, Any],
) -> dict[str, Any]:
    """Load a private checkpoint only when its contract and read scope match."""
    target = path.expanduser().absolute()
    if not target.exists():
        raise CheckpointError("CHECKPOINT_NOT_FOUND", f"Checkpoint file does not exist: {target}")
    if target.is_symlink() or not target.is_file():
        raise CheckpointError("CHECKPOINT_INVALID", "Checkpoint must be a regular non-symlink file.")
    metadata = target.stat()
    if metadata.st_mode & 0o077:
        raise CheckpointError(
            "CHECKPOINT_PERMISSIONS_INVALID",
            "Checkpoint permissions must not grant group or other access.",
        )
    if metadata.st_size > MAX_CHECKPOINT_BYTES:
        raise CheckpointError("CHECKPOINT_TOO_LARGE", "Checkpoint exceeds the supported size limit.")
    try:
        document = hcloud_common.load_json(target)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointError("CHECKPOINT_INVALID", f"Checkpoint is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("state"), dict):
        raise CheckpointError("CHECKPOINT_INVALID", "Checkpoint must contain an object state.")
    if document.get("contract") != contract:
        raise CheckpointError(
            "CHECKPOINT_CONTRACT_MISMATCH",
            f"Checkpoint contract does not match {contract}.",
        )
    if document.get("scope_sha256") != scope_sha256(scope):
        raise CheckpointError(
            "CHECKPOINT_SCOPE_MISMATCH",
            "Checkpoint belongs to a different query scope; start a fresh checkpoint.",
        )
    return document
