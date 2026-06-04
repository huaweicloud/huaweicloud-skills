# Phase 6: Scalar — DetailedReference

#### 6.1 Vector transformOptimization (Eliminate Scalar Loop) 

**Problem Pattern**: Usage `for` loopringIterativeunitelementoperatework (if one-hot compilecodeofloopringassignvalue) 

**oftenseeOptimizationMethod**: 
- use `Duplicate` + Single `SetValue` substituterepresentloopringassignvalue
- use `Exp`, `Log`, `Mul`, `Muls` etcdirectionQuantization API substituterepresentIterativeunitelementoperatework

**Examples** (one-hot compilecodeOptimization) : 

**reverseexample** — for loopring, eachtimethroughexceedSetValueperformstandardamountsubstituteexchangeoperatework: : 
```cpp
for (size_t classIdx = 0; classIdx < numClass_; ++classIdx) {
    int64_t weight = 0;
    if (labelIdx == classIdx) {
        weight = 1;
    }
    labelOneHotLocal_.SetValue(classIdx, weight);
}
```

**positiveexample** — UsageDuplicatebatchamountsubstituteexchange: 
```cpp
Duplicate(labelOneHotLocal_, float(0.0), numClass_);
// Synchronizationkeepcertify Duplicate completedafteragain SetValue
PipeBarrier<PIPE_V>();
TEventID eventIdVToS = GetTPipePtr()->FetchEventID(HardEvent::V_S);
SetFlag<HardEvent::V_S>(eventIdVToS);
WaitFlag<HardEvent::V_S>(eventIdVToS);
labelOneHotLocal_.SetValue(labelIdx, float(1.0));
```

**Optimizationreasonmanage**: 
- `Duplicate` isoneitemdirectionQuantizationfingercommand, HardwareParallelfillfillWhole tensor, compareloopringIterativecount `SetValue` rapidnumbertentimes
- loopringmethodsundereachcount iteration allhavestandardamountjudgejudgeandstandardamountassignvalueopenconsume, Scalar fingercommandoccupycompareextremehigh
- Optimizationafteronlyneed 1 item Vector fingercommand + 1 itemstandardamountassignvalue, largerangedowngradelow Scalar occupycompare



#### 6.2 Vector transformOptimization (Eliminate Scalar Loop) 

Usage `DataCopyParams` (blockCount / blockLen / srcStride / dstStride) willbetweenseparate
Data CopyDescriptionasoneitem DMA fingercommandunderissue, andnonuse for loopringIterativetraveladjustuse `DataCopy`. 

**reverseexample** — for loopring, eachtimeonlyData Copy 2 KB: 

```cpp
constexpr int32_t copyWidth = 2 * 1024 / sizeof(float);
constexpr int32_t imgWidth  = 16 * 1024 / sizeof(float);
constexpr int32_t imgHeight = 16;
// 16 timealoneestablishof 2KB Data Copy, Bandwidth Utilizationextremelow
for (int i = 0; i < imgHeight; i++) {
    DataCopy(tensorIn[i * copyWidth], tensorGM[i * imgWidth], copyWidth);
}
```

**positiveexample** — singleitem DMA Descriptioncharacter, onetimeData Copy 32 KB: 

```cpp
constexpr int32_t copyWidth = 2 * 1024 / sizeof(float);
constexpr int32_t imgWidth  = 16 * 1024 / sizeof(float);
constexpr int32_t imgHeight = 16;
DataCopyParams copyParams;
copyParams.blockCount = imgHeight;                     // 16 travel
copyParams.blockLen   = copyWidth / 8;                 // singlebit: 32B DataBlock
copyParams.srcStride  = (imgWidth - copyWidth) / 8;    // src travelbetweenbetweenseparate
copyParams.dstStride  = 0;                             // dst connectcontinuecomposeinput
DataCopy(tensorGM, tensorIn, copyParams);
```
**Optimizationreasonmanage**: 
- stride methodsunderissueoneitem DMA fingercommand, HardwareselfmaincompletedallpartData Copy, canfilldistributeutilizeusebandwidthwidth. 
- for loopringmethodsunderissue 16 itemsmall DMA fingercommand, eachitemofbetweenalsohave Scalar openconsume. 