# Data Flow Diagram

```mermaid
flowchart TD
    A[User Request] --> B[Phase 0: Credential Setup\nHUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY]
    B --> C[Phase 1: Resource Discovery\nhcloud Config ListAllResources]
    C --> D[RMS JSON Inventory]
    D --> E[Phase 2: Batch Analysis\nNetwork → Storage → Compute →\nCCE → Database → Cache/MQ → Aux]
    E --> F[Phase 3: Terraform HCL Generation\nproviders.tf / variables.tf / main.tf\nstorage.tf / compute.tf / cce.tf\nsecurity.tf / lts.tf ...]
    F --> G[Phase 4: Validation\nterraform fmt → init → validate → plan]
    G --> H{Plan OK?}
    H -- No --> I[Fix provider schema mismatches\nand regenerate]
    I --> G
    H -- Yes --> J[Phase 5: Gap Analysis\ncompare_resources.sh]
    J --> K[Final Report\ncoverage ratio + documented gaps]
    K --> L[Deliver to User\napply only after explicit confirmation]
```

## Description

1. **Discovery** — `query_all_resources.sh` calls the RMS `ListAllResources` API once per region and stores the full inventory as JSON.
2. **Analysis** — resources are grouped by service layer and analyzed in dependency order (VPC → storage → ECS → CCE → GaussDB → DCS/DMS → KMS/LTS).
3. **Generation** — Terraform HCL files are written layer by layer; only top-level resources are managed; AK/SK never appears in `.tf` files.
4. **Validation** — `validate_terraform.sh` runs `terraform fmt`, `init`, `validate`, and `plan`; schema mismatches are fixed iteratively.
5. **Gap analysis** — `compare_resources.sh` compares the plan's resource list against the RMS inventory and reports coverage plus documented gaps.