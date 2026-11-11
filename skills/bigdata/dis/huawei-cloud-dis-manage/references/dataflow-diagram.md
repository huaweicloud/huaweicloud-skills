# DIS Data Flow

```mermaid
flowchart LR
    subgraph Producers
        A1[Application / Service]
        A2[DIS Agent]
        A3[IoT / Log collector]
    end

    subgraph DIS["Huawei Cloud DIS (region)"]
        S1[Stream channel]
        P1[Partition shardId-0]
        P2[Partition shardId-1]
        S1 --> P1
        S1 --> P2
        M[Stream / partition metrics]
        C[Consumer apps + checkpoints]
        S1 --- M
        P1 --> C
        P2 --> C
    end

    subgraph Destinations["Dump (transfer) destinations"]
        O[OBS bucket]
        W[DWS cluster]
        L[DLI database/table]
        R[MRS HDFS]
        T[CloudTable HBase/OpenTSDB]
    end

    A1 -->|SendRecords Base64| S1
    A2 -->|SendRecords| S1
    A3 -->|SendRecords| S1
    P1 -->|CreateObsTransferTask| O
    P1 -->|CreateDwsTransferTask| W
    P1 -->|CreateDliTransferTask| L
    P1 -->|CreateMrsTransferTask| R
    P1 -->|CreateCloudTableTransferTask| T
    C -->|ShowCursor + ConsumeRecords| A1
    M -->|ShowStreamMetrics / ShowPartitionMetrics| A1
```

## Operational flow

1. Producers write records into a stream (`SendRecords`, Base64 payloads).
2. DIS distributes records across partitions using `partition_id`,
   `partition_key`, or `explicit_hash_key`.
3. Dump tasks asynchronously deliver stream data to one of the five destinations
   through the DIS agency.
4. Consumer apps read records with a cursor (`ShowCursor` -> `ConsumeRecords`)
   and persist progress with checkpoints (`CommitCheckpoint`).
5. Monitoring reads throughput, latency, success-rate, and throttling series
   from stream and partition metric APIs; consumer state exposes committed
   sequence numbers for lag assessment.

## Management boundaries

- The skill manages DIS streams, dump tasks, apps, checkpoints, policies, and
  tags only. It does not write to the destination systems on the user's behalf;
  it configures DIS to do so through the agency.
- Deleting a stream does not delete data already dumped to OBS/DWS/DLI/MRS/
  CloudTable.
- IAM policy changes and OBS object content changes are out of scope.