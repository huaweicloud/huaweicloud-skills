# Troubleshooting — huawei-cloud-iam-manage

| Error | Root cause → Fix |
| ----- | ---------------- |
| 403 AccessDenied on write | Caller lacks the IAM permission → add the corresponding `iam:...` grant (see `references/iam-policies.md`) |
| `PAP5.0001`-style deny on user/login/AK-SK writes | Account **SCP** (organization Service Control Policy) explicitly denies it — environment restriction, not skill defect → verify the org SCP; groups/policies/agencies are unaffected |
| User already exists | Duplicate name → pre-check `ListUsersV5`; choose a different name |
| 409 Conflict on policy attach | Policy already attached → verify with `ListAttachedUserPoliciesV5` |
| Policy cannot be deleted | Policy still attached to entities or is a **system** policy → detach first or try a custom policy id |
| Agency create fails (`PAP5.0011` / trust policy rejected) | `CreateAgencyV5 --trust_policy` JSON is validated strictly by the platform — **use the legacy `CreateAgency`** with `--agency.domain_id` + `--agency.name` + `--agency.trust_domain_name` (or `trust_domain_id`); the platform generates the trust policy automatically |
| Agency delete appears to do nothing | `DeleteAgencyV5` returns rc=0 but leaves the agency behind — **use the legacy `DeleteAgency --agency_id=...`**, then read back with `ListAgenciesV5` to confirm absence; retry if it still exists |
| `ListAgenciesV5 --name` rejected / ignored | `ListAgenciesV5` has **no `--name` filter** (only `--limit` / `--marker` / `--path_prefix`). Match by name **client-side**: run the full list, filter `agencies[].name == {agency_name}` → `agency_id`. Never pass `--name` to `ListAgenciesV5` |
| Legacy `DeleteAgency` returns 404 for a `ListAgenciesV5`-listed id | **V5/legacy agency id namespace mismatch** — an agency created via V5 (or a legacy id listed by `ListAgenciesV5`) may not be addressable the same way by the legacy API. Verify which interface created the agency; if 404 persists, re-list (`ListAgenciesV5`) after deleting and double-check the id, or use a V5-listable path consistently |
| ListAgenciesV5 empty but agencies exist | Wrong region / different account → verify `--cli-region` and the authenticated account |
| ListCustomPolicies returns 400 | `--page` and `--per_page` must be passed **together** → e.g. `--page=1 --per_page=100` |
| SK not seen after create | Response not captured (network/partner output) → the SK is only returned **once**; delete and re-create |
| `--password` prompts for disambiguation | Body `password` collides with the KooCLI system param → answer `b` at the prompt, or use `--cli-jsonInput=<file>` (see SKILL.md Core Commands) |
| `--limit=1` rejected on some operations | Test-framework boundary variant only — IAM List interfaces accept `--limit`; Attach/Detach/Show/Update do not. Use the documented parameters; not a skill defect (disclosed for reference) |
| hcloud not authenticated | No profile configured → run `hcloud configure set` (KooCLI reads `~/.hcloud/config.json` only; AK/SK environment variables such as `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK` are **not** read by KooCLI and cannot authenticate it) |
