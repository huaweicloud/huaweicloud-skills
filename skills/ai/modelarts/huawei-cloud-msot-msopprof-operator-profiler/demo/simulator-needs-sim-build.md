# Experience: Some Projects Require Simulator-Compatible Build

> This is an **experience case**, not a prerequisite for using `msprof op
> simulator`. The conclusion should be stated as: **Some projects / template
> libraries / build links require separate "simulator-compatible" executables
> for simulation scenarios**, not simply "all simulations need sim build".

## Symptoms

When using an existing executable to launch simulation, you may see errors like:

```text
terminate called after throwing an instance of 'std::__ios_failure'
  what():  basic_filebuf::xsgetn error reading the file: Bad address
[WARN]  Child process killed by signal 6
```

## Why This Is Not an Absolute Rule

Official documentation provides two types of information:

1. **Some projects explicitly require simulator build**
   - E.g., catkins/template library scenarios require `--simulator` in build
2. **Some official examples state the same executable runs on both device and
   simulator**

This means "whether simulator build is required" depends on the project's build
configuration, not a rigid rule of msOpProf.

Therefore, when encountering this error, the correct root cause statement is:

> The executable being launched may **not be a simulator-compatible build**, or
> is missing simulator-specific build options or dependencies.

## Common Root Causes

Typical scenarios:

- Project separates device/simulator build outputs
- Template library or scripts require explicit `--simulator`
- Executable defaults to device runtime only
- Simulator requires specific libraries, architecture params, or linking that
  differ from device build

## Recommended Troubleshooting Sequence

### 1. Check Project Documentation or Build Scripts

Look for indicators like:

- `--simulator`
- `sim`
- `*_sim`
- Separate simulator target/profile
- Architecture or run mode parameters

### 2. Check Simulator Environment

Verify:

```bash
export LD_LIBRARY_PATH=${INSTALL_DIR}/tools/simulator/Ascendxxxyy/lib:$LD_LIBRARY_PATH
```

Where `Ascendxxxyy` matches your actual simulator type.

### 3. If Build Supports It, Generate Simulator-Compatible Build

#### Example A: Template Library / catkins Style

```bash
bash scripts/build.sh --simulator 00_basic_matmul
```

#### Example B: Project-Level CMake Option (Example Only)

```bash
cmake -DCMAKE_ASC_RUN_MODE=sim -DCMAKE_ASC_ARCHITECTURES=dav-2201 ..
make -j
```

> Note: These CMake variables are **project-specific examples**, not `msprof op
> simulator` parameters. Support depends on your project.

## Verification Criteria

When the issue is resolved, you should see:

- No more `signal 6` / `Bad address`
- Simulation execution phase proceeds normally
- Output directory contains `dump/` and `simulator/`
- `simulator/` contains per-core subdirectories, `trace.json`,
  `visualize_data.bin`, etc.

## Scenarios Where This Does Not Apply

Do not conclude "requires sim build" when:

1. Using `--config` or `--export` mode (no app launch path involved)
2. Official examples already state the same executable works on both device
   and simulator
3. Root cause is actually:
   - Wrong `LD_LIBRARY_PATH`
   - Missing simulator installation
   - Architecture mismatch
