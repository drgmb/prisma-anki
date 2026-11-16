# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""
Prisma — Anki desktop add-on. Author: drgmb (https://github.com/drgmb).

Applies, to any note type you choose and without touching templates:
  • per-line color gradient (BeeLine)        • bionic reading
  • random layout                            • read aloud with adjustable speed
  • spoken-word highlight (karaoke)          • progressive reveal

Modules: config (load/save), injector (render hook), dialog (settings window).
Menu: Tools → "Prisma…". Toggle on/off: shortcut only (default Ctrl+Shift+L).
Read again (keys handled inside the card, see prisma.js): Q = the cloze answer, W = the whole card.
"""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

from aqt import gui_hooks, mw
from aqt.qt import QAction, QKeySequence
from aqt.utils import tooltip

from . import config, injector
from .dialog import SettingsDialog

_toggle_action: QAction | None = None


def _apply_shortcut(cfg: dict) -> None:
    if _toggle_action is not None:
        _toggle_action.setShortcut(QKeySequence(cfg.get("toggleShortcut") or ""))


def _on_saved(cfg: dict) -> None:
    _apply_shortcut(cfg)
    injector.redraw_current_card()


def open_settings() -> None:
    SettingsDialog(on_saved=_on_saved, parent=mw).exec()


def toggle_enabled() -> None:
    cfg = config.load()
    cfg["enabled"] = not cfg.get("enabled", True)
    config.save(cfg)
    tooltip("Prisma " + ("enabled" if cfg["enabled"] else "disabled") + " · by drgmb", period=1500)
    injector.redraw_current_card()


def _setup_menu() -> None:
    global _toggle_action
    settings = QAction("Prisma…", mw)
    settings.triggered.connect(open_settings)
    mw.form.menuTools.addAction(settings)

    # the toggle stays out of the menu: shortcut only, registered on the main window
    _toggle_action = QAction("Prisma: toggle", mw)
    _toggle_action.triggered.connect(toggle_enabled)
    mw.addAction(_toggle_action)
    _apply_shortcut(config.load())


def _on_profile_open() -> None:
    cfg = config.load()
    if config.follow_renames(cfg):
        config.save(cfg)


def _setup() -> None:
    injector.install()
    _setup_menu()
    mw.addonManager.setConfigUpdatedAction(config.ADDON, config.invalidate)
    gui_hooks.profile_did_open.append(_on_profile_open)
    if getattr(mw, "col", None):
        _on_profile_open()


# Two copies of Prisma can be installed side by side (the AnkiWeb one in a numeric folder and a
# local/dev one). Running both doubles the menu, makes the toggle shortcut ambiguous and lets each
# copy undo the other's baked templates, so exactly one may run: every copy registers itself here
# and, once all add-ons are loaded, the preferred one (a non-numeric folder, i.e. the dev copy,
# first) sets itself up.
_COPIES = "_prisma_copies"


def _start_preferred() -> None:
    copies = getattr(mw, _COPIES, None)
    if not copies:
        return
    setattr(mw, _COPIES, [])
    name, setup = sorted(copies, key=lambda c: (c[0].isdigit(), c[0]))[0]
    skipped = [n for n, _ in copies if n != name]
    if skipped:
        print(f"Prisma: several copies installed; using '{name}', ignoring {skipped}")
    setup()


if not hasattr(mw, _COPIES):
    setattr(mw, _COPIES, [])
    if hasattr(gui_hooks, "main_window_did_init"):
        gui_hooks.main_window_did_init.append(_start_preferred)
    else:
        mw.progress.single_shot(0, _start_preferred, False)
getattr(mw, _COPIES).append((config.ADDON, _setup))
