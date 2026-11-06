# Data Flow Diagram - Huawei Cloud OBS Directory Count

```mermaid
flowchart TD
    U[User] -->|asks: count directories in OBS bucket/prefix| A[Agent (skills_bot)]
    A -->|1. confirm bucket, prefix, recursive?| U
    U -->|confirms target| A
    A -->|2. preflight: hcloud present + obsutil configured| P{hcloud OBS ls -limit=1 OK?}
    P -- no --> C[Guide user: configure credentials per cli-installation-guide]
    C --> U
    P -- yes --> S[Run paython3 scripts/count_obs_directories.py<br/>--bucket B --prefix P [--recursive]]
    S --> L[hcloud OBS ls obs://B/P -d -limit=1000<br/>paginate via -marker]
    L --> V{Validate --bucket/--prefix regex}
    V -- invalid --> E1[exit 2 : input validation message]
    L --> Q[Count immediate/recursive directories<br/>exclude self-entry, dedupe]
    Q --> OUT{success?}
    OUT -- yes --> R[print integer count (or JSON) stdout, exit 0]
    OUT -- no --> E2[exit 3 : bilingual error on stderr]
    R --> A
    A -->|"4. return the integer to the user"| U
```

Notes:

- Input validation happens **before** any listing call, so malicious bucket/prefix values
  never reach the subprocess.
- The script only ever runs `hcloud OBS ls` (a read-only listing). It performs no
  create/upload/modify/delete operation.
- Recursive mode traverses each discovered directory level (bounded by `--max-depth`
  when set) and deduplicates visited directories.