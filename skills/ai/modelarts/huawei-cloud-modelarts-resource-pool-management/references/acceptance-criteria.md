# Acceptance Criteria

## Functional Requirements

- [x] All 53 operations documented in SKILL.md
- [x] All 10 functional domains covered
- [x] CLI commands verified available in hcloud
- [x] Write operations require user confirmation
- [x] Destructive operations show warnings
- [x] Error handling documented
- [x] `--pool_name` documented as resource metadata.name (from `ListPools`), not the display label name — fixes ISSUE-001 (P2/P3/P4)
- [x] CreatePool flavor constraints documented (.d suffix required; e.g. `modelarts.vm.cpu.8ud` cannot create pools) — fixes ISSUE-002
- [x] BatchResetPoolNodes / BatchResizePoolNodes VM availability limits documented in main SKILL.md — fixes ISSUE-002
- [x] Overview declares explicit "only ModelArts, not OBS/ECS" scope boundary — fixes ISSUE-003
- [x] CLI installation guide covers KooCLI env-var auth (HUAWEICLOUD_SDK_AK/SK) and --cli-access-key/--cli-secret-key — fixes ISSUE-004

## Non-Functional Requirements

- [x] SKILL.md follows Huawei Cloud Skill Specification
- [x] YAML frontmatter with name, description, tags
- [x] Triggers include section in description
- [x] IAM policies documented (least privilege)
- [x] Data flow diagram provided
- [x] CLI installation guide provided
- [x] Verification method documented

## Test Coverage

- [ ] Read operations tested (list/show/query)
- [ ] Write operations tested with confirmation flow
- [ ] Error handling tested for common failures
- [ ] All 10 functional domains have at least one test case
