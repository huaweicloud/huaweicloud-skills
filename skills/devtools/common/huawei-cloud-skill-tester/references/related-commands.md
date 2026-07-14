# Command Quick Reference

> Related command quick reference for huawei-cloud-skill-tester.

## npx skills Commands

| Command | Description |
|---------|-------------|
| `npx skills add <repo> --skill <name>` | Install a Skill |
| `npx skills list` | List installed Skills |
| `npx skills remove <name>` | Remove a Skill |
| `npx skills inspect <name> --format yaml` | View Skill metadata |

## hcloud Commands

| Command | Description |
|---------|-------------|
| `hcloud --version` | View CLI version |
| `hcloud configure list` | View authentication configuration |
| `hcloud configure set --region=<r>` | Set default region |
| `hcloud <Service> --help` | View service operation list |
| `hcloud <Service> List<Resources> --region=<r>` | Read-only query (idempotent) |

## Test Script Commands

| Command | Description |
|---------|-------------|
| `bash scripts/validate-skill.sh <path> --phase <phase>` | Installation verification |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase <phase>` | Execute tests |
| `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2>` | Hallucination detection |
| `bash scripts/generate-report.sh <dir> --output <path>` | Generate report |

## --phase Parameter Values

| Value | Description |
|-------|-------------|
| `install` | Phase 1: Installation verification |
| `all-install` | Phase 1: All installation verification |
| `basic` | Phase 2: Basic functionality |
| `trigger` | Phase 2: Trigger accuracy |
| `boundary` | Phase 2: Boundary/exception |
| `compare` | Phase 2: With/Without comparison |
| `all-basic` | Phase 2: All basic functionality |
| `identify-related` | Phase 3: Identify related Skills |
| `combination` | Phase 3: Combination scenarios |
| `competition` | Phase 3: Competition test |
| `isolation` | Phase 3: Context isolation |
| `all-combination` | Phase 3: All combination tests |
| `solution` | Phase 4: Solution |
| `performance` | Phase 4: Performance metrics |
| `report` | Phase 4: Generate report |
| `full` | All four phases |
