# ModelStructureAnalysisGuide

## 1. ConfirmModelStructure Source

- Read `config.json` of `model_type`, `architectures`, `auto_map`
- Determine Structure SourceModelRepository `modeling_*.py` alsois transformers officialmethodImplementation

## 2. definebitandreviewreadModelImplementation (mustmust) 

- **CustomImplementation**: ifresult `auto_map` fingerdirectionCustomImplementation (if `modeling_xxx.XXXForCausalLM`) , optimizefirstreviewreadModelDirectorymiddleof `modeling_*.py`
- **officialmethodImplementation**: ifresultUsage transformers officialmethodImplementation, throughoftenin: 
  - sourcecodePath: `transformers/src/transformers/models/<model_type>/modeling_<model_type>.py`
  - guideinputPath: `transformers.models.<model_type>.modeling_<model_type>`
- **weightpointreviewread**: 
  - DecoderLayer definemeaning
  - attention/MLP commandname
  - `forward` inputparticipationreturnreturnvalue
- **MoE ModelamountexternalCheck**: 
  - `experts` Weightsiswhetheras 3D packed Structure (if `experts.gate_up_proj` / `experts.down_proj`) 
