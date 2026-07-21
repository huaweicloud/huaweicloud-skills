# Verification Method

## Pipeline Verification

### Phase 0: Install Check

```bash
# Check skill directory exists
ls -la skills/{skill-name}/SKILL.md

# Check required subdirectories
ls -la skills/{skill-name}/references/
ls -la skills/{skill-name}/scripts/
ls -la skills/{skill-name}/templates/
```

### Phase 1: Skill Analysis

```bash
# Run analysis
bash scripts/tier1/phase-1-skill-analysis.sh skills/{skill-name}
```

### Phase 4: Test Execution

```bash
# Run all test cases
bash scripts/tier1/phase-4-execute-tests.sh skills/{skill-name}
```

## Output Verification

Check that phase summary JSON files are generated:

```bash
ls -la skills/{skill-name}/phase-*-summary.json
```
