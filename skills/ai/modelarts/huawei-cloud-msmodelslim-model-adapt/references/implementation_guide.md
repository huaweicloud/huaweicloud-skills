# AdaptationadapterImplementationGuide

## Directory Structure (Suggest) 

onecountModelAdaptationadapterDirectory Usually Contains at LeastPackagecontainin order tounderfile: 

```text
msmodelslim/model/<model_type>/
├── __init__.py
├── model_adapter.py
└── model.py
```

- `__init__.py`: mustmustkeepin, keepcertifyDirectorycanas Python Packagebeguideinput
- `model_adapter.py`: AdaptationadapterEntryand 5 countmustneedInterfaceImplementation
- `model.py`: ModelStructureRelatedImplementation (ifdistributelayervisitask/previousdirectionassistaidlogiclogic) 

ifresultoughtModelalreadyhaveotherotheraccordingdependfile (if `utils.py`, `configuration_*.py`) , according toactualactualrequiressupplementfill, butnotneedsavestrategy `__init__.py`. 

## mustneedInterface

1. `handle_dataset`
2. `init_model`
3. `generate_model_visit`
4. `generate_model_forward`
5. `enable_kv_cache`

## according toTemplateregiondistribute: LLM / VLM mustneedInterface

in order tounderconclusiontheorybased on `assets/model_adapter_template.py` and `assets/vlm_model_adapter_template.py`. 

### LLM (Decoder-only) 

- **pushrecommendcontinueadmit**: `TransformersModel + ModelSlimPipelineInterfaceV1` (`ModelInfoInterface` canselectbutSuggest) 
- **mustmustImplementation** (5 count) : `handle_dataset`, `init_model`, `generate_model_visit`, `generate_model_forward`, `enable_kv_cache`
- **TemplatemiddleoftenseeassistaidMethod** (nonFrameworkstrongmake, butmultiplenumberModelrequires) : `generate_decoder_layer`, `_decoder_layer_prefix`, `_load_decoder_if_not_exist`, `_create_model_instance`

### VLM (multiplemodelstatemanagesolve, onlyfiguredocumentmanagesolve) 

- **pushrecommendcontinueadmit**: `VLMBaseModelAdapter + ModelSlimPipelineInterfaceV1` (`ModelInfoInterface` canselectbutSuggest) 
- **mustmustImplementation** (5 count) : `handle_dataset`, `init_model`, `generate_model_visit`, `generate_model_forward`, `enable_kv_cache`
- **TemplatemiddleoftenseeassistaidMethod** (nonFrameworkstrongmake, butmultiplenumberModelrequires) : `generate_decoder_layer`, `_load_decoder_if_not_exist`, `_create_model_instance`

## specialspecialsituationsituation (requiressinglealonehandlemanage) 

### LLM specialspecialsituationsituation

- **decoder Pathnotoneconsistent**: notonedefineis `model.layers`, alsocanabilityis `model.decoder.layers` orotherotherPath; mustmustmodify `_decoder_layer_prefix`. 
- **layerstructurecreateparameternumberdifferencedifferent**: havesome block structurecreateadapternotconnectreceive `layer_idx`, needmodify `_load_decoder_if_not_exist` ofactualexampletransformmethods. 
- **MoE packed Weights**: ifas 3D packed experts, needfirst unpack, againsubstituteexchangeaslinepropertylayerspecializedexpertmodelblock. 
- **nonstandardstandardConfigurationcharacterparagraph**: ifno `num_hidden_layers` orcharacterparagraphnamenotsame, `init_model` needaccording toitemstandard config modifycompose. 

### VLM specialspecialsituationsituation

- **Datamustmustfiguredocumentbecomepair**: `handle_dataset` requiressametimehave `text` and `image`, puredocumentthissamplethisnotAdaptationoughtTemplate. 
- **looksense/documentthisPathdifferencedifferent**: Templatefakeset `model.visual` and `model.language_model.layers`, itemstandardModelcanabilitynotsame, needaccording toReal `modeling` modify. 
- **mergematchlogiclogicnotcansetTemplate**: `generate_model_forward` middle image embeds noteinputRules (token id, bitplacecompilecode, mask) Modeldifferencedifferentlarge, mustmustpairalignofficialmethod forward. 
- **text_config Structuredifferencedifferent**: ifnotkeepin `config.text_config`, needmodifyasModelactualactualdocumentthisConfigurationPathandSynchronizationlayernumbercharacterparagraph. 
- **processor travelasdifferencedifferent**: notsameModel `AutoProcessor` ofoutputinputkeyand `apply_chat_template` returnreturncharacterparagraphnotsame, needaccording toRealreturnreturnvalueadjustadjust keys. 

### InterfacefunctionabilityDescription (mustmustfallactualtoCode) 

#### 1) `handle_dataset(dataset, device) -> List[Any]`

- **jobresponsibility**: handlereasonbegincalibratestandardsamplethisconvertbecomeModelcanstraightconnectdisappearcostofoutputinputcolumntable. 
- **outputinput**: reasonbeginDataset (throughoftenisdocumentthis list) anditemstandardDevice. 
- **Output**: `List[Any]`, eachcountunitelementcanstraightconnectUsed foronetimepreviousdirection (if `model(*data)` or `model(**data)`) . 
- **ImplementationSuggest**: optimizefirstcomplexusebasetype tokenization abilityforce (if `_get_tokenized_data`) , keepcertifycharacterparagraphnameandModel forward parameternumberpairalign. 
- **completedjudgedefine**: QuantizationProcessReadoughtcolumntableafter, noneedamountexternalDataconvertexchangeimmediatecanenterinput `generate_model_forward`. 

#### 2) `init_model(device) -> nn.Module`

- **jobresponsibility**: InitializationandreturnreturncanparticipationQuantizationProcessofModelactualexample. 
- **outputinput**: itemstandardDevice (NPU/CPU) . 
- **Output**: `nn.Module` (`eval()` statusstate) . 
- **ImplementationSuggest**: according toModelRealStructureLoad; largeModelcanadoptusedistributelayer/lazyLoad, confirmkeepaftercontinue visit/forward canvisitasktoitemstandardlayer. 
- **completedjudgedefine**: returnreturnModelafter, `generate_model_visit` abilityiteratehistoryitemstandardQuantizationlayer, andpreviousdirectioncanExecute. 

#### 3) `generate_model_visit(model) -> Generator[ProcessRequest, Any, None]`

- **jobresponsibility**: definemeaning“according towhatwhatsequenceorderiteratehistorywhichsomemodelblock”performIterativelayerhandlemanage. 
- **outputinput**: InitializationafterofModel. 
- **Output**: according tosequenceorder `yield ProcessRequest` (eachcount request Correspondingonecountwaithandlemanagemodelblock) . 
- **ImplementationSuggest**: in order toReal decoder/block sequenceorderOutput, notjumplayer, notweightarrange; NamePathshouldcanonlyonedefinebitmodelblock. 
- **completedjudgedefine**: produceoutputoflayerordercolumnand `generate_model_forward` oneoneCorresponding. 

#### 4) `generate_model_forward(model, inputs) -> Generator[ProcessRequest, Any, None]`

- **jobresponsibility**: definemeaningand `visit` pairalignofdistributeparagraphpreviousdirection, Used forIterativelayercalibratestandard. 
- **outputinput**: Model + singleitemcalibratestandardoutputinput. 
- **Output**: according tosequenceorder `yield ProcessRequest` (PackagecontainoughtlayerExecuteallneedoutputinput) . 
- **ImplementationSuggest**: layersequenceorder, distributeparagraphsideboundary, expandamounttransferdeliverPathand `generate_model_visit` strictformatoneconsistent. 
- **completedjudgedefine**: sameonelayerin visit/forward ofsearchleadandlanguagemeaningcompleteallmatchmatch, notoutputappearerrorbit. 

#### 5) `enable_kv_cache(model, need_kv_cache) -> None`

- **jobresponsibility**: statisticsoneControl KV Cache openrelated. 
- **outputinput**: Modelactualexampleandarrangeyouopenrelated. 
- **Output**: noreturnreturn (reasonregionmodifymodify) . 
- **ImplementationSuggest**: optimizefirstcomplexusebasetype `_enable_kv_cache`; arrivefewconfirmkeepmaininterfereModel config middle `use_cache` bepositiveconfirmSet. 
- **completedjudgedefine**: openrelatedafterModeltravelasandpreperiodoneconsistent, calibratestandardScenariosunderthroughoftencanrelatedclosein order todowngradelowMemoryoccupyuse. 

## relatedkeyImplementationreasonrule

### 1) `generate_model_visit` and `generate_model_forward` mustmuststrictformatoneconsistent

- iteratehistorylayersetmatchoneconsistent
- sequenceorderoneconsistent
- distributelayeroutputinputOutputtransferdeliveroneconsistent

thisismostcontenteasyoutputerror, alsomostshadowloudQuantizationpositiveconfirmpropertyofpartdistribute. 

### 2) notneedrelyModelnameguessStructure

mustmustin order toReal `modeling` Codeasstandard, ConfirmlayerPath, commandnameand forward travelasafteragaincomposeAdaptationadapter. 

### 3) VLM onlywalk“looksenseadjustbody + documentthisIterativelayer”

- optimizefirstcomplexuse VLM basetype
- visit/forward middlelooksensemodelblockanddocumentthislayersequenceorderkeepmaintainoneconsistent
- figuredocumentmergematchlogiclogicneedpairalignitemstandardModelofficialmethod forward

### 4) MoE mergematchStructureoptimizefirstaccording to“unpack afterpurelinepropertylayer”Adaptation

verymultiplenewModelof MoE Usagemergematch/printPackageWeights (oftenseeas 3D expandamount) , andQuantizationandIterativelayerhandlemanagethroughoftenupdatesuitablematch `nn.Linear` shapeformulaofspecializedexpertImplementation. 

ImplementationRequirements: 
- firstjudgejudgereasonbeginImplementationiswhetheras 3D packed experts (notneedfakesetallhave MoE allonesample) 
- ifis packed Structure, notonlyneedinLoadtime unpack, alsoneedImplementationCorrespondingof MoE splitdistribute module
- unpack afterspecializedexpertshouldfalltopurelinepropertylayer (`gate_proj` / `up_proj` / `down_proj`) , avoidavoidaftercontinueProcessstraightconnectaccordingdepend 3D Weights
- pushrecommendStructure: `moe_utils.py` Providessplitdistributeafterof MoE module, `model_adapter.py` negativeresponsibilityWeights unpack andmodelblocksubstituteexchange

canReference `qwen3_5` ofImplementationthinkpath (`moe_utils.py`, `modeling_qwen3_5_mtp.py`) : firstrecognizecategory packed Weights, againsplitdistributeasIterative expert linepropertylayer. 

ExamplesCodepleaseReference: 
- `references/moe_unpacked_module_example.py`
- `references/moe_unpacked_adapter_example.py`
