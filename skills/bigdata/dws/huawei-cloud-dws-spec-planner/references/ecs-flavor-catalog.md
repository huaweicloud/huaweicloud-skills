# DWS Dedicated Flavor Catalog

> This document is extracted from SKILL.md Phase 4. Source: Huawei Cloud official documentation "Data Warehouse Specifications" dws_01_00018.html
> (Updated 2026-07-31).

## 1. Hard Constraints

| Constraint | Requirement | Description |
|-------|------|------|
| Production environment minimum per node | ≥ 16 vCPU and ≥ 64 GB | Official statement: "16GB, vCPU 4 cores and below are not recommended for production" |
| Migration scenario total cores | ≥ 96 vCPU | If not met, increase to guarantee production SLA |
| DWS flavor naming feature | **Non-general-purpose ECS** | Prefixes dwsx2 / dwsk2 / dwsx3 / dwsk3 / dwsax3 etc. |
| Output plan | **Single plan** (minimum spec) | From v2.0.0 onwards, Plan A/B dual plans are no longer output |

## 2. Flavor Family Overview

| Family prefix | CPU architecture | Product type | Description |
|---------|--------|---------|------|
| `dwsx2.*` | X86 | Storage-compute integrated 1:8 / 1:4 cloud disk flavor | General OLAP/HTAP |
| `dwsk2.*` | ARM (Kunpeng) | Storage-compute integrated 1:8 / 1:4 cloud disk flavor | Kunpeng enhanced edition |
| `dwsx3.*` | X86 | **Storage-compute separated** cloud disk flavor | Storage-compute separated X86 main |
| `dwsk3.*` | ARM (Kunpeng) | **Storage-compute separated** cloud disk flavor | Storage-compute separated Kunpeng main |
| `dwsax3.*` | X86 (AMD) | **Storage-compute separated** cloud disk flavor | Storage-compute separated AMD edition |
| `dws2.olap.*.i3/ki1` | X86/ARM | Storage-compute integrated **local disk** flavor | Fixed local disk capacity |
| `dws3.*.i7/ki1.*DPU` | X86/ARM | Storage-compute separated **local disk** flavor | Fixed local disk capacity |

## 3. Storage-compute Integrated 1:8 Cloud Disk Flavors (Default OLAP, CPU:Memory = 1:8)

> Default usage: new scenario (non-compute-intensive), migration scenario (competitor 1:8)

| Flavor name | CPU architecture | vCPU | Memory (GB) | Per-node storage range | DN count | Applicable scenario |
|--------|--------|------|----------|---------------|--------|---------|
| dwsx2.xlarge.m7 | X86 | 4 | 32 | 20GB~2000GB | 1 | ⚠️ Entry/testing (below production minimum) |
| dwsx2.xlarge.m7n | X86 | 4 | 32 | 20GB~2000GB | 1 | ⚠️ Entry/testing |
| dwsk2.xlarge.km2 | ARM | 4 | 32 | 20GB~2000GB | 1 | ⚠️ Entry/testing |
| **dwsx2.2xlarge.m7** | X86 | 8 | 64 | 100GB~4000GB | 1 | ⚠️ Near production minimum (8 cores not recommended) |
| **dwsx2.2xlarge.m7n** | X86 | 8 | 64 | 100GB~4000GB | 1 | ⚠️ Near production minimum (8 cores not recommended) |
| dwsk2.2xlarge.km2 | ARM | 8 | 64 | 100GB~4000GB | 1 | ⚠️ Near production minimum (8 cores not recommended) |
| **dwsx2.4xlarge.m7** | X86 | **16** | **128** | 100GB~8000GB | 1 | ✅ **Production minimum spec (1:8 baseline minimum)** |
| **dwsx2.4xlarge.m7n** | X86 | 16 | 128 | 100GB~8000GB | 1 | ✅ Production minimum spec (m7n bandwidth upgrade) |
| dwsk2.4xlarge.km2 | ARM | 16 | 128 | 100GB~8000GB | 1 | ✅ |
| **dwsx2.8xlarge.m7** | X86 | **32** | **256** | 100GB~16000GB | 2 | ⭐ 32-core mainstream tier |
| **dwsx2.8xlarge.m7n** | X86 | 32 | 256 | 100GB~16000GB | 2 | ⭐ 32-core mainstream tier (bandwidth upgrade, commonly used) |
| dwsk2.8xlarge.km2 | ARM | 32 | 256 | 100GB~16000GB | 2 | ⭐ |
| dwsk2.12xlarge | ARM | 48 | 384 | 100GB~24000GB | 4 | Large spec middle tier |
| **dwsx2.16xlarge.m7** | X86 | **64** | **512** | 100GB~32000GB | 4 | ⭐ Large spec tier |
| **dwsx2.16xlarge.m7n** | X86 | 64 | 512 | 100GB~32000GB | 4 | ⭐ Large spec tier (bandwidth upgrade) |
| dwsk2.16xlarge | ARM | 64 | 512 | 100GB~32000GB | 4 | ⭐ |
| dwsx2.24xlarge.m7 | X86 | 96 | 768 | 100GB~48000GB | 4 | Ultra-large scale |
| dwsx2.32xlarge.m7 | X86 | 128 | 1024 | 100GB~48000GB | 4 | Ultra-large scale |

## 4. Storage-compute Integrated 1:4 Cloud Disk Flavors (HTAP Mixed Workload, CPU:Memory = 1:4)

> Default usage: new scenario (compute-intensive + HTAP), migration scenario (competitor 1:4)

| Flavor name | CPU architecture | vCPU | Memory (GB) | Per-node storage range | DN count | Applicable scenario |
|--------|--------|------|----------|---------------|--------|---------|
| dwsx2.h.xlarge.4.c7n | X86 | 4 | 16 | 20GB~2000GB | 1 | ⚠️ Entry/testing |
| dwsk2.h.xlarge.4.kc1 | ARM | 4 | 16 | 20GB~2000GB | 1 | ⚠️ |
| dwsx2.h.2xlarge.4.c7n | X86 | 8 | 32 | 100GB~4000GB | 1 | ⚠️ |
| dwsk2.h.2xlarge.4.kc1 | ARM | 8 | 32 | 100GB~4000GB | 1 | ⚠️ |
| **dwsx2.h.4xlarge.4.c7n** | X86 | **16** | **64** | 100GB~8000GB | 1 | ✅ **1:4 production minimum spec** |
| dwsk2.h.4xlarge.4.kc1 | ARM | 16 | 64 | 100GB~8000GB | 1 | ✅ |
| **dwsx2.h.8xlarge.4.c7n** | X86 | **32** | **128** | 100GB~16000GB | 2 | ⭐ 1:4 32-core mainstream tier |
| dwsk2.h.8xlarge.4.kc1 | ARM | 32 | 128 | 100GB~16000GB | 2 | ⭐ |
| dwsk2.h.12xlarge.4.kc1 | ARM | 48 | 192 | 100GB~24000GB | 4 | |
| **dwsx2.h.16xlarge.4.c7n** | X86 | **64** | **256** | 100GB~32000GB | 4 | ⭐ 1:4 large spec tier |
| dwsk2.h.16xlarge | ARM | 64 | 256 | 100GB~32000GB | 4 | ⭐ |
| dwsk2.h.24xlarge | ARM | 96 | 384 | 100GB~48000GB | 4 | |
| dwsk2.h.32xlarge | ARM | 128 | 512 | 100GB~64000GB | 4 | |

## 5. Storage-compute Separated Cloud Disk Flavors (Prefix dwsx3 / dwsk3 / dwsax3)

> Official note: When creating a storage-compute separated cluster, the console only displays the latter half (e.g., 16U64G.16DPU); the prefix dwsx3/dwsk3/dwsax3 represents the CPU architecture.

### 5.1 Storage-compute Separated 1:4 Balanced Flavors (CPU:Memory = 1:4)
> Applicable to storage-compute separated non-compute-intensive scenarios.

| Flavor name | CPU architecture | vCPU | Memory (GB) | Per-node storage range | DN count | Note |
|--------|--------|------|----------|---------------|--------|------|
| dwsx3.4U16G.4DPU | X86 | 4 | 16 | 20GB~2000GB | 1 | ⚠️ Entry |
| dwsk3.4U16G.4DPU | ARM | 4 | 16 | 20GB~2000GB | 1 | ⚠️ |
| dwsx3.8U32G.8DPU | X86 | 8 | 32 | 100GB~4000GB | 1 | ⚠️ |
| dwsk3.8U32G.8DPU | ARM | 8 | 32 | 100GB~4000GB | 1 | ⚠️ |
| **dwsx3.16U64G.16DPU** | X86 | **16** | **64** | 100GB~8000GB | 1 | ✅ 1:4 storage-compute separated production minimum |
| dwsk3.16U64G.16DPU | ARM | 16 | 64 | 100GB~8000GB | 1 | ✅ |
| **dwsx3.32U128G.32DPU** | X86 | **32** | **128** | 100GB~16000GB | 2 | ⭐ 1:4 storage-compute separated 32-core baseline |
| dwsk3.32U128G.32DPU | ARM | 32 | 128 | 100GB~16000GB | 2 | ⭐ |
| dwsk3.48U192G.48DPU | ARM | 48 | 192 | 200GB~24000GB | 4 | |
| **dwsx3.64U256G.64DPU** | X86 | **64** | **256** | 200GB~32000GB | 4 | ⭐ 1:4 large spec |
| dwsk3.64U256G.64DPU | ARM | 64 | 256 | 100GB~32000GB | 4 | ⭐ |

### 5.2 Storage-compute Separated 1:8 Memory-optimized Flavors (CPU:Memory = 1:8, dwsax3.*U2G.*DPU)
> Applicable to storage-compute separated compute-intensive / memory-optimized scenarios.

| Flavor name | CPU architecture | vCPU | Memory (GB) | Per-node storage range | DN count | Note |
|--------|--------|------|----------|---------------|--------|------|
| dwsax3.4U32G.4DPU | X86 | 4 | 32 | 20GB~2000GB | 1 | ⚠️ |
| dwsax3.8U64G.8DPU | X86 | 8 | 64 | 100GB~4000GB | 1 | ⚠️ |
| **dwsax3.16U128G.16DPU** | X86 | **16** | **128** | 100GB~8000GB | 1 | ✅ 1:8 storage-compute separated production minimum |
| **dwsax3.32U256G.32DPU** | X86 | **32** | **256** | 100GB~16000GB | 2 | ⭐ 1:8 32-core baseline |
| **dwsax3.64U512G.64DPU** | X86 | **64** | **512** | 100GB~32000GB | 4 | ⭐ 1:8 large spec |
| **dwsax3.96U768G.96DPU** | X86 | 96 | 768 | 100GB~48000GB | 4 | |
| **dwsax3.128U1024G.128DPU** | X86 | 128 | 1024 | 100GB~64000GB | 4 | |

## 6. Storage-compute Integrated/Separated Local Disk Flavors (Fixed capacity, disk expansion not supported)

### 6.1 Storage-compute Integrated Local Disk (dws2.olap.*)

| Flavor name | Architecture | vCPU | Memory (GB) | Per-node storage | DN count |
|--------|------|------|----------|-----------|--------|
| dws2.olap.4xlarge.i3 | X86 | 16 | 128 | 1490GB | 1 |
| dws2.olap.4xlarge.ki1 | ARM | 16 | 64 | 2980GB | 1 |
| dws2.olap.8xlarge.i3 | X86 | 32 | 256 | 2980GB | 2 |
| dws2.olap.8xlarge.ki1 | ARM | 32 | 128 | 5960GB | 2 |
| dws2.olap.16xlarge.i3 | X86 | 64 | 512 | 5960GB | 4 |
| dws2.olap.16xlarge.ki1 | ARM | 64 | 228 | 11921GB | 4 |

### 6.2 Storage-compute Separated Local Disk (dws3.*DPU)

| Flavor name | Architecture | vCPU | Memory (GB) | Per-node storage | DN count |
|--------|------|------|----------|-----------|--------|
| dws3.16U128G.i7.16DPU | X86 | 16 | 128 | 2980GB | 1 |
| dws3.16U64G.ki1.16DPU | ARM | 16 | 64 | 5960GB | 1 |
| dws3.32U256G.i7.32DPU | X86 | 32 | 256 | 5960GB | 2 |
| dws3.32U128G.ki1.32DPU | ARM | 32 | 128 | 11920GB | 2 |
| dws3.64U512G.i7.64DPU | X86 | 64 | 512 | 11920GB | 4 |
| dws3.64U228G.ki1.64DPU | ARM | 64 | 228 | 23840GB | 4 |

## 7. Quick Selection Guide (Script Default Mapping)

```python
# Storage-compute integrated 1:8 (OLAP default, non-compute-intensive) → candidates dwsx2.*.m7/m7n series (16~128 cores)
# Storage-compute integrated 1:4 (HTAP / compute-intensive balanced) → candidates dwsx2.h.*.4.c7n (≤64 cores) + dwsk2.h.* (96/128, ARM)
# Storage-compute separated 1:4 → candidates dwsx3.*U*G.*DPU (≤64 cores) + dwsax3.*U*G.*DPU (96/128, AMD)
# Storage-compute separated 1:8 → candidates dwsax3.*U*G.*DPU series
# v2.2.0 single-plan selection: migration target cores = competitor cores (no 96 minimum);
# Generate feasible combinations for each candidate (node count = max(3, ceil(V/vCPU))),
# Take the one with the minimum "node + storage" compute surplus (node spec already includes system disk, no separate system disk item);

# Candidate production vCPU tiers (ascending): 16 / 32 / 64 / 96 / 128
```

> ⚠️ Selection results vary by requirement: small data volume / no index usually makes 32 cores × 3 most economical;
> When storage dominates (e.g., storage-compute separated large cache), larger spec with fewer nodes can be more economical (reduces rounding loss).
> For detailed algorithm and calculations, see [single-plan-algorithm.md](single-plan-algorithm.md).
