# ECS SDK Examples (Python and Java) & Create-Failure Troubleshooting

API-level examples for the five ECS lifecycle operations (create / start / stop / restart /
delete) in **Python** and **Java**, followed by a worked, executable create-failure
troubleshooting example that chains the 6 checks of SKILL.md §2
(quota → flavor → image → network → keypair → disk).

**SDK examples are a programming-access reference only.** The executable contract of this skill
is the `hcloud` CLI command set documented in `SKILL.md` and `references/manage-operations.md`.
When an agent runs this skill, it must build and run `hcloud` commands (wrapped with
`skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- ...`); the SDK snippets below are
for users who integrate ECS management into their own Python/Java programs.

## 0. What is verified in this document

| Part | Verification status |
| ---- | ------------------- |
| Python class names, client methods, region classes, model fields (§2, §4) | **Import-verified on this machine** — every symbol was resolved with `python -c`/`python -` against the installed SDK packages (see §5 for the symbol list and §0.2 for the commands) |
| Python troubleshooting script (§4.2) | **Syntactically checked and import-executed locally** without credentials (imports resolve); no live cloud call was made — this environment has no AK/SK |
| Java snippets (§3) | ⚠️ **Reference examples — not compiled or executed as part of this repository's build or test pipeline.** Class/method names were verified standalone against the published SDK jars with `javap`, and the snippets as shown compile with `javac`; nothing was run against Huawei Cloud. See the banner at the top of §3 |
| `hcloud` CLI sequence (§4.4) | Parameter names match `SKILL.md`, which was verified against `hcloud <Service> <Operation> --help` (KooCLI 7.2.12) |

### 0.1 Environment note

`huaweicloudsdkcore`, `huaweicloudsdkecs` and `huaweicloudsdkiam` are installed by default in the
reference environment. The troubleshooting example also needs the IMS / VPC / EIP / EVS / KPS
packages, which are **not** installed by default:

```bash
pip install huaweicloudsdkecs huaweicloudsdkims huaweicloudsdkvpc huaweicloudsdkeip huaweicloudsdkevs huaweicloudsdkkps
```

### 0.2 How to re-verify a class name before trusting it

```bash
# List the real request/model symbols of a module (never guess a class name)
python -c "import huaweicloudsdkecs.v2 as m; print([n for n in dir(m) if n.endswith('Request')])"
# Print the exact constructor parameters of the classes you use
python -c "import inspect, huaweicloudsdkecs.v2 as m; print(inspect.signature(m.PostPaidServer.__init__))"
# Confirm a client method exists
python -c "import huaweicloudsdkecs.v2 as m; print(hasattr(m.EcsClient, 'create_post_paid_servers'))"
```

Java symbols can be checked the same way against the published jars (no IDE needed):

```bash
# artifact: com.huaweicloud.sdk:huaweicloud-sdk-ecs / :huaweicloud-sdk-core (e.g. 3.1.222)
javap -cp "huaweicloud-sdk-ecs-3.1.222.jar;huaweicloud-sdk-core-3.1.222.jar" \
      com.huaweicloud.sdk.ecs.v2.EcsClient
javap -cp "huaweicloud-sdk-ecs-3.1.222.jar;huaweicloud-sdk-core-3.1.222.jar" \
      'com.huaweicloud.sdk.ecs.v2.model.PostPaidServerRootVolume$VolumetypeEnum'
```

## 1. Credentials — environment variables only

**Never hardcode AK/SK** (or any password/token) in source or in the document. Read credentials
from the environment:

| Variable | Meaning |
| -------- | ------- |
| `HUAWEICLOUD_SDK_AK` | Access key ID |
| `HUAWEICLOUD_SDK_SK` | Secret access key |
| `HUAWEICLOUD_SDK_PROJECT_ID` | Project ID of the target region |
| `HUAWEICLOUD_SDK_REGION` | Optional region override (default `cn-north-4`) |

```bash
# bash / Git Bash
export HUAWEICLOUD_SDK_AK="<your-ak>"      # do NOT commit these values
export HUAWEICLOUD_SDK_SK="<your-sk>"
export HUAWEICLOUD_SDK_PROJECT_ID="<your-project-id>"
export HUAWEICLOUD_SDK_REGION="cn-north-4"
```

```powershell
# PowerShell
$env:HUAWEICLOUD_SDK_AK="<your-ak>"
$env:HUAWEICLOUD_SDK_SK="<your-sk>"
$env:HUAWEICLOUD_SDK_PROJECT_ID="<your-project-id>"
$env:HUAWEICLOUD_SDK_REGION="cn-north-4"
```

Never print the credential values; report only whether they are present.

## 2. Python examples (import-verified)

### 2.1 Shared bootstrap

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

REGION = os.environ.get("HUAWEICLOUD_SDK_REGION", "cn-north-4")


def build_ecs_client():
    """Build an ECS client from environment credentials. Never hardcode AK/SK."""
    ak = os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("HUAWEICLOUD_SDK_SK")
    project_id = os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    if not (ak and sk and project_id):
        raise SystemExit(
            "Missing credentials: set HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / "
            "HUAWEICLOUD_SDK_PROJECT_ID (and optionally HUAWEICLOUD_SDK_REGION)."
        )
    credentials = BasicCredentials(ak, sk, project_id)          # (ak, sk, project_id)
    return EcsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EcsRegion.value_of(REGION)) \
        .build()
```

### 2.2 Create a post-paid instance — R2 (preview + confirm)

Mirrors `hcloud ECS CreatePostPaidServers` and the parameter map in `SKILL.md` §3
(`server.flavorRef` / `server.imageRef` / `server.root_volume.volumetype` / `server.vpcid` /
`server.nics.N.subnet_id` / `server.security_groups.N.id`).

```python
# [W] 写操作 (WRITE): creates an ECS instance — R2: preview + explicit confirmation required
from huaweicloudsdkecs.v2 import (
    CreatePostPaidServersRequest,
    CreatePostPaidServersRequestBody,
    PostPaidServer,
    PostPaidServerNic,
    PostPaidServerRootVolume,
    PostPaidServerSecurityGroup,
)


def create_instance(client, *, name, flavor_id, image_id, vpc_id, subnet_id,
                    security_group_id=None, availability_zone=None,
                    root_volume_type="GPSSD", root_volume_size=40, key_name=None,
                    dry_run=True):
    server = PostPaidServer(
        name=name,
        flavor_ref=flavor_id,
        image_ref=image_id,
        vpcid=vpc_id,
        root_volume=PostPaidServerRootVolume(
            volumetype=root_volume_type, size=root_volume_size),
        nics=[PostPaidServerNic(subnet_id=subnet_id)],
        availability_zone=availability_zone,
        key_name=key_name,
    )
    if security_group_id:
        server.security_groups = [PostPaidServerSecurityGroup(id=security_group_id)]

    # Always validate the payload first: same as `--dry_run=true` on the CLI.
    probe = client.create_post_paid_servers(
        CreatePostPaidServersRequest(
            body=CreatePostPaidServersRequestBody(server=server, dry_run=True)))
    print("dry-run result:", probe)

    # ... then ask the user for explicit confirmation before the real create ...
    response = client.create_post_paid_servers(
        CreatePostPaidServersRequest(
            body=CreatePostPaidServersRequestBody(server=server, dry_run=False)))
    print("job_id:", response.job_id)          # async: poll it, see 2.7
    print("server_ids:", response.server_ids)
    return response
```

### 2.3 Start (power on) — R2

Mirrors `hcloud ECS BatchStartServers --os-start.servers.1.id={server_id}`.

```python
# [W] 写操作 (WRITE): starts instances — R2: preview + explicit confirmation required
from huaweicloudsdkecs.v2 import (
    BatchStartServersRequest,
    BatchStartServersRequestBody,
    BatchStartServersOption,
    ServerId,
)


def start_instances(client, server_ids):
    request = BatchStartServersRequest(
        body=BatchStartServersRequestBody(
            os_start=BatchStartServersOption(
                servers=[ServerId(id=sid) for sid in server_ids])))
    return client.batch_start_servers(request)
```

### 2.4 Stop (power off) — R2

Mirrors `hcloud ECS BatchStopServers --os-stop.servers.1.id={server_id} --os-stop.type=SOFT`.
Use `type="HARD"` only for a forced power-off.

```python
# [W] 写操作 (WRITE): stops instances — R2: preview + explicit confirmation required
from huaweicloudsdkecs.v2 import (
    BatchStopServersRequest,
    BatchStopServersRequestBody,
    BatchStopServersOption,
    ServerId,
)


def stop_instances(client, server_ids, stop_type="SOFT"):   # SOFT (graceful) | HARD (forced)
    request = BatchStopServersRequest(
        body=BatchStopServersRequestBody(
            os_stop=BatchStopServersOption(
                servers=[ServerId(id=sid) for sid in server_ids], type=stop_type)))
    return client.batch_stop_servers(request)
```

### 2.5 Restart (reboot) — R2

Mirrors `hcloud ECS BatchRebootServers --reboot.servers.1.id={server_id} --reboot.type=SOFT`.

> **Naming note (verified):** the ECS SDK model class for the reboot option is
> `BatchRebootSeversOption` — with the historical SDK spelling `Severs`, not `Servers`. Use the
> exact name shown by `dir()`; a `BatchRebootServersOption` class does not exist in
> `huaweicloudsdkecs.v2`.

```python
# [W] 写操作 (WRITE): reboots instances — R2: preview + explicit confirmation required
from huaweicloudsdkecs.v2 import (
    BatchRebootServersRequest,
    BatchRebootServersRequestBody,
    BatchRebootSeversOption,          # NOTE: SDK spelling is "Severs" (verified via dir())
    ServerId,
)


def restart_instances(client, server_ids, reboot_type="SOFT"):   # SOFT | HARD
    request = BatchRebootServersRequest(
        body=BatchRebootServersRequestBody(
            reboot=BatchRebootSeversOption(
                servers=[ServerId(id=sid) for sid in server_ids], type=reboot_type)))
    return client.batch_reboot_servers(request)
```

### 2.6 Delete — R1 (irreversible)

Mirrors `hcloud ECS DeleteServers --servers.1.id={server_id}` with the optional
`--delete_publicip` / `--delete_volume` flags (both default to `false`).

```python
# [W] 写操作 (WRITE) — IRREVERSIBLE: deletes instances — R1: verify first, then explicit confirmation
from huaweicloudsdkecs.v2 import (
    DeleteServersRequest,
    DeleteServersRequestBody,
    ServerId,
    ShowServerRequest,
)


def delete_instances(client, server_ids, delete_publicip=False, delete_volume=False):
    # Pre-check (read-only): confirm the instance exists and record its status/volumes.
    for sid in server_ids:
        detail = client.show_server(ShowServerRequest(server_id=sid)).server
        print("pre-check:", sid, detail.status, detail.name)

    # ... require explicit confirmation, name the data-loss flags out loud ...
    request = DeleteServersRequest(
        body=DeleteServersRequestBody(
            servers=[ServerId(id=sid) for sid in server_ids],
            delete_publicip=delete_publicip,
            delete_volume=delete_volume))
    return client.delete_servers(request)
```

### 2.7 Poll the async job after a write

The five write operations are asynchronous. Get the `job_id` from the write response, poll
`show_job` until `SUCCESS`/`FAIL`, and for a create additionally poll `show_server` until the
instance reaches `ACTIVE`. Polling cadence and the reporting format are defined in
`references/manage-operations.md` §1.

```python
import time
from huaweicloudsdkecs.v2 import ShowJobRequest, ShowServerRequest


def wait_for_job(client, job_id, timeout_s=900, interval_s=10):
    """Poll ECS ShowJob until SUCCESS or FAIL. Returns the final response."""
    deadline = time.time() + timeout_s
    while True:
        job = client.show_job(ShowJobRequest(job_id=job_id))
        print("job %s: status=%s error_code=%s" % (job_id, job.status, job.error_code))
        if job.status in ("SUCCESS", "FAIL"):
            return job
        if time.time() > deadline:
            raise TimeoutError("job %s still %s after %ss" % (job_id, job.status, timeout_s))
        time.sleep(interval_s)


def wait_for_server_active(client, server_id, timeout_s=900, interval_s=10):
    """Poll ECS ShowServer until the instance leaves BUILD."""
    deadline = time.time() + timeout_s
    while True:
        detail = client.show_server(ShowServerRequest(server_id=server_id)).server
        print("server %s: status=%s" % (server_id, detail.status))
        if detail.status in ("ACTIVE", "ERROR"):
            return detail
        if time.time() > deadline:
            raise TimeoutError("server %s still %s after %ss" % (server_id, detail.status, timeout_s))
        time.sleep(interval_s)
```

Report the final result as: `SUCCESS` + instance `ACTIVE` → done; `FAIL` → print
`job.fail_reason` / `job.error_code` and continue with §4.

## 3. Java reference examples — ⚠️ read the verification status first

> ### ⚠️ Reference examples — read the verification status first
>
> These Java snippets are **reference examples: they were not compiled or executed in this
> repository's environment** (they are not part of any module here and the repository's build does
> not compile them), and **nothing was executed against Huawei Cloud** (this environment has no
> AK/SK, so no API call in this document was ever made).
>
> What was verified, and how — standalone, against the published artifacts
> `com.huaweicloud.sdk:huaweicloud-sdk-ecs:3.1.222` and `:huaweicloud-sdk-core:3.1.222`:
>
> 1. every class, enum constant and method used below was confirmed with `javap` against those jars;
> 2. the snippets as printed below compile cleanly with `javac` (JDK 21) against those two jars.
>
> If you use a different SDK version, re-run the checks in §0.2 before trusting a name. Two
> non-obvious details are called out inline: the region helper is `EcsRegion.valueOf(...)` (the
> core `Region` class has **no** `valueOf`), and the reboot-option model is spelled
> `BatchRebootSeversOption`.

The snippets below are fragments and share the imports shown in §3.1 and §3.2.

### 3.1 Shared bootstrap

```java
import com.huaweicloud.sdk.core.auth.BasicCredentials;
import com.huaweicloud.sdk.core.auth.ICredential;
import com.huaweicloud.sdk.ecs.v2.EcsClient;
import com.huaweicloud.sdk.ecs.v2.region.EcsRegion;

// Credentials from environment variables only — never hardcode AK/SK.
ICredential auth = new BasicCredentials()
        .withAk(System.getenv("HUAWEICLOUD_SDK_AK"))
        .withSk(System.getenv("HUAWEICLOUD_SDK_SK"))
        .withProjectId(System.getenv("HUAWEICLOUD_SDK_PROJECT_ID"));

String region = System.getenv("HUAWEICLOUD_SDK_REGION") != null
        ? System.getenv("HUAWEICLOUD_SDK_REGION") : "cn-north-4";

EcsClient client = EcsClient.newBuilder()
        .withCredential(auth)
        .withRegion(EcsRegion.valueOf(region))   // NOT Region.valueOf(...) — see banner
        .build();
```

### 3.2 Create — R2

```java
// [W] 写操作 (WRITE): creates an ECS instance — R2: preview + explicit confirmation required
import java.util.Collections;
import com.huaweicloud.sdk.ecs.v2.model.*;

PostPaidServer server = new PostPaidServer()
        .withName("ecs-demo")
        .withFlavorRef(flavorId)
        .withImageRef(imageId)
        .withVpcid(vpcId)                       // SDK spelling: lowercase "id"
        .withAvailabilityZone(az)
        .withKeyName(keyName)
        .withRootVolume(new PostPaidServerRootVolume()
                .withVolumetype(PostPaidServerRootVolume.VolumetypeEnum.GPSSD)   // enum, not a String
                .withSize(40))
        .withNics(Collections.singletonList(new PostPaidServerNic().withSubnetId(subnetId)))
        .withSecurityGroups(Collections.singletonList(
                new PostPaidServerSecurityGroup().withId(securityGroupId)));

// Validate the payload first (equivalent to `--dry_run=true` on the CLI), then confirm.
CreatePostPaidServersRequest dryRun = new CreatePostPaidServersRequest()
        .withBody(new CreatePostPaidServersRequestBody().withServer(server).withDryRun(true));
System.out.println(client.createPostPaidServers(dryRun));

CreatePostPaidServersRequest request = new CreatePostPaidServersRequest()
        .withBody(new CreatePostPaidServersRequestBody().withServer(server));
CreatePostPaidServersResponse response = client.createPostPaidServers(request);
System.out.println("job_id=" + response.getJobId());        // async: poll it, see 3.7
System.out.println("server_ids=" + response.getServerIds());
```

### 3.3 Start — R2

```java
// [W] 写操作 (WRITE): starts instances — R2: preview + explicit confirmation required
BatchStartServersRequest request = new BatchStartServersRequest()
        .withBody(new BatchStartServersRequestBody()
                .withOsStart(new BatchStartServersOption()
                        .withServers(Collections.singletonList(new ServerId().withId(serverId)))));
client.batchStartServers(request);
```

### 3.4 Stop — R2

```java
// [W] 写操作 (WRITE): stops instances — R2: preview + explicit confirmation required
// `type` takes the generated enum BatchStopServersOption.TypeEnum.SOFT | HARD (verified);
// it is NOT a String. Omit it for the default SOFT.
BatchStopServersRequest request = new BatchStopServersRequest()
        .withBody(new BatchStopServersRequestBody()
                .withOsStop(new BatchStopServersOption()
                        .withServers(Collections.singletonList(new ServerId().withId(serverId)))
                        .withType(BatchStopServersOption.TypeEnum.SOFT)));
client.batchStopServers(request);
```

### 3.5 Restart — R2

```java
// [W] 写操作 (WRITE): reboots instances — R2: preview + explicit confirmation required
// Verified against the published jars: the class is BatchRebootSeversOption (SDK spelling with
// "Severs") and its TypeEnum has SOFT | HARD — no String overload.
BatchRebootServersRequest request = new BatchRebootServersRequest()
        .withBody(new BatchRebootServersRequestBody()
                .withReboot(new BatchRebootSeversOption()
                        .withServers(Collections.singletonList(new ServerId().withId(serverId)))
                        .withType(BatchRebootSeversOption.TypeEnum.SOFT)));
client.batchRebootServers(request);
```

### 3.6 Delete — R1

```java
// [W] 写操作 (WRITE) — IRREVERSIBLE: deletes instances — R1: verify first, then explicit confirmation
// Read-only pre-check first: client.showServer(new ShowServerRequest().withServerId(serverId))
DeleteServersRequest request = new DeleteServersRequest()
        .withBody(new DeleteServersRequestBody()
                .withServers(Collections.singletonList(new ServerId().withId(serverId)))
                .withDeletePublicip(false)      // true releases the bound EIP
                .withDeleteVolume(false));      // true deletes attached volumes (data loss)
client.deleteServers(request);
```

### 3.7 Poll the async job

```java
ShowJobRequest jobRequest = new ShowJobRequest().withJobId(jobId);
ShowJobResponse job = client.showJob(jobRequest);
// getStatus() returns the generated enum ShowJobResponse.StatusEnum
// (INIT | RUNNING | SUCCESS | FAIL); use .getValue() for the raw string.
System.out.println("status=" + job.getStatus() + " error_code=" + job.getErrorCode()
        + " fail_reason=" + job.getFailReason());
if (ShowJobResponse.StatusEnum.FAIL.equals(job.getStatus())) {
    // report job.getFailReason() as the root cause
}

ShowServerRequest serverRequest = new ShowServerRequest().withServerId(serverId);
ShowServerResponse detail = client.showServer(serverRequest);
System.out.println("server status=" + detail.getServer().getStatus());   // String: ACTIVE | ERROR | ...
```

## 4. Create-failure troubleshooting: worked example (issue #995)

This section turns the 6 ordered checks of `SKILL.md` §2 into **executable** code instead of a
step list: the script stops at the first failing check and prints **root cause + evidence + fix
suggestion**. All checks are read-only (R3) and can be auto-executed.

### 4.1 Check → SDK call → pass condition → fix

| # | Check | Python call | Pass condition | Fix when it fails |
|---|-------|-------------|----------------|-------------------|
| 1 | Quota | `show_server_limits` | usage < limit for instances / cores / RAM | raise the quota in the console, or delete unused instances |
| 2 | Flavor | `list_flavors` (`flavor_id`, `availability_zone`) | flavor returned for the requested AZ | pick another flavor or another AZ |
| 3 | Image | IMS `list_images` (`id`, `status="active"`) | image exists, is `active`, and matches the flavor architecture | pick another image (`os_type`/`architecture` must match) |
| 4 | Network | VPC `list_subnets`, `list_security_groups`; EIP `list_publicips` if an EIP is requested | subnet exists with free IPs and `dhcp_enable`; referenced security groups exist; EIP available | fix the network parameters (subnet / SG / EIP) |
| 5 | Keypair | KPS `list_keypairs` | the `key_name` used in the request exists | create the keypair, or drop `key_name` |
| 6 | Disk | EVS `list_volumes`, `cinder_list_quotas` | volume type is available in the AZ and the volume quota is not exhausted | change the volume type / AZ, or raise the EVS quota |

> Check 1 evidence note: the ECS `ServerLimits` model exposes `max_total_instances`,
> `max_total_cores` and `max_total_ram_size` (plus their `total_*_used` counterparts); it does
> **not** expose a `max_total_volumes` field. Disk capacity is therefore checked in step 6 through
> the EVS quota API, exactly like `hcloud EVS CinderListQuotas` does on the CLI.

### 4.2 Full script

```python
#!/usr/bin/env python3
"""6-step ECS create-failure root-cause diagnosis (read-only / R3).

Order: quota -> flavor -> image -> network -> keypair -> disk.
Stops at the first failing check and prints root cause + evidence + fix suggestion.

Credentials are read from environment variables only:
    HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / HUAWEICLOUD_SDK_PROJECT_ID
Optional: HUAWEICLOUD_SDK_REGION (default cn-north-4).

Usage:
    python diagnose_create_failure.py --flavor-id {flavor_id} --image-id {image_id} \
        --vpc-id {vpc_id} --subnet-id {subnet_id} --security-group-id {sg_id} \
        --key-name {key_name} --volume-type GPSSD --availability-zone {az}
"""
import argparse
import os
from types import SimpleNamespace

from huaweicloudsdkcore.auth.credentials import BasicCredentials

from huaweicloudsdkecs.v2 import EcsClient, ListFlavorsRequest, ShowServerLimitsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

from huaweicloudsdkims.v2 import ImsClient, ListImagesRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

from huaweicloudsdkvpc.v2 import (
    ListSecurityGroupsRequest,
    ListSubnetsRequest,
    VpcClient,
)
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

from huaweicloudsdkeip.v2 import EipClient, ListPublicipsRequest
from huaweicloudsdkeip.v2.region.eip_region import EipRegion

from huaweicloudsdkkps.v3 import KpsClient, ListKeypairsRequest
from huaweicloudsdkkps.v3.region.kps_region import KpsRegion

from huaweicloudsdkevs.v2 import CinderListQuotasRequest, EvsClient, ListVolumesRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

REGION = os.environ.get("HUAWEICLOUD_SDK_REGION", "cn-north-4")


class CheckFailed(Exception):
    """Raised by the first failing check; carries the report payload."""

    def __init__(self, step, name, evidence, fix):
        super().__init__("check #%s (%s) failed" % (step, name))
        self.step, self.name, self.evidence, self.fix = step, name, evidence, fix


def build_clients():
    ak = os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("HUAWEICLOUD_SDK_SK")
    project_id = os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    if not (ak and sk and project_id):
        raise SystemExit(
            "Missing credentials: set HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / "
            "HUAWEICLOUD_SDK_PROJECT_ID (and optionally HUAWEICLOUD_SDK_REGION)."
        )
    credentials = BasicCredentials(ak, sk, project_id)

    def builder(client_cls, region_cls):
        return client_cls.new_builder() \
            .with_credentials(credentials) \
            .with_region(region_cls.value_of(REGION)) \
            .build()

    return SimpleNamespace(
        project_id=project_id,
        ecs=builder(EcsClient, EcsRegion),
        ims=builder(ImsClient, ImsRegion),
        vpc=builder(VpcClient, VpcRegion),
        eip=builder(EipClient, EipRegion),
        kps=builder(KpsClient, KpsRegion),
        evs=builder(EvsClient, EvsRegion),
    )


# --- check 1: quota ---------------------------------------------------------
def check_quota(c, args):
    limits = c.ecs.show_server_limits(ShowServerLimitsRequest()).absolute
    instances = "%s/%s instances" % (limits.total_instances_used, limits.max_total_instances)
    cores = "%s/%s cores" % (limits.total_cores_used, limits.max_total_cores)
    ram = "%s/%s MB RAM" % (limits.total_ram_used, limits.max_total_ram_size)
    evidence = "%s, %s, %s" % (instances, cores, ram)
    if limits.max_total_instances and \
            (limits.total_instances_used or 0) >= limits.max_total_instances:
        raise CheckFailed(1, "quota", evidence,
                          "raise the ECS instance quota in the console, or delete unused instances")
    return evidence


# --- check 2: flavor --------------------------------------------------------
def check_flavor(c, args):
    request = ListFlavorsRequest(flavor_id=args.flavor_id,
                                 availability_zone=args.availability_zone)
    flavors = c.ecs.list_flavors(request).flavors or []
    if not flavors:
        raise CheckFailed(
            2, "flavor",
            "flavor_id=%s not returned in region %s (az=%s)"
            % (args.flavor_id, REGION, args.availability_zone or "any"),
            "pick a flavor that exists and is on sale in the target AZ "
            "(list candidates with ECS ListFlavors --availability_zone={az})")
    flavor = flavors[0]
    return "flavor %s (%s): %s vCPU / %s MB" % (flavor.id, flavor.name, flavor.vcpus, flavor.ram)


# --- check 3: image ---------------------------------------------------------
def check_image(c, args):
    images = c.ims.list_images(
        ListImagesRequest(id=args.image_id, status="active")).images or []
    if not images:
        raise CheckFailed(
            3, "image",
            "image_id=%s not found with status=active" % args.image_id,
            "use an existing active image; private/deleted images or an architecture "
            "mismatch (x86 vs ARM) fail provisioning")
    image = images[0]
    if args.architecture and image.architecture and image.architecture != args.architecture:
        raise CheckFailed(
            3, "image",
            "image %s architecture=%s but the flavor requires %s"
            % (image.id, image.architecture, args.architecture),
            "select an image whose architecture matches the flavor")
    return "image %s (%s): os_type=%s architecture=%s min_disk=%s GB" % (
        image.id, image.name, image.os_type, image.architecture, image.min_disk)


# --- check 4: network -------------------------------------------------------
def check_network(c, args):
    subnet = None
    for s in c.vpc.list_subnets(ListSubnetsRequest(vpc_id=args.vpc_id)).subnets or []:
        if s.id == args.subnet_id:
            subnet = s
            break
    if subnet is None:
        raise CheckFailed(4, "network",
                          "subnet_id=%s not found in vpc_id=%s" % (args.subnet_id, args.vpc_id),
                          "reference an existing subnet of the target VPC")
    free = subnet.available_ip_address_count
    if free is not None and free <= 0:
        raise CheckFailed(4, "network",
                          "subnet %s has no free IP address (available_ip_address_count=0)"
                          % subnet.id,
                          "extend the subnet CIDR or use another subnet")
    if subnet.dhcp_enable is False:
        raise CheckFailed(4, "network", "subnet %s has dhcp_enable=false" % subnet.id,
                          "enable DHCP on the subnet, or assign a static IP explicitly")

    sgs = c.vpc.list_security_groups(
        ListSecurityGroupsRequest(vpc_id=args.vpc_id)).security_groups or []
    sg_ids = {sg.id for sg in sgs}
    if args.security_group_id and args.security_group_id not in sg_ids:
        raise CheckFailed(4, "network",
                          "security_group_id=%s not found in vpc_id=%s"
                          % (args.security_group_id, args.vpc_id),
                          "reference an existing security group of the target VPC")

    if args.bind_eip:
        publicips = c.eip.list_publicips(ListPublicipsRequest()).publicips or []
        if not publicips:
            raise CheckFailed(4, "network",
                              "an EIP was requested but the project has no available public IP",
                              "release an unused EIP or raise the EIP quota")

    return "subnet %s (%s) free_ips=%s dhcp=%s; security group %s ok" % (
        subnet.id, subnet.cidr, free, subnet.dhcp_enable, args.security_group_id or "default")


# --- check 5: keypair -------------------------------------------------------
def check_keypair(c, args):
    if not args.key_name:
        return "no key_name in the request (password login) - skipped"
    keypairs = c.kps.list_keypairs(ListKeypairsRequest()).keypairs or []
    names = {kp.keypair.name for kp in keypairs if kp.keypair}
    if args.key_name not in names:
        raise CheckFailed(5, "keypair",
                          "key_name=%s does not exist (known: %s)"
                          % (args.key_name, ", ".join(sorted(names)) or "none"),
                          "create the keypair first, or remove key_name from the create request")
    return "key_name=%s exists" % args.key_name


# --- check 6: disk ----------------------------------------------------------
def check_disk(c, args):
    volumes = c.evs.list_volumes(
        ListVolumesRequest(availability_zone=args.availability_zone)).volumes or []
    quota = c.evs.cinder_list_quotas(
        CinderListQuotasRequest(target_project_id=c.project_id, usage=True)).quota_set
    types_in_az = sorted({v.volume_type for v in volumes if v.volume_type})
    note = ""
    if args.volume_type and types_in_az and args.volume_type not in types_in_az:
        note = " (WARN: no existing volume of type %s in az=%s; verify availability)" % (
            args.volume_type, args.availability_zone)
    return "%s volume(s) in az=%s, types in use=%s%s; evs quota_set=%s" % (
        len(volumes), args.availability_zone, types_in_az or "n/a", note, quota)


CHECKS = (("quota", check_quota), ("flavor", check_flavor), ("image", check_image),
          ("network", check_network), ("keypair", check_keypair), ("disk", check_disk))


def main():
    parser = argparse.ArgumentParser(description="ECS create-failure 6-step diagnosis")
    parser.add_argument("--flavor-id")
    parser.add_argument("--image-id")
    parser.add_argument("--vpc-id")
    parser.add_argument("--subnet-id")
    parser.add_argument("--security-group-id")
    parser.add_argument("--key-name")
    parser.add_argument("--volume-type", default="GPSSD")
    parser.add_argument("--availability-zone")
    parser.add_argument("--architecture", help="x86 | arm (cross-check against the image)")
    parser.add_argument("--bind-eip", action="store_true")
    args = parser.parse_args()

    clients = build_clients()
    for step, (name, func) in enumerate(CHECKS, start=1):
        try:
            evidence = func(clients, args)
        except CheckFailed as failure:
            print("RESULT: FAILED at check #%s (%s)" % (failure.step, failure.name))
            print("  root cause: %s" % failure.name)
            print("  evidence  : %s" % failure.evidence)
            print("  fix       : %s" % failure.fix)
            return 1
        print("check #%s %-8s PASS  %s" % (step, name, evidence))

    print("RESULT: all 6 checks passed - the failure is likely transient or parameter-specific.")
    print("  re-run the create with --dry_run=true (CLI) / dry_run=True (SDK) and report the")
    print("  exact API error body; if a job id exists, inspect it with ECS ShowJob.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 4.3 Stage 2 — the async job and the instance state

A rejected create often only surfaces its reason on the job. After capturing the `job_id` from the
create response (or from the console):

```python
import time
from huaweicloudsdkecs.v2 import ShowJobRequest, ShowServerRequest

job = clients.ecs.show_job(ShowJobRequest(job_id=job_id))
print("status     :", job.status)         # SUCCESS | FAIL | RUNNING | INIT
print("error_code :", job.error_code)     # e.g. Ecs.0005 / Ecs.0013
print("fail_reason:", job.fail_reason)    # human-readable root cause
print("job_type   :", job.job_type)       # e.g. createSingleServer

detail = clients.ecs.show_server(ShowServerRequest(server_id=server_id)).server
print("server status:", detail.status)    # ACTIVE | ERROR | BUILD | SHUTOFF
fault = getattr(detail, "fault", None)
if fault:
    print("fault:", fault)                # message / code / details on ERROR
```

Report the conclusion exactly as `SKILL.md` §2 requires:
**root cause (check #N or the job's `fail_reason`) + evidence + fix suggestion**.

### 4.4 Minimal reproducible command-line equivalent (hcloud CLI)

The same 6 checks as an agent would actually run them — dual form, as required by `SKILL.md`
(every bare `hcloud` command is followed by its `skill-quality-cli` wrapper):

```bash
# Step 1 - quota
hcloud ECS ShowServerLimits --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServerLimits --cli-region={region}
# Step 2 - flavor (scope to the AZ when one was requested)
hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region} --flavor_id={flavor_id}
hcloud ECS ListFlavors --cli-region={region} --availability_zone={az}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ListFlavors --cli-region={region} --availability_zone={az}
# Step 3 - image
hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud IMS ListImages --cli-region={region} --id={image_id} --status=active
# Step 4 - network (subnet, security group, and EIP only if one is requested)
hcloud VPC ListSubnets --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud VPC ListSubnets --cli-region={region}
hcloud VPC ListSecurityGroups/v2 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud VPC ListSecurityGroups/v2 --cli-region={region}
hcloud EIP ListPublicips/v2 --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EIP ListPublicips/v2 --cli-region={region}
# Step 5 - keypair (KPS ListKeypairs needs only --cli-region / --project_id; --limit is
#   deliberately omitted here because it was dropped between KooCLI 7.2.12 and 7.3.12)
hcloud KPS ListKeypairs --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud KPS ListKeypairs --cli-region={region}
# Step 6 - disk: volumes + the EVS volume quota
hcloud EVS ListVolumes --cli-region={region}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS ListVolumes --cli-region={region}
hcloud EVS CinderListQuotas --cli-region={region} --target_project_id={project_id} --usage=True
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud EVS CinderListQuotas --cli-region={region} --target_project_id={project_id} --usage=True
# Stage 2 - job result and instance state
hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowJob --cli-region={region} --job_id={job_id}
hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
skill-quality-cli run --skill-name huawei-cloud-ecs-manage -- hcloud ECS ShowServer --cli-region={region} --server_id={server_id}
```

### 4.5 Example report

```
check #1 quota    PASS  3/50 instances, 6/200 cores, 12288/409600 MB RAM
check #2 flavor   PASS  flavor s6.large.2 (s6.large.2): 2 vCPU / 4096 MB
check #3 image    PASS  image 6a6a... (Ubuntu 22.04): os_type=Linux architecture=x86 min_disk=40 GB
RESULT: FAILED at check #4 (network)
  root cause: network
  evidence  : subnet 8b1c... has no free IP address (available_ip_address_count=0)
  fix       : extend the subnet CIDR or use another subnet
```

## 5. Python symbols used in this document (all import-verified)

| Module | Symbols |
| ------ | ------- |
| `huaweicloudsdkcore.auth.credentials` | `BasicCredentials(ak, sk, project_id)` |
| `huaweicloudsdkecs.v2` | `EcsClient` (`create_post_paid_servers`, `batch_start_servers`, `batch_stop_servers`, `batch_reboot_servers`, `delete_servers`, `show_job`, `show_server`, `show_server_limits`, `list_flavors`), `CreatePostPaidServersRequest`, `CreatePostPaidServersRequestBody`, `CreatePostPaidServersResponse` (`job_id`, `server_ids`), `PostPaidServer`, `PostPaidServerRootVolume`, `PostPaidServerNic`, `PostPaidServerSecurityGroup`, `BatchStartServersRequest`, `BatchStartServersRequestBody`, `BatchStartServersOption`, `BatchStopServersRequest`, `BatchStopServersRequestBody`, `BatchStopServersOption`, `BatchRebootServersRequest`, `BatchRebootServersRequestBody`, `BatchRebootSeversOption`, `DeleteServersRequest`, `DeleteServersRequestBody`, `ServerId`, `ShowJobRequest`, `ShowServerRequest`, `ShowServerLimitsRequest`, `ListFlavorsRequest`, `ServerLimits` |
| `huaweicloudsdkecs.v2.region.ecs_region` | `EcsRegion.value_of(region)` |
| `huaweicloudsdkims.v2` | `ImsClient` (`list_images`), `ListImagesRequest`, `ListImagesResponse` (`images`), `ImageInfo` |
| `huaweicloudsdkims.v2.region.ims_region` | `ImsRegion.value_of(region)` |
| `huaweicloudsdkvpc.v2` | `VpcClient` (`list_subnets`, `list_security_groups`), `ListSubnetsRequest`, `ListSecurityGroupsRequest`, `Subnet`, `SecurityGroup` |
| `huaweicloudsdkvpc.v2.region.vpc_region` | `VpcRegion.value_of(region)` |
| `huaweicloudsdkeip.v2` | `EipClient` (`list_publicips`), `ListPublicipsRequest`, `PublicipShowResp` |
| `huaweicloudsdkeip.v2.region.eip_region` | `EipRegion.value_of(region)` |
| `huaweicloudsdkkps.v3` | `KpsClient` (`list_keypairs`), `ListKeypairsRequest`, `Keypairs`, `KeypairDetail` |
| `huaweicloudsdkkps.v3.region.kps_region` | `KpsRegion.value_of(region)` |
| `huaweicloudsdkevs.v2` | `EvsClient` (`list_volumes`, `cinder_list_quotas`), `ListVolumesRequest`, `VolumeDetail`, `CinderListQuotasRequest`, `CinderListQuotasResponse` (`quota_set`) |
| `huaweicloudsdkevs.v2.region.evs_region` | `EvsRegion.value_of(region)` |

## 6. Related documents

- `SKILL.md` §2 — the 6-step create-failure diagnosis (CLI contract) and §3/§4 manage commands
- `references/manage-operations.md` §1 — async `job_id` polling and the reporting format
- `references/verification-method.md` — static/live verification of the CLI commands
- `references/iam-policies.md` — least-privilege policies required by these SDK calls
