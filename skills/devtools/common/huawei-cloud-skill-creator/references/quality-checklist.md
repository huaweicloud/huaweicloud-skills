# Quality Checklist

> Check each item after creating a Skill to ensure compliance. Run `bash scripts/validate-skill.sh {skill-path}` for automated checks.

## Required Items (must pass to publish)

### SKILL.md Structure

- [ ] SKILL.md file exists
- [ ] YAML Frontmatter is properly wrapped with `---`
- [ ] `name` field exists and is non-empty
- [ ] `name` follows `{platform}-{product}-{function}` naming formula
- [ ] `description` field exists and is non-empty
- [ ] `description` includes functional scope (point 1)
- [ ] `description` includes trigger conditions (point 2)
- [ ] `description` includes value description (point 3)
- [ ] `description` includes usage pattern (point 4)
- [ ] `description` includes prerequisites (point 5)
- [ ] `tags` field exists with 3-8 tags
- [ ] `version` field exists and follows SemVer (MAJOR.MINOR.PATCH)

### Body Structure

- [ ] Contains "Overview" section
- [ ] Contains "Main Steps" section
- [ ] Each step has clear CLI commands
- [ ] Key parameters have configuration notes
- [ ] Each operation notes required permissions
- [ ] Provides 3-5 typical usage examples
- [ ] Body line count ≤ 500

### Security

- [ ] No hardcoded AK/SK in SKILL.md
- [ ] No hardcoded AK/SK in scripts
- [ ] Secrets obtained via environment variables
- [ ] Write/delete operations have user confirmation prompts
- [ ] High-risk operations have dry-run option documentation
- [ ] Contains security operations section (must follow + must avoid)
- [ ] Contains User-Agent identification documentation

### Permissions

- [ ] `references/iam-policies.md` exists
- [ ] Query operations are listed
- [ ] Mutation operations are listed
- [ ] Includes minimum privilege policy JSON
- [ ] High-risk operations note MFA requirement

### Authentication

- [ ] Auth method is clearly specified (AK/SK / CLI config / temporary token / IAM role)
- [ ] CLI config flow has security reminder

## Recommended Items (may publish without, but should improve)

### Reference Docs

- [ ] `references/cli-installation-guide.md` exists
- [ ] `references/verification-method.md` exists
- [ ] `references/acceptance-criteria.md` exists
- [ ] `references/related-commands.md` exists
- [ ] All references/ files linked in SKILL.md exist
- [ ] Each ref file focuses on one problem
- [ ] Ref files have brief header description
- [ ] Large files (>300 lines) have TOC at top

### Directory Structure

- [ ] Skill is in the correct domain directory
- [ ] Scripts in scripts/ have shebang (#!/bin/bash or #!/usr/bin/env python3)
- [ ] Scripts in scripts/ have parameter validation and error handling
- [ ] Python script directory has `__init__.py`
- [ ] Node.js scripts use `.mjs` extension
- [ ] Templates use curly brace placeholders `{placeholder}`

### Content Quality

- [ ] Code blocks specify language type
- [ ] CLI commands have correct syntax (runnable)
- [ ] Common errors have solutions (edge cases section)
- [ ] Operation success verification methods are documented
- [ ] Script usage documentation included (if scripts/ exists)

### Version Management

- [ ] Version number follows SemVer
- [ ] Branch strategy is documented (main / preview)
- [ ] Deprecation strategy is documented

## Scoring

| Grade | Required Items | Recommended Items | Description |
|-------|---------------|-------------------|-------------|
| A | All pass | ≥ 80% | Ready for official release |
| B | All pass | ≥ 50% | Publishable, needs follow-up improvement |
| C | All pass | < 50% | Publishable, quality needs improvement |
| D | Has failures | — | Not publishable, must fix |
