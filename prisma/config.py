# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""Configuration loading and saving, defaults, and per-note-type resolution."""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import json
import os
from typing import Any, Dict, Tuple

from aqt import mw

ADDON = __name__.split(".")[0]
HERE = os.path.dirname(__file__)

# (key, label) — the order here is the order in the UI
FEATURES = [
    ("speech", "🔊 Read aloud"),
    ("karaoke", "🎤 Highlight spoken word"),
    ("progressiveReveal", "👁 Reveal word by word"),
    ("randomLayout", "🔀 Random layout"),
    ("bionic", "🅱 Bionic reading"),
    ("beeline", "🌈 Color gradient (BeeLine)"),
]
FEATURE_KEYS = [k for k, _ in FEATURES]


def _defaults() -> Dict[str, Any]:
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _merge(base: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Fill keys missing from the user's config with the defaults (one dictionary level deep)."""
    out = dict(user)
    for key, default in base.items():
        if key not in out:
            out[key] = default
        elif isinstance(default, dict) and isinstance(out[key], dict) and key != "models":
            out[key] = {**default, **out[key]}
    return out


def load() -> Dict[str, Any]:
    return _merge(_defaults(), mw.addonManager.getConfig(ADDON) or {})


def save(cfg: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON, cfg)


def resolve_model(cfg: Dict[str, Any], model_name: str) -> Tuple[bool, Dict[str, bool]]:
    """Return (enabled, features) for a note type, merging global defaults with per-model overrides."""
    entry = cfg.get("models", {}).get(model_name, {})
    enabled = bool(entry.get("enabled", cfg.get("defaultModelEnabled", False)))
    features = {k: bool(cfg.get("features", {}).get(k, False)) for k in FEATURE_KEYS}
    for k, v in entry.get("features", {}).items():
        if k in features:
            features[k] = bool(v)
    return enabled, features
