#!/usr/bin/env python3
"""Shared lightweight data shapes for Huawei Cloud CLI planning scripts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandPlan:
    """A planned hcloud command with execution metadata."""

    service: str
    operation: str
    command: list[str]
    mode: str
    dryrun_required: bool = False
    expect_json: bool = True
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class RiskAssessment:
    """Risk classification for a planned cloud operation."""

    level: str
    reasons: list[str]
    requires_confirmation: bool
    dryrun_required: bool
    verification_required: bool
    hard_guard: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class ExecutionResult:
    """Normalized command execution result."""

    success: bool
    return_code: int | None
    command: list[str]
    parsed_json: Any = None
    error_type: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    """Normalized verification result for job/resource/network/protocol checks."""

    scope: str
    success: bool
    status: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass
class TaskState:
    """Minimal task-level state for audit, resume, and final reporting."""

    task_type: str
    region: str | None = None
    project_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)
    commands: list[dict[str, Any]] = field(default_factory=list)
    dryrun_result: dict[str, Any] | None = None
    submit_result: dict[str, Any] | None = None
    job_id: str | None = None
    resource_ids: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)
