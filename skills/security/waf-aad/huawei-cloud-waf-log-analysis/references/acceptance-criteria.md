# Acceptance Criteria

## Analysis Report Quality

A generated analysis report must meet ALL of the following criteria:

### Completeness
- [ ] Report includes total event count for the queried time range
- [ ] At least 3 dimensions analyzed (from: attack type, source IP, target domain, target URL, geo, time trend)
- [ ] Each dimension shows actual data values (not placeholders or examples)
- [ ] Time range is clearly stated in the report header

### Accuracy
- [ ] All statistics are derived from actual `ListEvent` API responses
- [ ] Attack type codes are correctly mapped to human-readable names
- [ ] Percentages sum to approximately 100% for each breakdown dimension
- [ ] Timestamps are converted from milliseconds to human-readable format

### Actionability
- [ ] Rule recommendations reference specific observed patterns (not generic advice)
- [ ] Each recommendation includes: what was observed → what rule to add → expected effect
- [ ] Recommendations are prioritized by impact (highest-frequency attack patterns first)
- [ ] For rule recommendations, enough configuration detail is provided to act on them

### Presentation
- [ ] Top attacking IPs include geographic context (country/region)
- [ ] Target URLs show which attack types are directed at them
- [ ] Time trends highlight peak periods and anomalies
- [ ] Report is structured with clear sections and tables

## Rule Recommendation Quality

Each rule recommendation must satisfy:

| Criterion | Description |
|-----------|-------------|
| Evidence-based | Reference specific events/IPs/patterns from the analysis |
| Specific | Name the exact rule type (precise access control, CC protection, etc.) |
| Configurable | Provide enough parameter detail for rule creation |
| Safe | Warn if recommendation might affect legitimate traffic |
| Prioritized | Ordered by urgency/frequency of the observed attack pattern |

## Failure Modes

The analysis is considered incomplete if:
- Total event count is 0 and no alternative time range was suggested
- Only one dimension was analyzed when more data was available
- Recommendations are generic ("consider enabling protection") without referencing specific observed data
- Statistics contain hardcoded example numbers instead of real query results
