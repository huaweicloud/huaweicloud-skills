# Related Skills and Scope Boundaries

`huawei-cloud-ecs-manage` manages **compute instances** on Huawei Cloud. It is deliberately narrow:
it never pretends to cover another cloud service, and it stays self-contained at runtime. This
document (a) states the capability boundary and (b) gives the wording the Agent uses to hand an
out-of-scope request **back to the user** (issues #970 and #931).

## 1. Capability boundary

In scope for this skill:

| Area | Actions | Risk |
|------|---------|------|
| Query | instance list / instance detail / flavors / images / quotas | R3 — auto execute |
| Diagnose | 6-step create-failure root cause; instance health analysis | R3 — auto execute |
| Lifecycle | create (post-paid) / start / stop / restart / delete | R2 / R1 — preview + confirm |
| Change op on an existing instance | resize / reinstall OS / reset password / replace keypair / bind & unbind EIP / change security group / add & remove NIC / attach & detach volume | R2 / R1 — preview + confirm |
| Async tracking | poll `hcloud ECS ShowJob` (and `ShowServer` after create) until terminal state | R3 — after every write |

Out of scope — this skill must not perform these, and must not report them as done:

- **RDS / database** instance, parameter or backup questions, and any database operation → see §2.
- Creating, deleting or reconfiguring the **VPC / subnet / security-group resource** itself.
- Creating, deleting, resizing or snapshotting the **EVS volume resource** itself.
- Creating or deleting **EIPs and bandwidths** — this skill only binds or unbinds an EIP that
  already exists.
- **KMS keys / CSMS secrets** — this skill only chooses which existing keypair an instance logs in
  with.
- **IAM policy** changes — point the operator at `references/iam-policies.md` instead.

Three boundaries are easy to misread, so state them explicitly when reporting:

- **bind / unbind EIP** = attach an existing public IP to, or detach it from, an instance; the EIP
  itself is owned by the network service.
- **add / remove NIC** = allocate or release a port on the instance inside an **existing** subnet.
- **attach / detach volume** = attach or detach an **existing** EVS disk; the disk and its snapshots
  belong to EVS.

## 2. RDS (database) requests — user-facing hand-off (issue #970)

This skill does **not** query RDS. When RDS information is requested while the user is working on ECS
(for example *"list my RDS instances"* or *"which database backs this instance"*):

1. Say plainly that the request is outside `huawei-cloud-ecs-manage`, and why (this skill manages
   compute only).
2. Name the dedicated RDS skill that already covers RDS instance querying — the **user** decides
   whether to select it:
   - `huawei-cloud-rds-smart-service` — `skills/storage/rds/huawei-cloud-rds-smart-service/`.
     Its frontmatter advertises RDS Q&A and specification queries, and its SKILL.md body documents
     `hcloud RDS ListInstances --cli-region={region}` (RDS instance listing).
3. Offer the GUI alternative: the Huawei Cloud **RDS console**.
4. Ask which one the user prefers and stop there. Do not answer the RDS question from general
   knowledge, and do not try to satisfy it here.

### Suggested wording

> RDS (database) queries are outside `huawei-cloud-ecs-manage` — this skill manages compute only.
> To list or inspect RDS instances, please use the `huawei-cloud-rds-smart-service` skill, or open
> the Huawei Cloud RDS console. Which would you prefer? I can continue with the ECS side meanwhile.

### Why this stays a hand-off

- `huawei-cloud-ecs-manage` is self-contained: every command it runs is an `hcloud` (KooCLI) call
  against Huawei Cloud APIs documented in SKILL.md and `references/`. Nothing outside the skill
  participates at runtime.
- This document only **names** the skills above so the user can choose the right tool; the choice and
  the switch happen on the user's side.
- If no RDS skill is available in the user's client, fall back to the RDS console. Never invent or
  guess an RDS skill name.

### Which RDS skills were checked (at this revision)

| Skill | Covers plain RDS instance **query**? |
|-------|--------------------------------------|
| `huawei-cloud-rds-smart-service` | yes — RDS Q&A plus specification and instance listing (`hcloud RDS ListInstances`) |
| `huawei-cloud-rds-failover` | no — primary/standby failover drills only |
| `huawei-cloud-rds-mysql-replica-promotion` | no — single → primary/standby conversion only |

## 3. Where to hand off other out-of-scope requests

All names below were verified to exist in this repository when this document was written. The Agent
only points the user at them.

| User request | Point the user to | Repository path |
|--------------|-------------------|-----------------|
| RDS instance query / diagnosis | `huawei-cloud-rds-smart-service` (or the RDS console) | `skills/storage/rds/huawei-cloud-rds-smart-service/` |
| VPC / subnet / EIP / ELB / NAT / VPN / DNS read-only query | `huawei-cloud-network-query` | `skills/network/ops/huawei-cloud-network-query/` |
| Security-group resource CRUD, rule-conflict and over-exposure audit | `huawei-cloud-sg-manage` | `skills/network/ops/huawei-cloud-sg-manage/` |
| EVS disk / snapshot / OBS / SFS / CBR read-only query | `huawei-cloud-storage-query` | `skills/storage/obs/huawei-cloud-storage-query/` |
| Create a new EVS disk | `huawei-cloud-evs-disk-create` | `skills/storage/evs/huawei-cloud-evs-disk-create/` |
| ECS / BMS / IMS / AS read-only query (flavors, keypairs, quotas, images, scaling groups) | `huawei-cloud-computing-query` | `skills/computing/ops/huawei-cloud-computing-query/` |
| KMS keys / CSMS secrets, rotation and usage audit | `huawei-cloud-dew-key-management` | `skills/security/dew/huawei-cloud-dew-key-management/` |

## 4. Keeping the boundary honest

- Never tell the user that an RDS / VPC / EVS / security-group / IAM change was made by this skill.
- Never fill an ECS answer with data obtained from another service's console or another tool.
- When a request mixes ECS work with out-of-scope work, finish the ECS part, then hand off the rest
  using §2 and say clearly which part was **not** done.
- The permissions this skill needs for its in-scope actions are in `references/iam-policies.md`; do
  not ask the user for broader access than that document declares.
