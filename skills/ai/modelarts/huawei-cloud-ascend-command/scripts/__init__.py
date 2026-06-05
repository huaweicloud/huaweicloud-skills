"""
Ascend NPU Management Skill Module
"""

from .npu_client import NpuClient
from .executor import NpuExecutor

__all__ = ['NpuClient', 'NpuExecutor']
__version__ = '2.0.0'
