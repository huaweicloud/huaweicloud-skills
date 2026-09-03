# CLI Command Examples — ModelArts Notebook Management

> All 31 CLI command examples across 7 functional domains. Extracted from SKILL.md for readability.

---


### 1. Instance Management (8 APIs)

#### List Notebook Instances

```bash
# List notebooks with optional filters
hcloud ModelArts ListNotebooks --cli-region={region} [--feature=NOTEBOOK] [--billing=ALL]

# List all notebooks across all statuses
hcloud ModelArts ListAllNotebooks --cli-region={region} [--limit=10] [--offset=0] [--name={name}]
```

#### Show Notebook Details

```bash
# Show details of a specific notebook
hcloud ModelArts ShowNotebook --cli-region={region} --id={instance_id}
```

#### Create Notebook Instance

> ⚠️ **Requires user confirmation** — This operation creates a resource that may incur charges.

**前置条件**：
1. **ModelArts 委托（agency）已配置** — 否则报 `ModelArts.6701`。在控制台「模型训练服务 → 全局配置」中配置委托。
2. **镜像与规格架构匹配** — 使用 `ListImage` 和 `ListFlavors` 查询，确保 `arch` 字段一致（详见 known-issues #9）。

**方式一：OBS/OBSFS 作为主存储（CLI 直接支持）**

```bash
hcloud ModelArts CreateNotebook --cli-region={region} \
  --image_id={image_id} \
  --name={instance_name} \
  --volume.category=OBS \
  --volume.ownership=DEDICATED \
  --volume.uri=obs://{bucket_name}/ \
  --volume.mount_path=/home/ma-user/work/ \
  --volume.dew_secret_name={dew_secret_name} \
  --flavor={flavor_id}
```

> 注意：CLI 参数名是 `--flavor`（非 `flavor_id`）、`--volume.capacity`（非 `volume.size`）。`--volume.ownership` 仅支持 `MANAGED|DEDICATED`（非 `PRIVATE`）。CLI `--volume.category` 仅支持 `OBS|OBSFS|EFS`，不支持 `EVS`。

**方式二：EVS 作为系统盘（需 `--cli-jsonInput` 绕过 CLI 枚举限制）**

EVS 被 CLI 参数枚举拒绝，必须使用 JSON 文件方式（详见 known-issues #1/#10）：

```json
// create-notebook.json
{
  "body": {
    "name": "my-notebook",
    "flavor": "modelarts.vm.cpu.2u",
    "image_id": "{image_id}",
    "volume": {
      "category": "EVS",
      "ownership": "MANAGED",
      "capacity": 5,
      "mount_path": "/home/ma-user/work/"
    }
  }
}
```

```bash
hcloud ModelArts CreateNotebook --cli-region={region} \
  --project_id={project_id} \
  --cli-jsonInput=create-notebook.json
```

> ⚠️ 使用 `--cli-jsonInput` 时必须显式传 `--project_id`，自动解析不生效。JSON 必须用 `{"body":{...}}` 包裹。

#### Update Notebook Instance

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts UpdateNotebook --cli-region={region} --id={instance_id} [--name={new_name}] [--description={desc}]
```

#### Delete Notebook Instance

> ⚠️ **Requires user confirmation** — This operation is irreversible.

```bash
hcloud ModelArts DeleteNotebook --cli-region={region} --id={instance_id}
```

#### Start Notebook Instance

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts StartNotebook --cli-region={region} --id={instance_id} [--duration={duration}] [--type={type}]
```

#### Stop Notebook Instance

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts StopNotebook --cli-region={region} --id={instance_id}
```

---

### 2. Lease Management (2 APIs)

#### Show Lease Information

```bash
hcloud ModelArts ShowLease --cli-region={region} --id={instance_id}
```

#### Renew Lease

> ⚠️ **Requires user confirmation**

```bash
# type 仅支持小写 timing|idle（与 ShowLease 查询返回的大写 TIMING 不同）
hcloud ModelArts RenewLease --cli-region={region} --id={instance_id} --duration={duration} --type={type}
```

---

### 3. Tag Management (3 APIs)

#### Show Notebook Tags

```bash
hcloud ModelArts ShowNotebookTags --cli-region={region} [--workspace_id={workspace_id}]
```

#### Create Notebook Tags

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts CreateNotebookTags --cli-region={region} \
  --resource_id={resource_id} \
  --tags.1.key={key1} --tags.1.value={value1}
```

#### Delete Notebook Tags

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts DeleteNotebookTags --cli-region={region} \
  --resource_id={resource_id} \
  --tags.1.key={key1} --tags.1.value={value1}
```

---

### 4. Image Management (8 APIs)

#### Create Image from Running Instance

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts CreateImage --cli-region={region} \
  --id={instance_id} \
  --name={image_name} \
  --namespace={namespace} \
  --tag={tag} \
  [--description={desc}] \
  [--swr_instance_domain={domain}] \
  [--swr_instance_id={swr_id}]
```

#### List Supported Images

```bash
hcloud ModelArts ListImage --cli-region={region} [--limit=10] [--offset=0] [--name={name}] [--service_type={type}]
```

#### Register Custom Image

> ⚠️ **Requires user confirmation**

```bash
# arch 仅支持大写 X86_64|AARCH64（与 ListImage/ShowImage 查询返回的小写 x86_64 不同）
hcloud ModelArts RegisterImage --cli-region={region} \
  --swr_path={swr_path} \
  [--arch={arch}] \
  [--description={desc}] \
  [--flavor_type={flavor_type}] \
  [--service_type={service_type}]
```

#### Show Image Details

```bash
hcloud ModelArts ShowImage --cli-region={region} --id={image_id}
```

#### Delete Image

> ⚠️ **Requires user confirmation** — This operation is irreversible.

```bash
hcloud ModelArts DeleteImage --cli-region={region} --id={image_id} [--is_force=false]
```

#### Sync Image Status

> ⚠️ **Requires user confirmation** — Triggers async operation.

```bash
hcloud ModelArts SyncImage --cli-region={region} --image_id={image_id}
```

#### List Image Groups

```bash
hcloud ModelArts ListImageGroup --cli-region={region} [--limit=10] [--offset=0] [--name={name}] [--type={type}]
```

#### Delete Image Group

> ⚠️ **Requires user confirmation** — This operation is irreversible.

```bash
hcloud ModelArts DeleteImageGroup --cli-region={region} --id={group_id} [--is_force=false]
```

#### Update Image Group

> ⚠️ **Requires user confirmation**

```bash
hcloud ModelArts UpdateImageGroup --cli-region={region} --id={group_id} [--read_me={readme}] [--tags.1.key={k}] [--tags.1.value={v}]
```

---

### 5. Flavor and Cluster Queries (4 APIs)

#### List Notebook Flavors

```bash
hcloud ModelArts ListFlavors --cli-region={region} [--category={category}] [--feature={feature}] [--flavor_type={type}] [--limit=10] [--offset=0]
```

#### Show Switchable Flavors

```bash
hcloud ModelArts ShowSwitchableFlavors --cli-region={region} --id={instance_id} [--limit=10] [--offset=0]
```

#### List Authoring Clusters

```bash
# --type is required: MANAGED (public pool) or DEDICATED (dedicated pool)
hcloud ModelArts ListAuthoringClusters --cli-region={region} --type={type} [--limit=10] [--offset=0] [--scope={scope}]
```

#### Show Cluster Details

```bash
hcloud ModelArts ShowCluster --cli-region={region} --cluster_id={cluster_id}
```

---

### 6. Feature Query (1 API)

#### List Features

```bash
hcloud ModelArts ListFeatures --cli-region={region} --feature={feature}
```

---

### 7. Dynamic Storage Management (4 APIs)

#### List Dynamic Storages

```bash
hcloud ModelArts ListDynamicStorages --cli-region={region} --instance_id={instance_id}
```

#### Attach Dynamic Storage

> ⚠️ **Requires user confirmation**

**前置条件**：
1. **实例必须为 RUNNING 状态** — STOPPED 状态挂载报 `ModelArts.6958`
2. **mount_path 必须以 `/data/` 开头且带结尾斜杠** — 如 `/data/my-data/`；不带结尾斜杠报 `ModelArts.6785`
3. **uri 需带结尾斜杠** — 如 `obs://bucket/`
4. **仅支持 POSIX 桶（并行文件系统）** — OBJECT 桶报 `ModelArts.6772`（详见 known-issues #13）

```bash
hcloud ModelArts AttachDynamicStorage --cli-region={region} \
  --instance_id={instance_id} \
  --category={category} \
  --mount_path={mount_path} \
  --uri={uri} \
  [--efs_id={efs_id}]
```

#### Show Dynamic Storage Details

```bash
hcloud ModelArts ShowDynamicStorage --cli-region={region} --instance_id={instance_id} --storage_id={storage_id}
```

#### Detach Dynamic Storage

> ⚠️ **Requires user confirmation** — This operation is irreversible.

```bash
hcloud ModelArts DetachDynamicStorage --cli-region={region} --instance_id={instance_id} --storage_id={storage_id}
```

---

