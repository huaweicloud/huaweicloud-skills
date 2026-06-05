# mustneedInterfaceCheckChecklist

inrunVerificationprevious, Confirmin order tounderMethodalreadyImplementationandCorrect Integration: 

- [ ] `handle_dataset`
- [ ] `init_model`
- [ ] `generate_model_visit`
- [ ] `generate_model_forward`
- [ ] `enable_kv_cache`

## pairalignCheck

- [ ] `generate_model_visit` and `generate_model_forward` iteratehistoryoflayeroneconsistent
- [ ] iteratehistorysequenceorderoneconsistent
- [ ] layerbetweenoutputinputOutputtransferdeliveroneconsistent

## RegistrationCheck

- [ ] `config/config.ini` of `[ModelAdapter]` underalreadyConfigurationModelcategoryname
- [ ] `config/config.ini` of `[ModelAdapterEntryPoints]` underalreadyConfigurationEntry
- [ ] CodemodifymodifyafteralreadyweightnewInstallationPackage
