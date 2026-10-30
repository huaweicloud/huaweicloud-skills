# Dataflow Diagram — sac-intl-find-and-deploy-skill

```mermaid
flowchart LR
  U[User keyword] --> Q[query_catalog.py]
  Q --> C[(public OBS sac_intl.json (fresh fetch))]
  Q --> P[Candidate rows]
  P -->|user picks 1| D[download_tf_template_file.py]
  D --> W[workdir .tf/.tf.json]
  W --> N[normalize_tf_providers.py + env creds]
  N --> V[list_tf_variables.py + user confirm]
  V --> T[terraform init/plan/apply]
  T --> O[output + verify]
  O --> X[destroy + cleanup residue]
```
