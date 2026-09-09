# IAM Agency creation and management — **optional** capability

> **⚠️ Agency is not required for this skill**: the default flow is "**no agency / no OBS upload**". You need to create an agency and authorize the bucket only when the user explicitly wants evolve-task results to land in their own OBS bucket.
>
> Therefore:
> - **Read results only locally / in the OptVerse console**: no agency needed; use `CreateEvolveTask --output_path=""`.
> - **Upload results to an OBS bucket**: follow §A to create the policy → §B to create the agency → §C to bind the policy → switch to [`agency-policy.md`](agency-policy.md) for bucket authorization.

OptVerse needs an "**agency**" to perform bucket authorization and cross-service writes.
An agency is an IAM resource created by the account admin within their own account, which then delegates authority to other accounts or service principals.

> **Key distinction (concept + list)**:
> - **Agency**: an IAM resource inside the account, describing "**who may act on my behalf**" (the trusted party). hcloud operations: `IAM CreateAgency` / `ListAgencies` etc.
> - **Bucket authorization (`AuthorizePermission`)**: with the agency in place, grant the current account's OBS bucket access to the backend service account (see [`agency-policy.md`](agency-policy.md)).
>
> Without an agency, calling `AuthorizePermission` returns `IAM.0025` / `AgencyNotFound`.
>
> **The Action lists are also independent — do not mix them up**:
> - **This document (`iam-agency.md`)**: the agency Action list the user grants to the **backend service account** `op_svc_oroas_container0` (`iam:agencies:assume` + 30 OBS Actions).
> - **[`iam-policies.md`](iam-policies.md)**: the permission list the account admin grants to **sub-accounts**.
>
> **Naming conventions**:
> - Custom policy name: `policy_ai4s_llma4ad` (recommended)
> - Agency name: **`optverse_service_trust` is mandatory** — this is the fixed trusted agency name; using a different name will break the bucket authorization and the downstream evolve-task flow

---

## 0. Recommend invoking the existing IAM skill first for initialization

Policy and agency initialization are **one-time, low-frequency** operations, common to every OptVerse / LLM4AD task. This skill **does not reinvent the wheel**; strongly recommend invoking the existing IAM management skill first:

| Skill | Path | Applies to |
|---|---|---|
| `huawei-cloud-iam-query` | `skills/security/iam/huawei-cloud-iam-query/SKILL.md` | IAM resource management (policies, agencies, bucket authorization, etc.) |

Usage (agent flow):

1. When the user first enters the "upload to OBS" link, **switch to `huawei-cloud-iam-query` skill** to complete policy / agency / binding initialization;
2. After initialization, **switch back to this skill** to continue bucket authorization (`OptVerse AuthorizePermission`) and the evolve-task chain;
3. When starting a new evolve task afterwards, this skill can jump straight to the create-task / monitor steps.

The hcloud commands in §3-§5 below are "**examples / quick reference**"; in practice, going through the IAM skill is more robust (it has built-in ACL, parameter validation, and accompanying query scripts).

---

## 1. Key concepts

| Concept | Explanation |
|---|---|
| `domain_id` | The account ID creating the agency (i.e. the delegator's account) |
| `trust_domain_id` / `trust_domain_name` | The trusted account (Optwhere's account) |
| `name` | Agency name, up to 64 chars |
| `description` | Description, up to 255 chars |
| `duration` | Agency lifetime: `FOREVER` / `ONEDAY` / custom number of days |

Optwhere's trusted account is fixed to **`op_svc_oroas_container0`** (the Optwhere official service account). When creating the agency, pass this value directly to `--agency.trust_domain_name`.

---

## 2. End-to-end creation flow (recommended order)

```text
1. Create custom policy   IAM CreateAgencyCustomPolicy     → policy_ai4s_llma4ad
2. Create agency          IAM CreateAgency                 → optverse_service_trust
3. Attach policy          IAM AttachAgencyPolicyV5         → associate custom policy id
4. Verify                 IAM ListAgencies / ShowAgency
```

Once the 4 steps above are done, **the OptVerse service** runs under this account's `optverse_service_trust` agency; then execute [`agency-policy.md`](agency-policy.md)'s `OptVerse AuthorizePermission` for the bucket authorization to take effect.

---

## 3. ① Create the custom policy (`policy_ai4s_llma4ad`)

The custom policy is the "list of capabilities" the agency holds. For the agency `optverse_service_trust`, the policy must at least include:

- `iam:agencies:assume`: lets the trusted party (`op_svc_oroas_container0`) act on behalf of this account
- A set of OBS Actions: lets the OptVerse service read/write OBS buckets under this account as the agency

```bash
hcloud IAM CreateAgencyCustomPolicy \
  --role.display_name="policy_ai4s_llma4ad" \
  --role.description="AI4S LLM4AD delegation policy" \
  --role.description_cn="LLM4AD cross-service delegation policy" \
  --role.type="AX" \
  --role.policy.Version="1.1" \
  --role.policy.Statement.1.Effect="Allow" \
  --role.policy.Statement.1.Action.1="iam:agencies:assume" \
  --role.policy.Statement.1.Action.2="obs:bucket:CreateBucket" \
  --role.policy.Statement.1.Action.3="obs:bucket:DeleteBucket" \
  --role.policy.Statement.1.Action.4="obs:bucket:DeleteBucketPolicy" \
  --role.policy.Statement.1.Action.5="obs:bucket:GetBucketAcl" \
  --role.policy.Statement.1.Action.6="obs:bucket:GetBucketLocation" \
  --role.policy.Statement.1.Action.7="obs:bucket:GetBucketPolicy" \
  --role.policy.Statement.1.Action.8="obs:bucket:GetBucketQuota" \
  --role.policy.Statement.1.Action.9="obs:bucket:GetBucketStorage" \
  --role.policy.Statement.1.Action.10="obs:bucket:GetBucketStoragePolicy" \
  --role.policy.Statement.1.Action.11="obs:bucket:GetEncryptionConfiguration" \
  --role.policy.Statement.1.Action.12="obs:bucket:HeadBucket" \
  --role.policy.Statement.1.Action.13="obs:bucket:ListAllMyBuckets" \
  --role.policy.Statement.1.Action.14="obs:bucket:ListBucket" \
  --role.policy.Statement.1.Action.15="obs:bucket:ListBucketMultipartUploads" \
  --role.policy.Statement.1.Action.16="obs:bucket:PutBucketAcl" \
  --role.policy.Statement.1.Action.17="obs:bucket:PutBucketPolicy" \
  --role.policy.Statement.1.Action.18="obs:bucket:PutBucketQuota" \
  --role.policy.Statement.1.Action.19="obs:bucket:PutEncryptionConfiguration" \
  --role.policy.Statement.1.Action.20="obs:bucket:PutLifecycleConfiguration" \
  --role.policy.Statement.1.Action.21="obs:object:AbortMultipartUpload" \
  --role.policy.Statement.1.Action.22="obs:object:DeleteObject" \
  --role.policy.Statement.1.Action.23="obs:object:DeleteObjectVersion" \
  --role.policy.Statement.1.Action.24="obs:object:GetObject" \
  --role.policy.Statement.1.Action.25="obs:object:GetObjectAcl" \
  --role.policy.Statement.1.Action.26="obs:object:GetObjectVersion" \
  --role.policy.Statement.1.Action.27="obs:object:GetObjectVersionAcl" \
  --role.policy.Statement.1.Action.28="obs:object:ListMultipartUploadParts" \
  --role.policy.Statement.1.Action.29="obs:object:PutObject" \
  --role.policy.Statement.1.Action.30="obs:object:PutObjectAcl" \
  --role.policy.Statement.1.Action.31="obs:object:PutObjectVersionAcl" \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="role"
```

> The OBS Action list in the Policy Body is defined by company IAM ops; if the Action scope needs adjustment, edit it in the IAM console under "Modify Policy" rather than going through the CLI again (to avoid missing Actions).

Key return fields:

| Field | Purpose |
|---|---|
| `id` | Policy ID (`policy_id`), used later in `AttachAgencyPolicyV5` |
| `display_name` | Policy display name `policy_ai4s_llma4ad` |

> **Policy scope**: `Action` must include `iam:agencies:assume`; this is the prerequisite for the OptVerse service-side stub to take on its role. The full OBS Actions let the agency read/write the bucket.

---

## 4. ② Create the agency (`optverse_service_trust`)

```bash
hcloud IAM CreateAgency \
  --agency.domain_id=<my-account-id> \
  --agency.name="optverse_service_trust" \
  --agency.description="Trust agency for OptVerse code evolution" \
  --agency.duration="FOREVER" \
  --agency.trust_domain_name="op_svc_oroas_container0" \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="agency"
```

> The agency name is fixed to `optverse_service_trust` (user-specified). The trusted domain is fixed to `op_svc_oroas_container0` (the OptVerse official service account), meaning "this agency delegates my identity to this account".

Parameter details:

| Parameter | Required | Notes |
|---|---|---|
| `--agency.domain_id` | Yes | Creator's account ID (your own) |
| `--agency.name` | Yes | Agency name (≤ 64 chars) |
| `--agency.description` | No | Description (≤ 255 chars) |
| `--agency.duration` | No | `FOREVER` / `ONEDAY` / custom days (default `FOREVER`) |
| `--agency.trust_domain_id` | At least one of `trust_domain_id` / `trust_domain_name` | Trusted party's account ID |
| `--agency.trust_domain_name` | At least one of `trust_domain_id` / `trust_domain_name` | Trusted party's account name, fixed to `op_svc_oroas_container0` |

`agency.id` in the return body is the `agency_id` used by the subsequent `AttachAgencyPolicyV5`.

---

## 5. ③ Bind the custom policy to the agency

```bash
hcloud IAM AttachAgencyPolicyV5 \
  --agency_id=<agency-id> \
  --policy_id=<policy-id> \
  --cli-region=<region>
```

Visible relation after binding:

| Item | Value |
|---|---|
| Policy name | `policy_ai4s_llma4ad` |
| Agency name | `optverse_service_trust` |
| Trust domain | `op_svc_oroas_container0` (OptVerse service) |

---

## 6. Policy Action set

The full Action list is given in the flat-parameter version in §3; this file does not duplicate it.

> Note: §3 in this document is the "**agency given to the backend service**" Action set, which is independent from the "**permissions given to sub-accounts**" Action set in [`iam-policies.md`](iam-policies.md) §3 — **do not mix them up**.

---

## 7. Query / update / delete

```bash
# Details
hcloud IAM ShowAgency \
  --agency_id=<agency-id> \
  --domain_id=<my-account-id> \
  --cli-region=<region>

# List
hcloud IAM ListAgencies --domain_id=<my-account-id> \
  --cli-region=<region>

# Update (modify description / trust domain / duration)
hcloud IAM UpdateAgency \
  --agency_id=<agency-id> \
  --domain_id=<my-account-id> \
  --agency.description="new description" \
  --cli-region=<region>

# Detach a policy (does NOT delete the policy itself)
hcloud IAM DetachAgencyPolicyV5 \
  --agency_id=<agency-id> \
  --policy_id=<policy-id> \
  --cli-region=<region>

# Delete (dangerous, two-step confirmation)
hcloud IAM DeleteAgency \
  --agency_id=<agency-id> \
  --domain_id=<my-account-id> \
  --cli-region=<region>
```

> **Before deleting the agency, confirm**: every `AuthorizePermission` relation that depends on it will be reclaimed; subsequent task calls will all fail.

---

## 8. Collaboration with existing IAM skill

Initialization of policies and agencies is recommended to be done via [`skills/security/iam/huawei-cloud-iam-query`](../../../../security/iam/huawei-cloud-iam-query/SKILL.md). This skill uses the same set of `hcloud IAM …` operations; if the IAM skill has already prepared `policy_ai4s_llma4ad` + `optverse_service_trust`, this skill can start directly from the "bucket authorization" step.

---

## 9. Troubleshooting

See [`troubleshooting.md`](troubleshooting.md) §3 "Agency / bucket authorization errors" — the `IAM.*` rows.