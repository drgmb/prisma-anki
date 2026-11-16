# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""
Bake mode: writes a self-contained Prisma block into note-type templates so the
features also run on AnkiDroid / AnkiMobile, where add-ons don't exist.

The block is delimited by HTML comments so it can be updated or removed without
touching the rest of the template:

  front template  → ... <!--prisma:start--> style + config + script <!--prisma:end-->
  back template   → <!--prisma:marker-start--> hidden marker <!--prisma:marker-end--> ...
                  [+ the same block with side="answer", when speech.answerRead reads the back]

The marker tells the front block (re-rendered through {{FrontSide}}) that it is
on the back side, so it steps aside instead of running twice.
"""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import json
import re
from typing import Any, Dict, List, Tuple

from aqt import mw

from . import config, fields, injector
from .injector import _RESET

START, END = "<!--prisma:start by drgmb-->", "<!--prisma:end by drgmb · https://github.com/drgmb-->"
MARKER_START, MARKER_END = "<!--prisma:marker-start by drgmb-->", "<!--prisma:marker-end-->"
# The back must look exactly as its template made it: besides telling the front block (FrontSide) to
# step aside, the marker undoes what the front left on the shared #qa element (text size, speech…).
MARKER = (
    MARKER_START
    + '<div id="prisma-answer-marker" data-prisma-by="drgmb" data-sig="ZHJnbWI=" style="display:none"></div>'
    + _RESET
    + MARKER_END
)

_BLOCK_RE = re.compile(r"<!--prisma:start[^>]*-->.*?<!--prisma:end[^>]*-->", re.S)
_MARKER_RE = re.compile(r"<!--prisma:marker-start[^>]*-->.*?<!--prisma:marker-end[^>]*-->", re.S)


def reads_back(cfg: Dict[str, Any], features: Dict[str, bool]) -> bool:
    """True when the back should also get a (speech-only) block: speech.answerRead is "full" or "cloze"."""
    return bool(features.get("speech")) and cfg.get("speech", {}).get("answerRead", "off") in ("full", "cloze")


def build_block(cfg: Dict[str, Any], features: Dict[str, bool], text_size: int = 100, side: str = "question") -> str:
    """The same payload the runtime injector uses, frozen into template text."""
    payload = injector.payload(cfg, features, text_size, baked=True, side=side)
    css, js = injector.assets()
    block = (
        START
        + "\n<!-- Prisma by drgmb · https://github.com/drgmb · do not edit inside this block -->"
        + "\n<style data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">" + css + "</style>"
        + "\n<script data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">window.__PRISMA_CFG=" + json.dumps(payload, ensure_ascii=False) + ";window.__PRISMA_BY='drgmb';</script>"
        + "\n<script data-prisma-skip=\"1\" data-prisma-by=\"drgmb\">" + js + "</script>\n"
        + END
    )
    # Anki substitutes {{...}} anywhere in a template, scripts included: the block must never contain one.
    if "{{" in block or "}}" in block:
        raise ValueError("Prisma block contains a template tag sequence")
    return block


def strip(text: str) -> str:
    """Removes every Prisma block/marker and normalizes blank lines at both ends."""
    text = _BLOCK_RE.sub("", text)
    text = fields.unwrap(_MARKER_RE.sub("", text)).strip("\n")
    return text + "\n" if text else ""


def is_baked(text: str) -> bool:
    return "<!--prisma:start" in text or "<!--prisma:marker-start" in text or "<prisma-target" in text


def apply_to_templates(qfmt: str, afmt: str, cfg: Dict[str, Any], features: Dict[str, bool], text_size: int = 100,
                       model: Dict[str, Any] | None = None, field_names: List[str] | None = None) -> Tuple[str, str]:
    """Pure function: returns the new (front, back) template texts. The front gets the block and has
    its main text fields wrapped in <prisma-target>, so only those are processed; the back only gets
    the marker that keeps the front block (FrontSide) from running there."""
    qfmt, afmt = strip(qfmt).rstrip("\n"), strip(afmt).rstrip("\n")
    names = fields.main_field_names(model or {}, qfmt, afmt, field_names)
    qfmt = fields.wrap_template(qfmt, names)
    qfmt = qfmt + "\n" + build_block(cfg, features, text_size) + "\n"
    afmt = MARKER + "\n" + afmt
    if reads_back(cfg, features):
        # after the back's content, so the words (and the cloze answers) exist when the block runs
        afmt = afmt + "\n" + build_block(cfg, features, side="answer") + "\n"
    return qfmt, afmt


# ------------------------------------------------------------------ collection I/O
def _model(name: str):
    return mw.col.models.by_name(name)


def bake(name: str, cfg: Dict[str, Any]) -> bool:
    """Writes/refreshes the block. Returns True only when a template actually changed, so an
    unchanged note type is not rewritten (and re-synced) on every save."""
    model = _model(name)
    if not model:
        return False
    _, features = config.resolve_model(cfg, name)
    text_size = config.resolve_text_size(cfg, name)
    changed = False
    for tmpl in model["tmpls"]:
        qfmt, afmt = apply_to_templates(tmpl["qfmt"], tmpl["afmt"], cfg, features, text_size,
                                        model, config.resolve_fields(cfg, name))
        if (qfmt, afmt) != (tmpl["qfmt"], tmpl["afmt"]):
            tmpl["qfmt"], tmpl["afmt"] = qfmt, afmt
            changed = True
    if changed:
        mw.col.models.update_dict(model)
    return changed


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
    Returns (names whose templates were written, names the block was removed from)."""
    baked, removed = [], []
    # a note type that is baked but not enabled gets no block: "Enabled" rules on every platform
    wanted = {
        name for name, entry in cfg.get("models", {}).items()
        if entry.get("baked") and config.resolve_model(cfg, name)[0]
    }
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
