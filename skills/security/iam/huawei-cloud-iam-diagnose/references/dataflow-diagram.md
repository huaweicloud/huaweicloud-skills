# Data Flow Diagram

```mermaid
flowchart TD
    U[User input: user_name + action/resource] --> R[resolve_user_id]
    R -->|v3 keystone by name| V3[v3 keystone_list_users]
    R -->|fallback| V5[list_users_v5 full scan]
    R --> DH{found?}
    DH -- no --> EXIT[report user not found]
    DH -- yes --> EXPAND[expand permission chains]

    subgraph CHAINS[Step 2: Expand chains]
      EXPAND --> DPC[list_attached_user_policies_v5]
      EXPAND --> GRP[list_user_groups (keystone_list_groups_for_user)]
      EXPAND --> AGY[list_agencies_v5]
      GRP --> GP[list_attached_group_policies_v5]
      GRP --> GR[group_domain_roles / group_all_project_roles]
      AGY --> AP[list_attached_agency_policies_v5]
      AGY --> AR[agency_domain_roles / agency_all_project_roles]
    end

    DPC --> DOC[fetch policy docs]
    GP --> DOC
    AP --> DOC
    GR --> DOC
    AR --> DOC

    DOC --> EVAL[Step 3: evaluate Allow/Deny]
    EVAL --> FA[fetch get_policy_version_v5 / role.policy]
    FA --> MATCH[action/resource wildcard match]
    MATCH --> VERDICT[Step 4: verdict + confidence grade]
    VERDICT --> OUT[Output: likely has/has-not + chain + reference notes]

    OPTIONAL[Step 4b: real check cross-validation]
    GR --> OPTIONAL
    AR --> OPTIONAL
    OPTIONAL -->|keystone_check_*_for_group| CHECK_G[(check_group_permission.py)]
    OPTIONAL -->|check_*_permission_for_agency| CHECK_A[(check_agency_permission.py)]

    CHECK_G --> OUT
    CHECK_A --> OUT
```

## Legend

- R3 read-only: every node is a read call. No writes happen anywhere.
- Confidence grade computed from policy type (preset vs custom), `Condition` presence, and chain
  source (user direct / group / agency / EPS).