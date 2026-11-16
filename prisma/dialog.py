# -*- coding: utf-8 -*-
# Prisma — by drgmb (https://github.com/drgmb)
"""Settings window (Tools → Prisma…)."""
from __future__ import annotations

__author__ = "drgmb"
__url__ = "https://github.com/drgmb"

from typing import Any, Dict, List, Tuple

from aqt import mw
from aqt.qt import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, Qt,
)
from aqt.utils import showWarning, tooltip

from . import config, templates
from .config import FEATURES

OVERRIDE_OPTIONS = ["Global", "On", "Off"]  # combo index 0/1/2


def _centered(widget: QWidget) -> QWidget:
    cell = QWidget()
    lay = QHBoxLayout(cell)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(widget)
    return cell


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: gray")
    label.setWordWrap(True)
    return label


class SettingsDialog(QDialog):
    def __init__(self, on_saved=None, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Prisma — Settings · by drgmb")
        self.resize(940, 640)
        self.cfg = config.load()
        config.follow_renames(self.cfg)
        self.on_saved = on_saved
        self.model_ids: Dict[str, int] = {m.name: int(m.id) for m in mw.col.models.all_names_and_ids()}
        self.model_names: List[str] = sorted(self.model_ids, key=str.lower)
        self.rows: List[Tuple[str, QCheckBox, QCheckBox, QSpinBox, QLineEdit, Dict[str, QComboBox]]] = []
        self._build()

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "General")
        tabs.addTab(self._tab_models(), "Note types")
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        credit = QLabel(f'Prisma by <a href="{__url__}">{__author__}</a> · github.com/drgmb')
        credit.setOpenExternalLinks(True)
        credit.setStyleSheet("color: gray; font-size: 11px")
        credit.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(credit)
        root.addWidget(buttons)

    def _tab_general(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.addWidget(self._group_activation())
        col.addWidget(self._group_features())
        col.addWidget(self._group_text())
        col.addWidget(self._group_speech())
        col.addStretch()
        return page

    def _group_activation(self) -> QGroupBox:
        cfg = self.cfg
        box = QGroupBox("Activation")
        form = QFormLayout(box)

        self.cb_enabled = QCheckBox("Add-on enabled")
        self.cb_enabled.setChecked(bool(cfg["enabled"]))
        form.addRow(self.cb_enabled)

        form.addRow(_muted("Prisma works on the front of the card. The back is always shown exactly as the template made it."))

        self.cb_where = {}
        row = QHBoxLayout()
        for key, label in (("review", "Reviewer"), ("preview", "Card previewer"), ("cardLayout", "Template editor")):
            cb = QCheckBox(label)
            cb.setChecked(bool(cfg["applyIn"].get(key, False)))
            self.cb_where[key] = cb
            row.addWidget(cb)
        row.addStretch()
        form.addRow("Apply in:", row)

        self.cb_skip = QCheckBox("Skip note types whose template already has these features (defines LEITURA_CONFIG)")
        self.cb_skip.setChecked(bool(cfg["skipIfTemplateHasOwn"]))
        form.addRow(self.cb_skip)

        self.le_shortcut = QLineEdit(cfg.get("toggleShortcut", ""))
        self.le_shortcut.setPlaceholderText("e.g. Ctrl+Shift+L")
        form.addRow("Toggle shortcut (not shown in the menu):", self.le_shortcut)

        self.le_replay_answer = QLineEdit(cfg.get("keyReplayAnswer", ""))
        self.le_replay_answer.setPlaceholderText("e.g. Q or Shift + Q")
        form.addRow("Key: read the answer again (in the card):", self.le_replay_answer)
        self.le_replay_card = QLineEdit(cfg.get("keyReplayCard", ""))
        self.le_replay_card.setPlaceholderText("e.g. W or Shift + W")
        form.addRow("Key: read the whole card again, with the answer:", self.le_replay_card)
        self.cb_replay_buttons = QCheckBox("Show read-again buttons in the card (useful on mobile)")
        self.cb_replay_buttons.setChecked(bool(cfg.get("replayButtons", False)))
        form.addRow(self.cb_replay_buttons)
        return box

    def _group_features(self) -> QGroupBox:
        box = QGroupBox("Features (global defaults — each note type can override them)")
        form = QFormLayout(box)
        self.cb_feature = {}
        for key, label in FEATURES:
            cb = QCheckBox(label)
            cb.setChecked(bool(self.cfg["features"].get(key, False)))
            self.cb_feature[key] = cb
            form.addRow(cb)
        form.addRow(_muted("Every feature works on its own. Without Read aloud, the highlight and the word-by-word reveal follow a silent pacer at the speech speed set below."))
        return box

    def _group_text(self) -> QGroupBox:
        box = QGroupBox("Text")
        form = QFormLayout(box)
        self.sp_text = QSpinBox()
        self.sp_text.setRange(50, 300)
        self.sp_text.setSingleStep(5)
        self.sp_text.setSuffix(" %")
        self.sp_text.setValue(int(self.cfg.get("text", {}).get("sizePct", 100) or 100))
        form.addRow("Text size (100 % = the template's own size):", self.sp_text)
        form.addRow(_muted("Applies to the whole card. With Random layout on, the random variation is scaled around this value. Each note type can set its own size on the Note types tab."))
        return box

    def _group_speech(self) -> QGroupBox:
        s = self.cfg["speech"]
        box = QGroupBox("Speech")
        form = QFormLayout(box)

        self.sp_rate = self._double_spin(0.5, 2.0, 0.05, float(s["rate"]), "×")
        form.addRow("Speed (0.5× slow · 1× normal · 2× fast):", self.sp_rate)
        self.sp_pitch = self._double_spin(0.5, 2.0, 0.05, float(s["pitch"]), "")
        form.addRow("Pitch:", self.sp_pitch)

        self.le_lang = QLineEdit(s["lang"])
        form.addRow("Language (en-US, pt-BR…):", self.le_lang)
        self.le_voice = QLineEdit(s.get("voice", ""))
        self.le_voice.setPlaceholderText("empty = first voice for the language")
        form.addRow("Voice name:", self.le_voice)
        self.cmb_answer = QComboBox()
        self.cmb_answer.addItem("Don't read the back", "off")
        self.cmb_answer.addItem("Re-read the whole card", "full")
        self.cmb_answer.addItem("Read only the cloze answer(s)", "cloze")
        idx = self.cmb_answer.findData(s.get("answerRead", "off"))
        self.cmb_answer.setCurrentIndex(max(idx, 0))
        form.addRow("On the back (answer):", self.cmb_answer)
        form.addRow(_muted("The front is always read in full. The back keeps looking exactly as its template made it; this only chooses what is read aloud there. Cloze cards: \"only the cloze answer\" reads just the revealed words; other cards: only what comes after the answer divider. Needs Read aloud on. Baked note types are refreshed when you save here."))
        self.le_blank = QLineEdit(s.get("blankWord", "blank"))
        form.addRow("How to read a cloze [...]:", self.le_blank)

        self.sp_delay = QSpinBox()
        self.sp_delay.setRange(0, 5000)
        self.sp_delay.setSingleStep(50)
        self.sp_delay.setSuffix(" ms")
        self.sp_delay.setValue(int(s["delayMs"]))
        form.addRow("Delay before starting:", self.sp_delay)
        return box

    @staticmethod
    def _double_spin(lo: float, hi: float, step: float, value: float, suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setValue(value)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    def _tab_models(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.addWidget(_muted('Tick the note types to apply Prisma to. For each feature, "Global" follows the default from the General tab. "Main field(s)" is where Prisma applies: leave it on auto (everything the front of the card shows) or type the field names, comma-separated. Tags, extra fields, timers, buttons and images are never touched. "Bake" writes the features into the note type\'s templates so they also work on AnkiDroid and AnkiMobile; baked templates are refreshed every time you save here and cleaned up when you untick.'))

        top = QHBoxLayout()
        self.cb_default = QCheckBox("Unlisted / new note types are enabled by default")
        self.cb_default.setChecked(bool(self.cfg["defaultModelEnabled"]))
        top.addWidget(self.cb_default)
        top.addStretch()
        for label, value in (("Check visible", True), ("Uncheck visible", False)):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, v=value: self._set_visible(v))
            top.addWidget(btn)
        col.addLayout(top)

        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter note types…")
        self.filter.textChanged.connect(self._apply_filter)
        col.addWidget(self.filter)

        col.addWidget(self._models_table())
        return page

    def _models_table(self) -> QTableWidget:
        headers = ["Note type", "Enabled", "Bake (mobile)", "Text size", "Main field(s)"] + [label.split(" ", 1)[1] for _, label in FEATURES]
        table = QTableWidget(len(self.model_names), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, len(headers)):
            table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        models_cfg = self.cfg.get("models", {})
        default_enabled = bool(self.cfg["defaultModelEnabled"])
        for r, name in enumerate(self.model_names):
            entry = models_cfg.get(name, {})
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(r, 0, item)

            cb = QCheckBox()
            cb.setChecked(bool(entry.get("enabled", default_enabled)))
            table.setCellWidget(r, 1, _centered(cb))

            bake = QCheckBox()
            bake.setChecked(bool(entry.get("baked", False)))
            table.setCellWidget(r, 2, _centered(bake))

            size = QSpinBox()
            size.setRange(0, 300)
            size.setSingleStep(5)
            size.setSpecialValueText("Global")
            size.setSuffix(" %")
            stored = int(entry.get("textSize") or 0)
            size.setValue(max(50, stored) if stored else 0)
            # 0 = Global, otherwise 50–300 %: stepping up from Global lands on 50, stepping down from 50 on Global
            size.setKeyboardTracking(False)
            size.valueChanged.connect(lambda v, s=size: s.setValue(0 if v >= 45 else 50) if 0 < v < 50 else None)
            table.setCellWidget(r, 3, size)

            main = QLineEdit(", ".join(config.resolve_fields(self.cfg, name)))
            main.setPlaceholderText("auto")
            main.setMinimumWidth(110)
            table.setCellWidget(r, 4, main)

            combos: Dict[str, QComboBox] = {}
            overrides = entry.get("features", {})
            for c, (key, _) in enumerate(FEATURES, start=5):
                combo = QComboBox()
                combo.addItems(OVERRIDE_OPTIONS)
                if key in overrides:
                    combo.setCurrentIndex(1 if overrides[key] else 2)
                table.setCellWidget(r, c, combo)
                combos[key] = combo
            self.rows.append((name, cb, bake, size, main, combos))
        self.table = table
        return table

    # ------------------------------------------------------------ actions
    def _set_visible(self, value: bool) -> None:
        for r, (_, cb, _, _, _, _) in enumerate(self.rows):
            if not self.table.isRowHidden(r):
                cb.setChecked(value)

    def _apply_filter(self, text: str) -> None:
        needle = text.lower().strip()
        for r, (name, _, _, _, _, _) in enumerate(self.rows):
            self.table.setRowHidden(r, bool(needle) and needle not in name.lower())

    def _collect_models(self, default_enabled: bool) -> Dict[str, Any]:
        """Store only what differs from the defaults, so the config stays small."""
        # The config is shared by every profile: entries for note types that are not in this
        # collection belong to another profile and must survive the save.
        models: Dict[str, Any] = {
            name: entry for name, entry in self.cfg.get("models", {}).items() if name not in self.model_ids
        }
        for name, cb, bake, size, main, combos in self.rows:
            entry: Dict[str, Any] = {}
            if cb.isChecked() != default_enabled:
                entry["enabled"] = cb.isChecked()
            if bake.isChecked():
                entry["baked"] = True
            if size.value():
                entry["textSize"] = size.value()
            main_fields = [f.strip() for f in main.text().split(",") if f.strip()]
            if main_fields:
                entry["fields"] = main_fields
            overrides = {k: (c.currentIndex() == 1) for k, c in combos.items() if c.currentIndex() != 0}
            if overrides:
                entry["features"] = overrides
            if entry:
                entry["id"] = self.model_ids[name]  # lets the entry follow a rename
                models[name] = entry
        return models

    def _save(self) -> None:
        cfg = self.cfg
        cfg["enabled"] = self.cb_enabled.isChecked()
        cfg["applyIn"] = {k: cb.isChecked() for k, cb in self.cb_where.items()}
        cfg["skipIfTemplateHasOwn"] = self.cb_skip.isChecked()
        cfg["toggleShortcut"] = self.le_shortcut.text().strip()
        cfg["keyReplayAnswer"] = self.le_replay_answer.text().strip()
        cfg["keyReplayCard"] = self.le_replay_card.text().strip()
        cfg["replayButtons"] = self.cb_replay_buttons.isChecked()
        cfg["features"] = {k: cb.isChecked() for k, cb in self.cb_feature.items()}
        cfg["speech"].update({
            "rate": round(self.sp_rate.value(), 2),
            "pitch": round(self.sp_pitch.value(), 2),
            "lang": self.le_lang.text().strip() or "en-US",
            "voice": self.le_voice.text().strip(),
            "blankWord": self.le_blank.text().strip() or "blank",
            "answerRead": self.cmb_answer.currentData(),
            "delayMs": self.sp_delay.value(),
        })
        cfg["text"] = {"sizePct": self.sp_text.value()}
        cfg["defaultModelEnabled"] = self.cb_default.isChecked()
        cfg["models"] = self._collect_models(cfg["defaultModelEnabled"])
        config.save(cfg)
        baked, removed = [], []
        try:
            baked, removed = templates.sync(cfg)
        except Exception as exc:  # the settings are already saved: report, don't leave the dialog stuck
            showWarning(f"Prisma: the settings were saved, but updating the baked templates failed:\n\n{exc}")
        msg = "Prisma: settings saved"
        if baked:
            msg += f" · baked templates updated in {len(baked)} note type(s)"
        if removed:
            msg += f" · removed from {len(removed)} note type(s)"
        tooltip(msg, period=2500)
        if self.on_saved:
            self.on_saved(cfg)
        self.accept()
