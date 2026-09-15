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
"""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

from aqt import mw
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


injector.install()
_setup_menu()
