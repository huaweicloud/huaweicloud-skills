# AdaptationadapterVerificationGuide

## CoreVerificationProcess (mustmust)

mustmustExecute in Orderin order tounderfourstepVerification: 

1. **GenerateTestingModel** (Step 1)
   - VerificationModelLoadandBasicConfiguration
   - Generate Random WeightsofsmalltypeModelUsed forrapidspeedTesting
2. **allFallbackQuantization** (Step 2)
   - VerificationQuantizationProcessiswhetherabilityrunthrough (notinvolveandtoolbodyprecisiondegree, onlyrunthroughProcess) 
   - Check `model_adapter` Registrationiswhetherlivevalid
3. **allFallbackModeloneconsistentpropertyandcanLoad/keepkeepVerification** (Step 3)
   - based on Step2 GenerateofallFallbackModel, Verificationotherand Step1 floatpointModelWeightsstrictformatoneconsistent (key, shapestatus, numbervalue) 
   - VerificationoughtModelproduceobjecttoolpreparecompleteadjustLoad/keepkeepabilityforce (canbeaftercontinueProcessReadandcontinuecontinuehandlemanage) 
4. **actualactualQuantizationProcessVerification** (Step 4)
   - Runactualactual W8A8 quietstate/movestateQuantizationProcess (nonFallbackProcess) andproduceoutputQuantizationResult
   - VerificationQuantizationDescriptionfilewhether matchespreperiodRules, ChecklinepropertylayerQuantizationstandardsigniswhetherpositiveconfirm

## Verificationcommandcommand

```bash
# 1) GenerateTestingModel
python scripts/step1_generate_test_model.py \
  --model-path /path/to/your/model \
  --output-path /tmp/test_model

# 2) allFallbackQuantization
python scripts/step2_run_quantization.py \
  --model-path /tmp/test_model \
  --output-path /tmp/quantized_model \
  --model-type YourModelType \
  --model-family llm

# multiplemodelstateModelpleaseUsage:
#   --model-family vlm

# 3) allFallbackModeloneconsistentpropertyVerification (andfloatpointWeightsstrictformatpairalign) 
python scripts/step3_verify_weights.py \
  --original-path /tmp/test_model \
  --quantized-path /tmp/quantized_model \
  --tolerance 1e-5
```

### Step 4: allModelQuantizationCheck

ExecuteallModel W8A8 quietstateQuantizationandCheckDescriptionfile: 

```bash
# ExecuteQuantization
msmodelslim quant \
  --model_type <your_model_type> \
  --model_path /tmp/test_model \
  --save_path /tmp/quantized_w8a8_static \
  --device cpu \
  --config_path references/llm/w8a8_static_full_model.yaml \
  --trust_remote_code True

# VerificationDescriptionfile
python scripts/step4_verify_quant_description.py \
  --desc-path /tmp/quantized_w8a8_static \
  --rules-path /path/to/your_verify_rules_static.json
```

ExecuteallModel W8A8 movestateQuantizationandCheckDescriptionfile: 

```bash
# ExecuteQuantization
msmodelslim quant \
  --model_type <your_model_type> \
  --model_path /tmp/test_model \
  --save_path /tmp/quantized_w8a8_dynamic \
  --device cpu \
  --config_path references/llm/w8a8_dynamic_full_model.yaml \
  --trust_remote_code True

# VerificationDescriptionfile
python scripts/step4_verify_quant_description.py \
  --desc-path /tmp/quantized_w8a8_dynamic \
  --rules-path /path/to/your_verify_rules_dynamic.json
```

multiplemodelstateModel (VLM) SuggestUsagein order tounderConfigurationTemplate (containcalibratestandardDatacharacterparagraph) : 

```bash
references/vlm/w8a8_static_full_model.yaml
references/vlm/w8a8_dynamic_full_model.yaml
```

Description: notagaininsideplace `verify_rules_w8a8_static.json` / `verify_rules_w8a8_dynamic.json`, please agent according toitemstandardModellayernameselftravelGenerateRules Fileandtransferinput `--rules-path`. 

## throughexceedstandardstandard

- **CoreVerification**: Step 1/2/3/4 averagebecomefunctionExecutenoreporterror. 
- **Step 3 throughexceedPrerequisites**: allFallbackModelandfloatpointModelWeightsCheck PASS, andQuantizationproduceobjectcanbeaftercontinueProcesspositiveoftenLoad/Usage. 
- **Step 4 throughexceedPrerequisites**: actualactualQuantizationProcessExecutebecomefunction, DescriptionfileRulescalibrateverifythroughexceed. 

## rapidspeedarrangeerror / lossfailuredistributeflow

- **Step 1 lossfailure**: 
  - ModelLoadlossfailure: Check `transformers` Versionor `trust_remote_code` Set
  - typetypenotSupport: Check `model_type` iswhetherinSupportcolumntablemiddle
- **Step 2 lossfailure**: 
  - findnottoAdaptationadapter: Check `config.ini` Registrationiswhetherpositiveconfirm, iswhetherExecutecompleted `install.sh`
  - QuantizationEntryreporterror: Check `handle_dataset` Datahandlemanageiswhetherpositiveconfirm
- **Step 3 lossfailure (allFallbackModelandfloatpointnotoneconsistent/notcancompleteadjustLoad)**: 
  - CheckQuantizationbefore and afterWeightskeyname, shapestatusandreflectshootrelatedsystem (shouldoneoneCorresponding) 
  - Checknumbervaluedifferencedifferentiswhetherexceedoutputthresholdvalue (silentrecognize `tolerance=1e-5`) 
  - CheckQuantizationDirectoryinsideWeightsandmustneedConfigurationfileiswhethercompleteadjust, confirmkeepcanbeaftercontinueProcessRead
  - **MoE Model**: ifUsage packed Weights, Check `packed -> unpacked` splitdistributelogiclogiciswhetherpositiveconfirm (dimensiondegree, convertplace) 
- **Step 4 lossfailure (actualactualQuantizationProcessorDescriptionfiledifferentoften)**: 
  - CheckactualactualQuantizationConfigurationiswhetherpositiveconfirm (W8A8 quietstate/movestate, calibratestandardparameternumberetc) 
  - CheckiswhethererrorusecompletedFallbackConfiguration
  - CheckVerificationRules JSON middleofrelatedkeycharacteriswhethercovercovercompletedModelactualactuallayername
