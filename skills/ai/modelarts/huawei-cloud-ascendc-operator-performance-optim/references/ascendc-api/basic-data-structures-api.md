# AscendC BaseDataStructureInterfaceSummary

## one, LocalTensor

**Purpose**: StoreAI CoreInternalLocal MemoryData, Logical LocationPackageincludeVECIN, VECOUT, VECCALC, A1, A2, B1, B2, CO1, CO2. 

### structurecreateandInitialization

```cpp
// PipeFramework (notstraightconnectadjustuse) 
AscendC::LocalTensor<T>() {}

// quietstateTensorcompileprocess
AscendC::LocalTensor<T>(TPosition pos, uint32_t addr, uint32_t tileSize)
AscendC::LocalTensor<T>(uint32_t addr)  // onlySupportTensorTraittypetype
```

### CoreInterface

| Interface | functionability | Examples |
|------|------|------|
| `SetValue(index, value)` | Setunitelementvalue | `local.SetValue(0, 100)` |
| `GetValue(index)` | obtaingetunitelementvalue | `auto val = local.GetValue(0)` |
| `operator()(offset)` | obtaingetunitelementleaduse | `local(0) = 100` |
| `operator[](offset)` | partialmoveobtaingetnewTensor | `local[16]` |
| `GetSize()` | obtaingetunitelementcountnumber | `uint32_t size = local.GetSize()` |
| `SetSize(size)` | Setunitelementcountnumber | `local.SetSize(256)` |
| `GetPhyAddr()` | obtaingetobjectmanageregionaddress | `uint64_t addr = local.GetPhyAddr()` |
| `GetPosition()` | obtaingetLogical Location | `TPosition pos = local.GetPosition()` |
| `ReinterpretCast<T>()` | typetypeweightsolveexplain | `auto t = local.ReinterpretCast<half>()` |
| `SetShapeInfo(shapeInfo)` | Setshapestatusinformationinformation | `local.SetShapeInfo(ShapeInfo(...))` |
| `GetShapeInfo()` | obtaingetshapestatusinformationinformation | `ShapeInfo info = local.GetShapeInfo()` |
| `SetUserTag(tag)` | Setuseuserstandardsign | `local.SetUserTag(10)` |
| `GetUserTag()` | obtaingetuseuserstandardsign | `TTagType tag = local.GetUserTag()` |

### Examples

```cpp
// distributematchandUsage
AscendC::LocalTensor<half> srcLocal = inQueue.AllocTensor<half>();
AscendC::DataCopy(srcLocal, srcGlobal, 512);
inQueue.EnQue(srcLocal);

// unitelementvisitask
srcLocal.SetValue(0, 1.0f);
auto val = srcLocal.GetValue(0);

// partialmoveoperatework
AscendC::LocalTensor<half> offsetTensor = srcLocal[16];

// typetypeconvertexchange
AscendC::LocalTensor<int16_t> castTensor = srcLocal.ReinterpretCast<int16_t>();
```

---

## two, GlobalTensor

**Purpose**: StoreGlobal MemoryGlobalData. 

### CoreInterface

| Interface | functionability | Examples |
|------|------|------|
| `SetGlobalBuffer(buffer, size)` | Setslowconflictregion | `gm.SetGlobalBuffer((__gm__ half*)ptr, 1024)` |
| `SetGlobalBuffer(buffer)` | Setslowconflictregion (nosize)  | `gm.SetGlobalBuffer((__gm__ half*)ptr)` |
| `GetPhyAddr()` | obtaingetregionaddress | `const __gm__ T* addr = gm.GetPhyAddr()` |
| `GetValue(offset)` | obtaingetunitelementvalue | `auto val = gm.GetValue(0)` |
| `SetValue(offset, value)` | Setunitelementvalue | `gm.SetValue(0, 1.0f)` |
| `operator()(offset)` | obtaingetunitelementleaduse | `gm(0) = 1.0f` |
| `operator[](offset)` | partialmoveobtaingetnewTensor | `gm[256]` |
| `GetSize()` | obtaingetunitelementcountnumber | `uint64_t size = gm.GetSize()` |
| `SetShapeInfo(shapeInfo)` | Setshapestatusinformationinformation | `gm.SetShapeInfo(...)` |
| `GetShapeInfo()` | obtaingetshapestatusinformationinformation | `ShapeInfo info = gm.GetShapeInfo()` |
| `SetL2CacheHint(mode)` | SetL2slowkeepliftshow | `gm.SetL2CacheHint<CacheRwMode::RW>(mode)` |

### Examples

```cpp
AscendC::GlobalTensor<half> srcGlobal;
srcGlobal.SetGlobalBuffer((__gm__ half*)srcGm, dataSize);

// Read
auto val = srcGlobal.GetValue(0);

// partialmovevisitask
AscendC::GlobalTensor<half> offsetGlobal = srcGlobal[128];

// DataCopy
AscendC::DataCopy(srcLocal, srcGlobal, dataSize);
```

---

## three, Layout

**Purpose**: DescriptionmultipledimensionexpandamountMemoryarrangelocal, PackagecontainShapeandStride. 

### reasontype

```cpp
template <typename ShapeType, typename StrideType>
struct Layout {
    __aicore__ inline constexpr Layout(const ShapeType& shape = {}, const StrideType& stride = {});
    __aicore__ inline constexpr decltype(auto) GetShape();
    __aicore__ inline constexpr decltype(auto) GetStride();
    template <typename CoordType>
    __aicore__ inline constexpr auto operator()(const CoordType& coord) const;
};
```

### structurecreateMethod

```cpp
#include "kernel_operator_layout.h"

// Shapestructurecreate
auto shape = AscendC::MakeShape(4, 2);  // 4travel2column

// Stridestructurecreate
auto stride = AscendC::MakeStride(4, 1);  // travelsteplength4, columnsteplength1

// Layoutstructurecreate
auto layout = AscendC::MakeLayout(shape, stride);

// throughexceedsitstandardCalculationMemorysearchlead
auto coord = AscendC::MakeCoord(1, 0);  // chapter1travelchapter0column
auto idx = layout(coord);  // Calculationobtaintoregionaddresssearchlead
```

### Examples: 4travel2columnrulematrix

| regionaddress | 0 | 1 | 2,3 | 4 | 5 | 6,7 | 8 | 9 |
|------|---|---|-----|---|---|------|---|---|
| unitelement | a00 | a01 | - | a10 | a11 | - | a20 | a21 |

Shape: (4, 2), Stride: (4, 1)

---

## four, Coordinate

**Purpose**: tableshowexpandamountmultipledimensionsitstandard, matchmatchLayoutUsageCalculationMemorysearchlead. 

### reasontype

```cpp
template <typename... Coords>
using Coord = Std::tuple<Coords...>;
```

### Interface

```cpp
// structurecreatesitstandard
auto coord = AscendC::MakeCoord(row, col);

// sitstandardconvertMemorysearchlead
template <typename CoordType, typename ShapeType, typename StrideType>
__aicore__ inline constexpr auto Crd2Idx(const CoordType& coord,
                                         const Layout<ShapeType, StrideType>& layout);
```

### Examples

```cpp
auto shape = AscendC::MakeShape(4, 2);
auto stride = AscendC::MakeStride(4, 1);
auto layout = AscendC::MakeLayout(shape, stride);

auto coord = AscendC::MakeCoord(1, 0);  // row=1, col=0
auto idx = AscendC::Crd2Idx(coord, layout);  // idx = 4
```

---

## five, TensorTrait

**Purpose**: DescriptionTensorofcompleteadjustinformationinformation (Datatypetype, Logical Location, Layout) , Used forCompileperiodOptimization. 

### reasontype

```cpp
template <typename T, TPosition pos = TPosition::GM,
          typename LayoutType = Layout<Shape<>, Stride<>>>
struct TensorTrait {
    using LiteType = T;
    using LiteLayoutType = LayoutType;
    static constexpr const TPosition tPos = pos;

    __aicore__ inline LayoutType& GetLayout();
    __aicore__ inline void SetLayout(const LayoutType& t);
};
```

### structurecreateMethod

```cpp
#include "kernel_operator_tensor_trait.h"

auto shape = AscendC::MakeShape(16, 16, 16);
auto stride = AscendC::MakeStride(0, 0, 0);
auto layout = AscendC::MakeLayout(shape, stride);

// structurecreateTensorTrait
auto tensorTrait = AscendC::MakeTensorTrait<float, AscendC::TPosition::VECIN>(layout);

// UsageTensorTraittypetypestructurecreateLocalTensor
AscendC::LocalTensor<decltype(tensorTrait)> tensor(addr);
```

### SupportofDatatypetype

`int4b_t`, `uint8_t`, `int8_t`, `int16_t`, `uint16_t`, `bfloat16_t`, `int32_t`, `uint32_t`, `int64_t`, `uint64_t`, `float`, `half`

### Constraints

- sameoneInterfacenotSupportsametimeoutputinputTensorTraittypetypeandnonTensorTraittypetypeofTensor
- TensorTraittypetypeofTensorDoes Not IncludeShapeInfoinformationinformation
- DataCopycutsliceInterfacenotSupportTensorTraittypetype

---

## TPosition Logical Location

| bitplace | Description |
|------|------|
| VECIN | directionamountCalculationoutputinput |
| VECOUT | directionamountCalculationOutput |
| VECCALC | directionamountCalculationmiddlebetweenResult |
| A1 | rulematrixCalculationArulematrixoutputinputL1 |
| A2 | rulematrixCalculationArulematrixL0A |
| B1 | rulematrixCalculationBrulematrixoutputinputL1 |
| B2 | rulematrixCalculationBrulematrixL0B |
| CO1 | rulematrixCalculationOutputL0C |
| CO2 | rulematrixCalculationOutputUB |
| GM | GlobalMemory |
