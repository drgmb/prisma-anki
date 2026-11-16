# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""
Decides which part of a card Prisma works on, so it leaves tags, timers, extra fields, buttons and
images alone. Works from the templates, so it adapts to any customized note type.

  • front  → every field the front template shows (tags excluded);
  • back   → never touched;
  • an explicit list in the settings (models[name].fields) replaces the detection.

The references found here are wrapped in a <prisma-target> element: inside the templates in bake
mode (templates.py), or around the rendered field in the card's HTML at runtime (wrap_rendered).
"""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

import re
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple

TARGET_OPEN = '<prisma-target data-prisma-by="drgmb">'
TARGET_CLOSE = "</prisma-target>"
SKIP_OPEN = '<prisma-skip data-prisma-skip="1">'
SKIP_CLOSE = "</prisma-skip>"
TARGET_RE = re.compile(r"</?prisma-(?:target|skip)\b[^>]*>")
_SEP = "<!--prisma-sep-->"

_SPECIAL = {"frontside", "tags", "type", "deck", "subdeck", "card", "cardflag"}
_SKIP_FILTERS = {"type", "tts", "tts-voices"}
_REF_RE = re.compile(r"\{\{([^{}#^/!=>][^{}]*)\}\}")
_MODEL_CLOZE = 1


class Ref(NamedTuple):
    start: int
    end: int
    text: str            # "{{edit:cloze:Text}}"
    name: str            # "Text"
    filters: Tuple[str, ...]


def in_markup(text: str, pos: int) -> bool:
    """True when `pos` sits inside a tag (attribute value), a <script>/<style> body or a comment."""
    lower = text[:pos].lower()
    for open_, close in (("<script", "</script"), ("<style", "</style"), ("<!--", "-->")):
        if lower.rfind(open_) > lower.rfind(close):
            return True
    return lower.rfind("<") > lower.rfind(">")


def _all_refs(fmt: str) -> List[Ref]:
    out = []
    for m in _REF_RE.finditer(fmt):
        parts = [p.strip() for p in m.group(1).split(":")]
        name, filters = parts[-1], tuple(p.lower() for p in parts[:-1] if p)
        if name and not in_markup(fmt, m.start()):
            out.append(Ref(m.start(), m.end(), m.group(0), name, filters))
    return out


def refs(fmt: str) -> List[Ref]:
    """Field references of a template that render as visible content."""
    return [r for r in _all_refs(fmt)
            if r.name.lower() not in _SPECIAL and not _SKIP_FILTERS.intersection(r.filters)]


def tag_refs(fmt: str) -> List[Ref]:
    return [r for r in _all_refs(fmt) if r.name.lower() == "tags"]


def main_field_names(model: Dict[str, Any], qfmt: str, afmt: str,
                     override: Optional[Iterable[str]] = None) -> List[str]:
    wanted = [n for n in (override or []) if n]
    if wanted:
        return wanted
    q, a = refs(qfmt), refs(afmt)
    names = list(dict.fromkeys(r.name for r in q))
    if model.get("type") == _MODEL_CLOZE:
        return names or list(dict.fromkeys(r.name for r in a if "cloze" in r.filters))
    return names


def main_refs(fmt: str, names: Iterable[str]) -> List[Ref]:
    wanted = {n.lower() for n in names}
    return [r for r in refs(fmt) if r.name.lower() in wanted]


# ------------------------------------------------------------------ bake mode: wrap inside the template
def wrap_template(fmt: str, names: Iterable[str]) -> str:
    marks = [(r, TARGET_OPEN, TARGET_CLOSE) for r in main_refs(fmt, names)]
    marks += [(r, SKIP_OPEN, SKIP_CLOSE) for r in tag_refs(fmt)]
    out, last = [], 0
    for r, open_, close in sorted(marks, key=lambda m: m[0].start):
        out += [fmt[last:r.start], open_, r.text, close]
        last = r.end
    return "".join(out) + fmt[last:]


def unwrap(text: str) -> str:
    return TARGET_RE.sub("", text)


# ------------------------------------------------------------------ runtime: wrap inside the rendered card
_cache: Dict[Any, Dict[str, str]] = {}


def _render_refs(card, ref_texts: List[str]) -> List[str]:
    """Renders just the given references for this card, exactly as the full template renders them
    (same filters, same add-on hooks), and returns one HTML string per reference."""
    from anki.template import TemplateRenderContext
    from aqt import mw

    note = card.note()
    key = (card.id, card.ord, note.mod, tuple(ref_texts))
    hit = _cache.get("last")
    if hit and hit.get("key") == key:
        return hit["parts"]  # type: ignore[return-value]

    template = dict(card.template())
    template["qfmt"] = template["afmt"] = _SEP.join(ref_texts)
    output = TemplateRenderContext.from_card_layout(note, card, card.note_type(), template, False).render()
    parts = [mw.prepare_card_text_for_display(p) for p in output.question_text.split(_SEP)]
    if len(parts) != len(ref_texts):
        parts = []
    _cache["last"] = {"key": key, "parts": parts}  # type: ignore[dict-item]
    return parts


def _plain_len(html: str) -> int:
    return len(re.sub(r"<[^>]*>|\s+", "", html))


def _spots(text: str, part: str) -> List[int]:
    """Where `part` shows up as content of its own: not inside markup, not in the middle of a word."""
    out, at = [], text.find(part)
    while at >= 0:
        end = at + len(part)
        before, after = text[at - 1:at], text[end:end + 1]
        clean = (not before or before == ">" or before.isspace()) and (not after or after == "<" or after.isspace())
        if clean and not in_markup(text, at):
            out.append(at)
        at = text.find(part, end)
    return out


def wrap_rendered(text: str, card, override: Optional[Iterable[str]] = None) -> str:
    """Marks, inside the rendered card HTML, the fields Prisma works on (and the tags it must skip).
    Anything that can't be located with certainty is left alone; the script has its own fallbacks."""
    try:
        tmpl = card.template()
        names = main_field_names(card.note_type(), tmpl["qfmt"], tmpl["afmt"], override)
        wanted: Dict[str, Tuple[str, str]] = {}
        for r in main_refs(tmpl["qfmt"], names):
            wanted.setdefault(r.text, (TARGET_OPEN, TARGET_CLOSE))
        for r in tag_refs(tmpl["qfmt"]):
            wanted.setdefault(r.text, (SKIP_OPEN, SKIP_CLOSE))
        if not wanted:
            return text
        rendered = dict(zip(wanted, _render_refs(card, list(wanted))))
        # longest first, so a field whose text is part of another one can't steal its place
        for ref_text, part in sorted(rendered.items(), key=lambda kv: len(kv[1]), reverse=True):
            part = part.strip()
            if _plain_len(part) < 3:
                continue
            spots = _spots(text, part)
            if not spots or len(spots) > 3:
                continue
            open_, close = wanted[ref_text]
            for at in reversed(spots):
                if "<prisma-" in part or text.rfind("<prisma-", 0, at) > text.rfind("</prisma-", 0, at):
                    continue  # already inside a marked region
                text = text[:at] + open_ + part + close + text[at + len(part):]
        return text
    except Exception:
        return text
