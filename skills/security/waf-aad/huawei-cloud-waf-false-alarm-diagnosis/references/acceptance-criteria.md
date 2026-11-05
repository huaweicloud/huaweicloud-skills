# Acceptance Criteria

## Diagnosis Completeness

- [ ] Step 1 produced concrete `host_id` / `policy_id` / `protect_status` for the reported domain (or an explicit "domain not protected here" finding)
- [ ] Step 2 enumerated the reported blocking events for the domain+time+IP with `rule`, `attack_type`, `action`, `url`, `payload`
- [ ] ListEvent paging/分段 handling documented when >10,000 records or a >30-day window is involved
- [ ] Step 3 produced an explicit verdict (false positive YES/NO/UNCERTAIN) with evidence referencing the hit rule/payload and business context

## Accuracy

- [ ] All rule IDs / policy IDs / host IDs come from actual query results, never guessed
- [ ] Priority-chain order respected when pinpointing the blocking rule and recommending a release method
- [ ] Recommendation follows: global whitelist (ignore matched feature) > IP whitelist (fixed source IP) > log-only observation; never disables web basic protection first
- [ ] Timestamps converted from milliseconds to human-readable when presented

## Read-Only Compliance (MANDATORY)

- [ ] Zero `Create*` / `Update*` / `Delete*` commands were executed by the agent
- [ ] All release/rollback commands were handed to the user as copy-paste-ready text
- [ ] No credentials (AK/SK), full config, or project secrets exposed in output

## Actionability & Rollback

- [ ] Each recommendation states: observed event → which rule likely blocked it → exact release command → expected effect
- [ ] Final report includes before/after event comparison
- [ ] Rollback guide provided: delete whitelist/ignore rule, restore protect_status=1

## Presentation

- [ ] Report structured with clear sections: findings, verdict, blocked-rule location, recommendation, verification, rollback