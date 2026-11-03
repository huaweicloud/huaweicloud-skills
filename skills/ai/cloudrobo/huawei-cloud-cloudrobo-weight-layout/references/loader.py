"""Framework-agnostic checkpoint loader for the weight save layout spec.

Rules (see SKILL.md):
- Top level ``{output_root}``: all contents of the final-step checkpoint live
  under this root
- ``{output_root}/_ckpt/checkpoint_<N>/``: all contents of periodic checkpoints

This module only **locates** ``{output_root}`` and **selects the latest
checkpoint**; it does not presuppose any specific files (weight file names,
config file names, etc. vary by model).

Copy this file into your project and extend it with model rebuild logic as
needed.
"""

import os
import re
from pathlib import Path


def locate_output_root(weight_path):
    """Walk upward from the weight file and return the ancestor that contains
    the ``_ckpt/`` directory — that is ``{output_root}``.

    Works for every layout supported by the spec:

        <output_root>/<final weight>                                (final-step content)
        <output_root>/_ckpt/checkpoint_<N>/<weight file>            (periodic checkpoint)
        <output_root>/_ckpt/<N>/<weight file>                       (legacy plain-step dir)
        <output_root>/checkpoints/steps_<N>_*.pt                    (legacy flat layout)

    Args:
        weight_path: path to a weight file (any file name).

    Returns:
        Path | None: output_root, or None if it cannot be located.
    """
    current = Path(weight_path).parent
    while True:
        if (current / "_ckpt").is_dir():
            return current
        if current.parent == current:
            return None
        current = current.parent


def find_latest_checkpoint(ckpt_root):
    """Return the (step, checkpoint_dir) of the latest checkpoint.

    Scan ``_ckpt/`` for directory names matching ``checkpoint_<N>`` (also
    compatible with plain ``<N>``), plus legacy flat files ``steps_<N>_*``,
    and pick the largest N. Does not presuppose weight file names — a
    non-empty directory counts as a valid checkpoint.
    """
    ckpt_root = Path(ckpt_root)
    if not ckpt_root.exists():
        return 0, Path("")

    candidates = []  # (step, path)
    for name in os.listdir(ckpt_root):
        path = ckpt_root / name
        if path.is_dir():
            # checkpoint_<N> or plain <N> directory, valid if non-empty
            m = re.match(r"(?:checkpoint_)?(\d+)$", name)
            if m and any(path.iterdir()):
                candidates.append((int(m.group(1)), path))
            continue
        # legacy flat file: steps_<N>_<any weight name>
        m = re.match(r"steps_(\d+)_", name)
        if m and path.is_file():
            candidates.append((int(m.group(1)), path))

    if not candidates:
        return 0, Path("")
    candidates.sort(key=lambda item: item[0])
    return candidates[-1]


def load_state_dict(weight_path):
    """Load a raw state dict from a .pt or .safetensors file (CPU).

    ``.pt`` files are loaded with ``weights_only=True`` (requires
    torch>=1.13): only tensors and plain containers are unpickled, so a
    tampered checkpoint cannot execute code on load. Prefer ``.safetensors``
    when the training code can produce it.
    """
    weight_path = Path(weight_path)
    if weight_path.suffix == ".safetensors":
        from safetensors.torch import load_file

        return load_file(str(weight_path))
    import torch

    return torch.load(weight_path, map_location="cpu", weights_only=True)
