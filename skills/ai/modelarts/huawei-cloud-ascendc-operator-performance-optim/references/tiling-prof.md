# Phase 1: Tiling Optimization — DetailedReference

## 1.1 Multi-core Tiling

throughexceed `context->SetBlockDim(BLOCK_DIM)` SetOperatorUsageofCore count. 

| Architecture | SetRules |
|---|---|
| couplematchArchitecture (Vector+Cube onebody)  | `blockDim` = `GetCoreNumAiv()` or `GetCoreNumAic()` |
| distributeleaveArchitecture — pure Vector Operator | `blockDim` = AIV Core count (if 40)  |
| distributeleaveArchitecture — pure Cube Operator | `blockDim` = AIC Core count (if 20)  |
| distributeleaveArchitecture — MIX (V+C) Operator | `blockDim` = objectmanagecoregroupnumber (if 20 = 40 AIV / 2) , **notcanexceedexceedobjectmanageCore count** |

`blockDim` aslogiclogiccoregeneralmiss, getvaluerangescope [1, 65535]. asfilldistributeutilizeuseHardwareResource, onegeneralsetas
objectmanageCore countorotheradjustnumbertimes. AIC/AIV Core countdistributecategorythroughexceed `GetCoreNumAic()` and `GetCoreNumAiv()`
obtainget. 

## 1.2 L2Cache Tiling

when `outputinputDataamount + OutputDataamount > L2Cache contentamount` (if 192 MB) time, willDataaccording to L2Cache
largesmalletcdistributeasmultipleblock, allhavecorecoordinatesamehandlemanagesameoneblockafteragaincutexchangeunderoneblock. thissampleweightcomplexReadtimecancommandmiddle
L2Cache (~7 TB/s) , avoidavoidfrequencycomplexvisitask HBM (~1.6 TB/s) . 

**reverseexample** — notuseability L2Cache Tiling, eachcountcoreoftwocount tile mutualmutualcrowdoccupy L2Cache: 

```cpp
constexpr int32_t TOTAL_LENGTH = 384 * 1024 * 1024 / sizeof(half);
constexpr int32_t USE_CORE_NUM = 20;
constexpr int32_t TILE_NUM = 2;
constexpr int32_t BLOCK_LENGTH = TOTAL_LENGTH / USE_CORE_NUM;
constexpr int32_t TILE_LENGTH = BLOCK_LENGTH / TILE_NUM;

class KernelSample {
public:
    __aicore__ inline void Init(GM_ADDR x) {
        xGm.SetGlobalBuffer((__gm__ half*)x + BLOCK_LENGTH * GetBlockIdx(), BLOCK_LENGTH);
        pipe.InitBuffer(inQueueX, 1, BLOCK_LENGTH * sizeof(half));
    }
    __aicore__ inline void Process() {
        constexpr int32_t loopCount = 2;
        for (int32_t i = 0; i < loopCount; i++) {
            for (int32_t j = 0; j < TILE_NUM; j++) {
                CopyIn(j);    // eachcountcorereadtwocount tile, L2Cache bereversecomplexwasheliminate
                Compute();
                CopyOut(j);
            }
        }
    }
};
```

**positiveexample** — useability L2Cache Tiling, externallayerloopringaccording to L2Cache distributeblock, allhavecorecoordinatesamehandlemanage: 

```cpp
constexpr int32_t TOTAL_LENGTH = 384 * 1024 * 1024 / sizeof(half);
constexpr int32_t TILE_NUM = 2;
constexpr int32_t USE_CORE_NUM = 20;
constexpr int32_t TILE_LENGTH = TOTAL_LENGTH / TILE_NUM;
constexpr int32_t BLOCK_LENGTH = TILE_LENGTH / USE_CORE_NUM;

class KernelSample {
public:
    __aicore__ inline void Init(GM_ADDR x, GM_ADDR y, int32_t index) {
        xGm.SetGlobalBuffer(
            (__gm__ half*)x + BLOCK_LENGTH * GetBlockIdx() + index * TILE_LENGTH,
            BLOCK_LENGTH);
    }
    __aicore__ inline void Process() {
        constexpr int32_t loopCount = 2;
        for (int32_t i = 0; i < loopCount; i++) {
            CopyIn();       // eachcountcoreonlyreadselfselfofcutslice, chaptertwotimereadcommandmiddle L2Cache
            Compute();
            CopyOut();
        }
    }
};

extern "C" __global__ __aicore__ void simple_kernel(
    __gm__ uint8_t* srcGm, __gm__ uint8_t* dstGm)
{
    AscendC::KernelAdd op;
    for (int32_t i = 0; i < TILE_NUM; i++) {
        op.Init(srcGm, dstGm, i);
        op.Process();
    }
}
```

## 1.3 corebetweennegativeloadaveragebalance

L2Cache Tilingafter, ifeachtimeCalculationallneedblocknumbernotabilitybeCore countadjustdivide, rulepartdistributecoreablemultipledistributematchtailblock. 

**askproblem**: core 1–5 eachtime pass multiplecomputeonecountblock, beginfinalmostaftercompleted, core 6–20 emptyetc. 

**solveresolveMethod**: innotsame pass betweenexchangesubstitutedistributematchtailblock. exampleif 2 count pass × 25 block / 20 core, 
pass 1 oftailblockdistributematchgivecore 1–5, pass 2 oftailblockdistributematchgivecore 6–10, Globalcomeseecore 1–10
eachcompute 3 block, core 11–20 eachcompute 2 block, reachtoGlobalnegativeloadaveragebalance. 
