#!/usr/bin/env python3
"""
ModelStructureAnalysisScripts
AnalysisModelArchitecturetypetype, judgejudge msmodelslim Compatibility
"""

import argparse
import json


def analyze_model(model_path: str) -> dict:
    """
    AnalysisModelStructure
    
    Args:
        model_path: ModelPathorName
        
    Returns:
        AnalysisResultDictionary
    """
    result = {
        'model_path': model_path,
        'architecture': None,
        'params_count': None,
        'msmodelslim_compatible': None,
        'migration_route': None,
        'details': {}
    }
    
    # attempttryguideinputModel
    try:
        # Checkiswhetheris transformers Model
        from transformers import AutoConfig, AutoModel
        
        try:
            config = AutoConfig.from_pretrained(model_path)
            result['details']['source'] = 'transformers'
            result['details']['model_type'] = getattr(config, 'model_type', 'unknown')
            
            # judgejudgeArchitecturetypetype
            model_type = config.model_type.lower() if hasattr(config, 'model_type') else ''
            
            # Decoder-only LLM
            decoder_only_types = ['llama', 'qwen', 'mistral', 'gemma', 'deepseek', 'phi', 'yi']
            if any(t in model_type for t in decoder_only_types):
                result['architecture'] = 'Decoder-only LLM'
                result['msmodelslim_compatible'] = True
                result['migration_route'] = 'msmodelslim-model-adapt'
            
            # Encoder-only
            encoder_only_types = ['bert', 'roberta', 'deberta', 'electra', 'resnet', 'vit']
            if any(t in model_type for t in encoder_only_types):
                result['architecture'] = 'Encoder-only'
                result['msmodelslim_compatible'] = False
                result['migration_route'] = 'torch_npu straightconnectMigration'
            
            # Encoder-Decoder
            enc_dec_types = ['t5', 'bart', 'pegasus', 'encoder-decoder']
            if any(t in model_type for t in enc_dec_types):
                result['architecture'] = 'Encoder-Decoder'
                result['msmodelslim_compatible'] = False
                result['migration_route'] = 'torch_npu straightconnectMigration'
            
            # VLM
            vlm_types = ['llava', 'qwen-vl', 'internvl', 'cogvlm']
            if any(t in model_type for t in vlm_types):
                result['architecture'] = 'Vision-Language Model'
                result['msmodelslim_compatible'] = True  # documentthismaininterferecanuse
                result['migration_route'] = 'msmodelslim-model-adapt (documentthismaininterfere)'
                
        except Exception as e:
            result['details']['transformers_error'] = str(e)
            
    except ImportError:
        result['details']['transformers'] = 'not installed'
    
    # Checkiswhetheris ultralytics (YOLO) Model
    if 'yolo' in model_path.lower() or 'ultralytics' in model_path.lower():
        result['architecture'] = 'Detection Model (YOLO)'
        result['msmodelslim_compatible'] = False
        result['migration_route'] = 'torch_npu straightconnectMigration'
        result['details']['source'] = 'ultralytics'
    
    # ifresultalsononeDetermine, silentrecognizeas torch_npu Migration
    if result['migration_route'] is None:
        result['architecture'] = 'Unknown'
        result['msmodelslim_compatible'] = False
        result['migration_route'] = 'torch_npu straightconnectMigration (SuggestfirstAnalysis)'
    
    return result


def print_report(result: dict):
    """printprintAnalysisReport"""
    print("=" * 60)
    print("ModelStructureAnalysisReport")
    print("=" * 60)
    print()
    
    print(" [Basicinformationinformation] ")
    print(f"  ModelPath: {result['model_path']}")
    print(f"  Architecturetypetype: {result['architecture']}")
    if result['details'].get('source'):
        print(f"  Source: {result['details']['source']}")
    if result['details'].get('model_type'):
        print(f"  Modeltypetype: {result['details']['model_type']}")
    print()
    
    print(" [msmodelslim Compatibility] ")
    compatible = result['msmodelslim_compatible']
    status = "✅ Support" if compatible else "❌ notSupport"
    print(f"  statusstate: {status}")
    print()
    
    print(" [MigrationSuggest] ")
    print(f"  pushrecommendpathline: {result['migration_route']}")
    
    if not compatible:
        print()
        print("  reasoncause: oughtModelArchitecturenotin msmodelslim Supportrangescopeinside")
        print("  msmodelslim Support: Decoder-only LLM, managesolvetype VLM documentthismaininterfere")
        print("  thisModelneedUsage torch_npu straightconnectMigrationpathline")
    
    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='ModelStructureAnalysis')
    parser.add_argument('model_path', help='ModelPathorName')
    parser.add_argument('--json', action='store_true', help='Output JSON formatformula')
    args = parser.parse_args()
    
    result = analyze_model(args.model_path)
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_report(result)


if __name__ == '__main__':
    main()
