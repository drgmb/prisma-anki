# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""
Bake mode: writes a self-contained Prisma block into note-type templates so the
features also run on AnkiDroid / AnkiMobile, where add-ons don't exist.

The block is delimited by HTML comments so it can be updated or removed without
touching the rest of the template:

  front template  → ... <!--prisma:start--> style + config + script <!--prisma:end-->
  back template   → <!--prisma:marker-start--> hidden marker <!--prisma:marker-end--> ...
                    [+ the same block with side="answer", when the back is enabled]

The marker tells the front block (re-rendered through {{FrontSide}}) that it is
on the back side, so it steps aside instead of running twice.
"""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import json
import os
import re
from typing import Any, Dict, List, Tuple

from aqt import mw

from . import config

_WEB = os.path.join(config.HERE, "web")

START, END = "<!--prisma:start by drgmb-->", "<!--prisma:end by drgmb · https://github.com/drgmb-->"
MARKER_START, MARKER_END = "<!--prisma:marker-start by drgmb-->", "<!--prisma:marker-end-->"
MARKER = MARKER_START + '<div id="prisma-answer-marker" data-prisma-by="drgmb" data-sig="ZHJnbWI=" style="display:none"></div>' + MARKER_END

_BLOCK_RE = re.compile(r"<!--prisma:start[^>]*-->.*?<!--prisma:end[^>]*-->", re.S)
_MARKER_RE = re.compile(r"<!--prisma:marker-start[^>]*-->.*?<!--prisma:marker-end[^>]*-->", re.S)


def _read(name: str) -> str:
    with open(os.path.join(_WEB, name), encoding="utf-8") as fh:
        return fh.read()


def build_block(cfg: Dict[str, Any], features: Dict[str, bool], side: str) -> str:
    """The same payload the runtime injector uses, frozen into template text."""
    payload = {
        "features": features,
        "speech": cfg.get("speech", {}),
        "layout": cfg.get("layout", {}),
        "side": side,
        "baked": True,
        "skipIfTemplateHasOwn": bool(cfg.get("skipIfTemplateHasOwn", True)),
        "author": "drgmb",
        "sig": "ZHJnbWI=",
    }
    block = (
        START
        + "\n<!-- Prisma by drgmb · https://github.com/drgmb · do not edit inside this block -->"
        + "\n<style data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">" + _read("prisma.css") + "</style>"
        + "\n<script data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">window.__PRISMA_CFG=" + json.dumps(payload, ensure_ascii=False) + ";window.__PRISMA_BY='drgmb';</script>"
        + "\n<script data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">" + _read("prisma.js") + "</script>\n"
        + END
    )
    # Anki substitutes {{...}} anywhere in a template, scripts included: the block must never contain one.
    if "{{" in block or "}}" in block:
        raise ValueError("Prisma block contains a template tag sequence")
    return block


def strip(text: str) -> str:
    """Removes every Prisma block/marker and normalizes blank lines at both ends."""
    text = _BLOCK_RE.sub("", text)
    text = _MARKER_RE.sub("", text).strip("\n")
    return text + "\n" if text else ""


def is_baked(text: str) -> bool:
    return "<!--prisma:start" in text or "<!--prisma:marker-start" in text


def apply_to_templates(qfmt: str, afmt: str, cfg: Dict[str, Any], features: Dict[str, bool]) -> Tuple[str, str]:
    """Pure function: returns the new (front, back) template texts."""
    qfmt, afmt = strip(qfmt).rstrip("\n"), strip(afmt).rstrip("\n")
    if cfg.get("applyOn", {}).get("question", True):
        qfmt = qfmt + "\n" + build_block(cfg, features, "question") + "\n"
    afmt = MARKER + "\n" + afmt
    if cfg.get("applyOn", {}).get("answer", False):
        afmt = afmt + "\n" + build_block(cfg, features, "answer") + "\n"
    return qfmt, afmt


# ------------------------------------------------------------------ collection I/O
def _model(name: str):
    return mw.col.models.by_name(name)


def bake(name: str, cfg: Dict[str, Any]) -> bool:
    model = _model(name)
    if not model:
        return False
    _, features = config.resolve_model(cfg, name)
    for tmpl in model["tmpls"]:
        tmpl["qfmt"], tmpl["afmt"] = apply_to_templates(tmpl["qfmt"], tmpl["afmt"], cfg, features)
    mw.col.models.update_dict(model)
    return True


def unbake(name: str) -> bool:
    model = _model(name)
    if not model:
        return False
    changed = False
    for tmpl in model["tmpls"]:
        for key in ("qfmt", "afmt"):
            if is_baked(tmpl[key]):
                tmpl[key] = strip(tmpl[key])
                changed = True
    if changed:
        mw.col.models.update_dict(model)
    return changed


def sync(cfg: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Make the collection match the config: bake where `baked` is set, strip everywhere else.
    Returns (baked_names, removed_names)."""
    baked, removed = [], []
    wanted = {name for name, entry in cfg.get("models", {}).items() if entry.get("baked")}
    for nt in mw.col.models.all_names_and_ids():
        if nt.name in wanted:
            if bake(nt.name, cfg):
                baked.append(nt.name)
        else:
            model = _model(nt.name)
            if model and any(is_baked(t[k]) for t in model["tmpls"] for k in ("qfmt", "afmt")):
                if unbake(nt.name):
                    removed.append(nt.name)
    return baked, removed
