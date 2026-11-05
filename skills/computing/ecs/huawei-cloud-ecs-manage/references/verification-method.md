# Verification Method

How to verify that `huawei-cloud-ecs-manage` works, from syntax checks to live execution.
All business commands go through the hcloud CLI; verification is organized by risk level.

## 1. Static verification (no credentials needed)

For every operation documented in SKILL.md, confirm the command exists and the parameter names
match KooCLI 7.2.12 metadata:

```bash
hcloud ECS ListServersDetails --help --cli-region=cn-north-4
hcloud ECS ShowServer --help --cli-region=cn-north-4
hcloud ECS ListFlavors --help --cli-region=cn-north-4
hcloud IMS ListImages --help --cli-region=cn-north-4
hcloud ECS ShowServerLimits --help --cli-region=cn-north-4
hcloud ECS CreatePostPaidServers --help --cli-region=cn-north-4
hcloud ECS BatchStartServers --help --cli-region=cn-north-4
hcloud ECS BatchStopServers --help --cli-region=cn-north-4
hcloud ECS BatchRebootServers --help --cli-region=cn-north-4
hcloud ECS DeleteServers --help --cli-region=cn-north-4
hcloud ECS ShowJob --help --cli-region=cn-north-4
hcloud KPS ListKeypairs --help --cli-region=cn-north-4
hcloud EVS ListVolumes --help --cli-region=cn-north-4
hcloud EVS CinderListQuotas --help --cli-region=cn-north-4
```

Every command must print `Params:` with the exact `--key` names used in SKILL.md.

### 1.1 Change operations added for issue #931

```bash
hcloud ECS ResizeServer --help --cli-region=cn-north-4
hcloud ECS ReinstallServerWithCloudInit --help --cli-region=cn-north-4
hcloud ECS ResetServerPassword --help --cli-region=cn-north-4
hcloud ECS NovaCreateKeypair --help --cli-region=cn-north-4
hcloud ECS NovaDeleteKeypair --help --cli-region=cn-north-4
hcloud EIP AssociatePublicips --help --cli-region=cn-north-4
hcloud EIP DisassociatePublicips --help --cli-region=cn-north-4
hcloud ECS NovaAssociateSecurityGroup --help --cli-region=cn-north-4
hcloud ECS NovaDisassociateSecurityGroup --help --cli-region=cn-north-4
hcloud ECS NovaAttachInterface --help --cli-region=cn-north-4
hcloud ECS NovaDetachInterface --help --cli-region=cn-north-4
hcloud ECS BatchAddServerNics --help --cli-region=cn-north-4
hcloud ECS BatchDeleteServerNics --help --cli-region=cn-north-4
hcloud ECS AttachServerVolume --help --cli-region=cn-north-4
hcloud ECS DetachServerVolume --help --cli-region=cn-north-4
```

> **Service / operation traps, verified against KooCLI 7.2.12:**
> - `hcloud ECS ReinstallServer` does **not** exist — KooCLI answers
>   `[USE_ERROR]不支持的operation:ReinstallServer` and points at
>   `ReinstallServerWithCloudInit` (parameter family `--os-reinstall.*`).
> - EIP bind / unbind belong to the **EIP** service: `hcloud EIP AssociatePublicips` /
>   `hcloud EIP DisassociatePublicips`. `hcloud VPC AssociatePublicips` is not a valid operation.
> - The two NIC APIs use different parameter names: `NovaAttachInterface` takes
>   `--interfaceAttachment.net_id` / `--interfaceAttachment.port_id`, while `BatchAddServerNics`
>   takes `--nics.{n}.subnet_id` / `--nics.{n}.port_id`.

## 2. Read-only live verification (R3 — needs valid credentials)

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=5          # expect servers array
hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=5                 # expect flavors array
hcloud IMS ListImages --cli-region=cn-north-4 --limit=5                  # expect images array
hcloud ECS ShowServerLimits --cli-region=cn-north-4                      # expect absolute limits
hcloud VPC ListSubnets --cli-region=cn-north-4 --limit=5                 # expect subnets array
hcloud VPC ListSecurityGroups/v2 --cli-region=cn-north-4 --limit=5       # expect security_groups array
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4 --limit=5            # expect publicips array
hcloud KPS ListKeypairs --cli-region=cn-north-4                          # expect keypairs array (no --limit: see note)
hcloud EVS ListVolumes --cli-region=cn-north-4 --limit=5                 # expect volumes array
```

> **`KPS ListKeypairs` deliberately drops `--limit` here.** KPS `ListKeypairs` accepted `--limit` on
> KooCLI 7.2.12 but no longer lists it in `--help` on 7.3.12 (issue #967). Since the parameter is
> optional, omitting it keeps this verification command valid across both KooCLI 7.2.x and 7.3.x,
> whereas keeping it hard-fails on 7.3.12 with `[USE_ERROR]不正确的参数`. The `--limit=5` on the
> other list commands stays: issue #967 verified those calls as OK on the newer CLI.

If a real instance exists, additionally:

```bash
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={server_id}
hcloud ECS ListServerVolumeAttachments --cli-region=cn-north-4 --server_id={server_id}
hcloud ECS ListServerInterfaces --cli-region=cn-north-4 --server_id={server_id}
hcloud EVS ListVolumes --cli-region=cn-north-4 --server_id={server_id}
```

Qualify a case PASS only when the API returns clean JSON without an error body
(`error_code`/`error_msg`). Note: a 401 (`APIGW.0301`) means the credentials are invalid/expired,
not a command defect.

## 3. Write-operation verification (R2/R1 — needs explicit confirmation)

Write operations are **never auto-executed** in tests. Verify them as follows:

1. **Dry-run first**: `hcloud ECS CreatePostPaidServers --cli-region={region} ... --dry_run=true`
   — validates the payload without creating anything; expect a validation result, not a server id.
2. **Start/stop/restart/delete**: verify against a dedicated test instance owned by the tester;
   each step requires explicit user confirmation (preview → confirm → execute → verify → report).
3. **Destroy test resources** after the test and confirm release (see acceptance criteria).
4. **Change operations (issue #931)**: `ResizeServer` and `AttachServerVolume` also accept
   `--dry_run=true` — use it to validate the payload first. The other change operations have no
   dry-run parameter, so run them only on a dedicated test instance and require explicit
   confirmation for every step; record the pre-state (`ShowServer`, `ListServerInterfaces`,
   `ListServerVolumeAttachments`) before and after.
5. **Async jobs are part of the write**: after every change operation poll
   `hcloud ECS ShowJob --cli-region={region} --job_id={job_id}` until `status` is `SUCCESS` or
   `FAIL`; a write is PASS only when the job reached `SUCCESS`.

## 4. Test harness

`templates/test-vars.json` contains the machine-readable test cases (id / name / command /
expected / type / executor) used by `huawei-cloud-skill-tester` and CI. `type` is one of
`syntax` (help-only), `readonly` (safe live query), `write` (requires confirmation, never
auto-run).

## 5. Offline IAM policy assertions (no credentials needed)

`references/iam-policies.md` is the single source of truth for the least-privilege permissions this
skill needs. The three permissions that are easiest to miss (issue #2265 / PR #810) are not left to
review: run the assertion below to prove they are still declared in the policy JSON blocks. It needs
only Python 3 — no credentials, no network, no hcloud.

Paste it into `python3 -` (or save it as a scratch `.py` file) and run it **from the skill
directory**, so that `references/iam-policies.md` resolves:

```bash
python3 - <<'PY'
import json, re, sys

MD = "references/iam-policies.md"

def blocks(text):
    return re.findall(r"```json\n(.*?)```", text, re.DOTALL)

def actions(block):
    return set(json.loads(block)["Statement"][0]["Action"])

with open(MD, encoding="utf-8") as fh:
    json_blocks = blocks(fh.read())
query_policy = actions(json_blocks[0])   # section 1
manage_policy = actions(json_blocks[1])  # section 2
delete_policy = actions(json_blocks[2])  # section 3

required = [
    ("query policy declares kps:keypairs:list", "kps:keypairs:list", query_policy),
    ("delete policy declares evs:volumes:delete", "evs:volumes:delete", delete_policy),
    ("delete policy declares vpc:publicIps:delete", "vpc:publicIps:delete", delete_policy),
]
ok = 0
for label, action, policy in required:
    if action in policy:
        ok += 1
        print("PASS  " + label)
    else:
        print("FAIL  " + label)

kept = [
    ("query policy keeps ecs:cloudServers:list", "ecs:cloudServers:list", query_policy),
    ("query policy keeps vpc:subnets:list", "vpc:subnets:list", query_policy),
    ("query policy keeps evs:volumes:list", "evs:volumes:list", query_policy),
    ("delete policy keeps ecs:cloudServers:delete", "ecs:cloudServers:delete", delete_policy),
    ("delete policy keeps ecs:serverVolumes:list", "ecs:serverVolumes:list", delete_policy),
    ("delete policy keeps vpc:publicIps:list", "vpc:publicIps:list", delete_policy),
]
regressions = [label for label, action, policy in kept if action not in policy]
for label in regressions:
    print("FAIL  " + label)
if not regressions:
    print("PASS  retained actions kept (%d/%d)" % (len(kept), len(kept)))

print("IAM policy assertions: %d/3 OK" % ok)
sys.exit(0 if ok == 3 and not regressions else 1)
PY
```

Expected output (the acceptance signal):

```text
PASS  query policy declares kps:keypairs:list
PASS  delete policy declares evs:volumes:delete
PASS  delete policy declares vpc:publicIps:delete
PASS  retained actions kept (6/6)
IAM policy assertions: 3/3 OK
```

A non-zero exit code means a required permission was removed from `references/iam-policies.md` (or a
previously granted one was dropped); fix the policy document before submitting.

## 6. Environment gates

- Credentials invalid/expired (`APIGW.0301`) → live cases cannot run; record as
  `blocked-env`, re-run when valid credentials are provided. Do not count as skill failure.
- Region/project mismatch → re-check `--cli-region` and the hcloud profile.
