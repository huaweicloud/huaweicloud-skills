#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Utility Functions Module
"""

import os

REGIONS = {
    "cn-north-4": "North China - Beijing 4",
    "cn-east-3": "East China - Shanghai 1",
    "cn-south-1": "South China - Guangzhou",
    "cn-southwest-2": "Southwest China - Guiyang 1",
}

REGION_IDS = list(REGIONS.keys())


def print_region_list():
    """Print region list"""
    print("\nSupported regions for Huawei Cloud Flexus L Instance:")
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
        input_str: User input, can be region ID or region name
    
    Returns:
        Standard region ID, returns original input if not matched
    """
    if input_str in REGION_IDS:
        return input_str
    
    for region_id, name in REGIONS.items():
        if input_str == name:
            return region_id
        if input_str in name:
            return region_id
    
    return input_str


def prompt_for_input(prompt, required=True, default=None, choices=None, hide_input=False):
    """
    Prompt user for input interactively
    
    Parameters:
        prompt: Prompt message
        required: Whether input is required, default True
        default: Default value, optional
        choices: List of valid choices, optional
        hide_input: Whether to hide input (for passwords), default False
    
    Returns:
        str: User input value
    """
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
            print("This field cannot be empty, please enter a value")


def setup_credentials_interactive():
    """
    Set up Huawei Cloud temporary credentials interactively
    
    Returns:
        tuple: (ak, sk, security_token, region) credential tuple
    """
    print("\nPlease configure Huawei Cloud temporary credentials:")
    print("-" * 40)
    
    ak = prompt_for_input("Huawei Cloud Temporary AK: HW_ACCESS_KEY", required=True)
    sk = prompt_for_input("Huawei Cloud Temporary SK: HW_SECRET_KEY", required=True, hide_input=True)
    security_token = prompt_for_input("Huawei Cloud Security Token (required for temp credentials)", required=True)
    region = prompt_for_input("Region ID", required=False, default="cn-north-4")
    
    print(f"\n[OK] Temporary credentials configured")
    print(f"  AK: {ak[:4]}...{ak[-4:]}")
    print(f"  SK: {'*' * len(sk)}")
    print(f"  Security Token: {'*' * len(security_token)}")
    print(f"  Region: {region} ({REGIONS.get(region, '')})")
    
    return ak, sk, security_token, region
