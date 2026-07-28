# Data Flow Diagram

> Mermaid diagram showing the data flow for ModelArts training management operations.

---

## Overall Architecture

```mermaid
graph TB
    User[User Request] --> Agent[Agent]
    Agent --> Skill[Training Management Skill]
    Skill --> SKILLMD[SKILL.md]
    SKILLMD --> Refs[references/]
    Refs --> CLIExamples[cli-command-examples.md]
    Refs --> IAMPolicies[iam-policies.md]
    Refs --> KnownIssues[known-issues.md]
    Skill --> Confirm{Write Op?}
    Confirm -->|Yes| Prompt[User Confirmation]
    Prompt -->|Approved| Execute[Execute CLI]
    Prompt -->|Rejected| Abort[Abort Operation]
    Confirm -->|No| Execute
    Execute --> hcloud[hcloud CLI]
    hcloud -->|Success| Result[JSON Result]
    hcloud -->|Error| Error[Error Handling]
    Error -->|CLI Bug| SDK[SDK Fallback]
    Error -->|Auth Error| AuthError[Auth Error Message]
    Error -->|Param Error| ParamError[Param Error Message]
    SDK --> Result
    Result --> Agent
    Agent --> User
```

---

## Training Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Creating: CreateTrainingJob
    Creating --> Waiting: Resources allocated
    Waiting --> Running: Start execution
    Running --> Succeeded: Training complete
    Running --> Failed: Training error
    Running --> Stopped: StopTrainingJob
    Creating --> Stopped: StopTrainingJob
    Waiting --> Stopped: StopTrainingJob
    Succeeded --> [*]: DeleteTrainingJob
    Failed --> [*]: DeleteTrainingJob
    Stopped --> [*]: DeleteTrainingJob
    Running --> Running: ShowTrainingJobLogsPreview
    Running --> Running: ShowTrainingJobMetrics
    Running --> Running: ListTrainingJobEvents
    Running --> Running: ListTrainingJobStages
    Running --> Running: ListTrainingJobTasks
```

---

## Algorithm Management Flow

```mermaid
graph LR
    Create[CreateAlgorithm] --> List[ListAlgorithms]
    List --> Show[ShowAlgorithmByUuid]
    Show --> Change[ChangeAlgorithm]
    Change --> Delete[DeleteAlgorithm]
    Show --> Search[ShowSearchAlgorithms]
    Show --> Publish[CreateAlgorithmVersionToGallery]
    Publish --> Gallery[Algorithm Gallery]
```

---

## Training Experiment Flow

```mermaid
graph LR
    Check[CheckTrainingExperiment] --> Create[CreateTrainingExperiment]
    Create --> List[ListTrainingExperiments]
    List --> Show[ShowTrainingExperimentDetails]
    Show --> Change[ChangeTrainingExperiment]
    Change --> Delete[DeleteTrainingExperiment]
```

---

## Model Import Flow

```mermaid
graph LR
    Agency[CreateModelArtsAgency] --> Engine[ShowModelEngineAndRuntime]
    Engine --> Create[CreateModel]
    Create --> List[ListModels]
    List --> Show[ShowModel]
    Show --> Delete[DeleteModel]
```

---

## Auto Search Flow

```mermaid
graph TB
    Job[Training Job with Auto Search] --> Trials[ShowAutoSearchTrials]
    Trials --> Trial[ShowAutoSearchPerTrial]
    Trials --> Analysis[ShowAutoSearchParamsAnalysis]
    Analysis --> Path[ShowAutoSearchParamAnalysisResultPath]
    Trial --> EarlyStop[ShowAutoSearchTrialEarlyStop]
    Templates[ShowAutoSearchYamlTemplatesInfo] --> TemplateContent[ShowAutoSearchYamlTemplateContent]
```

---

## Training Image Save Flow

```mermaid
graph LR
    Job[Running Training Job] --> Create[CreateSaveImageJob]
    Create --> Show[ShowSaveImageJob]
    Show --> SWR[SWR Image Registry]
```

---

## Event Management Flow

```mermaid
graph TB
    Job[Training Job] --> Events[ListTrainingJobEvents]
    Job --> Stages[ListTrainingJobStages]
    Job --> Tasks[ListTrainingJobTasks]
    System[System] --> SysEvents[ListEvents]
    System --> Categories[ListEventCategories]
    System --> Scheduled[ListScheduledEvents]
    Scheduled --> Accept[AcceptScheduledEvent]
```
