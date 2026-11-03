# ocms API Reference

Source: `/data/anaconda3/envs/starVLA/lib/python3.10/site-packages/ocms/ocms.py`
Version: 0.1.0

## Summary Class

```python
from ocms import Summary

s = Summary(log_dir=os.getenv("METRICS", "/tmp/metrics"))
```

### Attributes

- `log_dir` — output file directory
- `chart_num` — number of initialized charts (read-only)
- `_metrics` — chart metadata dict (internal use)

### Methods

#### `init(name, x, ys, series=None, description="", smooth=True, with_timestamp=True)`

Initialize a new chart.

**Args:**
- `name` (str): chart identifier. Must not start with a digit or `-`.
  Allowed characters: `[\u4e00-\u9fa5a-zA-Z0-9_\-]`.
- `x` (str): X-axis label (e.g. `"step"`).
- `ys` (list[str]): Y-axis column names. Same character-set rule as `name`.
- `series` (list[str], optional): series names. When provided, `ys` must
  have exactly 1 element, and each series corresponds to one curve.
- `description` (str): chart description (for metadata).
- `smooth` (bool): whether to apply smoothing (default True).
- `with_timestamp` (bool): whether CSV rows include a timestamp
  (default True).

**Side effects:**
- On the first `init()` call (`chart_num == 0`), deletes the existing
  `metrics.json` in `log_dir`.
- Creates `metrics.json` with the chart metadata.
- Creates the `<name>.csv` file for this chart.

**Error handling:**
- If `chart_num >= 6`: logs an error and returns without creating a chart.
- If `name` already exists: logs an error and returns.
- If `name` starts with a digit or `-`: logs an error and returns.
- If `ys` or `series` contains illegal characters: logs an error and
  returns.

#### `__getattr__(name)`

Returns the `MetricRecorder` corresponding to the chart named `name`. Used
to access charts:

```python
s.loss.add(step=10, values=[1.23])
```

Raises `AttributeError` if the chart is not initialized.

## MetricRecorder Class

Created by `Summary.__getattr__`; do not instantiate directly.

### Methods

#### `add(step, values)`

Append one data row to the chart's CSV file.

**Args:**
- `step` (int): step number (X-axis value).
- `values` (list[float]): Y-axis values. Must be numeric (int, float, or
  numeric string). `len(values)` must equal the number of `ys` (or
  `series`) at `init()` time.

**Behavior:**
- If `step` is `None`: auto-increments based on the existing CSV row count.
- If a value is non-numeric: logs a warning and skips.
- If `len(values) != value_num`: logs a warning and skips.
- Appends the row `[step, val1, val2, ...]` to the CSV (append mode).

## File Output

After initialization and data logging, `log_dir` contains:

```
metrics.json     # chart metadata (array of chart info dicts)
loss.csv         # one CSV per chart
learning_rate.csv
epoch.csv
...
```

### metrics.json Structure

```json
[
  {
    "name": "loss",
    "x": "step",
    "ys": ["action_dit_loss", "vlm_loss"],
    "series": null,
    "description": "",
    "smooth": true,
    "with_timestamp": true,
    "file_path": "/path/to/loss.csv",
    "value_num": 2
  }
]
```

### CSV Structure

Each row is `[step, val1, val2, ...]` with no header row. If
`with_timestamp=True`, a timestamp column is prepended.

## Module-Level Behavior

On import, the `ocms` module:
- Creates a logger named `"train"` at INFO level
- Emits the log line `"开始记录日志"` ("Start logging")

This means importing `ocms` produces one log line. This is expected
behavior.
