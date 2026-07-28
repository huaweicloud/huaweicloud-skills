# IAM Policies for ModelArts Training Management

> Least-privilege IAM policies for the ModelArts training management skill.

---

## Required Permissions

### Training Job Management

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainingJob:create",
        "modelarts:trainingJob:list",
        "modelarts:trainingJob:getDetail",
        "modelarts:trainingJob:stop",
        "modelarts:trainingJob:delete",
        "modelarts:trainingJob:update",
        "modelarts:trainingJob:getLogs",
        "modelarts:trainingJob:getMetrics",
        "modelarts:trainingJob:getEngines",
        "modelarts:trainingJob:getFlavors",
        "modelarts:trainingJob:getQuotas",
        "modelarts:trainingJob:reportEvent"
      ],
      "Resource": "*"
    }
  ]
}
```

### Algorithm Management

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:algorithm:create",
        "modelarts:algorithm:list",
        "modelarts:algorithm:getDetail",
        "modelarts:algorithm:update",
        "modelarts:algorithm:delete",
        "modelarts:algorithm:search",
        "modelarts:algorithm:publishToGallery"
      ],
      "Resource": "*"
    }
  ]
}
```

### Training Job Tags

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainJobTag:create",
        "modelarts:trainJobTag:getDetail",
        "modelarts:trainJobTag:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

### Training Experiments

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:experiment:create",
        "modelarts:experiment:list",
        "modelarts:experiment:getDetail",
        "modelarts:experiment:delete",
        "modelarts:experiment:update",
        "modelarts:experiment:check"
      ],
      "Resource": "*"
    }
  ]
}
```

### Training Job Events

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainingJobEvent:list",
        "modelarts:trainingJobStage:list",
        "modelarts:trainingJobTask:list",
        "modelarts:event:list",
        "modelarts:eventCategory:list",
        "modelarts:scheduledEvent:list",
        "modelarts:scheduledEvent:accept"
      ],
      "Resource": "*"
    }
  ]
}
```

### Model Import

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:model:create",
        "modelarts:model:list",
        "modelarts:model:getDetail",
        "modelarts:model:delete",
        "modelarts:model:getEngineRuntime",
        "modelarts:agency:create"
      ],
      "Resource": "*"
    }
  ]
}
```

### Auto Search

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:autoSearch:getTrials",
        "modelarts:autoSearch:getTrialDetail",
        "modelarts:autoSearch:getParamsAnalysis",
        "modelarts:autoSearch:getAnalysisResultPath",
        "modelarts:autoSearch:trialEarlyStop",
        "modelarts:autoSearch:getYamlTemplateContent",
        "modelarts:autoSearch:getYamlTemplateInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

### Training Image Save

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:saveImageJob:create",
        "modelarts:saveImageJob:getDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Combined Policy (All Operations)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainingJob:*",
        "modelarts:algorithm:*",
        "modelarts:trainJobTag:*",
        "modelarts:experiment:*",
        "modelarts:trainingJobEvent:*",
        "modelarts:trainingJobStage:*",
        "modelarts:trainingJobTask:*",
        "modelarts:event:*",
        "modelarts:eventCategory:*",
        "modelarts:scheduledEvent:*",
        "modelarts:model:*",
        "modelarts:agency:create",
        "modelarts:autoSearch:*",
        "modelarts:saveImageJob:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Read-Only Policy

For query-only access (no write operations):

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainingJob:list",
        "modelarts:trainingJob:getDetail",
        "modelarts:trainingJob:getLogs",
        "modelarts:trainingJob:getMetrics",
        "modelarts:trainingJob:getEngines",
        "modelarts:trainingJob:getFlavors",
        "modelarts:trainingJob:getQuotas",
        "modelarts:algorithm:list",
        "modelarts:algorithm:getDetail",
        "modelarts:algorithm:search",
        "modelarts:trainJobTag:getDetail",
        "modelarts:experiment:list",
        "modelarts:experiment:getDetail",
        "modelarts:experiment:check",
        "modelarts:trainingJobEvent:list",
        "modelarts:trainingJobStage:list",
        "modelarts:trainingJobTask:list",
        "modelarts:event:list",
        "modelarts:eventCategory:list",
        "modelarts:scheduledEvent:list",
        "modelarts:model:list",
        "modelarts:model:getDetail",
        "modelarts:model:getEngineRuntime",
        "modelarts:autoSearch:getTrials",
        "modelarts:autoSearch:getTrialDetail",
        "modelarts:autoSearch:getParamsAnalysis",
        "modelarts:autoSearch:getAnalysisResultPath",
        "modelarts:autoSearch:getYamlTemplateContent",
        "modelarts:autoSearch:getYamlTemplateInfo",
        "modelarts:saveImageJob:getDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Additional Dependencies

ModelArts training jobs may require access to OBS for data and output storage:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "obs:bucket:GetBucketAcl",
        "obs:bucket:GetBucketPolicy",
        "obs:bucket:ListBucket",
        "obs:object:GetObject",
        "obs:object:PutObject"
      ],
      "Resource": [
        "obs:*:*:bucket:my-training-data",
        "obs:*:*:object:my-training-data/*"
      ]
    }
  ]
}
```
