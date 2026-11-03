"""ocms metric recorder — embeddable in any PyTorch training script.

Reports training metrics (loss, learning rate, timing, eval scores, etc.)
to the Huawei Octopus platform via the locally installed ``ocms`` library.
The library writes CSV files and a metrics.json metadata file, which the
Octopus UI reads to render training curves.

This module is framework-agnostic. It works with custom training loops,
HuggingFace Trainer, PyTorch Lightning, Accelerate, MMEngine, or any other
framework — as long as you can pass a ``step`` (int) and a ``metrics``
dict to ``recorder.log()``.

Usage
-----
    from ocms_recorder import OcmsRecorder

    # 1. Create the recorder (rank-0 only; falls back to output_dir
    #    outside the platform)
    recorder = OcmsRecorder(log_dir="path/to/metrics")

    # 2. Log metrics at each logging step (rank-0 only)
    recorder.log(step=global_step, metrics={"loss": 1.23, "learning_rate": 0.001})

    # 3. Optional: call finish() at training end (currently a no-op)
    recorder.finish()

Custom chart groups
-------------------
By default, metrics are grouped into 6 charts (the ocms hard limit).
Customize grouping via ``chart_groups``:

    recorder = OcmsRecorder(
        log_dir="...",
        chart_groups=[
            ("loss", lambda k: "loss" in k),
            ("lr", lambda k: "lr" in k or "learning_rate" in k),
            ("accuracy", lambda k: "acc" in k),
            # ... up to 6 groups
        ],
    )

Each group is a ``(chart_name, predicate)`` tuple. The predicate receives a
metric key name (str) and returns True when that metric belongs to this
chart. Charts are lazily initialized when a matching metric is first seen,
so groups that never match are never created.
"""

import logging
import os
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default chart groups: (chart_name, predicate), ordered by importance.
# The ocms library allows at most 6 charts. Groups use lazy
# initialization — only charts with actually appearing metrics are created.
DEFAULT_CHART_GROUPS: List[Tuple[str, Callable[[str], bool]]] = [
    # Loss metrics: "loss", "train_loss", "action_dit_loss", "vlm_loss", etc.
    ("loss", lambda k: k == "loss" or k.endswith("_loss")),
    # Learning rate: "learning_rate", "learning_rate/default", etc.
    ("learning_rate", lambda k: k == "learning_rate" or k.startswith("learning_rate/")),
    # Epoch progress
    ("epoch", lambda k: k == "epoch"),
    # Timing: "timing/data", "timing/model", etc.
    ("timing", lambda k: k.startswith("timing/")),
    # Eval scores: "mse_score", "accuracy", "mIoU", etc.
    ("eval_score", lambda k: k == "mse_score" or k == "accuracy" or k == "mIoU" or k.startswith("eval/")),
    # Gradient norm (HuggingFace Trainer, etc.)
    ("grad_norm", lambda k: k == "grad_norm"),
]


def _sanitize_y(chart_name: str, key: str) -> str:
    """Convert a metric key into a legal ocms y-axis name.

    ocms only allows ``[a-zA-Z0-9_\\-]`` (and Chinese characters).
    We strip the chart prefix to keep axis labels short and readable.
    """
    if chart_name == "learning_rate":
        return key.replace("learning_rate/", "lr_").replace("learning_rate", "lr")
    if chart_name == "timing":
        return key.replace("timing/", "")
    return key.replace("/", "_").replace(".", "_")


class OcmsRecorder:
    """Records training metrics through the ocms library.

    Parameters
    ----------
    log_dir : str, optional
        Directory for the metric files. Defaults to the ``METRICS``
        environment variable (set by the Octopus platform), falling back
        to ``/tmp/metrics``.
    chart_groups : list of (str, callable), optional
        Custom chart groups. Each tuple is ``(chart_name, predicate)``,
        where the predicate receives a metric key name and returns a bool.
        Defaults to ``DEFAULT_CHART_GROUPS`` (6 groups, the ocms cap).
    enabled : bool, default True
        Set to False to disable recording (e.g. on non-rank-0 processes).

    Attributes
    ----------
    _summary : ocms.Summary or None
        Underlying ocms Summary writer, lazily created on first use.
    _charts : dict
        Maps chart_name to ``{sanitized_y: original_key}`` (insertion
        order).
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        chart_groups: Optional[List[Tuple[str, Callable[[str], bool]]]] = None,
        enabled: bool = True,
    ):
        self.log_dir = log_dir or os.getenv("METRICS", "/tmp/metrics")
        self.chart_groups = chart_groups or DEFAULT_CHART_GROUPS
        self.enabled = enabled
        self._summary = None
        self._charts: Dict[str, Dict[str, str]] = {}

    @classmethod
    def from_output_dir(cls, output_dir: str, **kwargs) -> "OcmsRecorder":
        """Create a recorder using ``<output_dir>/ocms_metrics`` as the
        fallback directory.

        If the ``METRICS`` environment variable is set (Octopus platform),
        it is used; otherwise fall back to ``<output_dir>/ocms_metrics`` so
        non-platform runs still produce inspectable files.
        """
        log_dir = os.getenv("METRICS") or os.path.join(output_dir, "ocms_metrics")
        return cls(log_dir=log_dir, **kwargs)

    def _ensure_summary(self):
        """Lazily create the ocms.Summary instance."""
        if self._summary is not None:
            return
        try:
            from ocms import Summary
        except ImportError:
            logger.warning("ocms package not found; skipping Octopus metric reporting")
            self.enabled = False
            return
        self._summary = Summary(log_dir=self.log_dir)
        logger.info(f"ocms metric recorder initialized at {self.log_dir}")

    def log(self, step: int, metrics: dict):
        """Log one metric snapshot at the given training step.

        Parameters
        ----------
        step : int
            Training step (X-axis value).
        metrics : dict
            Flat metric key -> value dict. Non-numeric values are silently
            skipped. Keys are grouped into charts via the ``chart_groups``
            predicates.
        """
        if not self.enabled:
            return
        self._ensure_summary()
        if not self.enabled or self._summary is None:
            return

        try:
            for chart_name, predicate in self.chart_groups:
                # Find metrics matching this step.
                matching = [
                    (k, _sanitize_y(chart_name, k))
                    for k in metrics
                    if predicate(k) and isinstance(metrics[k], (int, float))
                ]
                if not matching:
                    continue

                # Initialize the chart on first encounter.
                if chart_name not in self._charts:
                    ys = [y for _, y in matching]
                    try:
                        self._summary.init(
                            name=chart_name, x="step", ys=ys,
                            series=[], description=chart_name, smooth=False,
                        )
                        # Keep insertion order so .add() values align with ys.
                        self._charts[chart_name] = {y: k for k, y in matching}
                    except Exception as exc:
                        logger.warning(f"ocms failed to initialize chart '{chart_name}': {exc}")
                        self._charts[chart_name] = {}
                        continue

                # Only append a data row when all initialized ys exist.
                key_map = self._charts[chart_name]
                if not key_map:
                    continue
                values: List[float] = []
                all_present = True
                for y, original_key in key_map.items():
                    val = metrics.get(original_key)
                    if isinstance(val, (int, float)):
                        values.append(val)
                    else:
                        all_present = False
                        break
                if not all_present or not values:
                    continue
                getattr(self._summary, chart_name).add(step, values)
        except Exception as exc:
            logger.warning(f"ocms recording failed: {exc}")
            self.enabled = False

    def finish(self):
        """No-op placeholder, kept for API symmetry with wandb.finish()."""
        pass
