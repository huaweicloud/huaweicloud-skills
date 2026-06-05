# AscendC DataData Copy API Reference

## ⚠️ Production Rules

**GM ↔ UB Data Copymust use DataCopyPad**, Do Not Use DataCopy. 

| API | Suitable forScenarios | liveproduceCode |
|-----|---------|---------|
| **DataCopyPad** | GM ↔ UB (allhavesituationsituation)  | ✅ must use |
| DataCopy | UB ↔ UB Internalcopyshell | ✅ allowallow |
| DataCopy GM↔UB | onlywhen count*sizeof(T) strictformat 32B pairalign | ⚠️ onlyadjusttry/reasontype |
| GlobalTensor::SetValue/GetValue | Iterativeunitelement GM visitask | ❌ Prohibited (extremelowvalid)  |

## DataCopyPad (pushrecommend) 

### GM → UB

```cpp
AscendC::DataCopyExtParams copyParams{blockCount, blockLen, srcStride, dstStride, 0};
AscendC::DataCopyPadExtParams<T> padParams{isPad, leftPad, rightPad, padValue};
AscendC::DataCopyPad(dstLocal, srcGlobal, copyParams, padParams);
```

### UB → GM

```cpp
AscendC::DataCopyExtParams copyParams{blockCount, blockLen, srcStride, dstStride, 0};
AscendC::DataCopyPad(dstGlobal, srcLocal, copyParams);
```

### DataCopyExtParams parameternumber

| parameternumber | containmeaning | singlebit | rangescope |
|------|------|------|------|
| blockCount | Datablockcountnumber (throughoften=travelnumber)  | - | [1, 4095] |
| blockLen | eachblocklengthdegree | **charactersection** | - |
| srcStride | sourcemutualneighborblockbetweenseparate | **GM=charactersection, UB=32Bblock** | - |
| dstStride | itemofmutualneighborblockbetweenseparate | **GM=charactersection, UB=32Bblock** | - |

**⚠️ Stride singlebitnotsame**: GM sideusecharactersection, UB sideuse 32B DataBlock. thisismostoftenseeofData Copy bug Source. 

### DataCopyPadExtParams parameternumber (only GM→UB) 

| parameternumber | containmeaning |
|------|------|
| isPad | iswhetherfillfillCustomvalue |
| leftPadding | leftsidefillfillunitelementcountnumber (≤32charactersection)  |
| rightPadding | rightsidefillfillunitelementcountnumber (≤32charactersection)  |
| padValue | fillfillvalue |

### rLength vs rLengthAlign usemethod

| parameternumber | Usage rLength (havevalidlengthdegree)  | Usage rLengthAlign (pairalignlengthdegree)  |
|------|------------------------|----------------------------|
| blockLen (CopyIn) | `rLength * sizeof(T)` | - |
| blockLen (CopyOut) | `rLength * sizeof(T)` | - |
| srcStride (CopyIn, GMside) | - | `rLengthAlign * sizeof(T)` |
| dstStride (CopyIn, UBside) | - | `rLengthAlign * sizeof(T) / 32` |
| srcStride (CopyOut, UBside) | - | `(rLengthAlign - rLength) * sizeof(T) / 32` |
| dstStride (CopyOut, GMside) | - | `rLengthAlign * sizeof(T)` |
| Calculation API count | `rLength` | - |
| UB travelpartialmove | - | `rowIdx * rLengthAlign` |
| InitBuffer largesmall | - | `rLengthAlign * sizeof(T)` |

**relatedkey**: CopyOut of `srcStride` isblockbetween**betweenseparate** (padding partdistribute) , notiscompleteadjusttravellengthdegree. 

### CopyIn/CopyOut oneconsistentproperty

CopyIn use DataCopyPad time, CopyOut alsomustmustuse DataCopyPad. mixuseableguideconsistenttravelerrorbit. 

## BaseDataData Copy (DataCopy)

onlyUsed for UB ↔ UB Internalcopyshell. 

```cpp
// UB -> UB
AscendC::DataCopy(dstLocal, srcLocal, count);
```

**parameternumber**: 
- `count`: unitelementcountnumber, `count * sizeof(T)` need32charactersectionpairalign

### nonconnectcontinueData Copy (DataCopyParams)

```cpp
AscendC::DataCopyParams params;
params.blockCount = 1;   // connectcontinueDatablockcountnumber [1, 4095]
params.blockLen = 8;     // eachblocklengthdegree, singlebitDataBlock(32B) [1, 65535]
params.srcGap = 0;       // sourcemutualneighborblockbetweenseparate, singlebitDataBlock(32B)
params.dstGap = 0;       // itemofmutualneighborblockbetweenseparate, singlebitDataBlock(32B)

AscendC::DataCopy(dstLocal, srcGlobal, params);
```

**showmeaningfigure**: 
```
blockCount=2, blockLen=8, srcGap=0, dstGap=1
source: [====8block====][====8block====]
itemof: [====8block====][gap][====8block====]
```

## cutsliceDataData Copy (SliceInfo)

```cpp
AscendC::SliceInfo srcSliceInfo[] = {{16, 70, 7, 3, 87}, {0, 2, 1, 1, 3}};
AscendC::SliceInfo dstSliceInfo[] = {{0, 47, 0, 3, 48}, {0, 1, 0, 1, 2}};
uint32_t dimValue = 2;

AscendC::DataCopy(dstLocal, srcGlobal, dstSliceInfo, srcSliceInfo, dimValue);
```

**SliceInfo Structure**: 
| parameternumber | containmeaning |
|------|------|
| startIndex | cutslicerisebeginbitplace |
| endIndex | cutslicefinalstopbitplace |
| stride | mutualneighborcutslicebetweenseparate (unitelementcountnumber)  |
| burstLen | eachsliceDatalengthdegree, singlebitDataBlock(32B), dimValue>1timemustmustas1 |
| shapeValue | whenpreviousdimensiondegreereasonbeginlengthdegree |

## nonpairalignData Copy (DataCopyPad)

```cpp
// GM -> UB, Supportnon32charactersectionpairalign
AscendC::DataCopyExtParams copyParams{1, 20 * sizeof(half), 0, 0, 0};
AscendC::DataCopyPadExtParams<half> padParams{true, 0, 2, 0};  // isPad, leftPad, rightPad, padValue
AscendC::DataCopyPad(dstLocal, srcGlobal, copyParams, padParams);

// UB -> GM
AscendC::DataCopyPad(dstGlobal, srcLocal, copyParams);
```

**DataCopyExtParams**: 
| parameternumber | containmeaning | singlebit |
|------|------|------|
| blockCount | connectcontinueDatablockcountnumber | - |
| blockLen | eachblocklengthdegree | **charactersection** |
| srcStride | sourcemutualneighborblockbetweenseparate | GM:charactersection, UB:DataBlock |
| dstStride | itemofmutualneighborblockbetweenseparate | GM:charactersection, UB:DataBlock |

**DataCopyPadExtParams**: 
| parameternumber | containmeaning |
|------|------|
| isPad | iswhetherfillfillCustomvalue |
| leftPadding | leftsidefillfillunitelementcountnumber (≤32charactersection)  |
| rightPadding | rightsidefillfillunitelementcountnumber (≤32charactersection)  |
| padValue | fillfillvalue |

## UBInternalcopyshell (Copy)

```cpp
// VECIN/VECCALC/VECOUT ofbetweenofcopyshell
AscendC::Copy(dstLocal, srcLocal, mask, repeatTime, {dstStride, srcStride, dstRepStride, srcRepStride});
```

**CopyRepeatParams**: 
| parameternumber | containmeaning |
|------|------|
| dstStride/srcStride | sameoneiteraterepresentinsideDataBlocksteplength |
| dstRepeatSize/srcRepeatSize | mutualneighboriteraterepresentbetweensteplength |

```cpp
// Examples: connectcontinuecopyshell512countint16_t
uint64_t mask = 128;
AscendC::Copy(dstLocal, srcLocal, mask, 4, {1, 1, 8, 8});
```

## increasestrongDataData Copy (DataCopyEnhancedParams)

```cpp
AscendC::DataCopyParams intriParams;
AscendC::DataCopyEnhancedParams enhancedParams;
enhancedParams.blockMode = BlockMode::BLOCK_MODE_MATRIX;  // or BLOCK_MODE_VECTOR
AscendC::DataCopy(dstLocal, srcLocal, intriParams, enhancedParams);
```

**blockMode modelformula**: 
| modelformula | transferoutputsinglebit | Suitable forthroughpath |
|------|----------|----------|
| BLOCK_MODE_MATRIX | 16×16 cube | CO1 -> CO2 |
| BLOCK_MODE_VECTOR | 1×16 cube | CO1 -> CO2 |
| BLOCK_MODE_NORMAL | 32B | throughusethroughpath |

**Quantizationmodelformula (deqScale)**: 
| modelformula | Description |
|------|------|
| DEQ | int32 -> half, UsagedeqValue |
| DEQ8 | int32 -> int8/uint8 |
| DEQ16 | int32 -> half/int16 |
| VDEQ/VDEQ8/VDEQ16 | UsagedeqTensorAddrparameternumberdirectionamount |

## Datathroughpathspeedsearch

| throughpath | source | itemof | Description |
|------|----|----|------|
| GM -> UB | GlobalTensor | LocalTensor(VECIN) | CopyInPhase |
| UB -> GM | LocalTensor(VECOUT) | GlobalTensor | CopyOutPhase |
| UB -> UB | LocalTensor | LocalTensor | ComputePhase |
| UB -> L1 | LocalTensor | LocalTensor(A1/B1/TSCM) | largeDataslowkeep |
| CO1 -> CO2 | LocalTensor(CO1) | LocalTensor(CO2) | rulematrixCalculationResult |

## regionaddresspairalignRequirements

| bitplace | pairalignRequirements |
|------|----------|
| UB (VECIN/VECOUT) | 32charactersection |
| L1 Buffer | 32charactersection |
| GM | according toDatatypetypelargesmallpairalign |
| C2 | 64charactersection |
| C2PIPE2GM | 128charactersection |

## CommonCodemodelformula

### CopyIn (multipletravelbatchamounttransferinput) 

```cpp
__aicore__ inline void CopyIn(uint32_t startRow, uint32_t rows) {
    LocalTensor<half> srcLocal = inQueue.AllocTensor<half>();
    // blockCount=travelnumber, blockLen=eachtravelhavevalidcharactersection, srcStride=GMtravelbetweendistance(charactersection), dstStride=UBtravelbetweendistance(32Bblock)
    AscendC::DataCopyExtParams copyParams{
        static_cast<uint16_t>(rows),                          // blockCount
        static_cast<uint32_t>(cols * sizeof(half)),           // blockLen (havevalidData)
        static_cast<uint32_t>(totalCols * sizeof(half)),      // srcStride (GM, charactersection)
        static_cast<uint16_t>(alignedCols * sizeof(half) / 32) // dstStride (UB, 32Bblock)
    };
    AscendC::DataCopyPadExtParams<half> padParams{true, 0,
        static_cast<uint8_t>(alignedCols - cols), 0};
    AscendC::DataCopyPad(srcLocal, srcGlobal[startRow * totalCols], copyParams, padParams);
    inQueue.EnQue(srcLocal);
}
```

### CopyOut (multipletravelbatchamounttransferoutput) 

```cpp
__aicore__ inline void CopyOut(uint32_t startRow, uint32_t rows) {
    LocalTensor<half> dstLocal = outQueue.DeQue<half>();
    AscendC::DataCopyExtParams copyParams{
        static_cast<uint16_t>(rows),
        static_cast<uint32_t>(cols * sizeof(half)),            // onlytransferoutputhavevalidData
        static_cast<uint16_t>((alignedCols - cols) * sizeof(half) / 32), // srcStride: padding betweenseparate
        static_cast<uint32_t>(totalCols * sizeof(half))        // dstStride (GM, charactersection)
    };
    AscendC::DataCopyPad(dstGlobal[startRow * totalCols], dstLocal, copyParams);
    outQueue.FreeTensor(dstLocal);
}
```

### Elementwise connectcontinueData Copy

```cpp
__aicore__ inline void CopyIn() {
    LocalTensor<half> srcLocal = inQueue.AllocTensor<half>();
    AscendC::DataCopyExtParams copyParams{1, static_cast<uint32_t>(tileLength * sizeof(half)), 0, 0, 0};
    AscendC::DataCopyPad(srcLocal, srcGlobal[offset], copyParams);
    inQueue.EnQue(srcLocal);
}
```

## regionaddresspairalignRequirements

| bitplace | pairalignRequirements |
|------|----------|
| UB (VECIN/VECOUT) | 32charactersection |
| L1 Buffer | 32charactersection |
| GM | according toDatatypetypelargesmallpairalign |

## 32 charactersectionpairalignCalculation

```cpp
// according to 32B pairalignofunitelementnumber
uint32_t alignedCols = ((cols * sizeof(T) + 31) / 32) * (32 / sizeof(T));

// etcvalueFormula
uint32_t elemsPerBlock = 32 / sizeof(T);  // half:16, float:8
uint32_t alignedCols = ((cols + elemsPerBlock - 1) / elemsPerBlock) * elemsPerBlock;
```
