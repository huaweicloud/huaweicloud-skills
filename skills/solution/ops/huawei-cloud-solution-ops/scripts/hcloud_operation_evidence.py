#!/usr/bin/env python3
"""Compose paired operation evidence fields for internal Skill consumers.

The underlying behavior and dependency profile files remain authoritative.
This module is a read-only accessor, not another fact store or a public
workflow entrypoint.
"""

from __future__ import annotations

from typing import Any

import hcloud_dependency_evidence
import hcloud_operation_behavior


def operation_evidence_fields(
    service: str,
    operation: str,
    *,
    behavior_profiles: dict[str, Any] | None = None,
    dependency_profiles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the profiled evidence fields available for one operation.

    Missing evidence is omitted so this additive view preserves the existing
    output shape for unprofiled operations. Both source readers return deep
    copies, preventing a consumer from mutating the published fact documents.
    """

    fields: dict[str, Any] = {}
    behavior = hcloud_operation_behavior.find_operation_behavior(
        service,
        operation,
        profiles=behavior_profiles,
    )
    if behavior is not None:
        fields["operation_behavior"] = behavior

    dependency = hcloud_dependency_evidence.find_dependency_evidence(
        service,
        operation,
        profiles=dependency_profiles,
    )
    if dependency is not None:
        fields["dependency_evidence"] = dependency
    return fields
