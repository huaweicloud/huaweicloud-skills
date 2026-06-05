# AscendC SynchronizationControl InterfaceSummary

## Overview
SynchronizationControlUsed for AI Core InternalAsynchronousParallelExecutesingleunitofbetweenofcoordinateadjust, distributeas**coreinsideSynchronization**and**corebetweenSynchronization**. 

## ⚠️ relatedkeygeneralmiss: DMA Asynchronous

MTE2 (GM→UB) and MTE3 (UB→GM) is**Asynchronous**of: `DataCopyPad` returnreturntimeDataData Copy**stillnotcompleted**. 

**mustmust**in DataCopyPad ofafterthroughexceed **EnQue/DeQue** Synchronization, onlyabilitysafeallvisitaskData:

```
AllocTensor → DataCopyPad → EnQue(VECIN)    ← standardrememberData Copycompleted
                            DeQue(VECIN)     ← etcwaitData Copycompleted, onlyabilityCalculation
                            ... Calculation ...
                            EnQue(VECOUT)    ← standardrememberCalculationcompleted
                            DeQue(VECOUT)    ← etcwaitCalculationcompleted, onlyabilitytransferoutput
                            DataCopyPad → FreeTensor
```

**pushrecommend EnQue/DeQue andnon PipeBarrier**: EnQue/DeQue isprecisionconfirmofliveproduce-disappearcostSynchronization, PipeBarrier isthickparticledegreeallPipelinelineblockblock. 

---

## one, coreinsideSynchronization

### 1.1 Pipelinetypetype

| Pipelinetypetype | containmeaning |
|----------|------|
| PIPE_S | standardamountPipelineline (GetValue/SetValue)  |
| PIPE_V | VectorCalculationPipelineline |
| PIPE_M | rulematrixCalculationPipelineline |
| PIPE_MTE1 | L1→L0A/L0B DataData Copy |
| PIPE_MTE2 | GM→L1/UB DataData Copy |
| PIPE_MTE3 | UB→GM DataData Copy |
| PIPE_FIX | L0C→GM/L1 DataData Copy |

### 1.2 multiplePipelineSynchronization (SetFlag/WaitFlag)

**functionability**: notsamePipelinelinebetweenofSynchronization, Used forDataaccordingdependScenarios. 

**ISASIInterface** (notkeepcertifystrideVersionCompatibility) :
```cpp
template <HardEvent event>
__aicore__ inline void SetFlag(int32_t eventID);

template <HardEvent event>
__aicore__ inline void WaitFlag(int32_t eventID);
```

**TQueSyncInterface** (keepcertifystrideVersionCompatibility) :
```cpp
AscendC::TQueSync<PIPE_S, PIPE_MTE3> sync;
sync.SetFlag(0);
sync.WaitFlag(0);
```

**HardEventtypetype**: `MTE2_V`, `V_MTE2`, `MTE3_V`, `V_MTE3`, `M_V`, `V_M`, `S_MTE3`etc

**Usageneedpoint**:
- SetFlag/WaitFlagmustmustbecomepairoutputappear
- eventIDneedthroughexceed`AllocEventID()`or`FetchEventID()`obtainget
- rangescope: Atlastrainpractice0-3, otherother0-7

**Examples**:
```cpp
dstLocal.SetValue(0, 0);
int32_t eventID = GetTPipePtr()->FetchEventID(AscendC::HardEvent::S_MTE3);
AscendC::SetFlag<AscendC::HardEvent::S_MTE3>(eventID);
AscendC::WaitFlag<AscendC::HardEvent::S_MTE3>(eventID);
AscendC::DataCopy(dstGlobal, dstLocal, dataSize);
```

### 1.3 singlePipelineSynchronization (PipeBarrier)

**functionability**: sameonePipelinelineInternalSynchronization, keepcertifypreviousorderfingercommandcompletedafterExecuteaftercontinuefingercommand. 

**reasontype**:
```cpp
template <pipe_t pipe>
__aicore__ inline void PipeBarrier()
```

**Examples**:
```cpp
AscendC::Add(dst0Local, src0Local, src1Local, 512);
AscendC::PipeBarrier<PIPE_V>();  // keepcertifyAddcompleted
AscendC::Mul(dst1Local, dst0Local, src2Local, 512);
```

> **Notes**: PIPE_SProhibitedadjustusePipeBarrier, ableleadissueHardwareerrorerror. 

### 1.4 DataSynchronizationscreenobstacle (DataSyncBarrier)

**functionability**: blockblockaftercontinuefingercommandstraighttoallhaveMemoryvisitaskcompleted. 

**reasontype**:
```cpp
template <MemDsbT arg0>
__aicore__ inline void DataSyncBarrier()
```

**parameternumber**: `ALL`(allhaveMemory), `DDR`(GM), `UB`, `SEQ`(prekeep)

**Examples**:
```cpp
AscendC::Mmad(...);
AscendC::DataSyncBarrier<MemDsbT::ALL>();
AscendC::Fixpipe(...);
```

---

## two, corebetweenSynchronization

### 2.1 SyncAll (allcoreSynchronization)

**functionability**: allhavecoreSynchronization, etcwaitallhavecoreExecution Complete. 

**yieldingSynchronization**:
```cpp
template <bool isAIVOnly = true>
__aicore__ inline void SyncAll(const GlobalTensor<int32_t>& gmWorkspace,
                               const LocalTensor<int32_t>& ubWorkspace,
                               const int32_t usedCores = 0);
```

**rigidSynchronization**:
```cpp
template <bool isAIVOnly = true>
__aicore__ inline void SyncAll();
```

**emptybetweenRequirements**: gmWorkspace ≥ Core count×32Bytes, ubWorkspace ≥ Core count×32Bytes

### 2.2 IBSet/IBWait (corebetweenSynchronization)

**functionability**: corebetweenSet/etcwaitSynchronizationstandardwill. 

**reasontype**:
```cpp
template <bool isAIVOnly = true>
__aicore__ inline void IBSet(const GlobalTensor<int32_t>& gmWorkspace,
                             const LocalTensor<int32_t>& ubWorkspace,
                             int32_t blockIdx, int32_t eventID);

template <bool isAIVOnly = true>
__aicore__ inline void IBWait(...);  // parameternumbersameabove
```

**emptybetweenRequirements**: gmWorkspace ≥ Core count×32×eventID_max + blockIdx_max×32 + 32

### 2.3 DeterminepropertyCalculationInterface

**InitDetermineComputeWorkspace** - InitializationtogethershareMemory:
```cpp
__aicore__ inline void InitDetermineComputeWorkspace(
    GlobalTensor<int32_t>& gmWorkspace,
    LocalTensor<int32_t>& ubWorkspace);
```

**WaitPreBlock** - etcwaitpreviousonecountcore:
```cpp
__aicore__ inline void WaitPreBlock(
    GlobalTensor<int32_t>& gmWorkspace,
    LocalTensor<int32_t>& ubWorkspace);
```

**NotifyNextBlock** - throughknowunderonecountcore:
```cpp
__aicore__ inline void NotifyNextBlock(
    GlobalTensor<int32_t>& gmWorkspace,
    LocalTensor<int32_t>& ubWorkspace);
```

### 2.4 CrossCoreSetFlag/CrossCoreWaitFlag (distributeleavemodelformula)

**functionability**: surfacedirectiondistributeleavemodelformulaofcorebetweenSynchronization. 

**reasontype**:
```cpp
template <uint8_t modeId, pipe_t pipe>
__aicore__ inline void CrossCoreSetFlag(uint16_t flagId);

template <uint8_t modeId = 0, pipe_t pipe = PIPE_S>
__aicore__ inline void CrossCoreWaitFlag(uint16_t flagId);
```

**modeId**:
- 0: AI CorecorebetweenSynchronization
- 1: AIVcoreofbetweenSynchronization
- 2: AICandAIVofbetweenSynchronization

**Examples**:
```cpp
// modelformula0: SynchronizationallhaveAIVcore
AscendC::CrossCoreSetFlag<0x0, PIPE_MTE3>(0x8);
AscendC::CrossCoreWaitFlag(0x8);
```

---

## three, EventIDManagement

### AllocEventID
applypleaseandoccupyuseEventID, needmatchmatchReleaseEventIDexplainrelease:
```cpp
AscendC::TEventID eventID = GetTPipePtr()->AllocEventID<AscendC::HardEvent::V_S>();
```

### FetchEventID
onlyobtaingetcanuseEventID, notoccupyuse:
```cpp
AscendC::TEventID eventID = GetTPipePtr()->FetchEventID(AscendC::HardEvent::V_S);
```

---

## produceproductSupportSummary

| Interface | Atlas A3 | Atlas A2 | Atlas 200I/500 A2 | Atlas pushmanage AI Core | Atlas trainpractice |
|------|----------|----------|-------------------|-------------------|------------|
| SetFlag/WaitFlag (ISASI) | √ | √ | × | √ | √ |
| TQueSync | √ | √ | √ | √ | √ |
| PipeBarrier | √ | √ | √ | √ | √ |
| DataSyncBarrier | × | √ | √ | × | × |
| SyncAll | √ | √ | × | √ | √ |
| CrossCoreSetFlag/WaitFlag | √ | √ | × | × | × |
