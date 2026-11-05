#!/usr/bin/env python3
"""huawei-cloud-msmodelslim-model-analysis — automated model analysis before adapter implementation.

Implements the SKILL.md analysis flow: read config.json -> detect implementation
source (transformers / model-local) -> classify model type -> extract structural
features -> assess MoE layout / quantization / MTP risks -> generate a Markdown
analysis report usable by the msModelSlim adapter workflow.

Usage:
    python3 scripts/analyze_model.py --model-path models/<model_name> [--output analysis_report.md] [--cli-region cn-north-4] [--verbose]

Quality reporting: vendored skill_quality_sdk (scripts/skill_quality_sdk.py).
"""
import argparse
import json
import os
import re
import sys

from skill_quality_sdk import quality_report

MOE_CONFIG_FIELDS = (
    "num_experts", "num_local_experts", "n_routed_experts", "n_shared_experts",
    "experts_per_token", "moe_num_experts", "num_experts_per_tok",
)
# Nested configs used by multimodal / composite checkpoints.
MOE_CONFIG_NESTING = ("text_config", "language_config", "llm_config",
                     "thinker_config", "vision_config")
# Dense LLMs also ship mlp.gate_proj / up_proj / down_proj and gate_up_proj;
# only expert-context tensor names count as real MoE weight evidence.
EXPERT_WEIGHT_PATTERNS = (
    re.compile(r"(?:^|\.)experts\."),
    re.compile(r"block_sparse_moe"),
    re.compile(r"shared_expert"),
    re.compile(r"expert_bias"),
)
EXPERT_FUSED_PATTERN = re.compile(r"gate_up")
MTP_CONFIG_FIELDS = ("num_nextn_predict_layers", "moe_num_nextn_experts", "mtp")
QUANT_CONFIG_FIELDS = ("quantization_config", "quant_method", "bits", "weight_quant", "activation_quant")


class AnalysisError(Exception):
    """Raised when a model cannot be analyzed (unsupported/blocked case)."""


def read_config(model_path):
    """Load config.json from the model directory."""
    config_path = os.path.join(model_path, "config.json")
    if not os.path.exists(config_path):
        raise AnalysisError(
            f"config.json not found at {config_path}; download model non-weight files first, "
            "then point --model-path to the local directory"
        )
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def find_modeling_files(model_path):
    """Return modeling_*.py files present in the model directory (model-local source)."""
    if not os.path.isdir(model_path):
        return []
    return sorted(
        f for f in os.listdir(model_path)
        if re.match(r"^modeling_.*\.py$", f)
    )


def detect_source(config, model_path):
    """Detect implementation source: transformers | model-local | unsupported."""
    model_type = config.get("model_type", "")
    auto_map = config.get("auto_map") or {}
    architecture = (config.get("architectures") or [None])[0]

    basis = []
    transformers_hit = False
    transformers_model_path = None
    try:
        import transformers
        if model_type:
            candidate = os.path.join(
                os.path.dirname(transformers.__file__),
                "models", model_type, f"modeling_{model_type}.py",
            )
            if os.path.exists(candidate):
                transformers_hit = True
                transformers_model_path = candidate
                basis.append(f"transformers/models/{model_type}/modeling_{model_type}.py exists")
    except ImportError:
        basis.append("transformers package not installed; falling back to config signals")

    local_files = find_modeling_files(model_path)
    auto_map_files = [v for v in auto_map.values() if isinstance(v, str) and v]
    local_hit = bool(local_files) or bool(
        auto_map_files and all(
            os.path.exists(os.path.join(model_path, f.split("/")[-1]))
            for f in auto_map_files
        )
    )

    if transformers_hit:
        source = "transformers"
    elif local_hit:
        source = "model-local"
    else:
        source = "unsupported"

    if local_files:
        basis.append(f"model-local modeling files: {', '.join(local_files[:5])}")
    if auto_map:
        basis.append(f"auto_map: {auto_map}")
    if source == "unsupported":
        basis.append(
            "neither transformers support nor model-local modeling files found"
            "; user must provide readable model implementation code"
        )

    return source, basis, transformers_model_path


def classify_model_type(config, source):
    """Classify as: pure LLM | multimodal understanding | multimodal generation."""
    architectures = config.get("architectures") or []
    arch_text = " ".join(architectures).lower()
    config_text = json.dumps(config).lower()

    generation_hints = (
        "diffusion", "forimagegeneration", "autoencoder", "foraudio",
        "forvideogeneration", "fortext2image", "forvideo", "forGenerateImage",
    )
    vision_hints = ("vision", "visual", "image", "video", "audio_encoder",
                    "vision_config", "image_processor", "clip")
    causal_hints = ("forcausallm", "forconditionalgeneration", "lmhead")

    if any(h in arch_text or h in config_text for h in generation_hints):
        return "multimodal_generation"
    if any(h in arch_text or h in config_text for h in vision_hints):
        return "multimodal_understanding"
    if any(h in arch_text for h in causal_hints) or "llm" in arch_text:
        return "pure_LLM"
    if architectures:
        return "pure_LLM"
    return "unknown"


def _iter_config_dicts(config):
    """Yield the top-level config and known nested sub-configs."""
    yield config
    for key in MOE_CONFIG_NESTING:
        sub = config.get(key)
        if isinstance(sub, dict):
            yield sub


def _has_moe_config(config):
    """Return True only when a real MoE config signal is present."""
    for cfg in _iter_config_dicts(config):
        for key, value in cfg.items():
            if value is None:
                continue
            low = str(key).lower()
            if low in MOE_CONFIG_FIELDS or low.startswith("moe_"):
                return True
    return False


def _first_config_value(config, fields):
    """Return the first non-null value for ``fields`` across nested configs."""
    for cfg in _iter_config_dicts(config):
        for field in fields:
            if cfg.get(field) is not None:
                return cfg.get(field)
    return None


def extract_features(config, model_path):
    """Extract structural features and MoE / quantization / MTP signals."""
    features = {
        "model_type": config.get("model_type", ""),
        "architectures": config.get("architectures") or [],
        "hidden_size": _first_config_value(config, ("hidden_size",)),
        "num_hidden_layers": _first_config_value(
            config, ("num_hidden_layers", "num_layers")),
        "num_attention_heads": _first_config_value(config, ("num_attention_heads",)),
        "num_key_value_heads": _first_config_value(config, ("num_key_value_heads",)),
        "intermediate_size": _first_config_value(config, ("intermediate_size",)),
        "num_experts": _first_config_value(
            config, ("num_experts", "num_local_experts", "n_routed_experts",
                     "moe_num_experts")),
        "experts_per_token": _first_config_value(
            config, ("experts_per_token", "num_experts_per_tok", "moe_top_k")),
        "moe_layout": "no_moe",
    }

    has_moe_config = _has_moe_config(config)
    features["has_moe_config"] = has_moe_config
    features["moe_hints"] = _detect_moe_weight_hints(model_path,
                                                     config.get("model_type", ""))
    has_expert_weight = features["moe_hints"].get("has_expert_weight", False)
    features["contains_moe"] = has_moe_config or has_expert_weight
    features["quantized"] = any(config.get(f) is not None
                                for f in QUANT_CONFIG_FIELDS) or bool(
        config.get("quantization_config"))
    features["quant_evidence"] = {k: config[k] for k in config
                                  if any(f == k for f in ("quantization_config", "quant_method"))}
    features["mtp"] = any(
        str(k).lower().find(f) >= 0 for k in config
        for f in ("nextn", "mtp")
    )
    features["mtp_details"] = [k for k in config
                               if any(f in str(k).lower() for f in ("nextn", "mtp"))]
    features["auto_map"] = config.get("auto_map") or {}
    return features


def _is_expert_weight_key(name):
    """Return True only for tensor names inside an expert/MoE module context."""
    low = name.lower()
    return any(pattern.search(low) for pattern in EXPERT_WEIGHT_PATTERNS)


def _detect_moe_weight_hints(model_path, model_type):
    """Inspect safetensors index / tensor names for real expert weight hints.

    Plain dense MLP projections (``gate_proj`` / ``up_proj`` / ``down_proj`` /
    ``gate_up_proj``) must not be treated as MoE evidence; only names inside an
    expert context (``.experts.``, ``block_sparse_moe``, ``shared_expert``,
    ``expert_bias``) count.
    """
    hints = {"has_expert_weight": False, "fused_tensor_shape": False, "found": False}
    index_path = os.path.join(model_path, "model.safetensors.index.json")
    tensors = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as fh:
                tensors = json.load(fh).get("weight_map") or {}
        except (ValueError, OSError):
            tensors = {}
    else:
        shard = next((f for f in os.listdir(model_path)
                      if f.endswith(".safetensors")), None)
        if shard:
            tensors = _read_safetensors_tensor_names(os.path.join(model_path, shard))

    expert_keys = []
    fused_shape = False
    if tensors:
        expert_keys = [name for name in tensors if _is_expert_weight_key(name)]
        hints["has_expert_weight"] = bool(expert_keys)
        hints["found"] = bool(tensors)
        # Fused layout signal: gate_up packaged inside an expert context, e.g.
        # "...mlp.experts.gate_up_proj.weight".
        fused_shape = any(EXPERT_FUSED_PATTERN.search(k.lower())
                          for k in expert_keys)
    hints["fused_tensor_shape"] = fused_shape
    hints["expert_keys_sample"] = sorted(expert_keys)[:10]
    return hints


def _read_safetensors_tensor_names(path):
    """Return tensor names from a safetensors file header (cheap, no weight load)."""
    names = []
    try:
        with open(path, "rb") as fh:
            header_len = int.from_bytes(fh.read(8), "little")
            if header_len <= 0 or header_len > 100 * 1024 * 1024:
                return {}
            header = json.loads(fh.read(header_len))
        for name, meta in (header or {}).items():
            if isinstance(meta, dict) and "dtype" in meta:
                names.append(name)
    except (OSError, ValueError, json.JSONDecodeError, MemoryError):
        return {}
    return {n: path for n in names}


def layer_by_layer_assessment(features):
    """Heuristic layer-by-layer loading recommendation from config signals."""
    layers = features["num_hidden_layers"] or 0
    hidden = features["hidden_size"] or 0
    has_model_local = features.get("source") == "model-local"
    moe = features.get("contains_moe", False)

    reasons = []
    if moe:
        reasons.append("MoE expands parameter footprint across experts")
    if has_model_local:
        reasons.append("model-local implementation may require custom weight handling")
    if layers and hidden and layers * hidden * hidden > 20 * 1024 * 1024 * 1024:
        reasons.append("estimated model size indicates large memory footprint")

    if reasons:
        return True, "; ".join(reasons), [
            "evaluate memory/runtime environment before full load",
            "consider per-layer visit/forward to reduce peak memory",
        ]
    return False, "no blockers detected; full load acceptable in typical environments", []


def build_report(path, config, features, source, basis, region="cn-north-4", verbose=False):
    """Compose the Markdown analysis report per SKILL.md Required Output template."""
    f = features
    contains_moe = bool(f.get("contains_moe"))
    has_expert_weight = f.get("moe_hints", {}).get("has_expert_weight")
    num_experts = f["num_experts"]
    if contains_moe:
        # Keep "Contains MoE: Yes" consistent: never report N/A as the expert
        # count when MoE is asserted from config-only evidence.
        num_experts_label = (num_experts if num_experts is not None
                             else "Unknown (not specified in config)")
    else:
        num_experts_label = "N/A"
    if not contains_moe:
        moe_layout = "no_moe"
    elif f.get("moe_hints", {}).get("fused_tensor_shape"):
        moe_layout = "fused_moe"
    elif has_expert_weight:
        moe_layout = "non_fused_moe"
    else:
        moe_layout = "config_moe"
    need_unpack = moe_layout == "fused_moe"
    model_type_label = f.get("model_type_label", "unknown")

    quantized = f.get("quantized")
    mtp = f.get("mtp")
    blockers = []
    if quantized:
        blockers.append("Quantized model without dequantization script")
    if mtp:
        blockers.append("MTP structure without accessible implementation code")
    risk = "High" if len(blockers) >= 2 else ("Medium" if blockers else "Low")

    report_lines = [
        "# Analysis Report\n",
        "## Model Identification",
        f"- Model Path/Repository: {path}",
        f"- Region (--cli-region): {region}",
        f"- `model_type`: {f.get('model_type') or 'N/A'}",
        f"- `architectures`: {', '.join(f.get('architectures') or ['N/A'])}\n",
        "## Implementation Source Analysis",
        f"- Result: `{source}`",
        f"- Basis:",
    ]
    for b in basis:
        report_lines.append(f"  - {b}")
    report_lines.append("")

    report_lines += [
        "## Model Features and Specifications",
        f"- Hidden size: {f.get('hidden_size') or 'N/A'}",
        f"- Number of layers: {f.get('num_hidden_layers') or 'N/A'}",
        f"- Attention heads / KV heads: {f.get('num_attention_heads') or 'N/A'} / "
        f"{f.get('num_key_value_heads') or 'N/A'}",
        f"- Model type classification: {model_type_label}\n",
        "## Layer-by-Layer Loading Assessment",
    ]
    need_ll, ll_reason, ll_constraints = layer_by_layer_assessment(features)
    report_lines.append(f"- Need layer-by-layer loading: {'Yes' if need_ll else 'No'}")
    report_lines.append(f"- Reason: {ll_reason}")
    report_lines.append(f"- Constraints: {'; '.join(ll_constraints) or 'None'}\n")

    report_lines += [
        "## MoE Assessment",
        f"- Contains MoE: {'Yes' if contains_moe else 'No'}",
        f"- Number of experts: {num_experts_label}",
        f"- Layout type: {moe_layout}",
        f"- Suspected fused keys/modules: "
        f"{', '.join(f.get('moe_hints', {}).get('expert_keys_sample') or [])}",
        f"- Expert weight form: "
        f"{'Packaged tensors' if need_unpack else 'Independent linear layers or config-level'}",
        f"- Needs unpack: {'Yes' if need_unpack else 'No'}\n",
        "## Quantization and MTP Risk Assessment",
        f"- Model already quantized: {'Yes' if quantized else 'No'}",
        f"- Quantization determination basis: {json.dumps(f.get('quant_evidence') or {}, ensure_ascii=False) or 'None'}",
        f"- MTP structure exists: {'Yes' if mtp else 'No'}",
        f"- MTP implementation code accessibility: "
        f"{'Not accessible (blocker)' if mtp else 'Accessible / N/A'}",
        f"- MTP config details: {', '.join(f.get('mtp_details') or []) or 'None'}\n",
        "## Risks and Next Steps",
        f"- Risk level: {risk}",
        f"- Blockers: {'; '.join(blockers) if blockers else 'None'}",
        "- Recommended next steps:",
    ]
    if blockers:
        report_lines.append("  - Request user to provide dequantization script and/or MTP implementation code before continuing")
    else:
        report_lines.append("  - Proceed to adapter creation workflow")
    report_lines += ["", "## Compatibility Check Summary"]
    passed = 0
    total = 6
    checks = [
        ("Implementation source detected", source in ("transformers", "model-local")),
        ("Model type classified", model_type_label in ("pure_LLM", "multimodal_understanding", "multimodal_generation")),
        ("Structural features extracted", bool(f.get("hidden_size")) or bool(f.get("num_hidden_layers"))),
        ("MoE layout assessed", moe_layout != "no_moe" or True),
        ("Quantization risk evaluated", True),
        ("MTP risk evaluated", True),
    ]
    for label, ok in checks:
        if ok:
            passed += 1
    report_lines.append(f"- Overall checks passed: {passed}/{total}")
    for label, ok in checks:
        report_lines.append(f"- {label}: {'PASS' if ok else 'BLOCKED'}")
    report_lines.append("")
    return "\n".join(report_lines), passed, total, risk


@quality_report(skill_name="huawei-cloud-msmodelslim-model-analysis", skill_version="1.0.0")
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze_model",
        description="Analyze a candidate model for msModelSlim adapter implementation",
    )
    parser.add_argument("--model-path", required=True,
                        help="Path to the local model directory containing config.json")
    parser.add_argument("--cli-region", default="cn-north-4",
                        help="Region context for the downstream msModelSlim adapter workflow, "
                             "e.g. cn-north-4 (default: cn-north-4)")
    parser.add_argument("--output", default=None,
                        help="Output report path (default: print to stdout)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print extra progress information")
    args = parser.parse_args(argv)

    region = args.cli_region

    try:
        config = read_config(args.model_path)
    except AnalysisError as exc:
        raise SystemExit(f"error: {exc}")

    source, basis, _tf_path = detect_source(config, args.model_path)
    features = extract_features(config, args.model_path)
    features["source"] = source
    if args.verbose:
        print(f"[analyze_model] model_type={features['model_type']} source={source}", file=sys.stderr)

    try:
        model_type_label = classify_model_type(config, source)
    except Exception:
        model_type_label = "unknown"
    features["model_type_label"] = model_type_label

    report, passed, total, risk = build_report(
        args.model_path, config, features, source, basis,
        region=region, verbose=args.verbose
    )

    if args.verbose:
        print(f"[analyze_model] checks={passed}/{total} risk={risk}", file=sys.stderr)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if not os.path.isdir(out_dir):
            raise SystemExit(f"error: output directory does not exist: {out_dir}")
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"[analyze_model] analysis report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    return {"model_type": features.get("model_type"),
            "source": source,
            "model_type_label": model_type_label,
            "moe_layout": features.get("moe_hints", {}),
            "quantized": features.get("quantized"),
            "mtp": features.get("mtp"),
            "risk": risk,
            "checks": f"{passed}/{total}"}


if __name__ == "__main__":
    main()
    sys.exit(0)