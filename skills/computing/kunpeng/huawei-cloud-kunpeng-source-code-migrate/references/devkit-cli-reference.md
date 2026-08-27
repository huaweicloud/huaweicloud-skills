# DevKit CLI Command Reference

Complete reference for Kunpeng DevKit CLI commands used in source code migration assessment.

## Table of Contents

- [Overview](#overview)
- [Global Commands](#global-commands)
- [Porting Command](#porting-command)
- [Source Migration Command (src-mig)](#source-migration-command-src-mig)
- [Output Formats](#output-formats)
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)

---

## Overview

Kunpeng DevKit CLI (`devkit`) is a command-line tool for analyzing source code migrability to the Kunpeng (ARM64) platform. It supports multiple sub-commands for different analysis tasks.

**Official documentation:** https://www.hikunpeng.com/document/detail/zh/kunpengdevps/portingadvisor/demo/smartdenovoptCli_21_0001.html

**⚠️ Important:** The `devkit` binary must be run from its installation directory (e.g., `cd /usr/local/devkit && ./devkit`), or the directory must be in PATH.

---

## Global Commands

### Version

```bash
cd /usr/local/devkit && ./devkit --version
```

**Output:**
```
devkit version 25.3.0
```

### Help

```bash
cd /usr/local/devkit && ./devkit --help
```

**Output:**
```
Usage: devkit [-h | --help] [-v | --version] COMMAND [ARGS]

 The most commonly used devkit sub commands are:
   help      Get help information
   version   Get version information
   porting   Run a command for porting
   sys-mig   Run a command for sys-mig
   advisor   Run a command for advisor
```

---

## Porting Command

The `porting` command is the parent command for migration-related tasks.

### Syntax

```bash
devkit porting --help
```

**Output:**
```
Usage: devkit porting [-h|--help] TASK [ARGS]

The most commonly used devkit porting sub tasks are:
    src-mig        Run the source migration task.
    pkg-mig        Run the package migration task.
```

---

## Source Migration Command (src-mig)

The `devkit porting src-mig` command is the primary command for source code migration analysis.

### Syntax

```bash
devkit porting src-mig -i <input_path> -o <output_path> -s <source_types> [options]
```

### Required Parameters

| Parameter | Long Form | Description | Example |
|-----------|-----------|-------------|---------|
| `-i` | `--input` | Source code directory path | `/home/user/project` |
| `-o` | `--output` | Output directory for report (must exist) | `/tmp/devkit-report` |
| `-s` | `--source-type` | Source language(s), comma-separated | `'c, c++, asm'` |

### Optional Parameters

| Parameter | Long Form | Description | Default | Example |
|-----------|-----------|-------------|---------|---------|
| `-c` | `--cmd` | Build/compiling command line | None | `'make all'` |
| `-b` | `--build-tool` | Build tool | None | `make`, `cmake`, `automake`, `go`, `bazel`, `blade` |
| `-p` | `--compiler` | Compiler version | None | `gcc9.3.0` |
| `-f` | `--fortran-compiler` | Fortran compiler version | None | `gfortran9` |
| `-t` | `--target-os` | Target OS | Auto-detect | `openEuler22.03` |
| `-r` | `--report-type` | Report format | `all` | `all`, `json`, `html`, `csv` |
| `-l` | `--log-level` | Log level | `1` (INFO) | `0`(DEBUG), `1`(INFO), `2`(WARN), `3`(ERROR) |
| `-np` | `--number-of-progress` | Concurrent processes | `1` | `4` |
| `--set-timeout` | - | Task timeout in minutes | None | `30` |
| `--ignore` | - | Ignore rules config file | Built-in | `/path/to/ignore_rules.json` |
| `--macro` | - | Custom x86 macros (semicolon-separated) | None | |
| `--keep-going` | - | Continue scanning with arm/arm64/aarch64 keywords | `False` | `True` |
| `--ignore-path` | - | Source paths to ignore | None | `/path/to/exclude` |
| `--kp-compatibility` | - | Kunpeng cross-generation compatibility check | Off | (flag) |

### Source Type Values (-s)

| Language | `-s` Value |
|----------|-----------|
| C | `c` |
| C++ | `c++` |
| Assembly | `asm` |
| Fortran | `fortran` |
| Go | `go` |
| Java | `java` |
| Python | `python` |
| Scala | `scala` |

Multiple languages: `-s 'c, c++, asm'`

### Compiler Version Values (-p)

| Compiler | Versions |
|----------|----------|
| GCC | `gcc4.8.5`, `gcc4.9.3`, `gcc5.1.0`-`gcc5.5.0`, `gcc6.1.0`-`! gcc6.5.0`, `gcc7.1.0`-`gcc7.4.0`, `gcc8.1.0`-`gcc8.3.0`, `gcc9.1.0`-`gcc9.3.0`, `gcc10.1.0`-`gcc10.3.1`, `gcc12.3.0` |
| BiSheng | `bisheng compiler2.1.0`, `bisheng compiler2.3.0`-`bisheng compiler2.5.0.1`, `bisheng compiler3.0.0`-`bisheng compiler3.2.0`, `bisheng compiler4.0.0`-`bisheng compiler4.2.0` |
| GCC for openEuler | `gcc for openeuler2.3.7`, `gcc for openeuler2.3.8`, `gcc for openeuler3.0.1`-`gcc for openeuler3.0.3` |

### Examples

**Scan C/C++ project with make build:**
```bash
devkit porting src-mig -i /home/project -s 'c, c++, asm' -b make -c 'make all' -p gcc9.3.0 -o /tmp/report -r all
```

**Scan Java/Python project (interpreted, no build command):**
```bash
devkit porting src-mig -i /home/project -s 'java, python' -o /tmp/report -r all
```

**Scan Fortran project:**
```bash
devkit porting src-mig -i /home/project -s 'fortran' -b make -c 'make all' -f gfortran9 -o /tmp/report -r all
```

**Scan Go project:**
```bash
devkit porting src-mig -i /home/project -s 'go' -b go -c 'go build' -o /tmp/report -r all
```

**Scan C/C++ project built by bazel:**
```bash
devkit porting src-mig -i /home/project -s 'c, c++, asm' -b bazel -p gcc9.3.0 -o /tmp/report -r all
```

---

## Output Formats

The `-r` / `--report-type` parameter controls the output format:

| Value | Description | Output Files |
|-------|-------------|-------------|
| `all` | Generate all formats (default) | `.json`, `.csv`, `.html`, `_file_list.txt` |
| `json` | JSON format only | `_zh.json`, `_en.json` |
| `html` | HTML format only | `.html` |
| `csv` | CSV format only | `_zh.csv`, `_en.csv` |

**Report file naming:**

```
Code_Porting_<timestamp>_<random_id>_<lang>.<ext>
```

Example:
```
Code_Porting_20260802132314_mKC78j_zh.json
Code_Porting_20260802132314_mKC78j_en.json
Code_Porting_20260802132314_mKC78j_zh.csv
Code_Porting_20260802132314_mKC78j_en.csv
Code_Porting_20260802132314_mKC78j.html
Code_Porting_20260802132314_mKC78j_file_list.txt
```

---

## Environment Variables

DevKit CLI respects the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEVKIT_HOME` | DevKit installation directory | `/usr/local/devkit` |
| `DEVKIT_LOG_LEVEL` | Log level (DEBUG, INFO, WARN,!  ERROR) | `INFO` |
| `DEVKIT_THREADS` | Number of analysis threads | CPU count |

---

## Exit Codes

| Exit Code | Description |
|-----------|-------------|
| `0` | Scan completed successfully |
| `1` | General error |
| `2` | Invalid command or parameters |
| `22` | execvp failed (usually .devkit binary missing) |

---

## Scan Workflow Summary

```
1. Parse command parameters
2. Validate input directory exists and is readable
3. Validate output directory exists and is writable
4. Detect source code language (if not specified)
5. Initialize scan engine
6. Walk directory tree and identify source files
7. For each source file:
   a. Parse file content
   b. Apply language-specific analysis rules
   c. Detect migration issues
   d. Classify issues by severity and category
8. Aggregate results
9. Generate report in specified format(s)
10. Write report to output directory
11. Return exit code
```
