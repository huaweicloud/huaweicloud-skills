#!/usr/bin/env python3
"""Steps3: VerificationWeight Consistency (Slim Version) . """

import argparse
import glob
import os
import sys

import torch


def _load_weights(model_path):
    try:
        from safetensors.torch import load_file

        files = sorted(glob.glob(os.path.join(model_path, "*.safetensors")))
        if files:
            merged = {}
            for file in files:
                merged.update(load_file(file))
            return merged
    except Exception:
        pass

    pt_path = os.path.join(model_path, "pytorch_model.bin")
    if os.path.exists(pt_path):
        return torch.load(pt_path, map_location="cpu", weights_only=True)
    return {}


def _tied_mirror(key):
    """Return the opposite tied-embedding alias for a key, or None if the key
    is not part of a tied lm_head/embed_tokens pair."""
    if key.endswith("lm_head.weight"):
        return key[: -len("lm_head.weight")] + "embed_tokens.weight"
    if key.endswith("embed_tokens.weight"):
        return key[: -len("embed_tokens.weight")] + "lm_head.weight"
    return None


def _lookup(state, key, mirror=None):
    if key in state:
        return state[key]
    if mirror is not None and mirror in state:
        return state[mirror]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-path", required=True)
    parser.add_argument("--quantized-path", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    args = parser.parse_args()

    left = _load_weights(args.original_path)
    right = _load_weights(args.quantized_path)
    if not left or not right:
        print("[ERROR] step3lossfailure: WeightsLoadlossfailure")
        return 1

    left_keys = set(left.keys())
    right_keys = set(right.keys())

    # One-sided keys that are tied-embedding aliases (lm_head.weight <-> embed_tokens.weight)
    # are legitimate for tie_word_embeddings models: the shared tensor may be
    # stored under either name, so a key can appear on one side only. Ignore
    # those aliases when checking key-set consistency; any other one-sided key
    # is a real inconsistency.
    left_only = sorted(k for k in left_keys - right_keys if _tied_mirror(k) is None)
    right_only = sorted(k for k in right_keys - left_keys if _tied_mirror(k) is None)
    if left_only or right_only:
        print("[ERROR] step3lossfailure: Weightskeynotoneconsistent")
        print(f"[INFO] onlyleftsidenumberamount: {len(left_only)}")
        print(f"[INFO] onlyrightsidenumberamount: {len(right_only)}")
        return 1

    # Verify one-sided tied-alias keys against their shared counterpart on the
    # other side so a genuine value drift is still caught.
    for key in sorted((left_keys - right_keys) | (right_keys - left_keys)):
        mirror = _tied_mirror(key)
        l = _lookup(left, key, mirror)
        r = _lookup(right, key, mirror)
        if l is None or r is None:
            continue
        if l.shape != r.shape:
            print(f"[ERROR] step3lossfailure: shapestatusnotoneconsistent {key}")
            return 1
        diff = torch.abs(l.float() - r.float()).max().item()
        if diff > args.tolerance:
            print(f"[ERROR] step3lossfailure: Weightsdifferencedifferentexceedthresholdvalue {key} diff={diff:.2e}")
            return 1

    max_diff = 0.0
    for key in sorted(left_keys & right_keys):
        l = left[key]
        r = right[key]
        if l.shape != r.shape:
            print(f"[ERROR] step3lossfailure: shapestatusnotoneconsistent {key}")
            return 1
        diff = torch.abs(l.float() - r.float()).max().item()
        if diff > max_diff:
            max_diff = diff
        if diff > args.tolerance:
            print(f"[ERROR] step3lossfailure: Weightsdifferencedifferentexceedthresholdvalue {key} diff={diff:.2e}")
            return 1

    print(f"[OK] step3completed: max_diff={max_diff:.2e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
