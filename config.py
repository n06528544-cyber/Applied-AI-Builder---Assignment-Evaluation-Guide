"""Configuration loading with safe defaults."""
from __future__ import annotations

import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "llm": {
        "provider": "none",
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "max_tokens": 2000,
        "api_key_env": "DDR_LLM_API_KEY",
        "base_url": "",
    },
    "extraction": {
        "dedupe_threshold": 0.82,
        "thermal_anomaly_delta_c": 5.0,
        "default_ref_temp_c": 30.0,
        "min_confidence": 0.0,
    },
    "report": {
        "brand_name": "Acme Applied AI - Diagnostic Reports",
        "output_format": ["html", "pdf", "md"],
        "include_images": True,
        "language": "en",
        "client_friendly": True,
    },
    "paths": {
        "inputs": "samples/inputs",
        "output": "samples/output",
        "images": "samples/inputs/images",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load YAML config and merge over built-in defaults."""
    cfg = DEFAULTS
    if path and os.path.exists(path):
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as fh:
                user_cfg = yaml.safe_load(fh) or {}
            cfg = _deep_merge(DEFAULTS, user_cfg)
        except Exception:
            # never fail hard on config; fall back to defaults
            cfg = DEFAULTS
    return cfg
