"""VLA NPU Patcher configuration.

Centrally manages all hardcoded values and patterns.
Adapted from ascend-driving-patcher: removed the autonomous-driving-specific
config, added VLA-specific config (transformers, accelerate).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PatcherConfig:
    """Central configuration for the VLA NPU patcher."""

    # =========================================================================
    # Directory/file exclusions
    # =========================================================================
    exclude_dirs: set[str] = field(default_factory=lambda: {
        'venv', '.venv', 'env', '.env', 'site-packages',
        '__pycache__', '.git', 'build', 'dist', 'node_modules',
    })

    # =========================================================================
    # dict/list variable-name hints (for heuristics)
    # =========================================================================
    dict_name_hints: tuple[str, ...] = field(default_factory=lambda: (
        'dict', 'map', 'mapping', 'lookup', 'cache', 'registry',
        'losses', 'info', 'meta', 'cfg', 'config',
    ))
    list_name_hints: tuple[str, ...] = field(default_factory=lambda: (
        'list', 'array', 'seq', 'items', 'batch', 'samples',
        'traj', 'idxes', 'indexes', 'inds',
    ))

    # =========================================================================
    # Test-file patterns (to skip)
    # =========================================================================
    test_file_patterns: tuple[str, ...] = field(default_factory=lambda: (
        'test', 'tests', '_test.py', 'test_', 'conftest',
    ))

    # =========================================================================
    # Tensor-value hints (for detecting tensor expressions)
    # =========================================================================
    tensor_value_hints: tuple[str, ...] = field(default_factory=lambda: (
        'torch.', '.to(', '.cuda', '.npu', '.float()',
        '.detach', '.view', '.reshape', '.squeeze',
        '.gather', '.scatter', '.index_select', '.cat(',
    ))

    # =========================================================================
    # Context window sizes (unified config)
    # =========================================================================
    context_windows: dict[str, dict[str, int]] = field(default_factory=dict)

    # =========================================================================
    # Other scan parameters
    # =========================================================================
    dict_check_context_lines: int = 30
    data_load_sample_count: int = 3
    import_search_lines: int = 50
    lookahead_lines: int = 6
    nearby_context_lines: int = 10
    function_scan_lines: int = 40
    entry_guard_lines: int = 20

    # =========================================================================
    # Lookahead/nearby scan parameters
    # =========================================================================
    tgt_func_scan_lines: int = 40
    var_source_max_backward: int = 50
    code_snippet_length: int = 100
    max_syntax_errors_shown: int = 5

    # =========================================================================
    # Scan options
    # =========================================================================
    model_build_timeout: int = 60
    data_load_timeout: int = 600
    runtime_check_timeout: int = 30
    syntax_check_timeout: int = 10
    import_check_timeout: int = 10

    # =========================================================================
    # Config-file search patterns (for verify.py auto-detection)
    # VLA models use JSON/YAML configs, not mmcv .py configs
    # =========================================================================
    config_search_patterns: tuple[str, ...] = field(default_factory=lambda: (
        '**/config.json',
        '**/config.yaml',
        '**/config.yml',
        '**/*config*.json',
        '**/*config*.yaml',
        '**/training_config*.py',
        '**/train_config*.py',
    ))

    # =========================================================================
    # Random functions (for P_RND detection)
    # =========================================================================
    random_functions: tuple[str, ...] = field(default_factory=lambda: (
        'torch.rand', 'torch.randn', 'torch.randint',
        'torch.zeros', 'torch.ones', 'torch.full',
    ))

    # =========================================================================
    # Device names (for consistent device detection)
    # =========================================================================
    npu_device_indicators: tuple[str, ...] = field(default_factory=lambda: (
        '.npu()', "device='npu'", 'device="npu"', 'torch.npu',
    ))
    gpu_device_indicators: tuple[str, ...] = field(default_factory=lambda: (
        '.cuda()', "device='cuda'", 'device="cuda"', 'torch.cuda',
    ))

    # =========================================================================
    # Output limits
    # =========================================================================
    max_error_message_length: int = 2000

    # =========================================================================
    # Auto-sync from patterns.py (on first access)
    # =========================================================================
    _synced: bool = field(default=False, repr=False)

    def _sync_from_patterns(self):
        """Sync context_windows from patterns.py (lazy load, avoids a
        circular import)."""
        if self._synced:
            return
        from patterns import get_context_windows
        for pid, window in get_context_windows().items():
            self.context_windows.setdefault(pid, window)
        self._synced = True


_config: PatcherConfig | None = None


def get_config() -> PatcherConfig:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = PatcherConfig()
    _config._sync_from_patterns()
    return _config


def set_config(config: PatcherConfig) -> None:
    """Set the global config instance."""
    global _config
    _config = config


def get_context_config(pattern_id: str) -> dict[str, int]:
    """Get the context window settings for a pattern."""
    cfg = get_config()
    return cfg.context_windows.get(pattern_id, cfg.context_windows.get('default', {'before': 3, 'after': 3}))
