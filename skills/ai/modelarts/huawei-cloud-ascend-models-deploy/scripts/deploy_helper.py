#!/usr/bin/env python3
"""
Model deployment helper script - Automatically matches model category and deployment script

Usage:
  python3 deploy_helper.py match <model_name>      → Output match result (JSON)
  python3 deploy_helper.py script <model_name>     → Output deployment script URL
  python3 deploy_helper.py list [category]         → List models (optional category filter)
  python3 deploy_helper.py info <model_name>       → Output model detailed info
  python3 deploy_helper.py command <model> <cards> <port> → Generate deploy command
"""

import json
import sys

# ============================================================
# Model Catalog - Single source of truth
# ============================================================

MODEL_CATALOG = {
    # Large Language Models (LLM)
    "Qwen3-14B": {
        "category": "LLM",
        "min_cards": 1,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "Qwen3-30B-A3B-Instruct-2507": {
        "category": "LLM",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "Qwen3-32B": {
        "category": "LLM",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "Qwen3-235B-A22B-Thinking-2507": {
        "category": "LLM",
        "min_cards": 16,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "Qwen3-235B-A22B-Instruct-2507": {
        "category": "LLM",
        "min_cards": 16,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "DeepSeek-R1-Distill-Llama-70B": {
        "category": "LLM",
        "min_cards": 4,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
    "DeepSeek-V4-Flash-w8a8-mtp": {
        "category": "OpenSource",
        "min_cards": 8,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },

    # Vision-Language (VL)
    "Qwen3-VL-30B-A3B-Instruct": {
        "category": "VL",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },
    "Qwen3-VL-32B-Instruct": {
        "category": "VL",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },
    "Qwen3-VL-235B-A22B-Instruct": {
        "category": "VL",
        "min_cards": 16,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },
    "Qwen3-VL-235B-A22B-Instruct-W8A8": {
        "category": "VL",
        "min_cards": 8,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },

    # Embedding
    "Qwen3-Embedding-8B": {
        "category": "Embedding",
        "min_cards": 1,
        "endpoint": "/v1/embeddings",
        "multimodal": False,
        "single_card_only": True,
    },
    "bge-large-zh-v1.5": {
        "category": "Embedding",
        "min_cards": 1,
        "endpoint": "/v1/embeddings",
        "multimodal": False,
        "single_card_only": True,
    },
    "bge-m3": {
        "category": "Embedding",
        "min_cards": 1,
        "endpoint": "/v1/embeddings",
        "multimodal": False,
        "single_card_only": True,
    },

    # Rerank
    "Qwen3-Reranker-8B": {
        "category": "Rerank",
        "min_cards": 1,
        "endpoint": "/v1/rerank",
        "multimodal": False,
        "single_card_only": True,
    },
    "bge-reranker-v2-m3": {
        "category": "Rerank",
        "min_cards": 1,
        "endpoint": "/v1/rerank",
        "multimodal": False,
        "single_card_only": True,
    },

    # OpenSource
    "Qwen3.6-35B-A3B": {
        "category": "OpenSource",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },
    "Qwen3.6-27B": {
        "category": "OpenSource",
        "min_cards": 2,
        "endpoint": "/v1/chat/completions",
        "multimodal": True,
    },
    "Qwen3-Next-80B-A3B-Instruct": {
        "category": "OpenSource",
        "min_cards": 4,
        "endpoint": "/v1/chat/completions",
        "multimodal": False,
    },
}

# ============================================================
# Deployment Script Mapping - Auto-match by category
# ============================================================

BASE_URL = "https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata"

DEPLOY_SCRIPTS = {
    # LLM / Embedding / Rerank share the same deployment template
    "LLM": {
        "script": "deploy-large-models.sh",
        "url": f"{BASE_URL}/deploy-large-models/single-machine/deploy-large-models.sh",
        "log_prefix": "deploy-large-models.sh",
    },
    "Embedding": {
        "script": "deploy-large-models.sh",
        "url": f"{BASE_URL}/deploy-large-models/single-machine/deploy-large-models.sh",
        "log_prefix": "deploy-large-models.sh",
    },
    "Rerank": {
        "script": "deploy-large-models.sh",
        "url": f"{BASE_URL}/deploy-large-models/single-machine/deploy-large-models.sh",
        "log_prefix": "deploy-large-models.sh",
    },
    # VL multimodal dedicated script
    "VL": {
        "script": "deploy-qwen3-vl-model.sh",
        "url": f"{BASE_URL}/deploy-vl-model/single-machine/deploy-qwen3-vl-model.sh",
        "log_prefix": "deploy-qwen3-vl-model.sh",
    },
    # OpenSource dedicated script
    "OpenSource": {
        "script": "deploy-ai-models.sh",
        "url": f"{BASE_URL}/deploy-large-models/single-machine/open_source/deploy-ai-models.sh",
        "log_prefix": "deploy-ai-models.sh",
    },
}

# ============================================================
# Fuzzy Matching
# ============================================================

def fuzzy_match(input_name: str) -> list:
    """Fuzzy match model name, return candidate list"""
    input_lower = input_name.lower().replace("-", "").replace(" ", "").replace(".", "")
    candidates = []

    for model_name, info in MODEL_CATALOG.items():
        model_lower = model_name.lower().replace("-", "").replace(" ", "").replace(".", "")
        # Exact match
        if input_lower == model_lower:
            return [(model_name, info, 1.0)]
        # Contains match
        if input_lower in model_lower or model_lower in input_lower:
            # Calculate similarity (longer match = higher similarity)
            ratio = min(len(input_lower), len(model_lower)) / max(len(input_lower), len(model_lower))
            candidates.append((model_name, info, ratio))

    # Sort by similarity
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates


def match_model(input_name: str) -> dict:
    """Match model, return complete information"""
    candidates = fuzzy_match(input_name)

    if not candidates:
        return {
            "matched": False,
            "input": input_name,
            "error": f"Model {input_name} not found",
            "available": list(MODEL_CATALOG.keys()),
        }

    model_name, info, score = candidates[0]
    category = info["category"]
    script_info = DEPLOY_SCRIPTS[category]

    return {
        "matched": True,
        "input": input_name,
        "model_name": model_name,
        "category": category,
        "min_cards": info["min_cards"],
        "endpoint": info["endpoint"],
        "multimodal": info["multimodal"],
        "single_card_only": info.get("single_card_only", False),
        "deploy_script": script_info["script"],
        "deploy_url": script_info["url"],
        "score": round(score, 2),
    }


def generate_deploy_command(model_name: str, cards: int, port: int) -> str:
    """Generate deployment command"""
    result = match_model(model_name)
    if not result["matched"]:
        return json.dumps(result, ensure_ascii=False, indent=2)

    script_url = result["deploy_url"]
    script_name = result["deploy_script"]
    actual_model = result["model_name"]
    deploy_dir = "/home/modelarts-agent"

    cmd = (
        f"nohup bash -c 'export model_name={actual_model} && "
        f"export required_cards={cards} && "
        f"export port={port} && "
        f"wget -P {deploy_dir}/ {script_url} && "
        f"chmod 755 {deploy_dir}/{script_name} && "
        f"sh {deploy_dir}/{script_name} ${{model_name}} ${{required_cards}} ${{port}}' "
        f"> {deploy_dir}/deploy_${{model_name}}.log 2>&1 &"
    )
    return cmd


def list_models(category: str = None) -> dict:
    """List models, optional category filter"""
    result = {}
    for model_name, info in MODEL_CATALOG.items():
        cat = info["category"]
        if category and cat.lower() != category.lower():
            continue
        if cat not in result:
            result[cat] = []
        result[cat].append({
            "name": model_name,
            "min_cards": info["min_cards"],
            "multimodal": info["multimodal"],
            "single_card_only": info.get("single_card_only", False),
        })
    return result


# ============================================================
# CLI Entry
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deploy_helper.py <match|script|list|info|command> [args...]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "match":
        if len(sys.argv) < 3:
            print("Usage: python3 deploy_helper.py match <model_name>")
            sys.exit(1)
        result = match_model(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "script":
        if len(sys.argv) < 3:
            print("Usage: python3 deploy_helper.py script <model_name>")
            sys.exit(1)
        result = match_model(sys.argv[2])
        if result["matched"]:
            print(result["deploy_url"])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        result = list_models(category)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "info":
        if len(sys.argv) < 3:
            print("Usage: python3 deploy_helper.py info <model_name>")
            sys.exit(1)
        result = match_model(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "command":
        if len(sys.argv) < 5:
            print("Usage: python3 deploy_helper.py command <model_name> <cards> <port>")
            sys.exit(1)
        cmd = generate_deploy_command(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
        print(cmd)

    else:
        print(f"Unknown action: {action}")
        print("Supported: match, script, list, info, command")
        sys.exit(1)


if __name__ == "__main__":
    main()
