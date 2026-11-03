# Verification Method

How to verify that a training project follows the weight save layout and
that `references/loader.py` resolves it correctly. Everything runs locally;
no cloud resources are created.

## 1. Verify the loader against a sample layout

Run from this skill's directory. The script builds a throwaway
`{output_root}` in a temporary directory, then checks the three loader
functions. The layout checks need only the Python standard library. The
weight-loading check runs only when `torch` is installed.

```bash
python3 - <<'EOF'
import importlib.util, os, sys, tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("loader", "references/loader.py")
loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "output_root"
    for step in (1000, 2000):
        d = root / "_ckpt" / f"checkpoint_{step}"
        d.mkdir(parents=True)
        (d / "model.pt").write_bytes(b"")
    (root / "_ckpt" / "checkpoint_3000").mkdir()   # empty dir: must be ignored
    (root / "model.pt").write_bytes(b"")           # final-step content at the root

    assert loader.locate_output_root(root / "model.pt") == root
    assert loader.locate_output_root(root / "_ckpt/checkpoint_1000/model.pt") == root
    assert loader.locate_output_root(Path(tmp) / "elsewhere.pt") is None
    assert loader.find_latest_checkpoint(root / "_ckpt") == (2000, root / "_ckpt/checkpoint_2000")
    assert loader.find_latest_checkpoint(root / "missing") == (0, Path(""))
    print("layout checks: OK")

    try:
        import torch
    except ImportError:
        print("load_state_dict: skipped (torch not installed)")
        sys.exit(0)
    w = root / "_ckpt/checkpoint_2000/model.pt"
    torch.save({"layer.weight": torch.ones(2, 2)}, w)
    sd = loader.load_state_dict(w)                 # weights_only=True
    assert torch.equal(sd["layer.weight"], torch.ones(2, 2))
    print("load_state_dict: OK")
EOF
```

Expected output: `layout checks: OK`, then `load_state_dict: OK` (or
`skipped` without torch).

## 2. Verify a real training output

After a short training run with periodic saving enabled, inspect
`{output_root}` (the directory configured in the training script):

| Check | Expected |
|---|---|
| `_ckpt/` exists | created at training start, before the first checkpoint |
| Periodic checkpoints | `_ckpt/checkpoint_<step>/` per save, each non-empty |
| Final-step content | directly under `{output_root}/`, with no `final_model/` subdirectory |
| File names | unchanged from what the framework writes (no renaming) |
| Resume | `find_latest_checkpoint("<output_root>/_ckpt")` returns the largest saved step |

## 3. Security check

`load_state_dict()` loads `.pt` files with `torch.load(..., weights_only=True)`
(torch>=1.13), so a checkpoint cannot run code when it is loaded. Keep this
flag when copying the loader into a project. Prefer `.safetensors` where the
framework supports it.
