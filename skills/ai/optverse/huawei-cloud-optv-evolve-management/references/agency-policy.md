# OBS Bucket Authorization via Agency — **optional** chain

> When an evolve task's `output_path` points to a user-owned OBS bucket (e.g. `obs://test-ai4s/result`), the OptVerse service needs permission to operate that bucket first — otherwise the task will fail.
>
> **The entire chain (agency + bucket authorization) is optional**:
> - No upload needed → skip all steps in this document; use `--output_path=""`.
> - Upload needed → follow the "**agency first, then authorize**" flow below.
>
> See [`iam-agency.md`](iam-agency.md) for agency creation. This skill recommends agency name `optverse_service_trust` and custom policy name `policy_ai4s_llma4ad`.

---

## 1. Agency vs authorization

| Operation | Nature | Tool | Required? |
|---|---|---|---|
| Create custom policy | One-time resource setup | `IAM CreateAgencyCustomPolicy` | **Optional** (only when upload is needed) |
| Create agency | One-time resource setup | `hcloud IAM CreateAgency` | **Optional** (only when upload is needed) |
| Attach custom policy | One-time relation setup | `hcloud IAM AttachAgencyPolicyV5` | **Optional** (only when upload is needed) |
| Grant OptVerse service bucket permission | One-time policy publish | `hcloud OptVerse AuthorizePermission` | **Optional** (only when upload is needed) |
| Start evolve task | Business runtime | `hcloud OptVerse StartEvolveTask` | **Required** |

`AuthorizePermission` grants the current account's specified bucket access to the backend service account (i.e. `op_svc_oroas_container0`, the trusted party specified when creating the agency), so the service can read/write OBS as the agency's delegate. **This operation requires the IAM Agency to already exist.**

> Note: `AuthorizePermission` does not take an Action list itself — the OBS Actions are injected internally by a default policy; this document does not maintain that Action list.
>
> The agency's capability list (including `iam:agencies:assume` plus a set of OBS action permissions) is defined together when creating the custom policy in [`iam-agency.md`](iam-agency.md) §3.

---

## 2. Authorization commands

```bash
# 1) Make sure custom policy policy_ai4s_llma4ad + agency optverse_service_trust exist
hcloud IAM ListAgencies --domain_id=<my-account-id> \
  --cli-region=<region> --cli-output=json
# Recommended policy name: policy_ai4s_llma4ad
# Recommended agency name: optverse_service_trust
# See iam-agency.md §3-§5

# 2) Grant the backend service account (op_svc_oroas_container0) access to your bucket
hcloud OptVerse AuthorizePermission \
  --project_id=<project_id> --bucket=<your-bucket> \
  --cli-region=<region> \
  --cli-output=json
```

After successful execution, subsequent `CreateEvolveTask --output_path=obs://<your-bucket>/xxx` will upload data correctly.

---

## 3. Query and revoke

```bash
# View existing authorization relations
hcloud OptVerse ListPermission \
  --project_id=<project_id> --cli-region=<region> --cli-output=json

# List buckets visible under the current account
hcloud OptVerse ListBuckets \
  --project_id=<project_id> --cli-region=<region> --cli-output=json

# Revoke authorization (dangerous, two-step confirmation; does NOT affect the underlying IAM Agency)
hcloud OptVerse RevokePermission \
  --project_id=<project_id> --bucket=<your-bucket> \
  --cli-region=<region>
```

---

## 4. When re-authorization is needed

| Scenario | Re-authorize? |
|---|---|
| Same account, same bucket | No (first-time auth is enough) |
| Cross-account shared bucket | Yes, and the agency needs cross-account authorization (see iam-agency.md) |
| Bucket deleted and recreated with the same name | Yes |
| User manually deletes the agency / agency is reclaimed | Yes |
| **Task itself does not need upload** | **No IAM/bucket operation needed**, just `--output_path=""` |

## 5. Troubleshooting

See [`troubleshooting.md`](troubleshooting.md) §3 "Agency / bucket authorization errors".

---

## 6. Relation with IAM system policies

`AuthorizePermission` itself requires the user to have `OptVerse:llm4ad:authorizePermission` (see [`iam-policies.md`](iam-policies.md) for details).

The agency's lifecycle is managed by the account admin via `IAM CreateAgency` / `ListAgencies` / `ShowAgency` / `UpdateAgency` / `DeleteAgency`; this skill does not delete agencies on its own.