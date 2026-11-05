# Analysis Checklist

Use this checklist before implementing model adaptation.

## 1. Implementation Source

- [ ] Read `config.json`
- [ ] Parse only one kind of source:

  - [ ] `transformers/models/<model_type>/modeling_<model_type>.py`
  - [ ] Through `auto_map` defined in model directory `modeling_*.py`

- [ ] If no method parsed, stop and require user to provide implementation code

## 2. Model Type, Structural Differences and Connections

(relative to common Qwen2)

- [ ] Determine model type: pure LLM / multimodal understanding /
      multimodal generation
- [ ] If multimodal understanding, confirm only analyzing text backbone scope
- [ ] If multimodal generation, mark as not supported and stop adaptation
- [ ] Document special structures vs common Qwen2 and their impact
- [ ] Document special structure connections (location, dependencies,
      serial/parallel/residual) and impact on traversal/forward

## 3. Structural Features

- [ ] Confirm decoder layer type
- [ ] Confirm attention and MLP module naming
- [ ] Confirm forward signature and key return values
- [ ] Confirm layer container path for traversal

## 4. Layer-by-Layer Loading Requirements

- [ ] Evaluate total loading memory and runtime environment
- [ ] Determine if layer-by-layer loading is required
- [ ] Document constraints and impact

## 5. MoE Fused Weight Risk

- [ ] Check if model contains MoE
- [ ] If contains MoE, check expert weight layout (independent linear layers
      vs packaged tensors)
- [ ] Check if `gate/up/down` are packaged as 3D weights along expert dimension
- [ ] Mark as: no MoE / MoE non-fused / MoE fused
- [ ] Document if unpack is required

## 6. Adaptation Impact Points

- [ ] Document `generate_model_visit` traversal sequence
- [ ] Document `generate_model_forward` alignment constraints
- [ ] Output impact on weight consistency verification

## 7. Quantized Model Risk (Dequantization Script)

- [ ] Check if model is "already quantized"
- [ ] If already quantized, require user to provide dequantization script
- [ ] If user cannot provide script, mark as blocker and stop adaptation

## 8. MTP Structure Risk (Implementation Missing)

- [ ] Check if model contains MTP structure
- [ ] If contains MTP, check if implementation code is accessible
- [ ] If no implementation code, clearly report that agent cannot fully
      implement MTP structure adaptation
- [ ] If user wants to continue, inform user they need to manually handle
      MTP weights
