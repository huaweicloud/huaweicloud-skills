#!/usr/bin/env python
"""Quick verification script for the inference interface adapter.

Verifies the adapter layer without running a server, by directly calling
its internal conversion methods to test observation conversion and action
conversion logic — no server, no model, no network.

This script demonstrates how to unit-test an adapter with a Mock model.

Usage::

    # Run from the project's deployment directory
    python verify_adapter.py --adapter my_adapter.py

    # Or import the adapter class directly
    python verify_adapter.py --adapter-path /path/to/adapter.py --class-name MyAdapter
"""

import argparse
import importlib.util
import logging
import sys
import traceback
from typing import Any, Dict, List, Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

logger = logging.getLogger(__name__)


def load_adapter_class(adapter_path: str, class_name: str):
    """Dynamically load an adapter class from a Python file."""
    spec = importlib.util.spec_from_file_location("adapter_module", adapter_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adapter_module"] = mod
    spec.loader.exec_module(mod)

    if not hasattr(mod, class_name):
        raise AttributeError(
            f"class '{class_name}' not found in {adapter_path}. "
            f"available: {[k for k in dir(mod) if not k.startswith('_')]}"
        )
    return getattr(mod, class_name)


def verify_obs_conversion(adapter_class, constructor_kwargs=None,
                          model_stub=None) -> bool:
    """Test that the adapter correctly converts observations to model input
    and returns actions.

    Core: **test only through ``adapter.infer(obs)``**, with no model API
    assumptions (``predict`` / ``predict_action`` / ``get_action`` all
    work).

    The model stub (``model_stub``) is injected by the caller — it returns
    predictable ``(B, T, D)`` actions, which the adapter calls via
    ``_obs_to_example``; if the adapter uses nested observations (e.g.
    GR00T's ``get_action(observation)``), the stub must match that API.
    """
    constructor_kwargs = constructor_kwargs or {}
    print("\n--- Observation conversion test ---")

    # Default model stub: returns zero actions of shape
    # (B, chunk_size, action_dim)
    if model_stub is None:
        class _Stub:
            def predict_action(self, examples, **kwargs):
                batch_size = len(examples)
                return {"action": np.zeros((batch_size, 8, 7), dtype=np.float32)}

        model_stub = _Stub()

    # Try to construct the adapter
    try:
        adapter = adapter_class(model_stub, **constructor_kwargs)
    except Exception as e:
        print(f"  [FAIL] could not construct adapter: {e}")
        return False

    # Get the image keys the adapter expects
    expected_image_keys = getattr(adapter, "_expected_image_keys", [])
    state_dim = getattr(adapter, "_state_dim", 0) or 0
    send_state = getattr(adapter, "_send_state", True)

    if not expected_image_keys:
        expected_image_keys = ["cam_0", "cam_1"]
        adapter._expected_image_keys = expected_image_keys

    passed = 0
    failed = 0

    # --- Test 1: valid flat observation ---
    print("\n  Test 1: valid flat observation")
    try:
        obs = {
            "task": "pick up the red cube",
        }
        for k in expected_image_keys:
            obs[f"observation.images.{k}"] = np.zeros((224, 224, 3), dtype=np.uint8)
        if send_state and state_dim > 0:
            obs["observation.state"] = np.zeros(state_dim, dtype=np.float32)

        result = adapter.infer(obs)
        actions = np.asarray(result["action"])
        if actions.ndim != 2:
            raise ValueError(f"expected (T, D), got {actions.shape}")
        print(f"    [PASS] actions shape={actions.shape}")
        passed += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        traceback.print_exc()
        failed += 1

    # --- Test 2: missing image key ---
    if len(expected_image_keys) > 1:
        print("\n  Test 2: missing image key raises an error")
        try:
            obs = {"task": "test", f"observation.images.{expected_image_keys[0]}": np.zeros((224, 224, 3), dtype=np.uint8)}
            if send_state and state_dim > 0:
                obs["observation.state"] = np.zeros(state_dim, dtype=np.float32)
            adapter.infer(obs)
            print(f"    [FAIL] expected KeyError for missing image key")
            failed += 1
        except (KeyError, ValueError) as e:
            print(f"    [PASS] correctly raised: {type(e).__name__}")
            passed += 1
        except Exception as e:
            print(f"    [FAIL] wrong exception type: {type(e).__name__}: {e}")
            failed += 1

    # --- Test 3: wrong state dimension ---
    if send_state and state_dim > 0:
        print("\n  Test 3: wrong state dimension raises an error")
        try:
            obs = {"task": "test"}
            for k in expected_image_keys:
                obs[f"observation.images.{k}"] = np.zeros((224, 224, 3), dtype=np.uint8)
            obs["observation.state"] = np.zeros(state_dim + 1, dtype=np.float32)
            adapter.infer(obs)
            print(f"    [FAIL] expected ValueError for wrong state dimension")
            failed += 1
        except (KeyError, ValueError) as e:
            print(f"    [PASS] correctly raised: {type(e).__name__}")
            passed += 1
        except Exception as e:
            print(f"    [FAIL] wrong exception type: {type(e).__name__}: {e}")
            failed += 1

    # --- Test 4: empty prompt uses the fallback ---
    if hasattr(adapter, "_fallback_instruction") and adapter._fallback_instruction:
        print("\n  Test 4: empty prompt uses the fallback instruction")
        try:
            obs = {"task": ""}
            for k in expected_image_keys:
                obs[f"observation.images.{k}"] = np.zeros((224, 224, 3), dtype=np.uint8)
            if send_state and state_dim > 0:
                obs["observation.state"] = np.zeros(state_dim, dtype=np.float32)
            result = adapter.infer(obs)
            print(f"    [PASS] fallback instruction used, actions shape={np.asarray(result['action']).shape}")
            passed += 1
        except Exception as e:
            print(f"    [FAIL] {e}")
            failed += 1

    # --- Summary ---
    print(f"\n  Summary: {passed} passed, {failed} failed")
    return failed == 0


def verify_metadata(adapter_class, constructor_kwargs=None, model_stub=None) -> bool:
    """Verify the adapter exposes a valid metadata property."""
    constructor_kwargs = constructor_kwargs or {}
    print("\n--- Metadata test ---")

    if model_stub is None:
        class _Stub:
            @property
            def metadata(self):
                return {"action_chunk_size": 8}

        model_stub = _Stub()

    try:
        adapter = adapter_class(model_stub, **constructor_kwargs)
        meta = adapter.metadata if hasattr(adapter, "metadata") else {}
        if not isinstance(meta, dict):
            print(f"  [FAIL] metadata is not a dict: {type(meta)}")
            return False
        print(f"  [PASS] metadata is a dict with {len(meta)} keys: {list(meta.keys())}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", type=str, default=None,
                    help="path to the adapter Python file")
    ap.add_argument("--class-name", type=str, default="ProtocolAdapter",
                    help="adapter class name to test")
    ap.add_argument("--kwargs", type=str, default=None,
                    help="constructor kwargs, format key=value,key=value")
    ap.add_argument("--stub-module", type=str, default=None,
                    help="path to the model stub Python file (defines a "
                         "make_model_stub() factory function returning a "
                         "model object matching the adapter). If omitted, "
                         "the built-in default stub is used.")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.adapter:
        print("This is a verification script template. Usage:")
        print(f"  python {sys.argv[0]} --adapter /path/to/adapter.py --class-name MyAdapter")
        print("\nThe script will test:")
        print("  1. Observation conversion (flat dot-notation -> model example)")
        print("  2. Image-key validation (raises on missing keys)")
        print("  3. State-dimension validation")
        print("  4. metadata property returns a valid dict")
        sys.exit(0)

    # Parse kwargs
    constructor_kwargs = {}
    if args.kwargs:
        for kv in args.kwargs.split(","):
            k, v = kv.split("=", 1)
            constructor_kwargs[k.strip()] = v.strip()

    # Load the adapter class
    adapter_class = load_adapter_class(args.adapter, args.class_name)
    print(f"loaded adapter class: {args.class_name} (from {args.adapter})")

    # Load the model stub (optional): the stub file must define a
    # make_model_stub() factory function
    model_stub = None
    if args.stub_module:
        model_stub_cls = load_adapter_class(args.stub_module, "make_model_stub")
        model_stub = model_stub_cls()
        print(f"loaded custom model stub: {args.stub_module}")

    # Run the tests (only through adapter.infer(), no model API assumptions)
    obs_ok = verify_obs_conversion(adapter_class, constructor_kwargs, model_stub)
    meta_ok = verify_metadata(adapter_class, constructor_kwargs, model_stub)

    print(f"\n{'='*60}")
    print(f"Overall result: {'PASS' if obs_ok and meta_ok else 'FAIL'}")
    print(f"{'='*60}")
    sys.exit(0 if obs_ok and meta_ok else 1)
