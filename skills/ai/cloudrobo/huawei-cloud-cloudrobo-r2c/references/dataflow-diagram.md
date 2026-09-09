# Dataflow Diagram

## High-Level Architecture

```mermaid
flowchart TD
    User[User / Agent] --> Trigger[Skill Trigger Matching]
    Trigger --> Route{Command}
    Route -->|client| ClientCmd[cloudrobo r2c client]

    ClientCmd --> Session1[Build R2CSession]
    Session1 --> HW[Hardware Adapter]
    Session1 --> Translator1[DeviceTranslator]
    Session1 --> SyncClient[SyncRobotClient]
    SyncClient --> ControlLoop[Control Loop]
```

> `cloudrobo r2c` exposes a single subcommand, `r2c client`. The cloud-side OpenPI adapter is
> a Python module/example (`inference/r2c_cloud_adapter.py`), not a CLI subcommand, and is out
> of scope for this skill.

## Robot Edge Client Dataflow

```mermaid
flowchart TD
    Start[cloudrobo r2c client --bundle cert.zip --robot-config config.yaml] --> LoadConfig[load_yaml robot_config]
    LoadConfig --> BuildSession[build_session<br/>R2CClient.connect bundle]
    BuildSession --> Heartbeat[_maybe_start_heartbeats<br/>if runtime.heartbeat.enabled]
    Heartbeat --> BuildSync[build_sync_robot_client<br/>SyncRobotClient.from_config]
    BuildSync --> Connect[hardware_adapter.connect]
    Connect --> StartLoop[robot_client.start<br/>control loop]

    subgraph ControlLoop[Control Loop - per tick]
        GetObs[hardware_adapter.get_observation] --> TranslateObs[translator.device_to_r2c]
        TranslateObs --> PubObs[session.publish_observations]
        PubObs --> WaitAction[wait for action<br/>timeout: action_response_timeout_s]
        WaitAction --> SubAction[session.subscribe_actions callback]
        SubAction --> TranslateAct[translator.r2c_to_device]
        TranslateAct --> ExecAction{dry_run?}
        ExecAction -->|true| LogOnly[Log action, skip execution]
        ExecAction -->|false| SendAct[hardware_adapter.send_action]
    end

    StartLoop --> ControlLoop
    ControlLoop --> Stop[Ctrl+C or duration elapsed]
    Stop --> Cleanup[robot_client.stop → hardware_adapter.disconnect → session.close]
```

## Cloud Adapter Dataflow (SDK, out of CLI scope)

The cloud-side OpenPI adapter is NOT a `cloudrobo r2c` CLI subcommand. It is a Python module
(`inference/r2c_cloud_adapter.py`) and example scripts (`examples/*_cloud_adapter.py`). For
reference, its dataflow is:

```mermaid
flowchart TD
    Start[cloud adapter example script<br/>e.g. examples/dummy_cloud_adapter.py] --> BuildSession[build_session_simple]
    BuildSession --> LoadCloud[load cloud_config.yaml]
    LoadCloud --> CreateAdapter[Create R2CCloudAdapter]
    CreateAdapter --> Start[adapter.start<br/>subscribe_observations]

    subgraph InferenceLoop[Per Observation Message]
        RecvObs[on_observations callback] --> TranslateIn[translator.r2c_to_model_input]
        TranslateIn --> Infer[policy_client.infer<br/>OpenPI websocket]
        Infer --> TranslateOut[translator.model_output_to_r2c]
        TranslateOut --> PubAct[session.publish_actions]
    end

    Start --> InferenceLoop
    InferenceLoop --> Stop[Ctrl+C]
    Stop --> Close[adapter.close → session.close]
```

## Credential Bundle Dataflow

```mermaid
flowchart LR
    subgraph Platform[Platform API - robot skill]
        Reg[robot create<br/>POST /v1/robots] --> Export[robot export-certificate<br/>POST /v1/robots/id/certificate/export]
    end
    Export --> Bundle[cert_config_*.zip]
    Bundle --> R2C[cloudrobo r2c client --bundle cert.zip]
    R2C --> Zenoh[Zenoh Router<br/>mTLS connection]
```

## Zenoh Topic Structure

```mermaid
flowchart LR
    subgraph Topics[Zenoh Pub/Sub Topics]
        Obs[project_id/device_id/observations]
        Act[project_id/device_id/actions]
        JointStates[project_id/device_id/joint_states]
        EEStates[project_id/device_id/end_effector_states]
        LocStates[project_id/device_id/localization_states]
        IMUStates[project_id/device_id/imu_states]
        Heartbeat[project_id/device_id/heartbeats]
    end

    EdgeClient[Robot Edge Client] -->|publish| Obs
    EdgeClient -->|publish| JointStates
    EdgeClient -->|publish| Heartbeat
    EdgeClient -->|subscribe| Act

    CloudAdapter[Cloud Adapter] -->|subscribe| Obs
    CloudAdapter -->|publish| Act
```

## Dry-Run Testing Dataflow

```mermaid
flowchart TD
    Start[Set dry_run: true in robot config] --> Launch[cloudrobo r2c client --bundle cert.zip]
    Launch --> GetObs[get_observation from hardware]
    GetObs --> PubObs[publish observations to Zenoh<br/>real data sent]
    PubObs --> RecvAct[receive action from cloud]
    RecvAct --> CheckDry{dry_run?}
    CheckDry -->|true| LogAction[Log action only<br/>no hardware execution]
    CheckDry -->|false| Execute[send_action to hardware]
```

## Cross-Skill Orchestration

```mermaid
flowchart LR
    subgraph robot[robot skill - Platform API]
        R1[robot create] --> R2[robot_id]
        R2 --> R3[robot export-certificate] --> R4[cert_config_*.zip]
    end
    subgraph r2c[r2c skill - Data Plane]
        D1[r2c client --bundle cert.zip]
    end
    subgraph workspace[workspace skill]
        W1[workspace use] --> W2[workspace_id]
    end
    W2 --> R1
    R4 --> D1
    D1 --> D2[Robot streaming<br/>observations + actions]
```

> The r2c skill depends on the robot skill for credential bundle production and the workspace
> skill for workspace context. The agent orchestrates across skills: register robot → export
> certificate → start r2c client (config is validated automatically at client startup).
