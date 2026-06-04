# AdaptationAdapter RegistrationGuide

in `config/config.ini` middleRegistrationModelandEntry. 

## Examples

```ini
[ModelAdapter]
my_model = MyModel-7B, MyModel-13B

[ModelAdapterEntryPoints]
my_model = msmodelslim.model.my_model.model_adapter:MyModelAdapter
```

Registrationcompletedafter, Must Execute `bash install.sh` InstallationUpdate. 
