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
        return torch.load(pt_path, map_location="cpu")
    return {}


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
    if left_keys != right_keys:
        print("[ERROR] step3lossfailure: Weightskeynotoneconsistent")
        print(f"[INFO] onlyleftsidenumberamount: {len(left_keys - right_keys)}")
        print(f"[INFO] onlyrightsidenumberamount: {len(right_keys - left_keys)}")
        return 1

    max_diff = 0.0
    for key in sorted(left_keys):
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
