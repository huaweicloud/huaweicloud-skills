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
```

Every command must print `Params:` with the exact `--key` names used in SKILL.md.

## 2. Read-only live verification (R3 — needs valid credentials)

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=5          # expect servers array
hcloud ECS ListFlavors --cli-region=cn-north-4 --limit=5                 # expect flavors array
hcloud IMS ListImages --cli-region=cn-north-4 --limit=5                  # expect images array
hcloud ECS ShowServerLimits --cli-region=cn-north-4                      # expect absolute limits
hcloud VPC ListSubnets --cli-region=cn-north-4 --limit=5                 # expect subnets array
hcloud VPC ListSecurityGroups/v2 --cli-region=cn-north-4 --limit=5       # expect security_groups array
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4 --limit=5            # expect publicips array
hcloud KPS ListKeypairs --cli-region=cn-north-4 --limit=5                # expect keypairs array
hcloud EVS ListVolumes --cli-region=cn-north-4 --limit=5                 # expect volumes array
```

If a real instance exists, additionally:

```bash
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={server_id}
hcloud ECS ListServerVolumeAttachments --cli-region=cn-north-4 --server_id={server_id}
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

## 4. Test harness

`templates/test-vars.json` contains the machine-readable test cases (id / name / command /
expected / type / executor) used by `huawei-cloud-skill-tester` and CI. `type` is one of
`syntax` (help-only), `readonly` (safe live query), `write` (requires confirmation, never
auto-run).

## 5. Environment gates

- Credentials invalid/expired (`APIGW.0301`) → live cases cannot run; record as
  `blocked-env`, re-run when valid credentials are provided. Do not count as skill failure.
- Region/project mismatch → re-check `--cli-region` and the hcloud profile.