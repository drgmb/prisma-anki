# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""Configuration loading and saving, defaults, and per-note-type resolution."""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import copy
import json
import os
from typing import Any, Dict, Tuple

from aqt import mw

ADDON = __name__.split(".")[0]
HERE = os.path.dirname(__file__)

# (key, label) — the order here is the order in the UI
FEATURES = [
    ("speech", "🔊 Read aloud"),
    ("karaoke", "🎤 Highlight word being read"),
    ("progressiveReveal", "👁 Reveal word by word"),
    ("randomLayout", "🔀 Random layout"),
    ("bionic", "🅱 Bionic reading"),
    ("beeline", "🌈 Color gradient (BeeLine)"),
]
FEATURE_KEYS = [k for k, _ in FEATURES]


_defaults_cache: Dict[str, Any] | None = None
_cfg_cache: Dict[str, Any] | None = None  # load() runs for every card shown: don't hit the disk each time


def _defaults() -> Dict[str, Any]:
    global _defaults_cache
    if _defaults_cache is None:
        with open(os.path.join(HERE, "config.json"), encoding="utf-8") as fh:
            _defaults_cache = json.load(fh)
    return _defaults_cache


def invalidate(*_args: Any) -> None:
    global _cfg_cache
    _cfg_cache = None


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
    """A private copy of the merged config: callers may mutate it freely."""
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = _merge(_defaults(), mw.addonManager.getConfig(ADDON) or {})
        # Prisma works on the front of the card only; an "applyOn" key left by a pre-1.2.0 config is ignored
        _cfg_cache.pop("applyOn", None)
    return copy.deepcopy(_cfg_cache)


def save(cfg: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON, cfg)
    invalidate()


def follow_renames(cfg: Dict[str, Any]) -> bool:
    """Entries are keyed by note-type name and remember the note type's id. When a name is gone from
    the open collection but its id is still there, the note type was renamed: move the entry along.
    Entries whose id is unknown here are left alone (they may belong to another profile)."""
    if not getattr(mw, "col", None):
        return False
    by_id = {int(nt.id): nt.name for nt in mw.col.models.all_names_and_ids()}
    names = set(by_id.values())
    models = cfg.get("models", {})
    changed = False
    for old_name in list(models):
        entry = models[old_name]
        new_name = by_id.get(int(entry.get("id") or 0)) if isinstance(entry, dict) else None
        if old_name in names or not new_name or new_name in models:
            continue
        models[new_name] = models.pop(old_name)
        changed = True
    return changed


def resolve_text_size(cfg: Dict[str, Any], model_name: str) -> int:
    """Text size in percent for a note type: per-model value when set (non-zero), else the global one."""
    entry = cfg.get("models", {}).get(model_name, {})
    size = int(entry.get("textSize") or 0) or int(cfg.get("text", {}).get("sizePct", 100) or 100)
    return max(50, min(300, size))


def resolve_fields(cfg: Dict[str, Any], model_name: str) -> list:
    """Explicit main-field names for a note type; empty = detect them from the templates."""
    value = cfg.get("models", {}).get(model_name, {}).get("fields") or []
    if isinstance(value, str):
        value = value.split(",")
    return [str(v).strip() for v in value if str(v).strip()]


def resolve_model(cfg: Dict[str, Any], model_name: str) -> Tuple[bool, Dict[str, bool]]:
    """Return (enabled, features) for a note type, merging global defaults with per-model overrides."""
    entry = cfg.get("models", {}).get(model_name, {})
    enabled = bool(entry.get("enabled", cfg.get("defaultModelEnabled", False)))
    features = {k: bool(cfg.get("features", {}).get(k, False)) for k in FEATURE_KEYS}
    for k, v in entry.get("features", {}).items():
        if k in features:
            features[k] = bool(v)
    return enabled, features
