#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
VerificationProcessSteps4: VerificationQuantizationDescriptionfile
rootdataRules FileCheck quant_weight_description.json middleoflayerQuantizationtypetypewhether matchespreperiod. 
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any

def load_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_description_file(path: str) -> str:
    """infingerdefinePathsearchfindDescriptionfile"""
    if os.path.isfile(path):
        return path
    
    p = os.path.join(path, "quant_weight_description.json")

    if os.path.exists(p):
        return p
            
    return None

def verify_description(desc_path: str, rules_path: str) -> bool:
    print("=" * 60)
    print("Steps4: VerificationQuantizationDescriptionfile")
    print("=" * 60)
    
    # 1. searchfindandLoadDescriptionfile
    real_desc_path = find_description_file(desc_path)
    if not real_desc_path:
        print(f"[ERROR] notfindtoQuantizationDescriptionfile (inPath: {desc_path})")
        print("  periodexpectedfile: quant_weight_description.json or quant_model_description.json")
        return False
        
    print(f"[INFO] Descriptionfile: {real_desc_path}")
    try:
        desc_data = load_json(real_desc_path)
    except Exception as e:
        print(f"[ERROR] LoadDescriptionfilelossfailure: {e}")
        return False

    if not isinstance(desc_data, dict):
        print(f"[ERROR] Descriptionfileformatformulaerrorerror: periodexpectedas JSON Object (dict)")
        return False

    # 2. LoadRules File
    print(f"[INFO] Rules File: {rules_path}")
    if not os.path.exists(rules_path):
        print(f"[ERROR] Rules Filenotkeepin: {rules_path}")
        return False
        
    try:
        rules = load_json(rules_path)
    except Exception as e:
        print(f"[ERROR] LoadRules Filelossfailure: {e}")
        return False
        
    if not isinstance(rules, list):
        print(f"[ERROR] Rules Fileformatformulaerrorerror: periodexpectedas JSON Array (list)")
        return False

    # 3. Executecalibrateverify
    print("\n[CHECK] openbeginmatchmatchRules...")
    all_passed = True
    total_checked_keys = 0
    
    for i, rule in enumerate(rules):
        quant_type = rule.get("quant_type")
        keywords = rule.get("keywords", [])
        
        if not quant_type or not keywords:
            print(f"[WARNING] Rules #{i+1} formatformulanovalid (Missing quant_type or keywords), jumpexceed")
            continue
            
        print(f"  > Rules #{i+1}: periodexpectedPackagecontain {keywords} ofWeightsas '{quant_type}'")
        
        matched_keys = []
        failed_keys = []
        
        # iteratehistoryDescriptionfilemiddleofallhavekey
        for key, value in desc_data.items():
            # onlyCheckWeightsfile (throughoftenin order to .weight conclusiontail), avoidavoidCheck bias orotherotherattributeproperty
            # If UserRulesinsideclearconfirmcomposecompletednotbandwidth .weight ofrelatedkeycharacter, thisinsidealsoCompatibility
            if not isinstance(key, str):
                continue
                
            # Checkiswhethermatchmatchanyonerelatedkeycharacter
            is_match = False
            for kw in keywords:
                if kw in key:
                    is_match = True
                    break
            
            if is_match:
                # silentrecognizeonlyCheck .weight conclusiontailofkey, dividenonRulesinsidedisplayformulaPackagecontain bias etc
                # thisinsideascompletedthroughuseproperty, IpeoplefakesetuseuserProvidesof keyword footenoughtoolbody, orwhosilentrecognizeexceedfilternon weight
                # modifyenterstrategystrategy: ifresult key Packagecontain keyword, thenperformCheck
                
                # strictformatCheckvalue
                if value != quant_type:
                    failed_keys.append((key, value))
                else:
                    matched_keys.append(key)

        total_checked_keys += len(matched_keys) + len(failed_keys)
        
        if failed_keys:
            all_passed = False
            print(f"    [FAILED] issueappear {len(failed_keys)} countnotmatchmatchitem (expandshowprevious10count):")
            for k, v in failed_keys[:10]:
                print(f"      - {k}: actualactualvalue='{v}', periodexpectedvalue='{quant_type}'")
            if len(failed_keys) > 10:
                print(f"      ... alsohave {len(failed_keys) - 10} count")
        elif not matched_keys:
            print(f"    [WARNING] notfindtomatchmatchoughtRulesrelatedkeycharacterofanywhatWeightskey (canabilityisrelatedkeycharacterhaveerror?)")
        else:
            print(f"    [OK] {len(matched_keys)} countWeightsitemVerificationthroughexceed")

    print("-" * 60)
    if all_passed and total_checked_keys > 0:
        print(f"[SUCCESS] Verificationthroughexceed! allhavematchmatchitemaveragecharactermatchpreperiodQuantizationtypetype. ")
        return True
    elif total_checked_keys == 0:
        print(f"[FAILED] Verificationlossfailure: notmatchmatchtoanywhatcharactermatchRulesofWeightsitem, pleaseCheckRulesrelatedkeycharacter. ")
        return False
    else:
        print(f"[FAILED] Verificationlossfailure: keepinQuantizationtypetypenotmatchmatchofWeightsitem. ")
        return False

def main():
    parser = argparse.ArgumentParser(description="VerificationQuantizationDescriptionfileinsidecontent")
    parser.add_argument("--desc-path", required=True, help="QuantizationOutputDirectoryorDescriptionfilePath")
    parser.add_argument("--rules-path", required=True, help="calibrateverifyRulesJSONfilePath")
    
    args = parser.parse_args()
    
    success = verify_description(args.desc_path, args.rules_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
