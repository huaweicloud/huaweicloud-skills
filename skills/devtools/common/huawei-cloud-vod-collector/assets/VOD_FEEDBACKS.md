# VoD Feedback Record

## Metadata
- **feedback_id**: VOD-YYYYMMDD-NNNN
- **feedback_type**: error | rejection | user_report
- **timestamp**: ISO 8601
- **session_id**: <session_id>
- **platform**: openclaw | hermes | generic
- **confidence**: 0.0-1.0
- **status**: open | promoted | resolved | discarded

## Error Information (feedback_type=error)
- **error_type**: command_failure | api_error | timeout
- **error_message**: <message>
- **error_stack**: <stack_trace>

## Context (extracted)
- **user_intent**: <inferred intent>
- **agent_action**: <agent behavior>
- **dialog_context**: <conversation turns>
  - [N] role: <full content, never truncate>
  - [N] role: <content>
    - [thinking]: <AI chain-of-thought, for assistant turns only>
- **environment**: <env metadata>

## Dedup
- **recurrence_count**: <count>
- **dedup_key**: <session_id + command + error_type>

## Annotations
- <annotation labels>