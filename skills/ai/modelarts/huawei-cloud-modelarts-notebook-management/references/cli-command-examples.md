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

```bash
hcloud ModelArts CreateNotebook --cli-region={region} \
  --image_id={image_id} \
  --name={instance_name} \
  --volume.category=EVS \
  --volume.ownership=PRIVATE \
  --volume.size={size_gb} \
  --flavor_id={flavor_id}
```

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

