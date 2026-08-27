# Migration Report Interpretation Guide

Guide for interpreting the Kunpeng DevKit migration assessment report.

## Table of Contents

- [Overview](#overview)
- [Report Structure](#report-structure)
- [Issue Severity Levels](#issue-severity-levels)
- [Issue Categories](#issue-categories)
- [Common Migration Patterns](#common-migration-patterns)
- [Remediation Guide](#remediation-guide)

---

## Overview

The DevKit migration assessment report identifies potential issues when porting source code from x86_64 to ARM64 (Kunpeng) architecture. This guide helps interpret the report findings and understand the recommended remediation actions.

---

## Report Structure

### HTML Report

The HTML report contains:

1. **Summary Dashboard** — Overall migration score, total files, total issues
2. **Issue List** — Detailed list of all detected issues
3. **Category Breakdown** — Issues grouped by category
4. **File Details** — Per-file issue analysis
5. **Recommendations** — Suggested remediation actions

### JSON Report

```json
{
  "scanType": "porting",
  "scanTime": "2024-01-15T10:30:00Z",
  "sourcePath": "/home/user/project",
  "language": "cpp",
  "summary": {
    "totalFiles": 150,
    "scannedFiles": 148,
    "skippedFiles": 2,
    "totalIssues": 23,
    "criticalIssues": 5,
    "majorIssues": 8,
    "minorIssues": 6,
    "infoIssues": 4,
    "compatibilityScore": 72
  },
  "issues": [
    {
      "id": "ASM_001",
      "severity": "critical",
      "category": "inline_assembly",
      "file": "src/cpu_info.c",
      "line": 42,
      "column": 5,
      "code": "__asm__ __volatile__(\"cpuid\" ...)",
      "description": "x86 inline assembly using cpuid instruction",
      "suggestion": "Use getauxval() on ARM64 or parse /proc/cpuinfo",
      "docLink": "https://www.hikunpeng.com/document/detail/..."
    }
  ]
}
```

---

## Issue Severity Levels

| Severity | Color | Description | Action Required |
|----------|-------|-------------|----------------|
| **Critical** | Red | Code will not compile or run on ARM64 | Must fix before migration |
| **Major** | Orange | Code will compile but produce incorrect results | Should fix before migration |
| **Minor** | Yellow | Code may work but with degraded performance | Should fix for optimal performance |
| **Info** | Blue | Informational, no immediate action needed | Review and consider |

---

## Issue Categories

### 1. Inline Assembly (`inline_assembly`)

**Severity:** Critical

**Description:** x86-specific inline assembly code that cannot run on ARM64.

**Common patterns:**
- `__asm__` blocks with x86 instructions (cpuid, rdtsc, etc.)
- `.s` / `.S` assembly source files with x86 syntax
- AT&T or Intel syntax assembly that needs ARM64 equivalent

**Example issues:**

| x86 Code | ARM64 Equivalent |
|----------|-----------------|
| `__asm__ __volatile__("cpuid" ...)` | Use `getauxval()` from `<sys/auxv.h>` |
| `__asm__ __volatile__("rdtsc" ...)` | Use `__builtin_ia32_rdtsc()` or `clock_gettime()` |
| `__asm__ __volatile__("mfence" ...)` | `__asm__ __volatile__("dmb ish" ::: "memory")` |
| `__asm__ __volatile__("pause" ...)` | `__asm__ __volatile__("yield" ::: "memory")` |

### 2. Compiler Intrinsics (`compiler_intrinsics`)

**Severity:** Critical/Major

**Description:** x86-specific compiler intrinsic functions.

**Common patterns:**
- SSE/AVX intrinsics (`_mm_*`, `_mm256_*`)
- x86 built-in functions (`__builtin_ia32_*`)
- MSVC intrinsics (`__cpuid`, `__rdtsc`)

**SSE/AVX → NEON mapping:**

| SSE/AVX Intrinsic | ARM64 NEON Equivalent |
|-------------------|----------------------|
| `_mm_add_ps` | `vaddq_f32` |
| `_mm_mul_ps` | `vmulq_f32` |
| `_mm_set1_ps` | `vdupq_n_f32` |
| `_mm_load_ps` | `vld1q_f32` |
| `_mm_store_ps` | `vst1q_f32` |
| `_mm_cmpgt_ps` | `vcgtq_f32` |
| `_mm_and_ps` | `vandq_f32` |
| `_mm_sqrt_ps` | `vsqrtq_f32` |

### 3. Platform-Specific API (`platform_api`)

**Severity:** Major

**Description:** API calls that are x86-specific or have different behavior on ARM64.

**Common patterns:**
- `__builtin_cpu_supports()` — CPU feature detection
- Direct hardware register access
- Architecture-specific ioctl calls

### 4. Byte Order / Endianness (`byte_order`)

**Severity:** Minor/Info

**Description:** Code that assumes a specific byte order.

**Note:** Kunpeng (ARM64) supports little-endian mode, which is the same as x86_64. This is typically not a blocking issue, but code should be verified for correctness.

**Common patterns:**
- `htonl()`, `ntohl()` usage — Verify correct behavior
- Direct byte manipulation — Verify endianness assumptions
- `#ifdef __BIG_ENDIAN__` — Check conditional compilation

### 5. Data Type Issues (`data_type`)

**Severity:** Major/Minor

**Description:** Code that makes assumptions about data type sizes.

**Common patterns:**
- `int` used for pointer arithmetic (should use `intptr_t`/`uintptr_t`)
- `long` size assumptions (4 bytes on x86_64 Windows, 8 bytes on Linux/ARM64)
- Structure packing differences
- `size_t` vs `unsigned int` confusion

### 6. Build Configuration (`build_config`)

**Severity:** Minor

**Description:** Build system configuration that is x86-specific.

**Common patterns:**
- `-march=native` or `-march=x86-64` compiler flags
- `-msse*`, `-mavx*` compiler flags
- Architecture-specific Makefile conditions
- CMake architecture checks

**Remediation:**
```makefile
# Before
CFLAGS = -march=native -msse4.2

# After
CFLAGS = -march=armv8-a+crc+crypto  # For ARM64
# Or use architecture-agnostic flags
CFLAGS = -O2 -Wall
```

### 7. Third-Party Dependencies (`third_party`)

**Severity:** Critical/Major

**Description:** Dependencies that may not have ARM64 builds.

**Common patterns:**
- Pre-built x86-only libraries (`.so`, `.a` files)
- npm/pip packages with native extensions
- Docker images based on x86

**Remediation:**
1. Check if the dependency has an ARM64 build
2. Build from source on ARM64
3. Find an ARM64-compatible alternative

### 8. JNI Native Code (`jni_native`)

**Severity:** Critical

**Description:** Java Native Interface (JNI) code with x86-specific implementations.

**Remediation:**
1. Rewrite JNI code for ARM64
2. Use pure Java alternatives where possible
3. Use JNA (Java Native Access) for simpler native calls

### 9. Python C Extensions (`python_cext`)

**Severity:** Critical/Major

**Description:** Python C extensions (Cython, CFFI, pybind11) with x86-specific code.

**Remediation:**
1. Rebuild extensions on ARM64
2. Replace architecture-specific code with portable alternatives
3. Use pure Python alternatives where possible

### 10. Go Assembly (`go_asm`)

**Severity:** Critical

**Description:** Go assembly files (`.s`) with x86-specific instructions.

**Remediation:**
1. Rewrite Go assembly for ARM64
2. Use Go's portable assembly syntax where possible
3. Use pure Go implementations where possible

---

## Common Migration Patterns

### Pattern 1: CPU Feature Detection

**x86:**
```c
#if defined(__x86_64__)
    __asm__ __volatile__("cpuid" : "=a"(a) : "a"(1));
    bool has_sse = (a >> 25) & 1;
#endif
```

**ARM64:**
```c
#if defined(__aarch64__)
    #include <sys/auxv.h>
    unsigned long hwcap = getauxval(AT_HWCAP);
    bool has_crc = (hwcap >> 7) & 1;  // HWCAP_CRC32
#endif
```

### Pattern 2: Memory Barriers

**x86:**
```c
__asm__ __volatile__("mfence" ::: "memory");  // Full barrier
__asm__ __volatile__("sfence" ::: "memory");  // Store barrier
__asm__ __volatile__("lfence" ::: "memory");  // Load barrier
```

**ARM64:**
```c
__asm__ __volatile__("dmb ish" ::: "memory");  // Full barrier
__asm__ __volatile__("dmb ishst" ::: "memory");  // Store barrier
__asm__ __volatile__("dmb ishld" ::: "memory");  // Load barrier
```

### Pattern 3: Spin Wait

**x86:**
```c
__asm__ __volatile__("pause");  // Spin-loop hint
```

**ARM64:**
```c
__asm__ __volatile__("yield");  // Spin-loop hint
```

---

## Remediation Guide

### Priority Order

1. **Critical issues** — Must be fixed; code will not work on ARM64
2. **Major issues** — Should be fixed; code may produce incorrect results
3. **Minor issues** — Should be reviewed; may affect performance
4. **Info issues** — Review for completeness

### General Approach

1. **Start with inline assembly** — This is the most common blocking issue
2. **Then address compiler intrinsics** — Replace SSE/AVX with NEON
3. **Update build configuration** — Remove x86-specific flags
4. **Verify third-party dependencies** — Ensure ARM64 builds are available
5. **Test on ARM64** — Build and run on a Kunpeng system to verify

### Conditional Compilation

Use preprocessor macros to support both architectures:

```c
#if defined(__x86_64__) || defined(_M_X64)
    // x86_64 specific code
#elif defined(__aarch64__) || defined(_M_ARM64)
    // ARM64 specific code
#else
    // Portable fallback
#endif
```
