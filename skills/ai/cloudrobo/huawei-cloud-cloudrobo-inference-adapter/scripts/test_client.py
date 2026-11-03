#!/usr/bin/env python
"""Generic test client for WSS (WebSocket over TLS) inference servers.

Follows the simple communication protocol: connect → receive metadata →
send obs → receive action. Works with any server following this pattern,
independent of the underlying model framework. The client auto-discovers
the server's I/O contract from the handshake metadata, so it adapts to
different model configs without code changes.

Prerequisites:
    pip install websockets msgpack numpy
    # To load images from disk (optional):
    pip install Pillow

Usage (smoke test with random images)::

    python test_client.py --host 127.0.0.1 --port 8000 \\
        --prompt "pick up the red cube"

Usage (load real images from disk)::

    python test_client.py --host 127.0.0.1 --port 8000 \\
        --image_dir /path/to/images \\
        --prompt "pick up the red cube" \\
        --num_inferences 5 --verbose

Usage (performance benchmark)::

    python test_client.py --host 127.0.0.1 --port 8000 \\
        --benchmark --num_inferences 100

The script supports two metadata formats:
  - hierarchical: {"action": {"shape": [T, D], ...}, "state": {"dim": D, ...}, "images": {"keys": [...]}}
  - flat: {"action_dim": D, "state_dim": D, "expected_image_keys": [...]}

Observations use flat dot-notation:
  {"observation.state": arr, "observation.images.cam_0": arr, "task": str}
"""

import argparse
import glob
import logging
import os
import ssl
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# --- msgpack serialization (numpy extension, same as test_openpi.py) ------
#
# Serialization format:
# - np.ndarray -> {"__ndarray__": True, "data": bytes, "dtype": str, "shape": tuple}
# - np.generic -> {"__npgeneric__": True, "data": scalar, "dtype": str}
# Both ends (server/client) MUST use the same pack_array/unpack_array.

import functools

try:
    import msgpack
    _HAS_MSGPACK = True
except ImportError:
    _HAS_MSGPACK = False


def pack_array(obj):
    """msgpack.Packer default: turn numpy objects into serializable dicts."""
    if (isinstance(obj, (np.ndarray, np.generic))) and obj.dtype.kind in ("V", "O", "c"):
        raise ValueError(f"Unsupported dtype: {obj.dtype}")

    if isinstance(obj, np.ndarray):
        return {
            b"__ndarray__": True,
            b"data": obj.tobytes(),
            b"dtype": obj.dtype.str,
            b"shape": obj.shape,
        }

    if isinstance(obj, np.generic):
        return {
            b"__npgeneric__": True,
            b"data": obj.item(),
            b"dtype": obj.dtype.str,
        }

    return obj


def unpack_array(obj):
    """msgpack object_hook: restore __ndarray__/__npgeneric__ dicts."""
    if b"__ndarray__" in obj:
        return np.ndarray(buffer=obj[b"data"], dtype=np.dtype(obj[b"dtype"]), shape=obj[b"shape"])

    if b"__npgeneric__" in obj:
        return np.dtype(obj[b"dtype"]).type(obj[b"data"])

    return obj


def _create_packer():
    if not _HAS_MSGPACK:
        raise ImportError(
            "msgpack is required. Install with:\n"
            "  pip install msgpack"
        )
    return functools.partial(msgpack.Packer, default=pack_array)()


def _unpack(data: bytes) -> Any:
    return msgpack.unpackb(data, object_hook=unpack_array)


# --- WebSocket client ------------------------------------------------------

try:
    import websockets.sync.client
    _HAS_WEBSOCKETS = True
except ImportError:
    _HAS_WEBSOCKETS = False


class InferenceTestClient:
    """Test client for a WSS inference server.

    Auto-discovers the server's I/O contract from the handshake metadata,
    so it works with any model config without hardcoding.

    Args:
        host: server hostname.
        port: server port.
        connect_timeout: seconds to wait for the server to come up.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        connect_timeout: float = 300.0,
    ) -> None:
        if not _HAS_WEBSOCKETS:
            raise ImportError(
                "websockets is required. Install with:\n"
                "  pip install websockets"
            )
        self._uri = f"wss://{host}:{port}"
        self._packer = _create_packer()
        self._ws, self._metadata = self._wait_for_server(connect_timeout)
        logger.warning("connected to %s. server metadata: %s", self._uri, self._metadata)

    @property
    def server_metadata(self) -> Dict[str, Any]:
        return self._metadata

    def infer(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Send an observation dict, receive an action dict.

        If the server returns a string (traceback), raise a RuntimeError
        — matching the common error contract.
        """
        data = self._packer.pack(obs)
        self._ws.send(data)
        resp = self._ws.recv()
        if isinstance(resp, str):
            raise RuntimeError(f"server-side error:\n{resp}")
        return _unpack(resp)

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            logger.warning("close connected error.")

    def _wait_for_server(self, timeout: float) -> Tuple[Any, Dict[str, Any]]:
        deadline = time.time() + timeout
        last_err = None
        # The server uses a self-signed certificate (see server_template.py);
        # the client skips certificate verification.
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        while time.time() < deadline:
            # Clear proxy env vars to avoid WebSocket proxy issues.
            for var in (
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy",
            ):
                os.environ.pop(var, None)

            try:
                # Note: websockets.sync.client.connect() does not accept
                # ping_interval or ping_timeout (those are async-API args).
                ws = websockets.sync.client.connect(
                    self._uri,
                    ssl=ssl_context,
                    compression=None,
                    max_size=None,
                    open_timeout=150,
                )
                # First frame = handshake metadata.
                metadata = _unpack(ws.recv())
                return ws, metadata
            except ConnectionRefusedError as e:
                last_err = e
                time.sleep(2)
        raise TimeoutError(
            f"could not connect to {self._uri} within {timeout}s: {last_err}"
        )


# --- Metadata parsing ------------------------------------------------------

def parse_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the server metadata, supporting hierarchical and flat formats.

    Returns a normalized dict with keys:
        action_shape, action_chunk_size, action_dim,
        state_dim, state_required, image_keys
    """
    # Try the hierarchical format first
    action_meta = meta.get("action", {})
    state_meta = meta.get("state", {})
    images_meta = meta.get("images", {})

    if action_meta:
        # Hierarchical format
        return {
            "action_shape": action_meta.get("shape", []),
            "action_chunk_size": action_meta.get("chunk_size") or action_meta.get("shape", [0])[0],
            "action_dim": action_meta.get("dim") or action_meta.get("shape", [0, 0])[-1],
            "state_dim": state_meta.get("dim", 0),
            "state_required": state_meta.get("required", False),
            "image_keys": images_meta.get("keys", []),
        }
    else:
        # Flat format (legacy/simple)
        image_keys = meta.get("expected_image_keys", [])
        if not image_keys:
            image_keys = meta.get("image_keys", [])
        return {
            "action_shape": None,
            "action_chunk_size": meta.get("action_chunk_size"),
            "action_dim": meta.get("action_dim"),
            "state_dim": meta.get("state_dim", 0),
            "state_required": meta.get("send_state", False) or meta.get("state_required", False),
            "image_keys": image_keys,
        }


# --- Observation construction ----------------------------------------------

def build_observation(
    images: Dict[str, np.ndarray],
    state: Optional[np.ndarray],
    prompt: str,
) -> Dict[str, Any]:
    """Build a flat dot-notation observation dict.

    Args:
        images: dict of image key -> (H, W, 3) uint8 ndarray.
        state: (D,) float32 ndarray, or None when there is no state.
        prompt: language instruction string.

    Returns a dict using the "observation.state" / "observation.images.{key}"
    / "task" flat keys.
    """
    obs: Dict[str, Any] = {"task": prompt}
    for key, img in images.items():
        obs[f"observation.images.{key}"] = img
    if state is not None:
        obs["observation.state"] = state
    return obs


# --- Image loading ---------------------------------------------------------

def load_images_from_dir(
    image_dir: str,
    image_keys: List[str],
    image_size: int = 224,
) -> Dict[str, np.ndarray]:
    """Load images from a directory, matching by key name.

    Looks for files matching: {image_key}*.jpg, {image_key}*.png,
    {image_key}*.jpeg. Falls back to random images when no match is found
    for a key.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL unavailable, using random images")
        return {k: np.random.randint(0, 256, (image_size, image_size, 3), dtype=np.uint8)
                for k in image_keys}

    images = {}
    for key in image_keys:
        patterns = [
            os.path.join(image_dir, f"{key}*.jpg"),
            os.path.join(image_dir, f"{key}*.png"),
            os.path.join(image_dir, f"{key}*.jpeg"),
        ]
        matched = []
        for pattern in patterns:
            matched.extend(glob.glob(pattern))

        if matched:
            img = Image.open(matched[0]).convert("RGB").resize((image_size, image_size))
            images[key] = np.asarray(img, dtype=np.uint8)
            logger.info("loaded image %s from %s", matched[0], key)
        else:
            logger.warning("no image found for key '%s' in %s, using random image", image_dir, key)
            images[key] = np.random.randint(0, 256, (image_size, image_size, 3), dtype=np.uint8)
    return images


# --- Statistics and benchmarking -------------------------------------------

def print_action_statistics(actions_list: List[np.ndarray], verbose: bool = False) -> None:
    """Print action-sequence statistics across multiple inferences."""
    if not actions_list:
        print("no actions to analyze.")
        return

    all_actions = np.stack(actions_list, axis=0)
    N, T, D = all_actions.shape

    print(f"\n{'='*60}")
    print(f"action statistics (N={N} inferences, T={T} steps, D={D} dims)")
    print(f"{'='*60}")

    print(f"\noverall:")
    print(f"  shape: {all_actions.shape}")
    print(f"  mean:  {all_actions.mean():.6f}")
    print(f"  std:   {all_actions.std():.6f}")
    print(f"  min:   {all_actions.min():.6f}")
    print(f"  max:   {all_actions.max():.6f}")

    print(f"\nper-dimension (D={D}):")
    dim_means = all_actions.mean(axis=(0, 1))
    dim_stds = all_actions.std(axis=(0, 1))
    for d in range(D):
        print(f"  dim {d:2d}: mean={dim_means[d]:+.4f}, std={dim_stds[d]:.4f}")

    if verbose and T > 1:
        print(f"\nper-timestep (T={T}):")
        for t in range(T):
            step = all_actions[:, t, :]
            print(f"  t={t:2d}: mean={step.mean():+.4f}, std={step.std():.4f}, "
                  f"min={step.min():+.4f}, max={step.max():+.4f}")

    if N > 1:
        print(f"\naction consistency (across {N} inferences):")
        baseline = actions_list[0]
        for i in range(1, N):
            diff = np.abs(actions_list[i] - baseline)
            print(f"  inference {i} vs 0: mean diff={diff.mean():.6f}, "
                  f"max diff={diff.max():.6f}")

    print(f"{'='*60}\n")


def run_benchmark(
    client: InferenceTestClient,
    obs: Dict[str, Any],
    num_inferences: int,
    warmup: int = 5,
) -> None:
    """Run a performance benchmark with warmup."""
    print(f"\n{'='*60}")
    print(f"performance benchmark")
    print(f"{'='*60}")
    print(f"warmup: {warmup} calls")
    print(f"measured: {num_inferences} calls")
    print()

    logger.info("running %d warmup calls...", warmup)
    for i in range(warmup):
        client.infer(obs)
    logger.info("warmup complete.")

    infer_times = []
    total_times = []

    print(f"running {num_inferences} inference calls...")
    for i in range(num_inferences):
        t_start = time.time()
        resp = client.infer(obs)
        t_total = (time.time() - t_start) * 1000

        timing = resp.get("server_timing", {})
        infer_ms = timing.get("infer_ms", 0)

        infer_times.append(infer_ms)
        total_times.append(t_total)

        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1:3d}/{num_inferences}] infer={infer_ms:7.2f}ms, "
                  f"total={t_total:7.2f}ms")

    infer_times = np.array(infer_times)
    total_times = np.array(total_times)

    print(f"\n{'='*60}")
    print("results:")
    print(f"{'='*60}")
    print(f"\ninference time (server-side):")
    print(f"  mean:   {infer_times.mean():7.2f} ms")
    print(f"  std:    {infer_times.std():7.2f} ms")
    print(f"  min:    {infer_times.min():7.2f} ms")
    print(f"  max:    {infer_times.max():7.2f} ms")
    print(f"  median: {np.median(infer_times):7.2f} ms")
    print(f"  p95:    {np.percentile(infer_times, 95):7.2f} ms")
    print(f"  p99:    {np.percentile(infer_times, 99):7.2f} ms")

    print(f"\ntotal time (client-side, incl. network):")
    print(f"  mean:   {total_times.mean():7.2f} ms")
    print(f"  std:    {total_times.std():7.2f} ms")
    print(f"  min:    {total_times.min():7.2f} ms")
    print(f"  max:    {total_times.max():7.2f} ms")
    print(f"  median: {np.median(total_times):7.2f} ms")

    avg_infer_ms = infer_times.mean()
    if avg_infer_ms > 0:
        fps = 1000.0 / avg_infer_ms
        print(f"\nthroughput: {fps:.2f} inferences/second")

    print(f"{'='*60}\n")


# --- Main ------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--host", default="127.0.0.1", help="server hostname")
    ap.add_argument("--port", type=int, default=8000, help="server port")
    ap.add_argument("--image_dir", type=str, default=None,
                    help="directory containing images (auto-loaded by key name)")
    ap.add_argument("--image_keys", type=str, default=None,
                    help="comma-separated camera key names (overrides server metadata)")
    ap.add_argument("--prompt", default="pick up the red cube", help="language instruction")
    ap.add_argument("--image_size", type=int, default=224, help="image size (H=W)")
    ap.add_argument("--num_inferences", type=int, default=1,
                    help="number of inference calls (default: 1)")
    ap.add_argument("--verbose", action="store_true",
                    help="print detailed per-timestep statistics")
    ap.add_argument("--benchmark", action="store_true",
                    help="run a performance benchmark (default 100 calls)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, force=True)

    # Connect and get metadata
    client = InferenceTestClient(host=args.host, port=args.port)
    meta = client.server_metadata
    contract = parse_metadata(meta)

    print(f"\nserver metadata:")
    print(f"  protocol: {meta.get('protocol', 'unknown')}")
    if contract["action_shape"]:
        print(f"  action: shape={contract['action_shape']}, dtype={meta.get('action', {}).get('dtype')}")
    else:
        print(f"  action: chunk_size={contract['action_chunk_size']}, dim={contract['action_dim']}")
    print(f"  state: dim={contract['state_dim']}, required={contract['state_required']}")
    print(f"  images: keys={contract['image_keys']}")

    # Determine image keys
    if args.image_keys:
        image_keys = [k.strip() for k in args.image_keys.split(",")]
    else:
        image_keys = contract["image_keys"]
        if not image_keys:
            logger.error("server did not provide image keys. "
                        "specify --image_keys manually.")
            client.close()
            sys.exit(1)

    # Load images
    if args.image_dir:
        print(f"\nloading images from {args.image_dir}...")
        images = load_images_from_dir(args.image_dir, image_keys, args.image_size)
    else:
        print(f"\nusing random images (size={args.image_size}x{args.image_size})...")
        images = {k: np.random.randint(0, 256, (args.image_size, args.image_size, 3),
                                       dtype=np.uint8)
                  for k in image_keys}

    # Build state
    state_dim = contract["state_dim"]
    state_required = contract["state_required"]
    state = np.zeros((state_dim,), dtype=np.float32) if state_required and state_dim else None

    # Build the observation (flat dot-notation)
    obs = build_observation(images, state, args.prompt)

    print(f"observation:")
    print(f"  format: flat dot-notation")
    print(f"  prompt: {args.prompt}")
    print(f"  images: {list(images.keys())}")
    if state is not None:
        print(f"  state: shape={state.shape}, dtype={state.dtype}")

    # Benchmark mode
    if args.benchmark:
        num_inferences = args.num_inferences if args.num_inferences > 1 else 100
        run_benchmark(client, obs, num_inferences=num_inferences, warmup=5)
        client.close()
        sys.exit(0)

    # Run inferences
    actions_list = []
    num_inferences = max(1, args.num_inferences)

    print(f"\nrunning {num_inferences} inference calls...")
    for i in range(num_inferences):
        resp = client.infer(obs)
        actions = np.asarray(resp["action"])
        timing = resp.get("server_timing", {})

        actions_list.append(actions)

        print(f"\n[inference {i+1}/{num_inferences}]")
        print(f"  actions shape: {actions.shape}, dtype: {actions.dtype}")
        print(f"  actions: mean={actions.mean():.6f}, std={actions.std():.6f}, "
              f"min={actions.min():.6f}, max={actions.max():.6f}")
        if timing:
            print(f"  server_timing: infer_ms={timing.get('infer_ms', 0):.2f}, "
                  f"prev_total_ms={timing.get('prev_total_ms', 0):.2f}")

        # Basic validation
        assert actions.ndim == 2, f"expected (T, D) actions, got shape {actions.shape}"
        if i == 0 and timing:
            assert timing.get("prev_total_ms") == 0, "prev_total_ms should be 0 for the first request"
        elif i > 0 and timing:
            assert timing.get("prev_total_ms", 0) > 0, "prev_total_ms should be > 0 after the first request"

    if num_inferences > 1:
        print_action_statistics(actions_list, verbose=args.verbose)

    print(f"\nall assertions passed. protocol works correctly.")
    client.close()
