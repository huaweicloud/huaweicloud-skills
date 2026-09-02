# Prohibited Operations (Non-GET APIs)

> **This skill is strictly read-only.** All non-GET operations (POST/PUT/DELETE) are prohibited regardless of user request. The skill must refuse and direct the user to the Huawei Cloud CDN console or manual hcloud CLI for any write/modify/delete operation.

## Total: 55 Prohibited Operations

Breakdown: 24 POST + 25 PUT + 6 DELETE = 55 non-GET operations.

## POST Operations (24)

| # | Operation | Purpose | Risk |
|---|-----------|---------|------|
| 1 | `ApplyDomainTemplate` | Apply a domain template to one or more domains | Affects production configuration |
| 2 | `BatchCopyDomain` | Batch copy domain configuration | Write operation; affects target domains |
| 3 | `BatchDeleteTags/v1` | Batch delete tags (v1) | Irreversible tag deletion |
| 4 | `BatchDeleteTags/v2` | Batch delete tags (v2) | Irreversible tag deletion |
| 5 | `BatchUpdateRuleStatus` | Batch update rule status | Affects rule evaluation on production |
| 6 | `CreateAccessControlTask` | Create an access control task | Write operation; affects access policy |
| 7 | `CreateDomain/v1` | Create a CDN domain (v1) | Creates production resource |
| 8 | `CreateDomain/v2` | Create a CDN domain (v2) | Creates production resource |
| 9 | `CreateDomainByDuplicate` | Create a domain by duplicating another | Creates production resource |
| 10 | `CreateDomainTemplate` | Create a domain template | Write operation |
| 11 | `CreateExportTask` | Create an export task | Write operation |
| 12 | `CreatePreheatingTasks/v1` | Create preheat tasks (v1) | Affects edge cache |
| 13 | `CreatePreheatingTasks/v2` | Create preheat tasks (v2) | Affects edge cache |
| 14 | `CreateRefreshTasks/v1` | Create refresh tasks (v1) | Affects edge cache |
| 15 | `CreateRefreshTasks/v2` | Create refresh tasks (v2) | Affects edge cache |
| 16 | `CreateRuleNew` | Create a rule | Write operation; affects rule evaluation |
| 17 | `CreateShareCacheGroups` | Create a shared cache group | Write operation |
| 18 | `CreateSubscriptionTask` | Create a subscription task | Write operation |
| 19 | `CreateTags/v1` | Create tags (v1) | Write operation |
| 20 | `CreateTags/v2` | Create tags (v2) | Write operation |
| 21 | `ExportStatsOpen` | Export statistics (open) | Write operation |
| 22 | `SetStatsConfig` | Set statistics configuration | Affects account-level stats collection |
| 23 | `UpdateFullRule` | Update full rule configuration | Affects rule evaluation on production |
| 24 | `VerifyDomainOwner` | Verify domain ownership | Triggers verification flow |

## PUT Operations (25)

| # | Operation | Purpose | Risk |
|---|-----------|---------|------|
| 1 | `DisableDomain/v1` | Disable a domain (v1) | Stops production traffic |
| 2 | `DisableDomain/v2` | Disable a domain (v2) | Stops production traffic |
| 3 | `EnableDomain/v1` | Enable a domain (v1) | Affects production traffic |
| 4 | `EnableDomain/v2` | Enable a domain (v2) | Affects production traffic |
| 5 | `ModifyAccountInfo` | Modify account info | Account-level change |
| 6 | `SetChargeModes` | Set billing mode | Financial impact |
| 7 | `UpdateBlackWhiteList` | Update IP black/white list | Affects access control |
| 8 | `UpdateCacheRules` | Update cache rules | Affects edge caching |
| 9 | `UpdateDomainFullConfig/v1` | Update full domain config (v1) | Affects production configuration |
| 10 | `UpdateDomainFullConfig/v2` | Update full domain config (v2) | Affects production configuration |
| 11 | `UpdateDomainMultiCertificates/v1` | Update domain certificates (v1) | Affects HTTPS/TLS config |
| 12 | `UpdateDomainMultiCertificates/v2` | Update domain certificates (v2) | Affects HTTPS/TLS config |
| 13 | `UpdateDomainOrigin` | Update domain origin | Affects origin pull |
| 14 | `UpdateDomainTemplate` | Update a domain template | Affects template-applied domains |
| 15 | `UpdateFollow302Switch` | Update follow 302 switch | Affects redirect behavior |
| 16 | `UpdateHttpsInfo` | Update HTTPS info | Affects HTTPS/TLS config |
| 17 | `UpdateOriginHost` | Update origin host | Affects origin pull |
| 18 | `UpdatePrivateBucketAccess/v1` | Update private bucket access (v1) | Affects OBS access |
| 19 | `UpdatePrivateBucketAccess/v2` | Update private bucket access (v2) | Affects OBS access |
| 20 | `UpdateRangeSwitch` | Update range switch | Affects range pull behavior |
| 21 | `UpdateRefer` | Update referer validation | Affects access control |
| 22 | `UpdateResponseHeader` | Update response header rules | Affects response behavior |
| 23 | `UpdateRuleNew` | Update a rule | Affects rule evaluation |
| 24 | `UpdateShareCacheGroups` | Update shared cache groups | Affects cache sharing |
| 25 | `UpdateSubscriptionTask` | Update a subscription task | Affects subscription behavior |

## DELETE Operations (6)

| # | Operation | Purpose | Risk |
|---|-----------|---------|------|
| 1 | `DeleteDomain/v1` | Delete a domain (v1) | Irreversible; removes domain from CDN |
| 2 | `DeleteDomain/v2` | Delete a domain (v2) | Irreversible; removes domain from CDN |
| 3 | `DeleteDomainTemplate` | Delete a domain template | Irreversible |
| 4 | `DeleteRuleNew` | Delete a rule | Irreversible; affects rule evaluation |
| 5 | `DeleteShareCacheGroups` | Delete a shared cache group | Irreversible |
| 6 | `DeleteSubscriptionTask` | Delete a subscription task | Irreversible |

## Handling User Requests for Prohibited Operations

If a user requests any of the operations listed above:

1. **Refuse immediately** — Do not execute, do not simulate, do not construct the command.
2. **Inform the user** with the following message:

   > Per security constraints, this skill does not allow write/delete/modify operations. This skill is for DNS resolution diagnosis only. Please use the Huawei Cloud CDN console (https://console.huaweicloud.com/cdn), the DNS service console, or run the hcloud CLI manually for configuration changes.

3. **Do not continue** — Even if the user insists, do not execute prohibited operations. The skill scope is strictly limited to read-only GET queries (`ShowDomainDetailByName`, `ShowIpInfo/v2`) and the read-only DNS probe (`dns_resolve.py`).

## Coverage Notes

- This skill is strictly read-only: it uses the GET APIs `ShowDomainDetailByName` and `ShowIpInfo/v2` plus the read-only probe script `scripts/dns_resolve.py`. No write operation is ever needed.
- DNS configuration changes (e.g., adding/updating CNAME or A records via `nsupdate` or a DNS console) are out of scope and must be performed by the user in the DNS service console.
