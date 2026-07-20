#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud ModelArts MaaS Model Integration Module
"""

import os
import sys
import time

# Add project root to Python path to import scripts modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import get_admin_session, install_configure_and_add_models
from scripts.utils import prompt_for_input


# ========== Scenario 1: Add Custom Large Models ==========
def do_install_maas(args):
    """Integrate Huawei Cloud ModelArts MaaS models"""
    print("=" * 60)
    print("Scenario: Integrate Huawei Cloud MaaS Models")
    print("=" * 60)

    flexusagent_base_url = getattr(args, 'flexusagent_base_url', None) or prompt_for_input("FlexusAgent Web UI URL (e.g. http://IP:80):", required=True)
    flexusagent_email = getattr(args, 'flexusagent_email', None) or prompt_for_input("FlexusAgent admin email:", required=True)
    flexusagent_password = getattr(args, 'flexusagent_password', None) or prompt_for_input("FlexusAgent admin password:", required=True, hide_input=True)
    maas_api_key = getattr(args, 'maas_api_key', None) or prompt_for_input("MaaS API key:", required=True, hide_input=True)

    # Confirm deployment (skip confirmation in non-interactive mode)
    non_interactive = getattr(args, 'non_interactive', False)
    if not non_interactive:
        confirm = prompt_for_input("Confirm deployment?", required=False, default="y", choices=["y", "n"])
        if confirm.lower() != "y":
            print("\nDeployment cancelled")
            return
    else:
        print("  Non-interactive mode: Auto-confirm")

    try:
        session = get_admin_session(flexusagent_base_url, flexusagent_email, flexusagent_password)
        print(f"✓ FlexusAgent login successful\n")

        result = install_configure_and_add_models(
            base_url=flexusagent_base_url,
            session=session,
            plugin_id="langgenius/maas",
            credential_schema={"api_key": maas_api_key}
        )

        print(f"\n{'=' * 40}\nIntegration Result:")
        print(f"  Plugin: {result.get('provider_name', 'langgenius/maas')}")
        print("  ✓ Plugin installation and credential configuration completed")
            
    except Exception as e:
        print(f"✗ Process execution failed: {str(e)}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Huawei Cloud FlexusAgent Model Integration Tool")
    parser.add_argument('--flexusagent-base-url', type=str, help='FlexusAgent Web UI URL')
    parser.add_argument('--flexusagent-email', type=str, help='FlexusAgent admin email')
    parser.add_argument('--flexusagent-password', type=str, help='FlexusAgent admin password')
    parser.add_argument('--maas-api-key', type=str, help='ModelArts MaaS API Key')

    do_install_maas(parser.parse_args())
