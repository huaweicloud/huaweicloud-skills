"""Protocol adapter template — conversion layer between the flat wire
format and the model's internal format.

This is the full reference implementation for SKILL.md "Step 2: Create the
Protocol Adapter". Copy this file into the project's deployment directory
and adjust the *_derive_* methods and __init__ parameters per the model's
actual interface.

Responsibilities:
- Accept flat dot-notation observation dicts (wire format)
- Convert to the example dict the model understands
- Call model.predict()
- Convert the model's returned actions to `{"action": (T, D)}` (wire
  format)

Wire contract (see SKILL.md "Fixed Protocol Contract"):
- Observation keys: observation.images.{key}, observation.state, task
- Response keys: action (fixed in wire), server_timing (added by the
  transport server)
"""

import numpy as np


class ProtocolAdapter:
    """Wraps the model's inference interface to speak the flat wire
    format."""

    def __init__(self, model, **kwargs):
        self._model = model
        # Cache the model's I/O contract — these define valid inputs.
        self._expected_image_keys = self._derive_image_keys(model)
        self._state_dim = self._derive_state_dim(model)
        self._state_keys = self._derive_state_keys(model)
        self._action_dim = self._derive_action_dim(model)
        self._action_chunk_size = self._derive_action_chunk_size(model)
        # Everything the `metadata` property reads is initialized above, so
        # the handshake (the first frame after connect) cannot hit an
        # uninitialized attribute.
        # The field name under which the model returns actions (varies by
        # model; determine per the actual model).
        self._model_action_key = kwargs.get("model_action_key", "action")
        self._send_state = kwargs.get("send_state", True)
        self._fallback_instruction = kwargs.get("fallback_instruction", "")

    # ------------------------------------------------------------------
    # Model contract derivation — implement these per the model's actual
    # interface; do not hardcode
    # ------------------------------------------------------------------

    def _derive_image_keys(self, model):
        """Derive the image keys from the model's DataConfig (e.g. video_keys
        minus the video. prefix).

        Different models use different camera names (cam_high /
        base_0_rgb / camera_head); must be derived from the model config,
        never hardcoded.
        """
        raise NotImplementedError("implement per the model's config/framework")

    def _derive_state_dim(self, model):
        """Read the state dimension from the model metadata."""
        raise NotImplementedError("implement per the model's metadata")

    def _derive_state_keys(self, model):
        """Derive the state component keys the model consumes (e.g. the
        DataConfig state_keys). Return [] when the model takes no state
        input; metadata then reports the state as not required."""
        raise NotImplementedError("implement per the model's config/framework")

    def _derive_action_dim(self, model):
        """Read the action dimension from the model metadata."""
        raise NotImplementedError("implement per the model's metadata")

    def _derive_action_chunk_size(self, model):
        """Read the action chunk size (actions returned per inference, T in
        the (T, D) response) from the model metadata."""
        raise NotImplementedError("implement per the model's metadata")

    # ------------------------------------------------------------------
    # Main flow
    # ------------------------------------------------------------------

    def infer(self, obs: dict) -> dict:
        """Convert flat obs -> model example -> infer -> convert -> response."""
        example = self._obs_to_example(obs)
        result = self._model.predict(examples=[example])
        return self._result_to_response(result, obs)

    @property
    def metadata(self) -> dict:
        """The contract dict sent at handshake. Clients need it to build
        requests."""
        return {
            "protocol": "<protocol-name>",
            "version": "1.0",
            "action": {
                "shape": [self._action_chunk_size, self._action_dim],
                "chunk_size": self._action_chunk_size,
                "dim": self._action_dim,
                "dtype": "float32",
            },
            "state": {
                "dim": self._state_dim,
                "dtype": "float32",
                "required": bool(self._send_state and self._state_keys),
            },
            "images": {
                "keys": self._expected_image_keys,
                "dtype": "uint8",
            },
            "task": {
                "type": "string",
                "required": True,
            },
        }

    def reset(self) -> dict:
        """No-op for stateless inference. Exists for protocol
        compatibility."""
        return {"ok": True}

    # ------------------------------------------------------------------
    # Observation conversion — the most critical part
    # ------------------------------------------------------------------

    def _obs_to_example(self, obs: dict) -> dict:
        """wire flat observation -> model example dict."""
        # 1. Images: extract from the observation.images.{key} prefix
        images = {}
        image_prefix = "observation.images."
        for key, value in obs.items():
            if key.startswith(image_prefix):
                image_key = key[len(image_prefix):]
                images[image_key] = np.ascontiguousarray(value, dtype=np.uint8)

        if not images:
            raise KeyError("missing image keys (expected 'observation.images.{key}')")

        if self._expected_image_keys:
            missing = [k for k in self._expected_image_keys if k not in images]
            if missing:
                raise KeyError(f"missing image keys {missing}. "
                              f"expected: {self._expected_image_keys}")
            ordered_images = [images[k] for k in self._expected_image_keys]
        else:
            ordered_images = list(images.values())

        # 2. Language: task -> lang, applying the fallback.
        lang = obs.get("task") or self._fallback_instruction

        # 3. State: observation.state -> (1, D), validate the dimension,
        #    omit when there is no state.
        example = {"image": ordered_images, "lang": lang}
        if self._send_state and self._state_dim > 0:
            state_in = obs.get("observation.state")
            if state_in is None:
                raise KeyError("missing state, but the model was trained with a state input")
            arr = np.asarray(state_in, dtype=np.float32).reshape(-1)
            if arr.shape[0] != self._state_dim:
                raise ValueError(f"state dimension {arr.shape[0]} != expected {self._state_dim}")
            example["state"] = arr[np.newaxis, :]  # (1, D)

        return example

    # ------------------------------------------------------------------
    # Action conversion — usually just squeeze the batch dimension
    # ------------------------------------------------------------------

    def _result_to_response(self, result: dict, obs: dict) -> dict:
        """model return value -> wire response. The wire field name is
        fixed as action."""
        # Take the actions from the model's return. The model-internal
        # field name varies by model (might be "actions", "action",
        # "pred_actions", etc.), configured via _model_action_key — never
        # assume every model names it "actions".
        actions = np.asarray(result[self._model_action_key])  # (B, T, D)
        if actions.ndim == 3:
            if actions.shape[0] != 1:
                raise ValueError(f"expected batch=1, got {actions.shape[0]}")
            actions = actions[0]  # (B, T, D) -> (T, D)
        actions = np.ascontiguousarray(actions, dtype=np.float32)
        return {"action": actions}  # wire field name fixed as action
