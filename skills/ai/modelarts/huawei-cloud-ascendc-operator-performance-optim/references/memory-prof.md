# Phase 4: MemoryOptimization — DetailedReference

## Memory HierarchyOverview

| Buffer | Purpose | Description |
|---|---|---|
| GM (HBM)  | GlobalMemory | bandwidthwidthapproximately 1.6 TB/s |
| L2Cache | togethershareslowkeep | approximately 192 MB, bandwidthwidthapproximately 7 TB/s |
| L1 Buffer | AI Core thisregionMemory | Cube Datamiddleconvert |
| L0A / L0B | Cube outputinput | by L1 Load |
| L0C (CO1)  | Cube Output | Supportreasonregionaccumulateadd |
| UB (Unified Buffer)  | Vector outputinput/Output | VECIN, VECOUT, VECCALC |
| BT Buffer (C2)  | Bias table | onlydistributeleaveArchitecture |
| FP Buffer (C2PIPE2GM)  | Fixpipe parameternumber | onlydistributeleaveArchitecture |

## 4.1 UB Buffer mergematch

connectcontinuemultipletime Vector runcomputetime, willmiddlebetweenResultkeepkeepin UB above, notvia GM towardsreturn. 
n timeconnectcontinueruncomputeof GM Data Copytimenumberfrom `2n` downgradeas `2`. 

**reverseexample** — eachtimeruncomputeallvia GM towardsreturn (Exp + Abs need 4 time GM Data Copy) : 

```cpp
class KernelSample {
    __aicore__ inline void Process() {
        CopyIn();       // GM → UB
        Compute();      // Exp
        CopyOut();      // UB → GM
        CopyIn1();      // GM → UB (weightnewreadreturn Exp Result) 
        Compute1();     // Abs
        CopyOut1();     // UB → GM
    }
};
```

**positiveexample** — in UB insidelinkformulaCalculation (only 2 time GM Data Copy) : 

```cpp
class KernelSample {
    __aicore__ inline void Compute() {
        LocalTensor<float> src0Local = inQueueSrc0.DeQue<float>();
        LocalTensor<float> dstLocal  = outQueueDst.AllocTensor<float>();
        Exp(dstLocal, src0Local, 1024);
        Abs(dstLocal, dstLocal, 1024);   // reasonregionoperatework, keepin UB
        outQueueDst.EnQue<float>(dstLocal);
        inQueueSrc0.FreeTensor(src0Local);
    }
    __aicore__ inline void Process() {
        CopyIn();       // GM → UB (onetime) 
        Compute();      // Exp + Abs mergematch
        CopyOut();      // UB → GM (onetime) 
    }
};
```

## 4.2 L0C accumulateaddrulematrixmultiply

`A1*B1 + A2*B2 + ...` Scenariosunder, utilizeuse Mmad ofinsidebuildaccumulateaddfunctionabilitywillpartdistributeResultkeepkeepin
CO1 (L0C) middle. avoidavoideachtimerulematrixmultiplyResultall CO1→GM→UB againdo Add. 

**reverseexample** — Iterativetimetransferoutputafterin UB requestand: 

```cpp
void Process() {
    Compute();       // Mmad → CO1
    CopyOut();       // CO1 → workspace (GM) 
    CopyIn1();       // workspace → UB

    Compute1();      // Mmad → CO1
    CopyOut1();      // CO1 → workspace (GM) 
    CopyIn2();       // workspace → UB

    Compute2();      // Add(result1, result2) in UB
    CopyOut2();      // UB → GM
}
```

**positiveexample** — in L0C middlereasonregionaccumulateadd: 

```cpp
void Compute() {
    MmadParams mmadParams;
    mmadParams.m = m;  mmadParams.n = n;  mmadParams.k = k;
    Mmad(c1Local, a2Local_1, b2Local_1, mmadParams);
    mmadParams.cmatrixInitVal = false;
    Mmad(c1Local, a2Local_2, b2Local_2, mmadParams);  // in CO1 reasonregionaccumulateadd
}
// mostafteronetime CopyOut: CO1 → GM
```

## 4.3 smallrulematrixlengthstation L1

when L1 nomethodsametimecontentcontainleftrightrulematrix (ifleftrulematrix 992K, rightrulematrix 16K, L1 contentamount 512K) time, 
willcomparesmallrulematrixonetimeLoadafteroftenstation L1, onlyloopringData Copycomparelargerulematrix. 

**reverseexample** — eachtimeiteraterepresentallweightnewLoadtwocountrulematrix: 

```cpp
void Process() {
    for (uint32_t i = 0; i < 2; i++) {
        CopyInA1(i);      // Loadleftrulematrixcutslice
        SplitA();
        for (uint32_t j = 0; j < 2; j++) {
            CopyInB1(j);  // eachtimeallweightnewLoadrightrulematrix
            SplitB();
            Compute(i, j);
        }
    }
    CopyOut();
}
```

**positiveexample** — rightrulematrixonetimeLoad, onlyloopringData Copyleftrulematrix: 

```cpp
void Process() {
    CopyInB1();          // rightrulematrixonetimeallloadinput L1
    SplitB();            // L1 → L0B
    for (uint32_t i = 0; i < 2; i++) {
        CopyInA1(i);     // loopringLoadleftrulematrixcutslice
        SplitA();
        for (uint32_t j = 0; j < 2; j++) {
            Compute(i, j);  // rightrulematrixalreadyin L0B
        }
    }
    CopyOut();
}
```

2 countleftrulematrixcutslicetime: Data Copytimenumberfrom 4+4=8 downgradeas 1+2=3. 

## 4.4 BT Buffer Store bias (distributeleaveArchitecture) 

will bias keepinput BT Buffer (C2) , in Mmad middleonestepmergematch bias addmethod, avoidavoid
CO1→GM→UB→Add→GM ofredundantlengthPath. 

**reverseexample** — in UB middlesinglealonedo bias Add: 

```cpp
TQue<QuePosition::VECIN, 1> inQueueBias;
// Mmad after: CO1 → workspace(GM) → UB
// bias: GM → UB
// Add(matmul_result, bias) in UB → GM
```

**positiveexample** — throughexceed BT Buffer mergematch: 

```cpp
TQue<QuePosition::C1, 1> inQueueC1;    // L1
TQue<QuePosition::C2, 1> outQueueC2;   // BT Buffer

void SplitBias() {
    LocalTensor<float> bias1Local = inQueueC1.DeQue<float>();
    LocalTensor<float> bias2Local = outQueueC2.AllocTensor<float>();
    // L1 → BT
    DataCopy(bias2Local, bias1Local, {1, (uint16_t)(n * sizeof(float) / 64), 0, 0});
    outQueueC2.EnQue<float>(bias2Local);
    inQueueC1.FreeTensor(bias1Local);
}

void Compute() {
    LocalTensor<float> bias2Local = outQueueC2.DeQue<float>();
    MmadParams mmadParams;
    mmadParams.m = m;  mmadParams.n = n;  mmadParams.k = k;
    mmadParams.cmatrixInitVal = false;
    Mmad(c1Local, a2Local, b2Local, bias2Local, mmadParams);  // mergematch bias
    outQueueC2.FreeTensor(bias2Local);
}
```

## 4.5 FP Buffer StoreQuantizationparameternumber (distributeleaveArchitecture) 

willQuantizationparameternumberkeepinput FP Buffer (C2PIPE2GM) , throughexceed Fixpipe intransferoutputPathabovefollowpathQuantization. 
avoidavoid CO1→GM→UB→QuantizationCalculation→GM ofredundantlengthPath. 

**reverseexample** — in UB middlesinglealonedoQuantization: 

```cpp
TQue<QuePosition::VECIN, 1> inQueueDeq;    // Quantizationparameternumberin UB
// CO1 → workspace → UB
// Quantizationparameternumber: GM → UB
// Cast + Mul + Cast in UB
// Result → GM
```

**positiveexample** — throughexceed FP Buffer mergematch: 

```cpp
TQue<QuePosition::C1, 1>        inQueueDeq1;   // L1
TQue<QuePosition::C2PIPE2GM, 1> inQueueDeq;    // FP Buffer

void SplitDeq() {
    LocalTensor<uint64_t> deq1Local = inQueueDeq1.DeQue<uint64_t>();
    LocalTensor<uint64_t> deqLocal  = inQueueDeq.AllocTensor<uint64_t>();
    // L1 → FP Buffer
    DataCopy(deqLocal, deq1Local, {1, (uint16_t)(cSize * sizeof(uint64_t) / 128), 0, 0});
    inQueueDeq.EnQue<uint64_t>(deqLocal);
    inQueueDeq1.FreeTensor(deq1Local);
}

void CopyOut() {
    LocalTensor<float>    c1Local  = outQueueCO1.DeQue<float>();
    LocalTensor<uint64_t> deqLocal = inQueueDeq.DeQue<uint64_t>();
    SetFixpipeNz2ndFlag(1, 0, 0);
    DataCopyCO12DstParams params;
    params.nSize    = n;
    params.mSize    = m;
    params.srcStride = m;
    params.dstStride = n;
    params.quantPre = QuantMode_t::VQF322B8_PRE;
    params.nz2ndEn  = true;
    DataCopy(cGM, c1Local, params);   // transferoutputtimefollowpathQuantization
    outQueueCO1.FreeTensor(c1Local);
}
```
