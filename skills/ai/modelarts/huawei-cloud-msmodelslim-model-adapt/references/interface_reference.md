# ModelAdaptationBase InterfaceReference

thisDocumentsKeep OnlyModelAdaptationDevelopmentRequiredBase Interface.   
Does Not Include SmoothQuant, QuaRot, FA3, FlatQuant etchighlevelcomputemethodInterface. 

## 1) IModel (BaseModelattributeproperty) 

**bitplace**: `msmodelslim/model/interface.py`

allhaveAdaptationadapterofBaseattributepropertyInterface: 

```python
class IModel:
    @property
    def model_type(self) -> str

    @property
    def model_path(self) -> Path

    @property
    def trust_remote_code(self) -> bool
```

ImplementationRequirements: 
- `model_type`: returnreturnModeltypetypestandardrecognize. 
- `model_path`: returnreturnModelDirectoryPath. 
- `trust_remote_code`: returnreturniswhetherallowallowfarprocessCode. 

## 2) ModelSlimPipelineInterfaceV1 (mustneed) 

**bitplace**: `msmodelslim/core/runner/pipeline_interface.py`

BaseQuantizationAdaptationmustmustImplementationofCoreInterface: 

```python
class PipelineInterface(IModel):
    @abstractmethod
    def handle_dataset(self, dataset: Any, device: DeviceType = DeviceType.NPU) -> List[Any]:
        ...

    @abstractmethod
    def init_model(self, device: DeviceType = DeviceType.NPU) -> nn.Module:
        ...

    @abstractmethod
    def generate_model_visit(self, model: nn.Module) -> Generator[ProcessRequest, Any, None]:
        ...

    @abstractmethod
    def generate_model_forward(self, model: nn.Module, inputs: Any) -> Generator[ProcessRequest, Any, None]:
        ...

    @abstractmethod
    def enable_kv_cache(self, model: nn.Module, need_kv_cache: bool) -> None:
        ...
```

Implementationweightpoint: 
- `generate_model_visit` and `generate_model_forward` oflayersequenceordermustmuststrictformatoneconsistent. 
- `handle_dataset` OutputmustmustcanstraightconnectUsed forpreviousdirection. 
- `init_model` returnreturncanExecutepreviousdirectionandcanbeIterativelayervisitaskofModel. 

## 3) ModelInfoInterface (pushrecommend) 

**bitplace**: `msmodelslim/app/naive_quantization/model_info_interface.py`  
 (partdistributeScenariosalsoin `msmodelslim/app/auto_tuning/model_info_interface.py` Usage) 

Used forProvidesModelBaseinformationinformation: 

```python
def get_model_pedigree(self) -> str
def get_model_type(self) -> str
```

Description: 
- oughtInterfacethroughoftenand `TransformersModel + ModelSlimPipelineInterfaceV1` groupmatchUsage. 
- ifyouofAdaptationProcessorguideoutputProcessaccordingdependModelexpertfamilyinformationinformation, SuggestImplementation. 

## pushrecommendcontinueadmitgroupmatch

BaseModelAdaptation (LLM/VLM documentthismaininterfere) Suggest: 

```python
class MyModelAdapter(TransformersModel,
                     ModelInfoInterface,
                     ModelSlimPipelineInterfaceV1):
    pass
```

ifwhenpreviousScenariosnotrequiresModelinformationinformationabilityforce, cansavestrategy `ModelInfoInterface`, but `ModelSlimPipelineInterfaceV1` notcansavestrategy. 
