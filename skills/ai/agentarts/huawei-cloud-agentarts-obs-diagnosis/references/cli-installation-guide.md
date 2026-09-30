# CLI Installation Guide

## hcloud CLI (KooCLI)

### Installation

Download and install from: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### Windows

```bash
winget install Huawei.KooCLI --source winget
```

### Configuration

Configure credentials interactively (never paste AK/SK in chat):

```bash
hcloud configure
hcloud configure set --cli-agree-privacy-statement=true
```

### Verify Installation

```bash
hcloud configure list
hcloud APM --help
hcloud AOM --help
hcloud LTS --help
```

### Services Used by This Skill

| Service | Description | Key Operations |
|---------|-------------|----------------|
| APM | Application Performance Management | ListBusiness, ShowToken, SearchAgent, SearchTransaction |
| AOM | Application Operations Management | ListPromInstance, ListAccessCode, ListInstantQueryAomPromGet |
| LTS | Log Tank Service | ListLogGroups, ListLogStreams, ListLogs |
| IAM | Identity and Access Management | ListPoliciesV5, GetAuthorizationSchemaV5 |
