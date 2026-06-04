# Phase 3: API UsageOptimization — DetailedReference

## 3.1 TPipe in kernel Create Outside Class

`TPipe` As Class Membertime, InitializationableSetGlobal TPipe fingerneedle, CompileadapterrecognizeastypeMemoryemptybetweenhavebe
externalpartdirtydyeofRisk, causethis**releaseabandonpairtypeinside Scalar changeamountofoftenamountfoldstackandoftenamounttransferbroadcastOptimization**. 

**reverseexample** — TPipe asClass member: 

```cpp
template <typename ComputeT> class KernelExample {
public:
    __aicore__ inline KernelExample() {}
    __aicore__ inline void Init(...) {
        pipe.InitBuffer(xxxBuf, BUFFER_NUM, xxxSize);
    }
private:
    TPipe pipe;       // ← intypeInternal, blockstop Scalar Optimization
};

extern "C" __global__ __aicore__ void example_kernel(...) {
    KernelExample<float> op;
    op.Init(...);
}
```

**positiveexample** — TPipe inCreate Outside Class, in order tofingerneedletransferinput: 

```cpp
template <typename ComputeT> class KernelExample {
public:
    __aicore__ inline KernelExample() {}
    __aicore__ inline void Init(..., TPipe* pipeIn) {
        pipe = pipeIn;
        pipe->InitBuffer(xxxBuf, BUFFER_NUM, xxxSize);
    }
private:
    TPipe* pipe;      // ← onlykeepfingerneedle, typeMemoryemptybetweeninterfereclean
};

extern "C" __global__ __aicore__ void example_kernel(...) {
    TPipe pipe;                     // ← inCreate Outside Class
    KernelExample<float> op;
    op.Init(..., &pipe);
}
```

actualtest: averageaverage scalar_time from 281 us downgradearrive 236 us (**−17%**) , scalar_time occupycomparefrom
21% downgradearrive 17%. **anywhatScenarios**allSuggestUsagethisOptimization, scalar bound Scenariosreceiveadvantageousespeciallyascleardisplay. 

## 3.2 pureData CopyOperatorUsage TQueBind

pureData CopyOperatornotinvolveand Vector Calculation, standardstandard VECIN→VECOUT modelformulaableleadinputonetimeredundantremainingof
LocalTensor→LocalTensor DataCopy. 

**reverseexample** — redundantremainingof Vector copyshell: 

```cpp
TQue<QuePosition::VECIN, BUFFER_NUM> QueI;
TQue<QuePosition::VECOUT, BUFFER_NUM> QueO;

auto iLocal = QueI.AllocTensor<ComputeT>();
DataCopy(iLocal, inGm[i * 32], size);
QueI.EnQue(iLocal);
auto iLocal2 = QueI.DeQue<ComputeT>();
for (int j = 0; j < jLen; ++j) {
    auto oLocal = QueO.AllocTensor<ComputeT>();
    DataCopy(oLocal, iLocal2, size);   // LocalTensor → LocalTensor, wavecost Vector
    QueO.EnQue(oLocal);
    auto oLocal2 = QueO.DeQue<ComputeT>();
    DataCopyPad(outGm[j], oLocal2, ...);
    QueO.FreeTensor(oLocal2);
}
QueI.FreeTensor(iLocal2);
```

**positiveexample** — TQueBind Eliminateredundantremainingcopyshell: 

```cpp
TQueBind<QuePosition::VECIN, QuePosition::VECOUT, BUFFER_NUM> queBind;

auto bindLocal = queBind.AllocTensor<ComputeT>();
DataCopy(bindLocal, inGm[i * 32], size);
queBind.EnQue(bindLocal);
auto bindLocal2 = queBind.DeQue<ComputeT>();
for (int j = 0; j < len; ++j) {
    DataCopyPad(outGm[j], bindLocal2, ...);
}
queBind.FreeTensor(bindLocal2);
```

validresult: `aiv_vec_time` downgradearriveapproximately 0. 

## 3.3 Counter modelformula (SetMaskCount) 

Normal modelformularequireshandmoveCalculationmainblock/tailblockof mask anditeraterepresenttimenumber, involveandlargeamount Scalar openconsume. 
Counter modelformulastraightconnecttransferinputtotalunitelementnumber, HardwareAutomaticpushjudgeiteraterepresenttimenumber. 

**reverseexample** — Normal modelformula (half typetype, 15000 countunitelement) : 

```cpp
uint32_t ELE_SIZE = 15000;
AscendC::BinaryRepeatParams binaryParams;
uint32_t numPerRepeat    = 256 / sizeof(DTYPE_X);   // half → 128
uint32_t mainRepeatTimes = ELE_SIZE / numPerRepeat;  // 117
uint32_t tailEleNum      = ELE_SIZE % numPerRepeat;  // 24

AscendC::SetMaskNorm();
AscendC::SetVectorMask<DTYPE_X, AscendC::MaskMode::NORMAL>(numPerRepeat);
AscendC::Add<DTYPE_X, false>(zLocal, xLocal, yLocal,
    AscendC::MASK_PLACEHOLDER, mainRepeatTimes, binaryParams);
if (tailEleNum > 0) {
    AscendC::SetVectorMask<DTYPE_X, AscendC::MaskMode::NORMAL>(tailEleNum);
    AscendC::Add<DTYPE_X, false>(
        zLocal[mainRepeatTimes * numPerRepeat],
        xLocal[mainRepeatTimes * numPerRepeat],
        yLocal[mainRepeatTimes * numPerRepeat],
        AscendC::MASK_PLACEHOLDER, 1, binaryParams);
}
AscendC::ResetMask();
```

**positiveexample** — Counter modelformula, onetimeadjustuse: 

```cpp
uint32_t ELE_SIZE = 15000;
AscendC::BinaryRepeatParams binaryParams;
AscendC::SetMaskCount();
AscendC::SetVectorMask<DTYPE_X, AscendC::MaskMode::COUNTER>(ELE_SIZE);
AscendC::Add<DTYPE_X, false>(zLocal, xLocal, yLocal,
    AscendC::MASK_PLACEHOLDER, 1, binaryParams);
AscendC::ResetMask();
```

whenmultiplecount Vector fingercommandhandlemanagemutualsameunitelementnumberamounttime, Counter modelformulaoptimizetrendupdatecleardisplay——noneedreversecomplex
CalculationDifferentmainblock/tailblock mask. 

## 3.4 Matmul AtomicAdd

Matmul Result C(m,n) requiresand GM aboverulematrix D(m,n) mutualaddtime, canintransferoutputPathabovemergematch. 

**reverseexample** — handmoveData Copyafterin UB do Add: 

```cpp
mm.IterateAll(local_c);

DataCopy(local_d, gm_d, d_size);
event_t eventId = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
SetFlag<HardEvent::MTE2_V>(eventId);
WaitFlag<HardEvent::MTE2_V>(eventId);
Add(local_d, local_d, local_c, d_size);
DataCopy(gm_d, local_d, d_size);
```

**positiveexample** — AtomicAdd mergematchtotransferoutput: 

```cpp
mm.IterateAll(gm_d, 1);          // enAtomic = 1
// orin Iterate loopringmiddle: 
// mm.GetTensorC(gm_d, 1);       // enAtomic = 1
```

M=64, N=256, K=256 actualtest: averageaverage cycle from 154181 downgradearrive 135054 (**−12.4%**) . 

## 3.5 returnapproximatelyfingercommandgroupmatch

willconnectcontinue buffer allpartaccumulateaddasonecountstandardamountofScenarios: 

| methodcase | fingercommandnumber | mutualpairspeeddegree |
|---|---|---|
| 2× WholeReduceSum | 2 | mostslow (WholeReduceSum singleitemcompareslow)  |
| 3× BlockReduceSum | 3 | middleetc |
| **1× BlockReduceSum + 1× WholeReduceSum** | **2** | **mostrapid** |

pushrecommendmodelformula (float, shape=256) : 

```cpp
static constexpr uint32_t BLK_LEN = 32;
TBuf<QuePosition::VECCALC> calcBuf;
pipe.InitBuffer(calcBuf, totalLength * sizeof(float));
AscendC::LocalTensor<float> tempTensor1 = calcBuf.Get<float>();
constexpr uint32_t c0Count = BLK_LEN / sizeof(float);
const uint32_t blockNum0 = (totalLength + c0Count - 1) / c0Count;

AscendC::SetMaskCount();
AscendC::SetVectorMask<float>(0, totalLength);
AscendC::BlockReduceSum<float, false>(tempTensor1, xLocal,
    AscendC::MASK_PLACEHOLDER, 1,
    DEFAULT_BLK_STRIDE, DEFAULT_BLK_STRIDE, DEFAULT_REP_STRIDE);
AscendC::PipeBarrier<PIPE_V>();

AscendC::SetVectorMask<float>(0, blockNum0);
AscendC::WholeReduceSum<float, false>(zLocal, tempTensor1,
    AscendC::MASK_PLACEHOLDER, 1,
    DEFAULT_BLK_STRIDE, DEFAULT_BLK_STRIDE, DEFAULT_REP_STRIDE);
AscendC::PipeBarrier<PIPE_V>();
AscendC::SetMaskNorm();
```
