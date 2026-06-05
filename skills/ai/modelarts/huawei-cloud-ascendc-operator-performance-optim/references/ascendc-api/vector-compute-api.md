# AscendC VectorCalculation API Reference

## API Calling Pattern

VectorCalculation API Provides Threeadjustusemethods: 

### 1. Whole Tensor participationCalculation (runcomputecharacterweightload) 
```cpp
dstLocal = src0Local + src1Local;  // Add
dstLocal = src0Local < src1Local;  // Compare
```

### 2. Tensor previous n countDataCalculation
```cpp
AscendC::Add(dstLocal, src0Local, src1Local, count);
```

### 3. Tensor highdimensionTilingCalculation
```cpp
// connectcontinuemodelformula
AscendC::Add(dstLocal, src0Local, src1Local, mask, repeatTime, repeatParams);
// Iterativebitmodelformula
AscendC::Add(dstLocal, src0Local, src1Local, maskArray, repeatTime, repeatParams);
```

## mask parameternumber

ControleachtimeiteraterepresentparticipationCalculationofunitelement: 

| modelformula | Description | getvaluerangescope |
|------|------|----------|
| connectcontinuemodelformula | previoussurfaceconnectcontinuemultiplefewcountunitelement | 16bit:[1,128], 32bit:[1,64], 64bit:[1,32] |
| Iterativebitmodelformula | according tobitControl | 16bit:mask[2], 32bit:mask[1] |

```cpp
// connectcontinuemodelformula
uint64_t mask = 128;  // handlemanageprevious128countunitelement

// Iterativebitmodelformula
uint64_t mask[2] = {UINT64_MAX, UINT64_MAX};  // handlemanageallpart128countunitelement
```

## repeatParams parameternumber

### BinaryRepeatParams (doublesourceoperateworknumber) 
```cpp
AscendC::BinaryRepeatParams {dstBlkStride, src0BlkStride, src1BlkStride,
                              dstRepStride, src0RepStride, src1RepStride};
```

### UnaryRepeatParams (singlesourceoperateworknumber) 
```cpp
AscendC::UnaryRepeatParams {dstBlkStride, srcBlkStride, dstRepStride, srcRepStride};
```

**CommonConfiguration**: connectcontinueDatahandlemanage
- half: `{1, 1, 1, 8, 8, 8}`
- float: `{1, 1, 8, 8}` (UnaryRepeatParams)

## Basecomputeart API

### twounitruncompute
```cpp
// Add, Sub, Mul, Div, Max, Min
AscendC::Add(dstLocal, src0Local, src1Local, count);
AscendC::Mul(dstLocal, src0Local, src1Local, mask, repeatTime, {1, 1, 1, 8, 8, 8});

// runcomputecharacterweightload
dstLocal = src0Local + src1Local;
```

**Supporttypetype**: half, int16_t, int32_t, float

### oneunitruncompute
```cpp
// Abs, Exp, Ln, Sqrt, Rsqrt, Reciprocal, Relu, LeakyRelu, Tanh
AscendC::Exp(dstLocal, srcLocal, count);
```

### standardamountruncompute (optimizefirstUsage) 
```cpp
// Adds, Muls, Maxs, Mins — straightconnectpaireachcountunitelementdostandardamountoperatework
AscendC::Adds(dstLocal, srcLocal, scalarValue, count);
AscendC::Muls(dstLocal, srcLocal, scalarValue, count);
```

**standardamountOptimization**: travelreturnapproximatelyafterrequirespaireachtraveldecreaseremove/dividein order toonecountstandardamountvaluetime, **optimizefirstuse Adds/Muls**:

| needrequest | pushrecommend | notpushrecommend |
|------|------|--------|
| `x - scalar` | `Adds(dst, src, -scalar, len)` | Duplicate(tmp, scalar) + Sub |
| `x / scalar` | `Muls(dst, src, 1.0f/scalar, len)` | Duplicate(tmp, scalar) + Div |
| `x * scalar` | `Muls(dst, src, scalar, len)` | Duplicate(tmp, scalar) + Mul |

### multipletravelwidebroadcast (BinaryRepeatParams) 

pairmultipletravelDatadosameonecountdirectionamountofruncompute (ifeachtraveldecreaseremove max directionamount) :

```cpp
// src1RepStride=0 use src1 ineachtime repeat timenotpreviousenter, Implementationwidebroadcast
uint64_t mask = alignedCols / (32 / sizeof(float));  // each repeat handlemanageofunitelementnumber
uint32_t repeatTime = rowCount;
AscendC::Sub(dst, src0, src1, mask, repeatTime,
             {1, 1, 1,                                    // blkStride
              alignedCols / 8, alignedCols / 8, 0});      // repStride: src1=0 widebroadcast
```

**⚠️ repeatTime Limitations**: repeatTime parameternumbertypetypeas `uint8_t`, mostlargevalue 255. exceedexceedneeddistributebatchhandlemanage:
```cpp
while (remaining > 0) {
    uint8_t batch = static_cast<uint8_t>(std::min(remaining, (int64_t)255));
    AscendC::Sub(dst[offset], src0[offset], src1, mask, batch, params);
    offset += batch * alignedCols;
    remaining -= batch;
}
```

## typetypeconvertexchange API (Cast)

```cpp
AscendC::Cast(dstLocal, srcLocal, AscendC::RoundMode::CAST_RINT, count);
```

### RoundMode give upinputmodelformula
| modelformula | Description |
|------|------|
| CAST_NONE | notgive upinput (noprecisiondegreedetrimentallosstime)  |
| CAST_RINT | fourgive upsixinputfivebecomedouble |
| CAST_FLOOR | directionnegativenopoorgive upinput |
| CAST_CEIL | directionpositivenopoorgive upinput |
| CAST_ROUND | fourgive upfiveinput |
| CAST_TRUNC | directionzerogive upinput |
| CAST_ODD | mostnearneighborstrangenumbergive upinput |

### Commonconvertexchangegroupmatch
| sourcetypetype | itemoftypetype | pushrecommend RoundMode | Scenarios |
|--------|----------|----------------|------|
| half → float | CAST_NONE | upgradeprecisiondegree (nodetrimental)  |
| bfloat16 → float | CAST_NONE | upgradeprecisiondegree (nodetrimental)  |
| float → half | CAST_ROUND | downgradeprecisiondegree (throughuse)  |
| float → bfloat16 | CAST_ROUND | downgradeprecisiondegree (throughuse)  |
| float → int32_t | CAST_RINT / CAST_ROUND | Quantization |
| int32_t → float | CAST_NONE | reverseQuantization (nodetrimental)  |
| int8_t → half | CAST_NONE | Quantizationoutputinput |
| half → int8_t | CAST_RINT | QuantizationOutput |

### mixmatchprecisiondegreemodelformula (FP16/BF16 upgradeprecisiondegreeCalculation) 

returnapproximately/returnonetransformtypeOperator (Softmax, LayerNorm etc) requires FP32 middlebetweenprecisiondegreekeepcertifynumbervaluestabledefineproperty:

```cpp
// Init Phase: amountexternaldistributematch FP32 workworkslowconflictregion
pipe.InitBuffer(calcBuf, alignedCols * sizeof(float));  // FP32 Calculationemptybetween

// Compute Phase: Iterativetravel Cast → FP32 Calculation → Cast return
LocalTensor<half> inLocal = inQueue.DeQue<half>();
LocalTensor<float> workLocal = calcBuf.Get<float>();
AscendC::Cast(workLocal, inLocal[rowIdx * alignedCols], RoundMode::CAST_NONE, rLength);
// ... FP32 returnapproximately/Calculation ...
AscendC::Cast(outLocal[rowIdx * alignedCols], workLocal, RoundMode::CAST_ROUND, rLength);
```

### highdimensionTilingExamples
```cpp
// half -> int32_t
uint64_t mask = 64;  // in order toint32_tasstandard
AscendC::Cast(dstLocal, srcLocal, AscendC::RoundMode::CAST_CEIL, mask, 8, {1, 1, 8, 4});
```

## returnapproximatelyCalculation API

### Level 2 returnapproximately (singletravel/anymeaninglengthdegree) 

```cpp
// ReduceSum / ReduceMax / ReduceMin
// tmpBuffer typetypemustmustand T mutualsame, notabilityis uint8_t
AscendC::ReduceSum(dstLocal, srcLocal, sharedTmpBuffer, count);
AscendC::ReduceMax(dstLocal, srcLocal, sharedTmpBuffer, count);
```

- `count` = **havevalidunitelementnumber** (rLength) , notispairalignafteroflengthdegree
- `tmpBuffer` typetypemustmustis `LocalTensor<T>` (andsourcemutualsametypetype) 
- `dst` **notability**and `tmpBuffer` fingerdirectionsameoneblockMemory

### tmpBuffer largesmallCalculation
```cpp
int elementsPerBlock = 32 / sizeof(T);      // half:16, float:8
int elementsPerRepeat = 256 / sizeof(T);    // half:128, float:64
int firstMaxRepeat = (count + elementsPerRepeat - 1) / elementsPerRepeat;
int tmpBufferSize = ((firstMaxRepeat + elementsPerBlock - 1) / elementsPerBlock) * elementsPerBlock;
// distributematch: pipe.InitBuffer(tmpBuf, tmpBufferSize * sizeof(T));
```

### Pattern returnapproximately (batchamountmultipletravel 2D) 

pairalignDataofbatchamounttravelreturnapproximately, Performanceupdateoptimize:

```cpp
// Pattern::Reduce::AR — returnapproximatelymostafteronedimension (eachtravelreturnapproximatelyasonecountstandardamount) 
// srcShape = {rows, alignedCols}, alignedCols mustmust 32B pairalign
AscendC::ReduceMax(dstLocal, srcLocal, sharedTmpBuffer,
                   srcShape, AscendC::Pattern::Reduce::AR, srcInnerPad);
```

| parameternumber | Description |
|------|------|
| srcShape | `{rows, alignedCols}`, alignedCols mustmust 32 charactersectionpairalign |
| Pattern::Reduce::AR | returnapproximatelymostafteronedimension (eachtravel→standardamount)  |
| Pattern::Reduce::RA | returnapproximatelychapteronedimension (eachcolumn→standardamount)  |
| srcInnerPad | A2/A3 averageplatformmustmustas `true` |

**tmpBuffer largesmall**: Usage `GetReduceMaxMaxMinTmpSize` / `GetReduceSumTmpSize` Calculation:
```cpp
uint32_t tmpSize = AscendC::GetReduceMaxMaxMinTmpSize<T>(srcShape);
pipe.InitBuffer(tmpBuf, tmpSize);
```

**⚠️ Pattern returnapproximatelyRequirements alignedCols is 32B pairalignof**, nonpairalignDataUsage Level 2 Iterativetravelreturnapproximately. 

### WholeReduceSum / BlockReduceSum

Hardwarefingercommand, PerformanceupdateoptimizebutLimitationsupdatemultiple:
```cpp
AscendC::WholeReduceSum(dstLocal, srcLocal, count);
```

## comparecompareandselectselect API

### Compare
```cpp
// runcomputecharacterweightload
dstLocal = src0Local < src1Local;

// functionnumberadjustuse
AscendC::Compare(dstLocal, src0Local, src1Local, AscendC::CMPMODE::LT, count);
```

**CMPMODE**: LT(<), GT(>), GE(>=), LE(<=), EQ(==), NE(!=)

**Output**: uint8_t typetype, according to bit bitMemoryResult

**⚠️ 256 charactersectionpairalignConstraints**: Compare API RequirementsparticipationcomparecompareofDataregiondomainis **256 charactersectionofadjustnumbertimes**. nonpairaligntimerequires padding:
```cpp
// notfoot 256B ofpartdistributefillfill ±inf / FLT_MAX, confirmkeep padding regionnotshadowloudResult
uint32_t alignedCount = ((count * sizeof(T) + 255) / 256) * (256 / sizeof(T));
AscendC::Duplicate(src[count], paddingValue, alignedCount - count);  // padding
AscendC::Compare(dst, src0, src1, CMPMODE::LT, alignedCount);
```

### Select
```cpp
// modelformula0: twocounttensorselectget (selMaskhavebitnumberLimitations) 
AscendC::Select(dstLocal, maskLocal, src0Local, src1Local,
                AscendC::SELMODE::VSEL_CMPMASK_SPR, count);

// modelformula1: tensorandscalarselectget
AscendC::Select(dstLocal, maskLocal, src0Local, scalarValue,
                AscendC::SELMODE::VSEL_TENSOR_SCALAR_MODE, count);

// modelformula2: twocounttensorselectget (selMaskconnectcontinuedisappearconsume) 
AscendC::Select(dstLocal, maskLocal, src0Local, src1Local,
                AscendC::SELMODE::VSEL_TENSOR_TENSOR_MODE, count);
```

**selMask Rules**: bit bitas1select src0, as0select src1

## Datafillfill API (Duplicate)

```cpp
AscendC::Duplicate(dstLocal, scalarValue, count);

// highdimensionTiling
AscendC::Duplicate(dstLocal, scalarValue, mask, repeatTime, dstBlkStride, dstRepStride);
```

## complexmatchCalculation API

```cpp
// FusedMulAdd: dst = src0 * src1 + src2
AscendC::FusedMulAdd(dstLocal, src0Local, src1Local, src2Local, count);

// FusedMulAddRelu: dst = Relu(src0 * src1 + src2)
AscendC::FusedMulAddRelu(dstLocal, src0Local, src1Local, src2Local, count);

// Axpy: dst = a * x + y
AscendC::Axpy(dstLocal, aLocal, xLocal, yLocal, count);
```

## CommonCodemodelformula

### unitelementlevelruncompute
```cpp
__aicore__ inline void Compute()
{
    LocalTensor<half> src0 = inQueueX.DeQue<half>();
    LocalTensor<half> src1 = inQueueY.DeQue<half>();
    LocalTensor<half> dst = outQueueZ.AllocTensor<half>();

    AscendC::Add(dst, src0, src1, tileLength);

    outQueueZ.EnQue(dst);
    inQueueX.FreeTensor(src0);
    inQueueY.FreeTensor(src1);
}
```

### upgradeprecisiondegreeCalculation (FP16 -> FP32) 
```cpp
__aicore__ inline void Compute()
{
    LocalTensor<half> src0 = inQueueX.DeQue<half>();
    LocalTensor<half> src1 = inQueueY.DeQue<half>();
    LocalTensor<half> dst = outQueueZ.AllocTensor<half>();

    // complexuseMemoryperformtypetypeconvertexchange
    LocalTensor<float> src0Fp32 = src0.ReinterpretCast<float>();
    LocalTensor<float> src1Fp32 = src1.ReinterpretCast<float>();
    LocalTensor<float> dstFp32 = dst.ReinterpretCast<float>();

    AscendC::Cast(src0Fp32, src0, AscendC::RoundMode::CAST_NONE, tileLength);
    AscendC::Cast(src1Fp32, src1, AscendC::RoundMode::CAST_NONE, tileLength);
    AscendC::Add(dstFp32, src0Fp32, src1Fp32, tileLength);
    AscendC::Cast(dst, dstFp32, AscendC::RoundMode::CAST_NONE, tileLength);

    outQueueZ.EnQue(dst);
    inQueueX.FreeTensor(src0);
    inQueueY.FreeTensor(src1);
}
```

### Prerequisitesselectselect
```cpp
__aicore__ inline void Compute()
{
    LocalTensor<float> src0 = inQueueX.DeQue<float>();
    LocalTensor<float> src1 = inQueueY.DeQue<float>();
    LocalTensor<uint8_t> cmpResult = tmpQueue.AllocTensor<uint8_t>();
    LocalTensor<float> dst = outQueueZ.AllocTensor<float>();

    // comparecompare
    AscendC::Compare(cmpResult, src0, src1, AscendC::CMPMODE::LT, tileLength);
    // selectselect
    AscendC::Select(dst, cmpResult, src0, src1,
                    AscendC::SELMODE::VSEL_CMPMASK_SPR, tileLength);

    outQueueZ.EnQue(dst);
    inQueueX.FreeTensor(src0);
    inQueueY.FreeTensor(src1);
    tmpQueue.FreeTensor(cmpResult);
}
```

## throughuseConstraints

- **regionaddresspairalign**: LocalTensor risebeginregionaddressneed 32 charactersectionpairalign
- **Datatypetypeoneconsistent**: sourceoperateworknumberanditemofoperateworknumbertypetypeneedoneconsistent (Cast divideexternal) 
- **TPosition**: Support VECIN/VECCALC/VECOUT
- **repeatTime ≤ 255**: UsagehighdimensionTilingmodelformulatime, repeatTime as `uint8_t`, transferinput >255 ablequietsilentcutjudgeas 0 guideconsistenterrorerrorResult. needin host SideLimitationsor kernel Sidedistributebatch
- **dst ≠ tmpBuffer**: ReduceMax/ReduceSum of dst notabilityand tmpBuffer issameoneblockMemory
- **Prohibited std:: Math Functions**: Kernel middleProhibited `std::min/max/abs/sqrt/exp` etc, Usage AscendC directionamount API orthreeunitruncomputecharactersubstituterepresent
