# Phase 5: PipelineOptimization — DetailedReference

## 5.1 CopyIn / Compute / CopyOut Paradigm

willOperatorDivide IntoThree-level PipelineTask, Usage `TQue` performlevelbetweenSynchronization. notsamePhasereflectshoottoaloneestablishof
Hardwarefingercommandteamcolumn (MTE2/MTE3 Data Copy, V Vector, M rulematrix) , canParallelExecute. 

```
CopyIn  → AllocTensor + DataCopy(GM→Local) + EnQue     [MTE2 teamcolumn]
Compute → DeQue + Vector/Cube runcompute + EnQue              [V / M teamcolumn]
CopyOut → DeQue + DataCopy(Local→GM) + FreeTensor       [MTE3 teamcolumn]
```

BaseFramework: 

```cpp
TPipe pipe;
TQue<VecIn, 1> queIn;
TQue<VecOut, 1> queOut;

pipe.InitBuffer(queIn, 2, 1024);   // double buffer

for (int i = 0; i < tileCount; i++) {
    // CopyIn
    auto tensor = queIn.AllocTensor<half>();
    DataCopy(tensor, gm, len);
    queIn.EnQue(tensor);

    // Compute
    auto tensorIn = queIn.DeQue<half>();
    auto tensorOut = queOut.AllocTensor<half>();
    Abs(tensorOut, tensorIn, 1024);
    queIn.FreeTensor(tensorIn);
    queOut.EnQue(tensorOut);

    // CopyOut
    auto result = queOut.DeQue<half>();
    DataCopy(gmOut, result, 1024);
    queOut.FreeTensor(result);
}
```

sameoneDatacutsliceinside, CopyIn → Compute → CopyOut mustmuststringtravel. butnotsamecutslicecanweightstack: 
Compute handlemanagecutslice N time, CopyIn cantransferinputcutslice N+1, CopyOut cantransferoutputcutslice N−1. 

## 5.2 Double Buffer

`InitBuffer` of buffer countnumbersetas **2**, useData CopyandCalculationweightstackExecute. 

**reverseexample** — notuseability double buffer (Vector utilizeuserateapproximately 33%) : 

```cpp
pipe.InitBuffer(inQueueSrc0, 1, sizeSrc0 * sizeof(half));   // single buffer
pipe.InitBuffer(inQueueSrc1, 1, sizeSrc1 * sizeof(half));
pipe.InitBuffer(outQueueDst, 1, sizeDst0 * sizeof(half));

for (uint32_t index = 0; index < round * 2; ++index) {
    CopyIn(index);    // MTE2 busy, Vector idle
    Compute();        // Vector busy, MTE idle
    CopyOut(index);   // MTE3 busy, Vector idle
}
```

**positiveexample** — useability double buffer (underone tile of CopyIn andwhenprevious tile of Compute weightstack) : 

```cpp
pipe.InitBuffer(inQueueSrc0, 2, sizeSrc0 * sizeof(half));   // double buffer
pipe.InitBuffer(inQueueSrc1, 2, sizeSrc1 * sizeof(half));
pipe.InitBuffer(outQueueDst, 2, sizeDst0 * sizeof(half));

for (uint32_t index = 0; index < round; ++index) {
    CopyIn(index);    // canandpreviousonetime CopyOut weightstack
    Compute();        // canandunderonetime CopyIn weightstack
    CopyOut(index);   // canandunderonetime Compute weightstack
}
```

**Notesmatteritem**: 
- Memoryopenconsumefliptimes (eachcountteamcolumndistributematch 2 block buffer) . 
- loopringtimenumbermust >= 2 onlyabilityobtainadvantageous. 
- whenCalculationtimebetweenfarlargeinData Copytimebetweentime, Data Copyalreadybehiddenhidden, double buffer receiveadvantageoushavelimit. 
- whenDataamountverysmall, onetimeimmediatecancompletedallpartCalculationtime, noneed double buffer. 

## 5.3 Asynchronous Iterate (MIX modelformula, AIC+AIV) 

Matmul MIX Scenariosunder, `Iterate` / `IterateAll` ablein AIV (Vector core) and
AIC (Cube core) ofbetweenissuepresentSynchronizationdisappearinformation. SynchronizationmodelformulaControldisappearinformationfrequencyrate: 

- `Iterate<true>()` (Synchronization) : **eachtime**iteraterepresentissueoneitemdisappearinformation——openconsumelarge. 
- `Iterate<false>()` (Asynchronous) : only**chapteronetime**issuedisappearinformation, aftercontinueiteraterepresentnoneed AIC/AIV Synchronization. 

**Synchronizationmodelformula** — eachtimeiteraterepresentallhavedisappearinformationopenconsume: 

```
AIV: send_msg → wait → send_msg → wait → send_msg → wait
AIC:           exec →           exec →           exec
```

**Asynchronousmodelformula** — onlyfirsttimeissuedisappearinformation: 

```
AIV: send_msg → continue → continue → continue
AIC:           exec     → exec     → exec
```

CodeExamples: 

```cpp
TQueBind<TPosition::CO2, TPosition::VECIN>    qVecIn;
TQueBind<TPosition::VECIN, TPosition::VECOUT> qVecOut;

mm.SetTensorA(gmA);
mm.SetTensorB(gmB);
mm.SetWorkspace(workspace, singleCoreM * singleCoreN * sizeof(float));

while (mm.template Iterate<false>()) {    // Asynchronousmodelformula
    auto cInUB = qVecIn.AllocTensor<float>();
    mm.GetTensorC(cInUB);
    qVecIn.EnQue(cInUB);
    cInUB = qVecIn.Deque<float>();
    auto cOutUB = qVecOut.AllocTensor<float>();
    Muls(cOutUB, cInUB, scalar, baseM * baseN);
    qVecIn.FreeTensor(cInUB);
    // ... aftercontinuehandlemanage
}
```

MIX ScenariosundersilentrecognizeUsageAsynchronousmodelformula. onlyinrequiresstrictformatofIterativetimeiteraterepresentsequenceorderkeepcertify (guardstopregionaddressstampstep) 
timeonlyFallbackasSynchronizationmodelformula. 
