# AscendC Kernel LimitationsandPitfallsGuide

## ProhibitedUsageof C++ Features (Kernel side) 

### Standard LibraryMath Functions

Kernel Codemiddle**Prohibited**Usage `std::` commandnameemptybetweenunderofMath Functions, CompiletimecanabilitythroughexceedbutRuntimeproduceliveerrorerrorResult:

| Prohibited | substituterepresentmethodcase |
|------|---------|
| `std::min(a, b)` | `a < b ? a : b` (standardamount) or `AscendC::Min(dst, src0, src1, count)` |
| `std::max(a, b)` | `a > b ? a : b` (standardamount) or `AscendC::Max(dst, src0, src1, count)` |
| `std::abs(x)` | `AscendC::Abs(dst, src, count)` |
| `std::sqrt(x)` | `AscendC::Sqrt(dst, src, count)` |
| `std::exp(x)` | `AscendC::Exp(dst, src, count)` |
| `std::log(x)` | `AscendC::Ln(dst, src, count)` |
| `#include <cmath>` | notrequiresleadinput |

### movestateMemorydistributematch

Kernel middle**Prohibited**UsageanywhatmovestateMemorydistributematch:

| Prohibited | substituterepresentmethodcase |
|------|---------|
| `std::vector<T>` | `LocalTensor<T>` + `pipe.InitBuffer` |
| `new / delete` | `pipe.InitBuffer` |
| `malloc / free` | `pipe.InitBuffer` |

### Host/Kernel headfileseparateleave

| filetypetype | canin order to include | notability include |
|---------|-------------|-------------|
| op_host (*.cpp) | `<cmath>`, `<algorithm>`, tiling headers | `kernel_operator.h` |
| op_kernel (*.cpp) | `kernel_operator.h` | `<cmath>`, `<algorithm>`, tiling headers |

## repeatTime overflowoutput

allhaveUsagehighdimensionTilingmodelformulaof API (Add, Sub, Mul, Div, Cast, Duplicate etc) , other `repeatTime` parameternumbertypetypeas **`uint8_t`**, mostlargevalue **255**. 

**quietsilentcutjudge**: transferinput 256 ablebecutjudgeas 0, guideconsistent**notExecuteanywhatCalculation**andnoreporterror. 

### Host Sideguardshield
```cpp
// Tiling PhaseLimitationsmostlargetravelnumber
tileRows = std::min(tileRows, static_cast<uint32_t>(255));
```

### Kernel Sidedistributebatch
```cpp
int64_t remaining = rowCount;
int64_t offset = 0;
while (remaining > 0) {
    uint8_t batch = static_cast<uint8_t>(std::min(remaining, (int64_t)255));
    AscendC::Sub(dst[offset], src0[offset], src1, mask, batch, params);
    offset += batch * alignedCols;
    remaining -= batch;
}
```

### receiveshadowloudof API

allhaveconnectreceive `repeatTime` parameternumberofhighdimensionTilingweightload: Add, Sub, Mul, Div, Adds, Muls, Cast, Duplicate, Compare, Select, Exp, Ln, Abs, Sqrt, Reciprocal etc. 

## Compare API 256 charactersectionpairalign

Compare RequirementsparticipationcomparecompareofDataregiondomainas **256 charactersectionadjustnumbertimes**. notfootpartdistributeneed padding:
- ArgMax → padding fill `-inf` or `-FLT_MAX`
- ArgMin → padding fill `+inf` or `FLT_MAX`

```cpp
uint32_t align256Elems = 256 / sizeof(T);
uint32_t alignedCount = ((count + align256Elems - 1) / align256Elems) * align256Elems;
if (alignedCount > count) {
    AscendC::Duplicate(src[count], paddingValue, alignedCount - count);
}
```

## oftenamountandCompileperiodOptimization

- optimizefirstUsage `constexpr` definemeaningCompileperiodoftenamount
- avoidavoidRuntimeCalculationcanin order toinCompileperiodDetermineofvalue
- 32 charactersectionpairalignCalculation: `((x + 31) / 32) * 32`

## API blacknamesingle

| API | Prohibitedreasoncause | substituterepresentmethodcase |
|-----|---------|---------|
| `GlobalTensor::SetValue()` | validrateextremelow, Iterativeunitelement GM compose | `DataCopyPad` |
| `GlobalTensor::GetValue()` | validrateextremelow, Iterativeunitelement GM read | `DataCopyPad` |
| `DataCopy(GM↔UB)` | nomethodhandlemanagenonpairalignData | `DataCopyPad` |

onlyallowallowadjusttrytimeUsage:
```cpp
AscendC::printf("debug: xGm[0]=%f\n", xGm.GetValue(0));  // onlyadjusttry
```

## diagnosejudgeCheckChecklist

meetto Kernel CompileorRunerrorerrortimeaccording tothissequenceorderarrangesearch:

1. iswhetherUsagecompleted `std::` functionnumber? → substituteexchangeas AscendC API
2. DataData Copyiswhetherusecompleted `DataCopyPad`? → GM↔UB mustmustuse DataCopyPad
3. `repeatTime` iswhetherexceedexceed 255? → distributebatchhandlemanage
4. Compare Dataiswhether 256B pairalign? → padding
5. ReduceMax/Sum of dst and tmpBuffer iswhethernotsame? → distributeopendistributematch
6. InitBuffer totalnumberiswhetherexceedexceed 64? → Merge buffer
7. EnQue/DeQue iswhethermatchpair? → Data CopyaftermustmustSynchronization
