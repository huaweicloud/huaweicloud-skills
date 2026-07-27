# Verification Method

## CLI Verification

### Verify hcloud CLI is installed

```bash
hcloud --version
```

### Verify ModelArts service is available

```bash
hcloud ModelArts --help
```

### Verify authentication

```bash
hcloud ModelArts ListNotebooks --cli-region={region} --limit=1
```

If this returns successfully, authentication and connectivity are confirmed.

## Functional Testing

### Read Operations (Safe to test directly)

```bash
# List notebooks
hcloud ModelArts ListNotebooks --cli-region={region}

# List all notebooks
hcloud ModelArts ListAllNotebooks --cli-region={region}

# List flavors
hcloud ModelArts ListFlavors --cli-region={region}

# List images
hcloud ModelArts ListImage --cli-region={region}

# List authoring clusters
hcloud ModelArts ListAuthoringClusters --cli-region={region}
```

### Write Operations (Require user confirmation)

All write operations must be confirmed by the user before execution:

- CreateNotebook, UpdateNotebook, DeleteNotebook
- StartNotebook, StopNotebook
- RenewLease
- CreateNotebookTags, DeleteNotebookTags
- CreateImage, RegisterImage, DeleteImage, SyncImage
- DeleteImageGroup, UpdateImageGroup
- AttachDynamicStorage, DetachDynamicStorage

## SDK Fallback

If a CLI operation fails due to a CLI bug, fall back to SDK:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkmodelarts.v1.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v1.region.modelarts_region import ModelArtsRegion

# Initialize client
credentials = BasicCredentials(ak="{AK}", sk="{SK}", project_id="{project_id}")
client = ModelArtsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(ModelArtsRegion.value_of("{region}")) \
    .build()
```
