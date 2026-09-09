# IAM permission policies (account admin grants sub-accounts)

OptVerse uses IAM for authorization; the corresponding action namespace is `OptVerse:llm4ad:<action>`. Agencies use a separate IAM namespace, `iam:agencies:<action>`, and custom policies use `iam:roles:<action>`.

> **Key distinction (two Action lists are independent)**:
> - **This document (`iam-policies.md`)**: the permission list the **account admin grants to sub-accounts**.
> - **[`iam-agency.md`](iam-agency.md) §3**: the Action list the user grants to the **backend service account** `op_svc_oroas_container0` (contains 30 OBS Actions + `iam:agencies:assume`).
>
> These two Action sets share **no overlap**; do not confuse them.

> **Default account permissions**:
> - **The account admin has all needed permissions by default** (the full LLM4AD action set + agency / custom-policy management); with the admin's AK/SK, no permission grants are typically needed and all skill operations work directly.
> - **Only sub-accounts need to worry about permissions**: if a sub-account's AK/SK is used and the call returns `APIGW.0303` / `IAM.0008` / `IAM.0043` etc., add actions to the sub-account per this document. Retry after adding.
>
> The default scenario (`--output_path=""`) only needs the `OptVerse:llm4ad:*` action set; the upload scenario additionally involves `iam:agencies:*` and `iam:roles:*`.

> **The entire agency + IAM resource-permission chain is optional** — only needed when uploading to OBS.

The sections below list the actions this skill touches and the recommended grouping when an account admin grants a sub-account.

---

## 1. OptVerse (LLM4AD) permissions

> This action set is required for every scenario (even when not uploading).

### 1.1 Running code-evolution scenario

| Action | Type | Purpose |
|---|---|---|
| `OptVerse:llm4ad:createAlgorithm` | ReadWrite | Create design project |
| `OptVerse:llm4ad:deleteAlgorithm` | ReadWrite | Delete algorithm project |
| `OptVerse:llm4ad:listAlgorithms` | ListOnly | List algorithms |
| `OptVerse:llm4ad:listDirectoryByAlgorithmId` | ListOnly | List algorithm directory |
| `OptVerse:llm4ad:listDirectoryByResultCommitId` | ListOnly | List result directory |
| `OptVerse:llm4ad:saveAlgorithmFile` | ReadWrite | Save algorithm file |
| `OptVerse:llm4ad:importAlgorithmFile` | ReadWrite | Import ZIP file |
| `OptVerse:llm4ad:getAlgorithm` | ReadOnly | Get algorithm fields |
| `OptVerse:llm4ad:getAlgorithmFile` | ReadOnly | Get algorithm file |
| `OptVerse:llm4ad:updateAlgorithm` | ReadWrite | Update algorithm |
| `OptVerse:llm4ad:createEvolveTask` | ReadWrite | Create evolve task |
| `OptVerse:llm4ad:deleteEvolveTask` | ReadWrite | Delete evolve task |
| `OptVerse:llm4ad:batchDeleteEvolveTask` | ReadWrite | Batch-delete tasks |
| `OptVerse:llm4ad:updateEvolveTask` | ReadWrite | Update evolve task |
| `OptVerse:llm4ad:startEvolveTask` | ReadWrite | Start task |
| `OptVerse:llm4ad:stopEvolveTask` | ReadWrite | Stop task |
| `OptVerse:llm4ad:listEvolveTaskMetas` | ListOnly | List tasks |
| `OptVerse:llm4ad:listEvolveTaskStats` | ListOnly | Task statistics |
| `OptVerse:llm4ad:getTaskDetails` | ReadOnly | Task details |
| `OptVerse:llm4ad:getTaskRunningDetails` | ReadOnly | Task run details |
| `OptVerse:llm4ad:getTaskResultCommit` | ReadOnly | Task result commit |
| `OptVerse:llm4ad:getTaskResultList` | ReadOnly | Task result list |
| `OptVerse:llm4ad:getTaskRunningLog` | ReadOnly | Task run log |

### 1.2 Bucket authorization (**only needed for the upload scenario**)

| Action | Type | Purpose |
|---|---|---|
| `OptVerse:llm4ad:authorizePermission` | ReadWrite | Authorize bucket permission |
| `OptVerse:llm4ad:listBuckets` | ListOnly | List buckets |
| `OptVerse:llm4ad:listObject` | ListOnly | List objects |
| `OptVerse:llm4ad:listPermission` | ListOnly | Query permissions |
| `OptVerse:llm4ad:revokePermission` | ReadWrite | Revoke permission |

---

## 2. IAM Agency permissions (**only for the upload scenario**)

| Action | Type | Purpose |
|---|---|---|
| `iam:agencies:create` | ReadWrite | Create agency |
| `iam:agencies:list` | ListOnly | List agencies |
| `iam:agencies:get` | ReadOnly | View agency details |
| `iam:agencies:update` | ReadWrite | Update agency |
| `iam:agencies:delete` | ReadWrite | Delete agency |
| `iam:agencies:attachPolicy` | ReadWrite | Attach policy |
| `iam:agencies:detachPolicy` | ReadWrite | Detach policy |

Agency-related custom-policy resource (referenced by `policy_ai4s_llma4ad`):

| Action | Type | Purpose |
|---|---|---|
| `iam:roles:create` | ReadWrite | Create custom policy (incl. `CreateAgencyCustomPolicy`) |
| `iam:roles:list` | ListOnly | List custom policies |
| `iam:roles:get` | ReadOnly | Get custom policy |
| `iam:roles:update` | ReadWrite | Update custom policy |
| `iam:roles:delete` | ReadWrite | Delete custom policy |

> §3 gives the action list grouped by "must-have / upload-addition" plus a flat-parameter hcloud command; the ops account can follow it to grant the sub-account permissions.

---

## 3. Sub-account permission grants (by group)

The table below is the recommended grouping when the account admin grants a sub-account. The ops account creates a custom policy and binds it to the sub-account per this list. **This is independent from the backend service-agency Action list in [`iam-agency.md`](iam-agency.md) §3 — do not mix them**.

> **Clear division of labour**: creating agencies and policies is the **ops account's** job (typically the account admin, or a specific sub-account granted `Security Administrator`); sub-accounts do **NOT** need `iam:agencies:*` / `iam:roles:*` IAM management actions. Once the sub-account has its AK/SK, it can run this skill directly.

| Group | Action set | Purpose |
|---|---|---|
| **Required (default scenario)** | `OptVerse:llm4ad:createAlgorithm` / `deleteAlgorithm` / `updateAlgorithm` / `listAlgorithms` / `getAlgorithm` / `saveAlgorithmFile` / `importAlgorithmFile` / `getAlgorithmFile` / `listDirectoryByAlgorithmId` / `listDirectoryByResultCommitId` / `createEvolveTask` / `updateEvolveTask` / `startEvolveTask` / `stopEvolveTask` / `deleteEvolveTask` / `batchDeleteEvolveTask` / `listEvolveTaskMetas` / `listEvolveTaskStats` / `getTaskDetails` / `getTaskRunningDetails` / `getTaskResultList` / `getTaskResultCommit` / `getTaskRunningLog` | Sub-account must create algorithm projects / upload files / create and monitor evolve tasks when not uploading |
| **Required (upload-scenario addition)** | `OptVerse:llm4ad:authorizePermission` / `revokePermission` / `listBuckets` / `listObject` / `listPermission` | Add the 5 bucket-authorization actions |

### 3.1 Flat-parameter version of the required group (for `hcloud` custom-policy creation)

For the full action list see §1.1 + §1.2; fill in `Action.N` per the template below:

```bash
hcloud IAM CreateCloudServiceCustomPolicy \
  --role.display_name="policy_optverse_dev" \
  --role.description="AI4S LLM4AD sub-account permission policy" \
  --role.type="AX" \
  --role.policy.Version="1.1" \
  --role.policy.Statement.1.Effect="Allow" \
  --role.policy.Statement.1.Action.1="OptVerse:llm4ad:createAlgorithm" \
  ...
  # Default scenario: fill all 23 actions from §1.1;
  # Upload scenario: append the 5 bucket-authorization actions from §1.2
```

Upload scenario: keep the default 23 rows, then append all 5 actions from §1.2 (starting at row 24).
Default scenario: keep only the 23 rows from §1.1.

---

## 4. System policies (for ops account / sub-account grants)

> The account admin does NOT need this section (the admin has all permissions by default). When granting a **sub-account** and you hit `APIGW.0303` / `IAM.0008`, pick from this table:

| System policy | Target | When needed |
|---|---|---|
| `OptVerse FullAccess` | **Developer sub-accounts** | For any LLM4AD call, start with this — at least covers the OptVerse part |
| `OptVerse ReadOnlyAccess` | **Read-only sub-accounts** | Observation-only scenarios |
| `Security Administrator` | **Ops sub-accounts** (dedicated to agency / policy creation) | When **creating / managing agencies and custom policies**, add this. Includes `iam:agencies:*` + `iam:roles:*` + the full IAM action set |

> Note: system policies include actions across multiple service types and are not minimum-privilege; in production environments prefer the custom policy in §3.
>
> **Minimum practice**:
> - **Regular developer sub-accounts**: only need `OptVerse FullAccess` for the default scenario; for the upload scenario they do NOT need `Security Administrator` (creating agencies is the ops account's job).
> - **Ops sub-accounts**: in addition to `OptVerse FullAccess`, add `Security Administrator` to complete the full "create policy + create agency + bind + bucket-authorize" chain.

---

## 5. Agency / bucket authorization relations

> **The entire flow is only needed for the upload scenario**.

- User account → create IAM Agency (one-time)
- Same account → call `OptVerse AuthorizePermission` to inject bucket operations into the agency
- When the evolve task starts → the service reads / writes `output_path` as the agency

---

## 6. Troubleshooting

See [`troubleshooting.md`](troubleshooting.md) §1-§3 for the error catalogue (including `APIGW.*` / `IAM.*` / `OptVerse.1009` / `OBS.0419` etc.).

---

## 7. Related documents

- [`iam-agency.md`](iam-agency.md): agency creation and management
- [`agency-policy.md`](agency-policy.md): bucket authorization (OBS)