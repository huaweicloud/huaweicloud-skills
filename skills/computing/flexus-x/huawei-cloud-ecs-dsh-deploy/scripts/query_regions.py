#!/usr/bin/env python3
"""
Query supported Huawei Cloud regions and Flexus X instance flavors for dsh deployment.
"""

import sys


def main():
    from utils import show_supported_regions
    show_supported_regions()


if __name__ == "__main__":
    main()
