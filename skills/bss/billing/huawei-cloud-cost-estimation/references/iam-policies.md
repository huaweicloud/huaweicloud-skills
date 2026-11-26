# IAM scope and permissions

Read `gotchas.md` G01 for error handling. Identify the operation, account/customer scope and denied action from current help, the 403 response and API Explorer; the user's administrator grants permissions. Do not elevate privileges yourself.

| Workflow | Required scope |
| --- | --- |
| Pricing | Read-only BSS pricing/dictionaries, including `ListUsageTypes`; commonly `bss:order:view` plus matching read actions |
| Project discovery | IAM `KeystoneListAuthProjects` / `KeystoneListProjects`; select projects per `gotchas.md` G02 |
| Provisioning | The allowlisted service's create actions; dependency lookups need only read actions |
| Partner quote | Customer-authorized token; select projects per `gotchas.md` G02 |

Use current service action definitions, which vary by account/site/version. A failed read needs the relevant read permission, not broader write access. Partner authorization failure stops that scope. Historical bills and balances follow the routing in `../SKILL.md`.
