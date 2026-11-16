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

from . import config, fields

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

_SCRIPT = '<script data-prisma-skip="1" data-prisma-by="drgmb">'

# #qa outlives the card, so whatever Prisma wrote on it would leak into what gets no Prisma: the back
# of the card (always shown exactly as its template made it), other note types, add-on toggled off… Keep the property list in sync with prisma.js (STYLE_PROPS).
_RESET = (
    _SCRIPT
    + "(function(){ if(window.speechSynthesis)speechSynthesis.cancel();"
    + "var s=window.__PRISMA_STATE;window.__PRISMA_STATE=null;"
    + "if(s&&s.stop){ try{ s.stop(); }catch(e){ } }"
    + "var props=['maxWidth','marginLeft','marginRight','textAlign','wordSpacing','letterSpacing','paddingLeft','fontSize'];"
    + "[].slice.call(document.querySelectorAll('[data-prisma-styled]')).forEach(function(r){"
    + " props.forEach(function(p){ r.style[p]=''; });"
    + " r.removeAttribute('data-prisma-styled'); });"
    + "var q=document.getElementById('qa');"
    + "if(q){ q.removeAttribute('data-prisma-by');q.removeAttribute('data-prisma-sig'); }"
    + " })();</script>"
)
# it is also written into baked templates, where Anki would read a doubled brace as a field tag
assert "{{" not in _RESET and "}}" not in _RESET


def _off_flag(off: bool) -> str:
    """Read by baked blocks, so they obey the desktop toggle / per-note-type switch too."""
    return _SCRIPT + "window.__PRISMA_OFF=" + ("true" if off else "false") + ";</script>"


def _read(name: str) -> str:
    with open(os.path.join(_WEB, name), encoding="utf-8") as fh:
        return fh.read()


# read once per session; restarting Anki reloads them
_JS = _read("prisma.js")
_CSS = _read("prisma.css")


def payload(cfg: Dict[str, Any], features: Dict[str, bool], text_size: int = 100, baked: bool = False,
            side: str = "question") -> Dict[str, Any]:
    """What prisma.js reads as window.__PRISMA_CFG; shared by the runtime injection and the baked block."""
    out = {
        "features": features,
        "textSizePct": text_size,
        "speech": cfg.get("speech", {}),
        "layout": cfg.get("layout", {}),
        "side": side,  # the front gets everything; the back only gets reading aloud (see answerRead)
        "skipIfTemplateHasOwn": bool(cfg.get("skipIfTemplateHasOwn", True)),
        "author": "drgmb",
        "sig": "ZHJnbWI=",
    }
    if baked:
        out["baked"] = True
    return out


def assets() -> tuple:
    """(css, js) as loaded at startup."""
    return _CSS, _JS


def _model_name(card) -> Optional[str]:
    try:
        return card.note_type()["name"]
    except Exception:
        return None


def templates_marker_in(text: str) -> bool:
    return "<!--prisma:start" in text or "<!--prisma:marker-start" in text


def on_card_will_show(text: str, card, kind: str) -> str:
    where_side = _KINDS.get(kind)
    if not where_side:
        return text
    where, side = where_side

    cfg = config.load()
    off = not cfg.get("enabled") or not cfg.get("applyIn", {}).get(where, False)
    name = _model_name(card)

    # Baked note types carry the block inside their templates: nothing to inject, only tell the
    # block whether it may run. What counts is the rendered text, not the `baked` flag: if the
    # flag is set but the templates hold no block, the card falls through to runtime injection.
    if templates_marker_in(text):
        if not off:
            off = name is None or not config.resolve_model(cfg, name)[0]
        return _off_flag(off) + text + (_RESET if off else "")

    if off or name is None:
        return text + _RESET
    enabled, features = config.resolve_model(cfg, name)
    if not enabled:
        return text + _RESET
    if side == "answer":
        # the back is always shown exactly as its template made it: it only gets reading aloud,
        # and only when asked for (speech.answerRead = "full" re-reads the card, "cloze" reads the answers)
        if not features.get("speech") or cfg.get("speech", {}).get("answerRead", "off") not in ("full", "cloze"):
            return text + _RESET
        data = json.dumps(payload(cfg, features, side="answer"), ensure_ascii=False)
    else:
        # mark the main text field, so nothing else on the card (tags, timers, extra fields) is touched
        text = fields.wrap_rendered(text, card, config.resolve_fields(cfg, name))
        data = json.dumps(payload(cfg, features, config.resolve_text_size(cfg, name)), ensure_ascii=False)
    return (
        text
        + "<!-- Prisma by drgmb · https://github.com/drgmb -->"
        + '<style data-prisma-skip="1" data-prisma-by="drgmb">' + _CSS + "</style>"
        + '<script data-prisma-skip="1" data-prisma-by="drgmb">window.__PRISMA_CFG=' + data + ";window.__PRISMA_BY='drgmb';</script>"
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
        try:  # the templates may just have been (un)baked: don't redraw from the cached render
            mw.reviewer.card.render_output(reload=True)
        except Exception:
            pass
        if mw.reviewer.state == "question":
            mw.reviewer._showQuestion()
        else:
            mw.reviewer._showAnswer()
    except Exception:
        pass


def install() -> None:
    gui_hooks.card_will_show.append(on_card_will_show)
    gui_hooks.state_did_change.append(on_state_did_change)
