#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click Hermes Deployment - Utility Function Module

Note: This module only supports temporary credentials (temporary AK/SK + security_token).
      Permanent AK/SK credentials are not supported.
"""

import os

REGIONS = {
    "cn-north-4": "华北-北京四",
    "cn-east-3": "华东-上海一",
    "cn-south-1": "华南-广州",
    "cn-southwest-2": "西南-贵阳一",
}

REGION_IDS = list(REGIONS.keys())


def print_region_list():
    """Print region list"""
    print("\nHuawei Cloud Flexus L Instance Supported Regions:")
    print("-" * 50)
    print(f"{'Region ID':<20} {'Region Name':<25}")
    print("-" * 50)
    for region_id, name in REGIONS.items():
        print(f"{region_id:<20} {name:<25}")
    print("-" * 50)


def get_region_id_by_name(input_str: str) -> str:
    """
    Convert user input to standard region ID
    
    Parameters:
        input_str: User input, can be region ID or Chinese name
        
    Returns:
        Standard region ID, returns input string if no match found
    """
    # First check if already a valid region ID
    if input_str in REGION_IDS:
        return input_str
    
    # Try matching by Chinese name
    for region_id, name in REGIONS.items():
        if input_str == name:
            return region_id
        # Support fuzzy matching (e.g., input "Guiyang" only)
        if input_str in name:
            return region_id
    
    return input_str


def prompt_for_input(prompt, required=True, default=None, choices=None, hide_input=False):
    """Interactive prompt for user input"""
    while True:
        if default and choices:
            display_prompt = f"{prompt} [{', '.join(choices)}, default: {default}]: "
        elif default:
            display_prompt = f"{prompt} [default: {default}]: "
        elif choices:
            display_prompt = f"{prompt} [{', '.join(choices)}]: "
        else:
            display_prompt = f"{prompt}: "

        if hide_input:
            try:
                from getpass import getpass
                user_input = getpass(display_prompt).strip()
            except ImportError:
                user_input = input(display_prompt).strip()
        else:
            user_input = input(display_prompt).strip()

        if user_input:
            if choices and user_input not in choices:
                print(f"Invalid option, please choose from: {', '.join(choices)}")
                continue
            return user_input
        elif default:
            return default
        elif not required:
            return None
        else:
            print("This parameter cannot be empty, please enter a value")


def setup_credentials_interactive():
    """Interactive setup for Huawei Cloud temporary credentials (deprecated, use CLI parameters to pass AK/SK/security-token)"""
    print("\nWarning: setup_credentials_interactive is deprecated. Please use CLI parameters --ak, --sk and --security-token to pass credentials")
    print("-" * 40)
    
    ak = prompt_for_input("Huawei Cloud Temporary AK", required=True)
    sk = prompt_for_input("Huawei Cloud Temporary SK", required=True, hide_input=True)
    security_token = prompt_for_input("Huawei Cloud Security Token", required=True, hide_input=True)
    
    print(f"\n✓ Credentials input completed")
    print(f"  AK: {ak[:4]}...{ak[-4:]}")
    print(f"  SK: {'*' * len(sk)}")
    print(f"  Security Token: {'*' * len(security_token)}")
    
    return ak, sk, security_token