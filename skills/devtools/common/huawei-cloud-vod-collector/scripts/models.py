from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    ERROR = "error"
    REJECTION = "rejection"
    USER_REPORT = "user_report"


class FeedbackStatus(Enum):
    OPEN = "open"
    PROMOTED = "promoted"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReqStatus(Enum):
    OPEN = "open"
    PROMOTED = "promoted"
    RESOLVED = "resolved"


class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"


class Stage(Enum):
    CAPTURE = "capture"
    EXTRACTION = "extraction"
    REFINEMENT = "refinement"
    DELIVERY = "delivery"


class StageStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    DEGRADED = "degraded"


class RejectionType(Enum):
    EXPLICIT_CORRECTION = "explicit_correction"
    EXPLICIT_REJECTION = "explicit_rejection"
    IMPLICIT_DISSATISFACTION = "implicit_dissatisfaction"


class EventType(Enum):
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    POST_TOOL_USE = "post_tool_use"
    ERROR = "error"
    USER_REPORT = "user_report"


class ReportStatus(Enum):
    COLLECTING = "collecting"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class DialogTurn:
    turn_index: int
    role: str
    content: str
    timestamp: datetime
    thinking: str | None = None


@dataclass
class DialogContext:
    session_id: str
    turns: list[DialogTurn]
    total_turns: int


@dataclass
class ExceptionSignal:
    error_type: str
    error_message: str
    exit_code: int | None = None
    tool_name: str | None = None
    duration_ms: int | None = None


@dataclass
class RejectionSignal:
    rejection_type: RejectionType
    confidence: float
    user_expression: str
    agent_response_ref: str


@dataclass
class PlatformInfo:
    platform_type: str
    platform_version: str | None = None
    os_info: str | None = None
    session_id: str | None = None


@dataclass
class FeedbackRecord:
    feedback_id: str
    feedback_type: FeedbackType
    timestamp: datetime
    session_id: str
    platform: str
    error_type: str | None = None
    error_message: str | None = None
    error_stack: str | None = None
    user_intent: str | None = None
    agent_action: str | None = None
    user_expected: str | None = None
    dialog_context: list[DialogTurn] | None = None
    environment: dict[str, str] | None = None
    confidence: float = 0.0
    status: FeedbackStatus = FeedbackStatus.OPEN
    recurrence_count: int = 1
    dedup_key: str | None = None
    annotations: list[str] = field(default_factory=list)
    problem_description: str | None = None
    occurrence_scenario: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    product_name: str | None = None
    more_details: dict[str, str] | None = None


@dataclass
class RequirementRecord:
    requirement_id: str
    title: str
    description: str
    priority: Priority
    domain: str
    status: ReqStatus = ReqStatus.OPEN
    suggested_action: str | None = None
    source_feedbacks: list[str] = field(default_factory=list)
    recurrence_count: int = 1
    see_also: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_at: datetime | None = None
    delivery_channel: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    annotations: list[str] = field(default_factory=list)


@dataclass
class UserReport:
    report_id: str
    problem_description: str
    occurrence_scenario: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    linked_requirement_id: str | None = None
    status: ReportStatus = ReportStatus.COLLECTING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StageReport:
    stage: Stage
    stage_status: StageStatus
    input_count: int
    output_count: int
    duration_ms: int
    details: dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PriorityWeights:
    recurrence: float = 0.4
    severity: float = 0.4
    confidence: float = 0.2


@dataclass
class DedupResult:
    merged_count: int = 0
    created_count: int = 0
    degraded: bool = False
    details: list[str] = field(default_factory=list)


@dataclass
class DeliveryResult:
    written_files: list[str] = field(default_factory=list)
    notified_ids: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)