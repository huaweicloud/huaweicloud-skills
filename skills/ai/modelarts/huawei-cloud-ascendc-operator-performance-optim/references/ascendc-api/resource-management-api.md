# AscendC ResourceManagementInterfaceSummary

## one, TPipe

**Purpose**: statisticsoneManagementDeviceSideMemory andSynchronizationmatterfileResource, onecountKernelmustmustandonlyabilityhaveonecountTPipepairimage. 

### Corefunctionability

1. **MemoryResourceManagement**: throughexceedInitBufferasTQueandTBufdistributematchMemory
2. **SynchronizationmatterfileManagement**: throughexceedAllocEventID/ReleaseEventIDManagementmatterfileID

### relatedkeyInterface

| Interface | functionability |
|------|------|
| `InitBuffer(que, num, len)` | asTQuedistributematchMemory (numblock, eachblocklencharactersection)  |
| `InitBuffer(buf, len)` | asTBufdistributematchMemory (lencharactersection)  |
| `AllocEventID<HardEvent>()` | applypleaseEventID (occupyusetype)  |
| `FetchEventID(HardEvent)` | obtaingetEventID (nonoccupyusetype)  |
| `ReleaseEventID<HardEvent>(id)` | explainreleaseEventID |
| `Reset()` | weightplaceResource |
| `GetBaseAddr()` | obtaingetbaseregionaddress |

### Examples

```cpp
AscendC::TPipe pipe;

// asTQuedistributematchMemory
AscendC::TQue<AscendC::TPosition::VECIN, 1> inQueue;
pipe.InitBuffer(inQueue, 2, 1024);  // 2block, eachblock1024charactersection

// asTBufdistributematchMemory
AscendC::TBuf<AscendC::TPosition::VECCALC> tmpBuf;
pipe.InitBuffer(tmpBuf, 512);  // 512charactersection

// EventIDManagement
AscendC::TEventID eventId = GetTPipePtr()->AllocEventID<AscendC::HardEvent::V_S>();
// ... UsageEventID ...
GetTPipePtr()->ReleaseEventID<AscendC::HardEvent::V_S>(eventId);
```

---

## two, TQue

**Purpose**: Managementteamcolumnoperatework, ImplementationPipelinelineParallel. 

### Templateparameternumber

```cpp
template <TPosition pos, int32_t depth, auto mask = 0>
class TQue {...};
```

| parameternumber | Description |
|------|------|
| pos | Logical Location (VECIN/VECOUT/A1/A2/B1/B2/CO1/CO2)  |
| depth | teamcolumnDeep Dive (pushrecommendsetas1, Tensorreasonregionoperateworksetas0)  |
| mask | canselectConfiguration (ND↔NZconvertexchangeetc)  |

### CoreInterface

| Interface | functionability |
|------|------|
| `AllocTensor<T>()` | distributematchTensor |
| `AllocTensor<T>(tensor)` | inplacemethodsdistributematch |
| `EnQue(tensor)` | Tensorinputteam |
| `DeQue<T>()` | Tensoroutputteam |
| `DeQue<T>(tensor)` | inplacemethodsoutputteam |
| `FreeTensor(tensor)` | explainreleaseTensor |
| `HasTensorInQue()` | teamcolumniswhetherhaveData |
| `HasIdleBuffer()` | iswhetherhaveemptyidleBuffer |
| `GetTensorCountInQue()` | obtaingetteamcolumnmiddleTensornumberamount |

### BuffernumberamountLimitations

| produceproduct | EventIDnumberamount | mostlargeBuffernumber |
|------|-------------|--------------|
| Atlas trainpractice | 4 | 4 |
| Atlas pushmanage AI Core | 8 | 8 |
| Atlas A2/A3 | 8 | 8 |
| Atlas 200I/500 A2 | 8 | 8 |

### standardstandardPipelinelinemodelformula

```cpp
// CopyIn -> Compute -> CopyOut
AscendC::LocalTensor<half> srcLocal = inQueue.AllocTensor<half>();
AscendC::DataCopy(srcLocal, srcGlobal, dataSize);
inQueue.EnQue(srcLocal);

srcLocal = inQueue.DeQue<half>();
// ... Calculationoperatework ...
inQueue.FreeTensor(srcLocal);
```

### Double Buffer modelformula

Double Buffer ofitemofis**let DMA Data Copy (MTE2/MTE3) and Vector CalculationParallelExecute**, andnonsimplesingleof"twoblockMemorydoCalculation". 

```cpp
// MTE throughpathteamcolumn: depth=1, num=2 (double buffer)
AscendC::TQue<AscendC::TPosition::VECIN, 1> inQueue;
AscendC::TQue<AscendC::TPosition::VECOUT, 1> outQueue;
pipe.InitBuffer(inQueue, 2, len);   // 2block: oneblockinData Copy, oneblockinCalculation
pipe.InitBuffer(outQueue, 2, len);

// pureCalculationapproachtimeslowconflictregion: noneed double buffer
AscendC::TBuf<AscendC::TPosition::VECCALC> tmpBuf;
pipe.InitBuffer(tmpBuf, len);       // 1blockimmediatecan
```

**whattimeuse TQue vs TBuf**:

| Scenarios | use TQue (VECIN/VECOUT) | use TBuf (VECCALC) |
|------|------------------------|-------------------|
| GM↔UB Data Copy | ✅ depth=1, num=2 | - |
| pureCalculationmiddlebetweenchangeamount | - | ✅ depth=1 |
| returnapproximately tmpBuffer | - | ✅ |
| upgradeprecisiondegree FP32 workspace | - | ✅ |

---

## three, TBuf

**Purpose**: ManagementapproachtimechangeamountMemory, notSupportinputteamoutputteamoperatework. 

### specialpoint

- onlyabilityparticipationCalculation, nomethodExecuteteamcolumnoperatework
- TPipeonlyasTBufdistributematchoneblockMemory
- obtaingetofTensornoneedexplainrelease
- multiplecountapproachtimechangeamountrequiresdefinemeaningmultiplecountTBuf

### Interface

| Interface | functionability |
|------|------|
| `Get<T>()` | obtaingetfingerdefinetypetypeofTensor |
| `GetWithOffset<T>(offset)` | obtaingetbandwidthpartialmoveofTensor |

### Examples

```cpp
AscendC::TPipe pipe;
AscendC::TBuf<AscendC::TPosition::VECCALC> tmpBuf;
pipe.InitBuffer(tmpBuf, 512);

// obtaingetTensorUsage
AscendC::LocalTensor<float> tmp = tmpBuf.Get<float>();
// UsagetmpperformCalculation, noneedexplainrelease
```

---

## four, TQueBind

**Purpose**: binddefineVECINandVECOUTImplementationMemorycomplexuse. 

### Templateparameternumber

```cpp
template <TPosition srcPos, TPosition dstPos, int32_t depth>
class TQueBind {...};
```

### UsageScenarios

Used forkeepinVectorCalculationtimeImplementationVECINandVECOUTMemorycomplexuse. 

### Examples

```cpp
AscendC::TQueBind<AscendC::TPosition::VECIN, AscendC::TPosition::VECOUT, 1> que;
pipe.InitBuffer(que, 2, 1024);

AscendC::LocalTensor<half> tensor = que.AllocTensor<half>();
que.EnQue<AscendC::TPosition::GM, AscendC::TPosition::VECIN, half>(tensor);
tensor = que.DeQue<AscendC::TPosition::GM, AscendC::TPosition::VECIN, half>();
```

---

## five, WorkspaceManagement

### GetUserWorkspace

obtaingetuseuserUsageofworkspacefingerneedle: 

```cpp
__aicore__ inline GM_ADDR GetUserWorkspace(GM_ADDR workspace);
```

```cpp
GM_ADDR usrWorkspace = AscendC::GetUserWorkspace(workspace);
```

### GetSysWorkSpacePtr

obtaingetsystemstatisticsworkspacefingerneedle (Used forMatmuletchighlevelAPI) : 

```cpp
__aicore__ inline __gm__ uint8_t* GetSysWorkSpacePtr();
```

```cpp
REGIST_MATMUL_OBJ(&pipe, GetSysWorkSpacePtr(), mm, &tiling);
```

### SetSysWorkSpace

Setsystemstatisticsworkspace (KernelstraightadjustScenarios) : 

```cpp
__aicore__ inline void SetSysWorkspace(GM_ADDR workspace);
```

```cpp
AscendC::SetSysWorkspace(workspace);
if (GetSysWorkSpacePtr() == nullptr) {
    return;
}
```

### HostsideConfiguration

```cpp
// Tilingfunctionnumbermiddle
size_t usrSize = 256;
auto ascendcPlatform = platform_ascendc::PlatformAscendC(context->GetPlatformInfo());
uint32_t sysWorkspaceSize = ascendcPlatform.GetLibApiWorkSpaceSize();
size_t *currentWorkspace = context->GetWorkspaceSizes(1);
currentWorkspace[0] = usrSize + sysWorkspaceSize;
```

---

## six, MemoryManagementConstraints

### InitBuffer Constraints

- applypleaseofMemoryablein TPipe analyzestructuretimeAutomaticexplainrelease
- onecount kernel middleallhave Buffer numberamountofandnotabilityexceedexceed 64
- CustomregionaddressmethodsandnotfingerdefineregionaddressmethodsnotSuggestmixuse
- len notfullfoot 32 charactersectionpairaligntimeableAutomaticsupplementalign

### UB contentamountandtravelnumberCalculation

Host Sidethroughexceedaverageplatform API obtainget UB largesmallafter, Calculationeachtimehandlemanageoftravelnumber:

```cpp
// Host side
uint64_t ubSize;
ascendc_platform->GetCoreMemSize(platform_ascendc::CoreMemType::UB, ubSize);

// eachtraveloccupyuse UB charactersection = alignedCols * sizeof(T)
// considerconsidermultiplecount buffer (if inQueue×2 + outQueue×2 + tmpBuf×1 + calcBuf×1 = 6portion) 
uint32_t tileRows = ubSize / (alignedCols * sizeof(T) * bufferCount);
```

### DataCopyPad blockCount Limitations

`DataCopyExtParams.blockCount` mostlargevalueas **4095**. when `tileRows > 4095` timerequiresdistributebatch:
```cpp
tileRows = std::min(tileRows, (uint32_t)4095);
```

### AllocTensorConstraints

sameoneTPositionaboveconnectcontinueAllocofTensornumberamountLimitations: 

| produceproduct | mostlargenumberamount |
|------|----------|
| Atlas trainpractice | 4 |
| Atlas pushmanage AI Core | 8 |
| Atlas A2/A3 | 8 |

### solveresolveBuffernotfoot

```cpp
// Method1: Mergemultiplecountbuffertooneblock, throughexceedpartialmoveUsage
pipe.InitBuffer(que0, 1, len * 3);
AscendC::LocalTensor<T> local1 = que0.AllocTensor<T>();
AscendC::LocalTensor<T> local2 = local1[len];
AscendC::LocalTensor<T> local3 = local1[len * 2];

// Method2: explainreleasenotuseofTQue
que0.FreeAllEvent();
```

---

## seven, classictypeUsagemodelformula

### VectorOperatorstandardstandardmodelformula

```cpp
class KernelOp {
public:
    __aicore__ inline void Init(GM_ADDR x, GM_ADDR y, uint32_t size) {
        xGlobal.SetGlobalBuffer((__gm__ half*)x, size);
        yGlobal.SetGlobalBuffer((__gm__ half*)y, size);
        pipe.InitBuffer(inQueue, 1, size * sizeof(half));
        pipe.InitBuffer(outQueue, 1, size * sizeof(half));
    }

    __aicore__ inline void Process() {
        CopyIn();
        Compute();
        CopyOut();
    }

private:
    __aicore__ inline void CopyIn() {
        AscendC::LocalTensor<half> xLocal = inQueue.AllocTensor<half>();
        AscendC::DataCopy(xLocal, xGlobal, dataSize);
        inQueue.EnQue(xLocal);
    }

    __aicore__ inline void Compute() {
        AscendC::LocalTensor<half> xLocal = inQueue.DeQue<half>();
        AscendC::LocalTensor<half> yLocal = outQueue.AllocTensor<half>();
        AscendC::Add(yLocal, xLocal, xLocal, dataSize);
        outQueue.EnQue<half>(yLocal);
        inQueue.FreeTensor(xLocal);
    }

    __aicore__ inline void CopyOut() {
        AscendC::LocalTensor<half> yLocal = outQueue.DeQue<half>();
        AscendC::DataCopy(yGlobal, yLocal, dataSize);
        outQueue.FreeTensor(yLocal);
    }

private:
    AscendC::TPipe pipe;
    AscendC::TQue<AscendC::TPosition::VECIN, 1> inQueue;
    AscendC::TQue<AscendC::TPosition::VECOUT, 1> outQueue;
    AscendC::GlobalTensor<half> xGlobal, yGlobal;
    uint32_t dataSize;
};
```
