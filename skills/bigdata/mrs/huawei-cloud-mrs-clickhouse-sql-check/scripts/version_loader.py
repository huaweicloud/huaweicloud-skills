# -*- coding: utf-8 -*-
"""
ClickHouse SQL Check Skill - Version Loader

Dynamically loads version-specific rule modules (keywords, grammar_rules,
token_types) based on the specified ClickHouse kernel version.

Version-specific rules live in rules/v{version}/ (e.g., v24.8/, v23.3/).
Common rules (spec_rules) live in rules/common/.

Usage:
    from version_loader import load_keywords, load_grammar_rules, load_token_types
    kw = load_keywords("23.3")
"""

import os
import sys
import importlib.util

_this_dir = os.path.dirname(os.path.abspath(__file__))
_rules_dir = os.path.join(_this_dir, '..', 'rules')

# Supported versions (directory names under rules/)
SUPPORTED_VERSIONS = []
for d in os.listdir(_rules_dir):
    if d.startswith('v') and os.path.isdir(os.path.join(_rules_dir, d)):
        SUPPORTED_VERSIONS.append(d[1:])  # strip 'v' prefix
SUPPORTED_VERSIONS.sort()

DEFAULT_VERSION = SUPPORTED_VERSIONS[-1] if SUPPORTED_VERSIONS else "24.8"


def _load_module(version, module_name):
    """Dynamically load a module from the version-specific rules directory."""
    version_dir = os.path.join(_rules_dir, f'v{version}')
    if not os.path.isdir(version_dir):
        raise ValueError(
            f"Unsupported ClickHouse version: {version}. "
            f"Supported: {SUPPORTED_VERSIONS}"
        )
    module_path = os.path.join(version_dir, f'{module_name}.py')
    if not os.path.isfile(module_path):
        raise FileNotFoundError(
            f"Module '{module_name}' not found for version {version}: {module_path}"
        )
    # Use a unique module name to avoid cache collisions between versions
    full_name = f"_ck_v{version}_{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_keywords(version=DEFAULT_VERSION):
    """Load the keywords module for the specified version."""
    return _load_module(version, 'keywords')


def load_grammar_rules(version=DEFAULT_VERSION):
    """Load the grammar_rules module for the specified version."""
    return _load_module(version, 'grammar_rules')


def load_token_types(version=DEFAULT_VERSION):
    """Load the token_types module for the specified version."""
    return _load_module(version, 'token_types')


def load_spec_rules():
    """Load the common spec_rules module (version-independent)."""
    common_dir = os.path.join(_rules_dir, 'common')
    module_path = os.path.join(common_dir, 'spec_rules.py')
    spec = importlib.util.spec_from_file_location('_ck_spec_rules', module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_supported_versions():
    """Return list of supported ClickHouse versions."""
    return list(SUPPORTED_VERSIONS)


if __name__ == "__main__":
    print(f"Supported versions: {SUPPORTED_VERSIONS}")
    print(f"Default version: {DEFAULT_VERSION}")
    for v in SUPPORTED_VERSIONS:
        kw = load_keywords(v)
        gr = load_grammar_rules(v)
        tt = load_token_types(v)
        print(f"  v{v}: keywords={kw.get_keyword_count()}, "
              f"token_types={len(tt.TokenType)}, "
              f"stmt_types={len(gr.StatementType)}")
