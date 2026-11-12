# Data Flow Diagram

```mermaid
sequenceDiagram
    participant User as User / Agent
    participant Script as bcs_manage.py
    participant SDK as huaweicloudsdkbcs
    participant API as BCS v2 API
    participant Op as ListOpRecord
    participant Quality as skill-quality-cli

    User->>Script: subcommand + --region [read options | write target/body + --confirm]
    Script->>Script: load AK/SK from env, build BcsClient

    alt read-only subcommand
        Script->>SDK: List*/Show* request
        SDK->>API: GET/POST verified read path
        alt list
            API-->>SDK: instances (id, name)
            Script->>SDK: ShowBlockchainDetail (concurrent N+1 enrichment)
            SDK->>API: GET /v2/{project_id}/blockchains/{blockchain_id}
        end
        API-->>SDK: structured response
        SDK-->>Script: parsed response
        Script->>Script: render table or exactly one JSON payload
    else write subcommand without --confirm
        Script-->>User: impact preview + exit 2 (no change)
    else write subcommand with --confirm
        Script->>Script: build request model from flags / body file
        Script->>SDK: mutating call (create/delete/update/download)
        SDK->>API: POST/PUT/DELETE/GET verified path
        API-->>SDK: operation_id / stream / result
        alt binary download
            SDK-->>Script: SdkStreamResponse
            Script->>Script: consume_download_stream -> local file (mode 0600)
        else operation_id returned and not --no-wait
            loop until finished/failed/stop or --timeout
                Script->>SDK: ListOpRecord(operation_id)
                SDK->>API: GET /v2/{project_id}/operation/record
                API-->>SDK: operation status
            end
        end
        Script-->>User: operation summary / final status
    end

    Script-->>Quality: report trace_id / status / cost (non-blocking, external wrapper)
```

## Irreversible actions

| Action | Reversible? | Default guard |
|--------|-------------|---------------|
| delete-instance | No | preview + `--confirm` |
| delete-channel | No | preview + `--confirm` |
| remove-peers | No | preview + `--confirm` |
| remove-orgs | No | preview + `--confirm` |
| update-instance with `is_delete_org=true` | No (organization data lost) | preview + `--confirm` |
| freeze-cert | Yes (unfreeze) | preview + `--confirm` |
| create-instance | Yes (delete, data loss) | preview + `--confirm`, cost warning |

## Read vs write isolation

| Aspect | Read-only subcommands | Write subcommands |
|--------|----------------------|-------------------|
| `--confirm` | Not accepted / not required | Required, otherwise preview only + exit 2 |
| SDK methods | `list_*`, `show_*` only | create/update/delete/download methods |
| Output | tables or one JSON payload on stdout | preview + operation summary; `--json` gives one block |
| Side effects | none | may create/scale/freeze/delete resources |