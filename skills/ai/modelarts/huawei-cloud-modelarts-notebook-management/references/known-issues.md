# Known Issues and Practical Solutions

> Discovered during real-world testing in cn-north-4 (2026-07). All solutions verified unless noted otherwise.

---

## 1. CLI Does Not Support EVS as volume.category

**Symptom**: The `CreateNotebook` CLI help lists `volume.category` as `[OBS|OBSFS|EFS]`, omitting `EVS`. Direct CLI parameters reject EVS.

**Root Cause**: The hcloud CLI parameter schema does not include EVS in the enum for `--volume.category`, even though the underlying API accepts it.

**Solution**: Use `--cli-jsonInput` with a JSON file to bypass CLI parameter validation. The JSON must wrap the request body in a `"body"` key, and `project_id` must be passed explicitly on the command line (auto-resolution does not work with `--cli-jsonInput`):

```json
{
  "body": {
    "volume": {
      "category": "EVS",
      "ownership": "MANAGED",
      "capacity": 5
    }
  }
}
```

```bash
hcloud ModelArts CreateNotebook --cli-region={region} --project_id={project_id} --cli-jsonInput=create-notebook.json
```

---

## 2. Storage Category × Ownership Compatibility Matrix (Main Volume)

**Symptom**: Different combinations of `volume.category` and `volume.ownership` produce varying results, and the CLI documentation is misleading.

**Verified Results** (tested in cn-north-4, 2026-07):

| category | ownership=MANAGED | ownership=DEDICATED | Notes |
|----------|-------------------|---------------------|-------|
| **EVS** | ✅ Supported | — (N/A) | Default system disk, requires `capacity` |
| **OBS** | ❌ `ModelArts.6702` | ✅ **Works** | Requires `uri` + `dew_secret_name` |
| **OBSFS** | ❌ `ModelArts.6702` | ✅ **Works** | Requires `uri` + `dew_secret_name` |
| **EFS** | — (untested) | ✅ (per docs) | Requires `id` (SFS Turbo file system ID) |

**Key Correction**: Previous documentation stated "OBS Cannot Be Used as Main Storage". This is **incorrect**. `OBS:DEDICATED` and `OBSFS:DEDICATED` both work as main storage (`volume`), producing `status=IN_USE` and `mount_type=MAIN`. Only `MANAGED` ownership is rejected for OBS/OBSFS main storage.

**Solution**: For OBS/OBSFS as main storage, always use `ownership=DEDICATED` with `uri` and `dew_secret_name`:

```bash
hcloud ModelArts CreateNotebook --cli-region={region} \
  --volume.category=OBS \
  --volume.ownership=DEDICATED \
  --volume.uri=obs://{bucket_name}/ \
  --volume.mount_path=/home/ma-user/work/ \
  --volume.dew_secret_name={dew_secret_name}
```

---

## 3. Dedicated Resource Pool Requires pool_id

**Symptom**: Creating a notebook with `volume.ownership=DEDICATED` (专属资源池) without specifying `pool_id` will fail or cannot target the correct pool.

**Root Cause**: `DEDICATED` ownership means the storage and compute resources are allocated from a user-owned dedicated pool. The API requires a top-level `pool_id` parameter to identify which dedicated pool to use. Omitting it leaves the API unable to determine the target resource pool.

**Solution**: First query available dedicated pools, then pass `pool_id` in the CreateNotebook request:

```bash
# 1. List dedicated pools available in the region
hcloud ModelArts ListAuthoringClusters --cli-region={region} --type=DEDICATED

# 2. Create notebook targeting a specific dedicated pool
hcloud ModelArts CreateNotebook --cli-region={region} \
  --pool_id={pool_id} \
  --volume.category=OBS \
  --volume.ownership=DEDICATED \
  --volume.uri=obs://{bucket_name}/ \
  --volume.mount_path=/home/ma-user/work/ \
  --volume.dew_secret_name={dew_secret_name} \
  --flavor_id={flavor_id} \
  --image_id={image_id} \
  --name={instance_name}
```

> **Note**: `pool_id` is a top-level parameter of CreateNotebook, not nested inside `volume`. Each dedicated pool supports specific flavors — verify flavor availability via `ShowCluster --cluster_id={pool_id}` before creation.

---

## 4. OBS as data_volume Silently Fails to Mount

**Symptom**: Creating a notebook with `data_volumes` containing `category=OBS` succeeds (API returns 200, instance enters RUNNING), but the OBS data volume is **not actually mounted**. The data volume shows `mount_type=STATIC` with no `status` field (no `MOUNTED`/`IN_USE`), while successful mounts show `status=MOUNTED` or `status=IN_USE`.

**Root Cause**: OBS as a `data_volume` (extended storage) uses `mount_type=STATIC`, which does not result in an actual filesystem mount. In contrast, OBS as the main `volume` uses `mount_type=MAIN` and mounts successfully (`status=IN_USE`).

**Verified Comparison**:

| Configuration | mount_type | status | Actually Mounted? |
|---------------|-----------|--------|-------------------|
| `volume.category=OBS` (main storage) | MAIN | IN_USE | ✅ Yes |
| `data_volumes[].category=OBS` (data volume) | STATIC | (none) | ❌ No |
| `data_volumes[].category=OBSFS` (data volume) | DYNAMIC | MOUNTED | ✅ Yes |

**Solution**: To mount OBS storage to a notebook:
- **As main storage**: Use `volume.category=OBS` + `ownership=DEDICATED` (verified working)
- **As additional data volume**: Use `data_volumes[].category=OBSFS` (DYNAMIC mount, verified working) — note that OBSFS data volumes do not require `dew_secret_name`
- **Avoid**: `data_volumes[].category=OBS` — the API accepts it but the mount silently fails

---

## 5. Bucket Type (POSIX vs OBJECT) Is Not a Determining Factor

**Symptom**: Initial analysis suspected that OBS/OBSFS mounting requires a POSIX-type (并行文件系统) bucket, and that regular OBJECT-type buckets would fail.

**Verified Results**: Both bucket types work for `OBS:DEDICATED` as main storage:

| Bucket | BucketType | category | Result |
|--------|-----------|----------|--------|
| `apr` | POSIX | OBS:DEDICATED (main) | ✅ `status=IN_USE` |
| `devserver` | OBJECT | OBS:DEDICATED (main) | ✅ `status=IN_USE` |
| `apr` | POSIX | OBSFS:DEDICATED (main) | ✅ `status=IN_USE` |

**Conclusion**: The bucket type (POSIX vs OBJECT) does **not** determine whether OBS/OBSFS mounting succeeds. The determining factors are: (1) using `DEDICATED` ownership, and (2) using OBS/OBSFS as the main `volume` rather than as a `data_volume` with `category=OBS`.

---

## 6. OBSFS:MANAGED as Extended Storage Not Supported

**Symptom**: Using `data_volumes` with `category=OBSFS` + `ownership=MANAGED` returns:

```json
{"error_code": "ModelArts.6702", "error_msg": "The extended storage OBSFS:MANAGED is not supported"}
```

**Solution**: OBSFS extended storage requires `ownership=DEDICATED`. Use an existing dedicated pool or specify the bucket URI directly.

---

## 7. OBS Storage Requires DEW Secret (dew_secret_name)

**Symptom**: Creating a notebook with OBS/OBSFS main storage without `dew_secret_name` returns:

```json
{"error_code": "ModelArts.6967", "error_msg": "The dew secret is empty."}
```

**Root Cause**: ModelArts needs AK/SK credentials to access the user's OBS bucket. These credentials are stored securely in DEW (Data Encryption Workshop) / CSMS (Cloud Secret Management Service).

**Solution**: Create a DEW/CSMS secret containing your AK/SK credentials, then reference its name via `dew_secret_name`. Query existing secrets with:

```bash
hcloud CSMS listSecrets --cli-region={region} --limit=50
```

Use the `name` field from the response as the `dew_secret_name` value in the CreateNotebook request.

> **Note**: OBSFS as a `data_volume` (DYNAMIC mount) does **not** require `dew_secret_name`. Only OBS/OBSFS as main `volume` requires it.

---

## 8. OBS Data Volume Requires mount_path

**Symptom**: Creating a notebook with an OBS data volume without `mount_path` returns:

```json
{"error_code": "ModelArts.6927", "error_msg": "The format of mount path null is invalid."}
```

**Solution**: Always specify a `mount_path` for OBS data volumes. The path must start with `/` and contain only alphanumeric characters, hyphens, and underscores (e.g., `/obs/`, `/data/`). Blocklist paths such as `/cache/` are prohibited.

---

## 9. Architecture Mismatch Between Image and Flavor

**Symptom**: Creating a notebook with an aarch64 image and an x86_64 flavor (or vice versa) fails or results in unexpected behavior.

**Solution**: Ensure architecture compatibility:

| Image Architecture | Compatible Flavor Categories | Example Flavors |
|--------------------|------------------------------|-----------------|
| `x86_64` | CPU, GPU | `modelarts.vm.cpu.2u`, `modelarts.vm.gpu.t4u8` |
| `aarch64` | CPU (ARM), ASCEND | `modelarts.vm.arm.cpu.free`, `modelarts.bm.d910.xlarge.1` |

Query image architecture via `ListImage` (look for the `arch` field) and flavor architecture via `ListFlavors` (look for the `arch` field) before creating a notebook.

---

## 10. Use --cli-jsonInput as a General Workaround

When the hcloud CLI rejects valid API parameters due to schema validation limitations (e.g., missing enum values, unsupported nested structures), use `--cli-jsonInput` with a JSON file to pass parameters directly to the API:

```bash
hcloud ModelArts CreateNotebook --cli-region={region} --project_id={project_id} --cli-jsonInput=/path/to/input.json
```

> ⚠️ **Two requirements when using `--cli-jsonInput`**:
> 1. The JSON **must** wrap the request body in a `"body"` key — using the raw request body directly will be rejected with `cli-jsonInput文件内容不符合要求`.
> 2. `project_id` **must** be passed explicitly via `--project_id` on the command line — auto-resolution from credentials does not work with `--cli-jsonInput`, and omitting it will fail with `缺少必填参数:project_id`.

The JSON structure (with `body` wrapper):

```json
{
  "body": {
    "name": "my-notebook",
    "flavor": "modelarts.vm.cpu.2u",
    "image_id": "{image_id}",
    "pool_id": "{pool_id}",
    "volume": {
      "category": "EVS",
      "ownership": "MANAGED",
      "capacity": 5,
      "mount_path": "/home/ma-user/work/"
    },
    "data_volumes": [
      {
        "category": "OBSFS",
        "uri": "obs://{bucket_name}/",
        "mount_path": "/data/"
      }
    ]
  }
}
```

This approach bypasses CLI parameter validation while still using hcloud for authentication and request signing.

---

## 11. ShowLease duration Field Is Total Lease Duration, Not Remaining Time

**Symptom**: `ShowLease` returns a `duration` field that is easily misinterpreted as the remaining lease time. For example, `duration=4573131` (≈76 minutes) might be reported as "76 minutes remaining", but the actual remaining time visible in the console is ~1 hour.

**Root Cause**: The `duration` field represents the **total lease duration measured from `create_at`**, not the remaining time. The API does not directly return the remaining time — it must be calculated by the caller.

**Solution**: Calculate the remaining time manually:

```
remaining = (create_at + duration) - current_time
```

Where `current_time` can be obtained from `ShowNotebook` response. Example:

```python
create_at   = 1784946917652
duration    = 4573131        # ms, total lease duration from create_at
current_time = 1784948034829

remaining_ms = (create_at + duration) - current_time
# remaining_ms = 3455954 ≈ 57.6 minutes ≈ 1 hour
```

> **Note**: Always fetch `current_time` from `ShowNotebook` at the same time as querying `ShowLease`, since `ShowLease` does not include a `current_time` field.

---

## 12. ListImageGroup Response Field Inconsistent with --limit

**Symptom**: When calling `ListImageGroup` without `--limit`, the response returns image groups in a `groups` field. When calling with `--limit`, the `groups` field becomes empty and the data moves to a `data` field.

**Verified**:

| Call | Data Field | Count |
|------|-----------|-------|
| `ListImageGroup` (no limit) | `groups` | 200 |
| `ListImageGroup --limit=500` | `data` | 220 |

**Root Cause**: The CLI response parsing maps the API response differently depending on whether pagination parameters are included. Without `--limit`, the default response structure uses `groups`. With `--limit`, the paginated response structure uses `data` (alongside `current`, `pages`, `size`, `total`).

**Solution**: When parsing `ListImageGroup` response, check both fields:

```python
groups = data.get('groups') or data.get('data') or []
```

> **Note**: The default limit appears to be 200. Use `--limit=500` or higher to get the full list, and always parse from the `data` field when using pagination.

---

## 13. AttachDynamicStorage Only Supports POSIX Buckets

**Symptom**: When calling `AttachDynamicStorage` with `--category=OBS` or `--category=OBSFS` using an OBJECT-type OBS bucket, the API returns `ModelArts.6772`: "OBS storage bucket does not exist or user does not have permission to access it."

**Root Cause**: Dynamic storage mounting only supports **POSIX-type** buckets (parallel file systems). Standard OBJECT-type buckets are rejected even if they exist and the user has permission.

**Solution**: Use `obsutil stat obs://<bucket>` to check bucket type before attaching. Only buckets with `FsType: POSIX` can be dynamically mounted. Use `--category=OBSFS` for POSIX buckets.

> **Note**: This differs from `CreateNotebook` where both POSIX and OBJECT buckets can be used as storage volumes.

---

## Quick Reference: Storage Compatibility Matrix

| category | MANAGED (public pool) | DEDICATED (dedicated pool) | As data_volume |
|----------|----------------------|---------------------------|----------------|
| **EVS** | ✅ | — | — |
| **OBS** | ❌ `ModelArts.6702` | ✅ (main volume only, needs `pool_id`) | ❌ silently fails |
| **OBSFS** | ❌ `ModelArts.6702` | ✅ (main volume, needs `pool_id`) | ✅ (DYNAMIC mount, no dew_secret needed) |
| **EFS** | untested | ✅ (per docs, needs SFS Turbo ID + `pool_id`) | untested |
