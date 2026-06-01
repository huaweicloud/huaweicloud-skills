# Test Scenarios: terraform-installer

## Scenario 1: Check Installation Status

**Input:**
```bash
python scripts/install_terraform.py --check
```

**Expected Output:**
```
[INFO] Checking Terraform installation status...
[INFO] Terraform version: 1.15.2
[INFO] HuaweiCloud Provider: 1.81.0
```

**Validation:**
- Correctly detect installed/not installed
- Show version information if installed

---

## Scenario 2: Install on Linux (Auto-detect)

**Input:**
```bash
python scripts/install_terraform.py
```

**Expected Output:**
```
[INFO] Platform: Linux (Ubuntu/Debian)
[INFO] Installing Terraform via APT...
[INFO] Terraform installed successfully
[INFO] Installing HuaweiCloud Provider...
[INFO] Provider installed successfully
```

**Validation:**
- `terraform version` command succeeds
- Provider available in cache

---

## Scenario 3: Install on Windows (Binary)

**Input:**
```bash
python scripts/install_terraform.py
```

**Expected Output:**
```
[INFO] Platform: Windows
[INFO] Downloading Terraform binary...
[INFO] Extracting to C:\Program Files\terraform...
[INFO] Configuring PATH...
[INFO] Terraform installed successfully
```

**Validation:**
- PATH configured correctly
- `terraform version` succeeds in new terminal

---

## Scenario 4: Specify Version

**Input:**
```bash
python scripts/install_terraform.py --version 1.5.0
```

**Expected Output:**
```
[INFO] Installing Terraform 1.5.0...
[INFO] Terraform 1.5.0 installed successfully
```

**Validation:**
- `terraform version` shows 1.5.0

---

## Scenario 5: Install with Init

**Input:**
```bash
python scripts/install_terraform.py --init
```

**Expected Output:**
```
[INFO] Installing Terraform...
[INFO] Running terraform init...
[INFO] Initialization complete
```

**Validation:**
- `.terraform` directory created
- Provider downloaded

---

## Scenario 6: Uninstall

**Input:**
```bash
python scripts/install_terraform.py --uninstall
```

**Expected Output:**
```
[INFO] Uninstalling Terraform...
[INFO] Terraform removed successfully
```

**Validation:**
- `terraform` command not found
- Installation directory removed

---

## Scenario 7: Format Validation

**Input:**

```bash
skillcheck SKILL.md
markdownlint-cli2 SKILL.md
skill-scanner scan .
```

**Expected Output:**

```text
skillcheck: PASS (0 errors)
markdownlint-cli2: 0 error(s)
skill-scanner: PASS (only expected findings)
```

**Validation:**

- skillcheck passes with no errors
- markdownlint-cli2 reports 0 errors
- skill-scanner findings are expected (network requests for Terraform download)
