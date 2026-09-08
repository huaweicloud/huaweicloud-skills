# Dataflow Diagrams — cloudrobo-dispatch

## 1. High-Level Architecture

```mermaid
flowchart LR
    subgraph Agent["Agent / LLM"]
        PROMPT["User intent: '让机器人去抓红色方块'"]
    end

    subgraph Access["Access Layers"]
        CLI["cloudrobo dispatch <cmd>"]
        SDK["DispatchClient (Python)"]
    end

    SERVICE["cloudrobo-service (REST API)"]
    BACKEND["robo-dispatcher /v1/robo-dispatcher/sessions/{session_id}/tasks"]

    Agent --> CLI
    Agent --> SDK
    CLI --> SERVICE
    SDK --> SERVICE
    SERVICE --> BACKEND
```

## 2. Task Dispatching Dataflow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant CLI as cloudrobo dispatch
    participant S as cloudrobo-service
    participant D as robo-dispatcher

    U->>A: "让机器人 R1 去抓红色方块"
    A->>A: resolve session_id (= current workspace_id) + robot_id + exec_model_id + stop condition
    A->>U: confirm task config (mutating op)
    U-->>A: confirm
    A->>CLI: create-task --session-id <sid> --name ... --task "..." --constraints-json '{"model":{...},"robot_id":...,"exec_constraints":{...}}'
    CLI->>S: POST /v1/robo-dispatcher/sessions/{sid}/tasks
    S->>D: forward request
    D-->>S: created task (task_id, status=PENDING)
    S-->>CLI: JSON {task_id, status}
    CLI-->>A: print result
    A->>CLI: wait-task --session-id <sid> --task-id <tid> [--timeout 600]  (blocks; polls every 5s)
    CLI->>S: GET /v1/robo-dispatcher/sessions/{sid}/tasks/{tid}  (repeated internally every 5s)
    S-->>CLI: task detail + status (RUNNING ... COMPLETED/FAILED/CANCELLED)
    Note over A,CLI: wait-task returns once status != RUNNING (no manual 20-30s polling loop)
    A->>CLI: show-task-result --session-id <sid> --task-id <tid>
    CLI->>S: GET /v1/robo-dispatcher/sessions/{sid}/tasks/{tid}/result
    S-->>CLI: {task, log_items}
    CLI-->>A: print result + logs
    A-->>U: summarize outcome
```

## 3. Task Cancellation Dataflow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant CLI as cloudrobo dispatch
    participant S as cloudrobo-service
    participant D as robo-dispatcher

    U->>A: "取消刚才的调度任务"
    A->>CLI: show-task --session-id <sid> --task-id <tid>
    CLI->>S: GET ...
    S-->>CLI: current status
    A->>U: confirm cancellation (mutating op)
    U-->>A: confirm
    A->>CLI: cancel-task --session-id <sid> --task-id <tid>
    CLI->>S: DELETE /v1/robo-dispatcher/sessions/{sid}/tasks/{tid}
    S->>D: request cancellation
    D-->>S: task transitioned to terminal (cancelled)
    S-->>CLI: JSON
    CLI-->>A: print result
    A->>CLI: show-task --session-id <sid> --task-id <tid>
    CLI->>S: GET ...
    S-->>CLI: status = CANCELLED
    A-->>U: report cancelled state
```

## 4. Task Listing & Filtering Dataflow

```mermaid
flowchart LR
    U["User wants to see tasks"] --> A["Agent"]
    A --> FETCH["cloudrobo dispatch list-tasks --session-id <sid> [filters]"]
    FETCH --> API["GET /v1/robo-dispatcher/sessions/{sid}/tasks"]
    API --> RESP["JSON array of tasks"]
    RESP --> REPORT["Agent reports: status count, filters applied"]

    subgraph Filters["List Filters"]
        F1["--status"]
        F2["--robot-id"]
        F3["--start-time / --end-time"]
        F4["--infer-service-id"]
        F5["--content-match"]
        F6["--sort-key / --sort-dir"]
        F7["--limit / --offset"]
    end
    A -.-> Filters
```

## 5. Cross-Module Orchestration Dataflow

```mermaid
flowchart TD
    subgraph Prior["Pre-requisite modules (resolved by other skills)"]
        WS["cloudrobo-workspace: confirm workspace"]
        ROBOT["cloudrobo-robot: register / lookup robot_id"]
        ASSET["cloudrobo-asset / infer: model & infer-service_id"]
    end

    SESSION["session_id (== current workspace_id in current version)"]

    subgraph Dispatch["This skill (cloudrobo-dispatch)"]
        CREATE["create-task"]
        LIST["list-tasks"]
        SHOW["show-task"]
        WAIT["wait-task"]
        CANCEL["cancel-task"]
        RESULT["show-task-result"]
    end

    WS --> SESSION
    ROBOT --> CREATE
    ASSET --> CREATE
    SESSION --> CREATE
    CREATE --> LIST
    CREATE --> SHOW
    CREATE --> WAIT
    SHOW --> RESULT
    WAIT --> RESULT
    SHOW --> CANCEL
```

> **Note**: This skill does not call other skills by name. The agent orchestrates across
> skills: it uses `cloudrobo-robot`/`cloudrobo-asset`/`cloudrobo-infer` first to resolve
> `robot_id`, model / `exec_model_id`, and `infer-service_id`, then uses this dispatch skill
> to create and monitor the dispatcher task.
