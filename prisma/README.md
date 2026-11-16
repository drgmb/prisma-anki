# Prisma

**by [drgmb](https://github.com/drgmb)**

An Anki desktop add-on that makes reading cards more active, on any note type you choose, without touching templates.

## Features

| | Feature | What it does |
|---|---|---|
| 🌈 | **Color gradient (BeeLine)** | Every line of text gets a color gradient; the end of one line has the color of the start of the next, guiding your eye across line breaks. Colors are drawn fresh for each card and stay readable in both light and dark themes. |
| 🅱 | **Bionic reading** | The beginning of each word is bold, anchoring your eye. |
| 🔀 | **Random layout** | Width, alignment, spacing and font size change on every showing, so you memorize the content rather than the visual shape of the card. |
| 🔊 | **Read aloud** | Reads the card with the system's speech synthesis, with **adjustable speed** from 0.5× to 2×, plus pitch, language and voice settings. |
| 🎤 | **Word highlight** | Karaoke style: the word being read lights up in amber. Follows the voice when Read aloud is on; otherwise a silent pacer moves it at the configured speed. |
| 👁 | **Progressive reveal** | The text appears word by word, in time with the speech, or with the silent pacer when Read aloud is off. |

| 🔠 | **Text size** | Scale the whole card's text from 50 % to 300 %, globally or per note type. Works together with Random layout. |

Every feature works on its own and in any combination; everything can be turned on or off globally and overridden per note type.

## Two ways to apply it

| Mode | How | Works on |
|---|---|---|
| **Runtime** (default) | The add-on injects the features into each card while it is shown. Templates are never touched. | Anki desktop |
| **Baked** | Tick **Bake (mobile)** for a note type and the add-on writes a marked block (style, preset, script) into that note type's templates. It syncs with the collection like any template edit, is refreshed every time you save the settings, and is removed cleanly when you untick it. | Anki desktop, AnkiDroid, AnkiMobile |

The block sits between `<!--prisma:start-->` and `<!--prisma:end-->` at the end of the template, plus a hidden marker at the top of the back template. Don't edit inside those markers; edit the settings instead.

## Installation

1. In Anki: **Tools → Add-ons → Install from file…** and pick `prisma.ankiaddon`.
2. Restart Anki.
3. Open **Tools → Prisma…** and, on the **Note types** tab, tick the note types to apply it to. No note type is enabled by default.

## Settings

**Tools → Prisma…**

- **General**
  - Enable/disable the add-on.
  - Where to apply: reviewer, card previewer, template editor.
  - Global default for each feature, and the text size in percent.
  - Speech: speed, pitch, language (`en-US`, `pt-BR`…), voice name, how to read a cloze `[...]`, initial delay, and **what to read on the back** — nothing, the whole card again, or only the cloze answer(s).
  - Shortcut to toggle the add-on during review (default `Ctrl+Shift+L`; it is not shown in the menu).
- **Note types**
  - An "Enabled" box per note type, a name filter, and buttons to check/uncheck the visible rows.
  - For each feature, `Global` / `On` / `Off` per note type. Example: gradient everywhere, speech only on the English deck.
  - A text-size box per note type (`Global` or a percent), handy for dense decks or small screens.

The same options exist as JSON under **Tools → Add-ons → Config** (documented there).

## What Prisma touches on a card

Prisma works from the note type's templates, so it adapts to customized note types:

- **Front**: every field the front template shows. Tags, countdown timers, buttons, hidden or transparent text are never processed or read aloud.
- **Back**: never touched. The answer side is always shown exactly as the template made it.
- **Images** are never altered: the random layout narrows and indents the text only; images keep the size limit the template gives them and stay centered on the card.
- To choose the fields yourself, type their names in the **Main field(s)** column of the Note types tab (or `models[name].fields` in the JSON config).


- Hidden text, scripts, input fields and buttons are ignored by speech and by the gradient.
- Words you colored by hand in a card keep their color.
- If a note type's template already ships these features (it defines `LEITURA_CONFIG`), the add-on does not apply on top. This can be turned off.
- Switching cards or leaving the reviewer stops any speech in progress.
- **Read again, on demand** (reviewer, Read aloud on): `Ctrl+Shift+A` reads the answer again (the cloze answer(s)); `Ctrl+Shift+E` reads the whole card together with the answer. Both shortcuts can be changed in the settings window.
- The gradient is recomputed whenever the card's lines move: window resize, late images, MathJax, opened hints.
- Cloze deletions keep the color the template gives them.
- MathJax formulas (`\( … \)`, `\[ … \]`) are left untouched.
- The features are applied before the card's first paint; `speech.delayMs` only delays the reading.
- Cards that get no Prisma (other note types, add-on toggled off) are reset, so a previous card's layout or text size never leaks into them.
- Baked note types obey the desktop toggle and the per-note-type "Enabled" box too; a note type that is baked but not enabled gets no block.
- Settings follow a note type when it is renamed, and saving in one profile keeps the entries of the other profiles.
- If two copies of Prisma are installed (AnkiWeb + a local one), only one runs: the local (non-numeric folder) copy wins.

## Limitations

- The settings window and runtime mode are desktop only. On AnkiDroid and AnkiMobile use baked mode; the preset is frozen into the template at the time you save, so change settings on the desktop and sync.
- On mobile, reading aloud depends on the app's web view. iOS may require a tap before speech can start, and the available voices differ from the desktop.
- Speech depends on the voices installed on the system. On macOS the `Samantha` voice is the default; on other systems leave the voice name empty to use the first voice for the language.
- On heavily structured templates (tables, boxes), the random layout may shift elements. Use the per-note-type override to turn it off where it gets in the way.

## Code layout

```
prisma/
├── __init__.py    menu and shortcut
├── config.py      config load/save and per-note-type resolution
├── injector.py    Anki hooks: injects CSS + JS into the card HTML
├── fields.py      finds the fields Prisma works on and marks them (templates or rendered card)
├── dialog.py      settings window (PyQt6)
├── templates.py   bake mode: writes/removes the block in note-type templates
├── config.json    defaults
├── config.md      config documentation shown inside Anki
├── manifest.json  package metadata
└── web/
    ├── prisma.js   the features, executed inside the card
    └── prisma.css  styles for the highlight and the reveal
```

Tested on Anki 25.02.

## Author

Prisma is written and maintained by **drgmb** · https://github.com/drgmb. The injected blocks are signed with the author's name in comments and `data-prisma-by` attributes.

## Credits

The features were ported from the author's own note template, inspired by Anki-Prettify, AnKing Note Types, BeeLine Reader and Bionic Reading.
