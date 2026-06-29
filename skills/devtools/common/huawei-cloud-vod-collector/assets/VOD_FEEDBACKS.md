# VoD Feedback Record

## Metadata
- **feedback_id**: VOD-YYYYMMDD-NNNN
- **feedback_type**: error | rejection | user_report | suggestion
- **timestamp**: ISO 8601
- **session_id**: <session_id>
- **platform**: openclaw | hermes | generic
- **confidence**: 0.0-1.0
- **status**: open | promoted | resolved | discarded
- **product_name**: <product/skill name>

## Error Information
- **error_type**: command_failure | api_error | timeout | service_error | configuration_issue
- **error_message**: <message>
- **error_stack**:
  ```
  【问题描述】
  <problem_description>

  【复现场景】
  <occurrence_scenario>

  【预期行为】
  <expected_behavior>

  【实际行为】
  <actual_behavior>

  【错误堆栈】
  <stack_trace>
  ```

## Context (extracted)
- **user_intent**: <inferred intent>
- **agent_action**:
  ```
  <agent behavior>
  ```
- **user_expected**: <what user expected to happen>
- **dialog_context**: <conversation turns>
  - [N] role: <full content, never truncate>
  - [N] role: <content>
    - [thinking]: <AI chain-of-thought, for assistant turns only>
- **environment**: <env metadata>

## Dedup
- **recurrence_count**: <count>
- **dedup_key**: <session_id + command + error_type>

## More Details (optional)
- <key>: <value> (e.g. summary, additional_info, etc.)

## Annotations
- <annotation labels>
