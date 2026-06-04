# MigrationReportTemplate

## completeadjustReportStructure

```markdown
# [ModelName] AscendMigrationReport

> Generation Time: YYYY-MM-DD HH:MM
> Servicesadapter: ascend-server-01
> Container: skill-the

---

## one, ModelStructureAnalysis

### 1.1 Basicinformationinformation

| itemitem | value |
|------|-----|
| ModelName | xxx |
| ModelSource | transformers / thisregionDirectory / PyPI |
| Architecturetypetype | Encoder-only / Decoder-only / Encoder-Decoder |
| parameternumberamount | xxx M |
| outputinputscaleinch | xxx × xxx |

### 1.2 ArchitectureAnalysis

- **maininterferenetworknetwork: ** ResNet / CSPDarknet / ViT / ...
- **checktesthead: ** have/no
- **Notesforcemachinemake: ** have/no
- **specialspecialOperator: ** NMS / ROIAlign / ...

### 1.3 msmodelslim Compatibility

| Checkitem | Result |
|--------|------|
| Decoder-only Architecture | is/whether |
| Transformers Implementation | is/whether |
| msmodelslim Support | ✅ / ❌ |

### 1.4 MigrationpathlineSuggest

**pushrecommendpathline: ** torch_npu straightconnectMigration

**manageby: **
- [toolbodyreasoncause]

**substituterepresentmethodcase: **
- [ifhave]

---

## two, MigrationVerification

### 2.1 Environmentinformationinformation

| itemitem | value |
|------|-----|
| Servicesadapter | ascend-server-01 |
| Container | skill-the |
| mirrorlike | quay.io/ascend/vllm-ascend:v0.18.0 |
| CANN | cann-version-placeholder.220 |
| torch_npu | x.x.x |
| NPU | 8× Ascend 910B3 |

### 2.2 accordingdependInstallation

```bash
pip install torch_npu
pip install [Modelaccordingdepend]
```

### 2.3 pushmanageTestingResult

| itemitem | Result |
|------|------|
| ModelLoad | ✅ becomefunction |
| NPU pushmanage | ✅ becomefunction |
| precisiondegreeVerification | ✅ throughexceed |

### 2.4 Performancefingerstandard

| fingerstandard | value |
|------|-----|
| averageaveragepushmanageTime consumption | xx.xx ms |
| mostsmallTime consumption | xx.xx ms |
| mostlargeTime consumption | xx.xx ms |
| FPS | xx.x |

### 2.5 issueappearofaskproblem

| askproblem | shadowloud | statusstate |
|------|------|------|
| xxx | xxx | waitOptimization |

---

## three, PerformanceCollection

### 3.1 CollectionConfiguration

| itemitem | value |
|------|-----|
| Collectionmodelformula | device / simulator |
| NPU | npu:0 |
| Collectiontimelength | xx s |
| Collectiontimebetween | YYYY-MM-DD HH:MM |

### 3.2 Databitplace

| itemitem | value |
|------|-----|
| Servicesadapter | ascend-server-01 |
| DataDirectory | /home/xxx/PROF_xxx/ |
| Database | msprof_xxx.db |
| Datalargesmall | xx MB |

---

## four, Performance Analysis

### 4.1 OperatorTime consumptiondistributearrange (TOP 20) 

| arrangename | Operatorname | typetype | Time consumption(ms) | occupycompare | adjustusetimenumber | averageaverageTime consumption(us) |
|------|--------|------|----------|------|----------|--------------|
| 1 | xxx | AI_CPU | xx.xx | xx.x% | xxx | xx.xx |
| 2 | xxx | AI_CORE | xx.xx | xx.x% | xxx | xx.xx |
| ... | ... | ... | ... | ... | ... | ... |

### 4.2 according toOperatortypetypestatisticscalculate

| typetype | Total time(ms) | occupycompare | Operatornumber |
|------|------------|------|--------|
| AI_CPU | xx.xx | xx.x% | xxx |
| AI_CORE | xx.xx | xx.x% | xxx |
| AI_VECTOR_CORE | xx.xx | xx.x% | xxx |

### 4.3 BottleneckOperatorAnalysis

| Operator | typetype | occupycompare | askproblemAnalysis |
|------|------|------|----------|
| Index | AI_CPU | xx.x% | searchleadoperateworkin CPU Implementation, validratelow |
| TransData | AI_VECTOR_CORE | xx.x% | formatformulaconvertexchangeopenconsume, needdecreasefew CPU-NPU Datacomereturn |
| NMS | AI_CPU | xx.x% | torchvision::nms notSupport NPU, Fallback CPU |

### 4.4 tableappeargoodgoodOperator

| Operator | typetype | Description |
|------|------|------|
| Conv2D | AI_CORE | Cube utilizeuserate 70-90%, positiveoften |
| BatchNorm | AI_CORE | mergematchto Conv, noamountexternalopenconsume |

### 4.5 PerformanceBottleneckSummary

**mainneedBottleneck: **
1. xxx Operator (occupycompare xx%) : [reasoncause]
2. xxx Operator (occupycompare xx%) : [reasoncause]

**timeneedBottleneck: **
1. xxx Operator (occupycompare xx%) : [reasoncause]

---

## five, OptimizationSuggest

### 5.1 Optimizationmethodcase

| optimizefirstlevel | Operator | askproblem | Optimizationmethodcase | preperiodreceiveadvantageous | difficultdegree |
|--------|------|------|----------|----------|------|
| P0 | Index | AI_CPU Implementation | use AscendC DevelopmentOptimizationversion | +xx% | middle |
| P1 | TransData | formatformulaconvertexchange | decreasefew CPU-NPU Datacomereturn | +xx% | low |
| P2 | NMS | Fallback CPU | use AscendC Development NPU version | +xx% | high |

### 5.2 underonesteptravelmove

1. **briefperiodOptimization**
   - [toolbodySteps]

2. **middleperiodOptimization**
   - canadjustuse `ascendc-operator-performance-optim` DevelopmentOptimizationOperator
   - [toolbodySteps]

3. **lengthperiodOptimization**
   - [toolbodySteps]

---

## Summary

### Migrationstatusstate

✅ **Migrationbecomefunction**

### Performancetableappear

| fingerstandard | value |
|------|-----|
| pushmanageTime consumption | xx.xx ms |
| FPS | xx.x |
| mainneedBottleneck | xxx |

### Optimizationpotentialforce

throughexceedOptimizationBottleneckOperator, precalculatecanliftupgrade **xx%** Performance. 

### RelatedResource

- PerformanceData: `/home/xxx/PROF_xxx/`
- VerificationScripts: `references/migration-scripts.md`
- SQL Query: `references/profiler-sql.md`
```

---

## simpletransformReportTemplate

suitable forrapidspeedVerificationScenarios: 

```markdown
# [ModelName] rapidspeedVerificationReport

## Environment
- Servicesadapter: ascend-server-01 (skill-the)
- NPU: Ascend 910B3

## Result
- Migrationstatusstate: ✅ becomefunction
- pushmanageTime consumption: xx.xx ms
- FPS: xx.x

## Bottleneck
- [mainneedBottleneckOperator]

## underonestep
- [OptimizationSuggest]
```
