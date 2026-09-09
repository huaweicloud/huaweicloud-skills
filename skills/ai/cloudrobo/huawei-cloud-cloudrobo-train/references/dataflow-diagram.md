# Dataflow Diagram

## High-Level Architecture

```mermaid
flowchart TD
    User[User Request] --> Trigger[Skill Trigger Matching]
    Trigger --> Route[Capability Domain Routing]
    Route --> CLI[cloudrobo train CLI]
    CLI --> AssetPkg[cloudrobo-asset]
    CLI --> TrainPkg[cloudrobo-train SDK]
    AssetPkg --> AssetAPI[cloudrobo-asset-manager API]
    TrainPkg --> TaskAPI[cloudrobo-service API]
    TrainPkg --> SimAPI[cloudrobo-service SimRL API]
    AssetAPI --> OBS[(OBS Storage)]
    TaskAPI --> CCE[(CCE Cluster)]
    SimAPI --> CCE
    CCE --> NPU[Ascend NPU]
```

## API Surface Routing (--sim-rl flag)

```mermaid
flowchart LR
    Cmd[CLI command] --> Flag{--sim-rl?}
    Flag -->|No| TrainAPI[/v1/training/train-tasks]
    Flag -->|Yes| SimAPI[/v1/training/rl-tasks/simulation]
    TrainAPI --> TrainClient[12 train_* SDK methods]
    SimAPI --> SimClient[15 sim_rl_* SDK methods<br/>+ 6 unprefixed = 33 total]
```

## Task Lifecycle (16 states)

```mermaid
stateDiagram-v2
    [*] --> DRAFT: save-draft
    [*] --> CREATING: pretrain/finetune/create-task
    DRAFT --> CREATING: restart-task (edit & resubmit)
    CREATING --> WAITING: submit accepted
    CREATING --> CREATE_FAILED: submit error
    WAITING --> RUNNING: resources scheduled
    WAITING --> FAILED: schedule error
    RUNNING --> FINISHED: task complete
    RUNNING --> RUN_FAILED: execution error
    RUNNING --> STOPPING: stop-task
    STOPPING --> STOPPED: stop success
    STOPPING --> STOP_FAILED: stop error
    FINISHED --> [*]: terminal success
    CREATE_FAILED --> [*]: terminal failure
    RUN_FAILED --> [*]: terminal failure
    STOPPED --> [*]: terminal stopped
    STOP_FAILED --> [*]: terminal failure
    FAILED --> [*]: terminal failure
    [*] --> DELETING: delete-tasks (batch POST for train / DELETE per-id for SimRL)
    DELETING --> [*]: delete success (task removed)
    DELETING --> DELETE_FAILED: delete error
    NOT_EXIST --> [*]: terminal
    ABNORMAL --> [*]: terminal
    UNKNOWN --> [*]: terminal
```

## Execution Stages (4 phases)

```mermaid
flowchart LR
    S1[SCHEDULING<br/>stage_order=1] --> S2[PREPARING<br/>stage_order=2]
    S2 --> S3[RUNNING<br/>stage_order=3]
    S3 --> S4[END<br/>stage_order=4]
    S4 --> Done[Task FINISHED]
```

Each main stage contains `sub_stages[]` with name, en_message, zh_message, create_time.

## Fine-tuning Dataflow

```mermaid
flowchart LR
    subgraph Prepare
        P1[Query Base Model<br/>list-assets --type model] --> P2[Query Dataset<br/>list-assets --type dataset]
        P2 --> P3[Choose Method<br/>SFT/LORA/QLORA/DEEPSPEED]
        P3 --> P4[Choose Spec<br/>Ascend format string]
    end
    subgraph Execute
        E1[Create finetune task<br/>POST /v1/training/train-tasks<br/>train_mode=MODEL_TUNING] --> E2[Poll Status<br/>show-task 30-60s]
        E2 --> E3[Monitor Stages<br/>get-stages]
        E3 --> E4[FINISHED]
    end
    subgraph Export
        X1[Extract output_models] --> X2[Export via cloudrobo asset<br/>or deploy via cloudrobo-infer]
    end
    P4 --> E1
    E4 --> X1
```

## Pretrain Dataflow

```mermaid
flowchart LR
    subgraph Prepare
        P1[Query Algorithm<br/>list-publication-assets / list-assets] --> P2[Extract algorithm fields<br/>asset_id, image_url, command, boot_file]
        P2 --> P3[Query Dataset]
        P3 --> P4[Choose Spec<br/>typically larger]
    end
    subgraph Execute
        E1[Create pretrain task<br/>POST /v1/training/train-tasks<br/>train_mode=TRAIN_FROM_SCRATCH<br/>full algorithm object] --> E2[Poll Status]
        E2 --> E3[FINISHED]
    end
    P4 --> E1
```

## SimRL Dataflow (--sim-rl)

```mermaid
flowchart TD
    Start[SimRL task request] --> Create[create-task --sim-rl<br/>POST /v1/training/rl-tasks/simulation]
    Create --> Poll[Poll status<br/>show-task --sim-rl]
    Poll --> Monitor[Monitor<br/>get-resource-usage --sim-rl --metric --start --end<br/>get-events --sim-rl --start-time --end-time<br/>get-logs --sim-rl<br/>get-signed-url --sim-rl --file-source --file-name<br/>(no get-stages — train-only)]
    Monitor --> Terminal{Terminal?}
    Terminal -->|No| Poll
    Terminal -->|Yes| Done[FINISHED/FAILED]
    Done --> Lifecycle[stop-task --sim-rl<br/>restart-task --sim-rl<br/>clone-task (SimRL-only)<br/>delete-tasks --sim-rl]
```

## Draft Dataflow (save & resubmit)

```mermaid
flowchart TD
    Start[Need to save config without executing] --> Save[save-draft<br/>POST /v1/training/train-tasks/draft<br/>DraftTrainTaskDto: name + workspace_id]
    Save --> DraftState[Task status = DRAFT<br/>task_id returned]
    DraftState --> Later{Later}
    Later -->|Resubmit as-is| RestartCLI[restart-task --task-id<br/>CLI: resubmit existing config]
    Later -->|Resubmit with edits| RestartEdit[restart-task --task-id --config<br/>CLI: override fields via --config]
    Later -->|SDK full body| RestartSDK[restart_train_task task_id, req<br/>SDK: full TrainTaskDto body]
    RestartCLI --> Submit[Task status = CREATING]
    RestartSDK --> Submit
    Submit --> Poll[Poll to terminal]
```

## Diagnosis Dataflow (failure analysis)

```mermaid
flowchart TD
    Fail[Task FAILED/RUN_FAILED/CREATE_FAILED] --> Detail[Get task detail<br/>show-task --task-id]
    Detail --> Stages[get-stages<br/>identify failed stage]
    Stages --> Events[get-events --start-time --end-time<br/>filter --level Error]
    Events --> Logs[get-logs --file-name<br/>detailed output]
    Logs --> Diagnose{Diagnose}
    Diagnose -->|CREATE_FAILED| S1[Check spec format<br/>cluster_id, resource]
    Diagnose -->|Schedule failure| S2[Check spec, worker_num<br/>cluster capacity]
    Diagnose -->|Image pull| S3[Check algorithm.image_url]
    Diagnose -->|Dataset denied| S4[Check dataset_asset_id<br/>workspace permissions]
    Diagnose -->|OOM| S5[Check spec memory<br/>reduce batch_size]
    Diagnose -->|Algorithm error| S6[Check command, boot_file<br/>parameters]
```

## Field Mapping Dataflow (Algorithm → TrainTaskDto.algorithm)

```mermaid
flowchart LR
    subgraph Algorithm Asset
        A1[algorithm_asset_id] --> A2[algorithm_asset_name]
        A2 --> A3[algorithm_version_id]
        A3 --> A4[image_url]
        A4 --> A5[command]
        A5 --> A6[boot_file]
        A6 --> A7[code_dir]
    end
    subgraph TrainTaskDto.algorithm
        T1[algorithm_asset_id]
        T2[algorithm_asset_name]
        T3[algorithm_version_id]
        T4[engine.image_url]
        T5[command]
        T6[boot_file]
        T7[code_dir]
    end
    A1 --> T1
    A2 --> T2
    A3 --> T3
    A4 --> T4
    A5 --> T5
    A6 --> T6
    A7 --> T7
```
