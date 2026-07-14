# Verification Method

## Phase 1: Installation Verification

```bash
bash scripts/validate-skill.sh <skill-path> --phase all-install
# Expected output: [PASS] All installation checks passed
```

Pass criteria:
- SKILL.md exists and is readable
- YAML Frontmatter has valid name, description (5-point), version, tags
- Recommended directories (references/, scripts/, templates/, demo/) present or warned
- CLI dependency (hcloud) available and authenticated

## Phase 2: Basic Functionality Testing

```bash
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-basic
# Expected: pass_rate >= 0.9, trigger_accuracy >= 0.9
```

Pass criteria:
- Trigger identification accuracy >= 90%
- Core use case output structure complete
- Boundary/exception cases handled without fabrication
- No false triggers on unrelated requests
- With/Without comparison shows quantified value delta > 0

## Phase 3: Combination Compatibility Testing

```bash
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-combination --related <skill2>
# Expected: hallucination_rate < 0.05, no conflict errors
```

Pass criteria:
- No responsibility confusion (invoked Skill == expected Skill)
- No parameter fabrication (values within valid range)
- No workflow stitching errors (actual steps == expected sequence)
- No context pollution (Task B output independent of Task A)
- No format hallucination (output matches specification)

## Phase 4: Solution-Level Testing

```bash
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase solution --scenario <name>
# Expected: full pipeline passes, performance within thresholds
```

Pass criteria:
- End-to-end scenario completes successfully
- Performance metrics within thresholds:
  - total_time_seconds < 300s
  - total_tokens < 50000
  - accuracy_rate > 0.9
  - hallucination_rate < 0.05
  - trigger_accuracy > 0.9

## Full Pipeline Verification

```bash
bash scripts/test-skill.sh <skill-name> \
  --skill-path <skill-path> \
  --phase full \
  --related <skill2,skill3> \
  --scenario <scenario-name> \
  --output ./test-report.yaml
```

All four phases must pass. A YAML test report is generated at the specified output path.
