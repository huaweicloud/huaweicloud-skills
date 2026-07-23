from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    ERROR = "error"
    REJECTION = "rejection"
    USER_REPORT = "user_report"
    SUGGESTION = "suggestion"


class FeedbackStatus(Enum):
    OPEN = "open"
    PROMOTED = "promoted"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"


@dataclass
class DialogTurn:
    turn_index: int
    role: str
    content: str
    timestamp: datetime
    thinking: str | None = None


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
    product_name: str | None = None
    voice_source: str | None = None
    more_details: dict[str, str] | None = None
