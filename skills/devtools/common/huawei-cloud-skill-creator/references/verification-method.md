# Verification Method - huawei-cloud-skill-creator-skill

> Read this file when verifying that a generated Skill complies with the specification.

## Automated Verification

Use `scripts/validate-skill.sh` for automated checks:

```bash
bash scripts/validate-skill.sh {generated-skill-path}
```

Verification covers: SKILL.md structure, Frontmatter completeness, naming conventions, AK/SK security, references links, body line count, etc.

## Manual Verification Checklist

### Structural Verification

1. Directory structure complete: SKILL.md + references/ + scripts/ (as needed) + templates/ (as needed)
2. SKILL.md YAML Frontmatter format correct
3. All referenced files in references/ exist

### Content Verification

1. description contains 5 structured points
2. Each step has CLI commands
3. Provides 3-5 usage examples
4. AK/SK not hardcoded
5. iam-policies.md contains minimum privilege policy JSON

### Functional Verification

1. CLI command syntax correct (verify via CLI help output)
2. Parameter names match CLI help output
3. Region parameter uses valid values

## Functional Testing Method

> Read this section when testing generated Skill's CLI commands, API calls, or SDK operations.

### Automated Testing (Recommended)

Use the automated test script to run all CLI functional tests:

```bash
bash scripts/test-cli-commands.sh {skill-path}
```

This single command extracts all `hcloud` commands from SKILL.md and references/, runs `--help` for syntax verification, executes read-only live tests (List/Show/Get with `--limit=1`), and generates `references/test-report.md`.

Equivalent one-liner via validate-skill.sh:

```bash
bash scripts/validate-skill.sh {skill-path} --phase functional-test
```

### Manual Testing (Fallback)

If hcloud CLI is not available, follow the manual testing steps below.

### Credential Privacy Notice

Before testing, check if the Skill requires credentials (AK/SK, tokens, passwords, API keys). If so, **ask the user** to provide them. Never log or display private keys.

### CLI Syntax Verification (Dry-Run)

```bash
# Run --help on every command listed in SKILL.md
hcloud {SERVICE} {OPERATION} --help
```

**Success indicator:** CLI returns help text without errors. All expected parameters are listed.

### Read-Only Live Test (Safe)

```bash
# Execute read-only operations with minimal data
hcloud {SERVICE} List{Resources} --cli-region={region} --limit=1
hcloud {SERVICE} Show{Resource} --cli-region={region} --{resource}_id={id}
```

**Success indicator:** Returns valid JSON/data without errors. Confirms API endpoint and IAM permissions work.

### Mutation Operation Safety Check

**Do NOT execute Create/Update/Delete commands live.** Only verify parameters:

```bash
hcloud {SERVICE} Create{Resource} --help
```

### SDK Method Verification

```bash
# Python SDK example
python3 -c "import huaweicloudsdk{service}; help(huaweicloudsdk{service}.{client_class})" 2>/dev/null || echo "SDK not installed"
```

### Test Report

Save results to `references/test-report.md` in the generated Skill (see format template).

### Semantic Validation

> Read this section when the Skill queries financial, usage, or metric data where field semantics can be ambiguous.

**Problem:** API responses often return multiple numeric fields with similar names (`total_amount`, `available_amount`, `cash_balance`, `recharge_amount`). A common mistake is using `recharge_amount` (充值总额) as the "balance" when the actual remaining balance is in a different field.

**Validation procedure when querying financial/metric data:**

1. Execute the live read-only query and capture the raw JSON response
2. For each numeric field that could represent the intended value:
   - Check its name against known semantics (`balance` / `available` / `remaining` = what's left; `total` / `recharge` / `累计` = historical sum)
   - Cross-reference values: if values differ significantly, the smaller one is more likely the remaining balance
3. If still ambiguous after API docs and cross-referencing → **ask the user** which field is correct
4. Once confirmed, add a semantic note to the generated SKILL.md, e.g.:

```markdown
> **Note on balance field:** This Skill uses `available_amount` (available balance) to
> represent the user's remaining account balance. Do NOT use `total_amount` or
> `recharge_amount` which represent total recharged amount, not remaining balance.
```

5. Include the semantic confirmation in the test report

## Verification Scoring

| Grade | Condition | Description |
|-------|-----------|-------------|
| A | All required pass, WARN ≤ 2 | Ready for official release |
| B | All required pass, WARN ≤ 5 | Publishable, needs improvement |
| C | All required pass, WARN > 5 | Publishable, quality needs improvement |
| D | Required checks failed | Not publishable |
