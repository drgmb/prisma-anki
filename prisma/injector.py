# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""Decides, for every card shown, whether and how to inject the Prisma script."""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import json
import os
from typing import Any, Dict, Optional

from aqt import gui_hooks, mw

from . import config

_WEB = os.path.join(config.HERE, "web")

# card_will_show `kind` → (where, side)
_KINDS = {
    "reviewQuestion": ("review", "question"),
    "reviewAnswer": ("review", "answer"),
    "previewQuestion": ("preview", "question"),
    "previewAnswer": ("preview", "answer"),
    "clayoutQuestion": ("cardLayout", "question"),
    "clayoutAnswer": ("cardLayout", "answer"),
}

_CANCEL_SPEECH = '<script data-prisma-skip="1" data-prisma-by="drgmb">if(window.speechSynthesis)speechSynthesis.cancel();</script>'


def _read(name: str) -> str:
    with open(os.path.join(_WEB, name), encoding="utf-8") as fh:
        return fh.read()


# read once per session; restarting Anki reloads them
_JS = _read("prisma.js")
_CSS = _read("prisma.css")


def _payload(cfg: Dict[str, Any], features: Dict[str, bool], side: str, text_size: int = 100) -> Dict[str, Any]:
    return {
        "features": features,
        "textSizePct": text_size,
        "speech": cfg.get("speech", {}),
        "layout": cfg.get("layout", {}),
        "side": side,
        "skipIfTemplateHasOwn": bool(cfg.get("skipIfTemplateHasOwn", True)),
        "author": "drgmb",
        "sig": "ZHJnbWI=",
    }


def _model_name(card) -> Optional[str]:
    try:
        return card.note_type()["name"]
    except Exception:
        return None


def on_card_will_show(text: str, card, kind: str) -> str:
    where_side = _KINDS.get(kind)
    if not where_side:
        return text
    where, side = where_side

    cfg = config.load()
    if not cfg.get("enabled"):
        return text
    if not cfg.get("applyIn", {}).get(where, False):
        return text

    # Always stop the previous card's speech, even when this side gets no features.
    if not cfg.get("applyOn", {}).get(side, False):
        return text + _CANCEL_SPEECH

    name = _model_name(card)
    if name is None:
        return text + _CANCEL_SPEECH
    # baked note types carry the block inside their templates: nothing to inject
    if cfg.get("models", {}).get(name, {}).get("baked"):
        return text
    enabled, features = config.resolve_model(cfg, name)
    if not enabled:
        return text + _CANCEL_SPEECH

    payload = json.dumps(_payload(cfg, features, side, config.resolve_text_size(cfg, name)), ensure_ascii=False)
    return (
        text
        + "<!-- Prisma by drgmb · https://github.com/drgmb -->"
        + '<style data-prisma-skip="1" data-prisma-by="drgmb">' + _CSS + "</style>"
        + '<script data-prisma-skip="1" data-prisma-by="drgmb">window.__PRISMA_CFG=' + payload + ";window.__PRISMA_BY='drgmb';</script>"
        + '<script data-prisma-skip="1" data-prisma-by="drgmb">' + _JS + "</script>"
    )


def on_state_did_change(new_state: str, old_state: str) -> None:
    """Leaving the reviewer stops any speech still playing."""
    if old_state == "review" and new_state != "review":
        try:
            mw.web.eval("if(window.speechSynthesis)speechSynthesis.cancel();")
        except Exception:
            pass


def redraw_current_card() -> None:
    """Re-apply the settings to the card on screen (reviewer only)."""
    try:
        if mw.state != "review" or not mw.reviewer.card:
            return
        if mw.reviewer.state == "question":
            mw.reviewer._showQuestion()
        else:
            mw.reviewer._showAnswer()
    except Exception:
        pass


def install() -> None:
    gui_hooks.card_will_show.append(on_card_will_show)
    gui_hooks.state_did_change.append(on_state_did_change)
