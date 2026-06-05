# AscendC OperatorCode GenerationReference DocumentsLoadGuide

thisDocumentsfingerguide agent inDifferentOperatorDevelopmentScenariosunder, Load on DemandCorrespondingof reference Documents, avoidavoidonetimepropertyLoadallpartDocumentscreatebecomeaboveunderdocumentwavecost. 

## ReferencesDocumentsChecklist

| Documents | Path | Coreinsidecontent |
|------|------|----------|
| BaseDataStructure | `references/basic-data-structures-api.md` | LocalTensor, GlobalTensor, Layout, TPosition etcBasetypetype |
| ResourceManagement | `references/resource-management-api.md` | TPipe, TQue, TBuf, Double Buffer, Workspace, UB contentamountCalculation |
| DataData Copy | `references/data-copy-api.md` | DataCopyPad usemethod, Stride singlebit, rLength/rLengthAlign, pairalignCalculation |
| VectorCalculation | `references/vector-compute-api.md` | standardamountOptimization, widebroadcast, returnapproximately (Level2/Pattern) , Cast mixmatchprecisiondegree, Compare |
| SynchronizationControl | `references/sync-control-api.md` | DMA Asynchronousreasonmanage, EnQue/DeQue Synchronization, PipeBarrier, SyncAll |
| LimitationsandPitfalls | `references/kernel-constraints.md` | Prohibited std::, repeatTime≤255, Compare 256B pairalign, API blacknamesingle, diagnosejudgeChecklist |

## ScenariostransformLoadstrategystrategy

### Scenarios 1: Elementwise Operator (ReLU, GELU, Add, Mul etc) 

**specialfeature**: Iterativeunitelementoperatework, outputinputOutput shape mutualsame, onedimensionTiling

**mustmustLoad**:
- `basic-data-structures-api.md` — GlobalTensor/LocalTensor usemethod
- `resource-management-api.md` — TPipe/TQue/TBuf Initialization, Double Buffer
- `data-copy-api.md` — DataCopyPad connectcontinueData Copy
- `vector-compute-api.md` — computeart/oneunit/standardamountruncompute, Cast upgradeprecisiondegreemodelformula
- `kernel-constraints.md` — Prohibited std::, repeatTime Limitations

**notrequiresLoad**:
- `sync-control-api.md` — unitelementlevelOperatornocorebetweenaccordingdepend, EnQue/DeQue alreadyinResourceManagementmiddleDescription

### Scenarios 2: returnapproximately/returnonetransformtypeOperator (LayerNorm, Softmax, BatchNorm etc) 

**specialfeature**: Packagecontain ReduceSum/ReduceMax, according totravel/dimensiondegreeTiling, canabilityrequires FP32 middlebetweenprecisiondegree

**mustmustLoad**:
- `basic-data-structures-api.md` — GlobalTensor/LocalTensor
- `resource-management-api.md` — TPipe/TQue/TBuf, UB contentamountCalculation, blockCount Limitations
- `data-copy-api.md` — DataCopyPad multipletravelData Copy, rLength/rLengthAlign usemethod, Stride singlebit
- `vector-compute-api.md` — **weightpoint**: returnapproximately API (Level2/Pattern) , tmpBuffer Calculation, standardamountOptimization (Adds/Muls) , Cast mixmatchprecisiondegree, multipletravelwidebroadcast
- `kernel-constraints.md` — repeatTime≤255 distributebatch, Compare pairalign

**notrequiresLoad**:
- `sync-control-api.md` — travellevelaloneestablishreturnapproximatelynocorebetweenaccordingdepend

### Scenarios 3: pooltransformtypeOperator (AvgPool, MaxPool etc) 

**specialfeature**: slipperymovewindowmouthoperatework, multipledimensiondegreeiteratehistory, coreinsidehavecomplexmixedloopringStructure

**mustmustLoad**:
- `basic-data-structures-api.md` — GlobalTensor/LocalTensor
- `resource-management-api.md` — TPipe/TQue/TBuf, accumBuf etcmultipleapproachtimeslowconflictregion
- `data-copy-api.md` — multipletime DataCopyPad transferinputnotsametravel/bitplace
- `vector-compute-api.md` — accumulateadd, typetypeconvertexchange, Duplicate Initialization
- `kernel-constraints.md` — throughuse Kernel Limitations

**notrequiresLoad**:
- `sync-control-api.md` — each slice aloneestablishhandlemanage

### Scenarios 4: requirescorebetweenSynchronizationofOperator (AllReduce, Globalreturnapproximatelyetc) 

**specialfeature**: Multi-coreofbetweenkeepinDataaccordingdepend, requiresfirstlocalpartCalculationagainGlobalMerge

**allpartLoad**:
- `basic-data-structures-api.md`
- `resource-management-api.md` — requires Workspace Management (GM + UB workspace) 
- `data-copy-api.md`
- `vector-compute-api.md`
- `sync-control-api.md` — **weightpoint**: SyncAll/IBSet/IBWait corebetweenSynchronization, workspace emptybetweenRequirements
- `kernel-constraints.md`

### Scenarios 5: onlymodifymodifyalreadyhaveOperator (bug modifycomplex, smallrangescopemodifymove) 

**Load on Demand**: onlyLoadandmodifymodifyRelatedofDocuments. exampleif: 
- modifymodifyCalculationlogiclogic → `vector-compute-api.md` + `kernel-constraints.md`
- modifymodifyDataData Copy → `data-copy-api.md`
- modifymodifyResourcedistributematch → `resource-management-api.md`
- Runtime crash / Dataerrorerror → optimizefirst `kernel-constraints.md` diagnosejudgeChecklist

### Scenarios 6: PerformanceOptimization

**mustmustLoad**:
- `resource-management-api.md` — Double Buffer reasonmanage, UB utilizeuserate
- `vector-compute-api.md` — standardamountOptimization (Adds/Muls representsubstitute Duplicate+runcompute) , multipletravelwidebroadcast, Pattern returnapproximately
- `kernel-constraints.md` — repeatTime distributebatchOptimization

## throughuseRules

1. **mostsmallLoadreasonrule**: optimizefirstLoadandwhenpreviousOperatortypetypestraightconnectRelatedofDocuments, avoidavoidnorelatedDocumentsdisappearconsumeaboveunderdocument
2. **LimitationsDocumentsoftenLoad**: `kernel-constraints.md` Packagecontainhighfrequencystamppitfallpoint, newOperatorDevelopmenttimeSuggestbeginfinalLoad
3. **according tocompilecodePhaseLoad**: compilecompose Init timesideweight `resource-management-api.md`, compilecompose Compute timesideweight `vector-compute-api.md`
4. **meettoCompile/Runerrorerrortime**: optimizefirstsearchsee `kernel-constraints.md` diagnosejudgeChecklist
5. **DataData Copyaskproblem**: optimizefirstCheck `data-copy-api.md` middleof Stride singlebitand rLength/rLengthAlign regiondistribute
