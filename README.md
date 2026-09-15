# Prisma

**by [drgmb](https://github.com/drgmb)** · [MIT license](LICENSE)

![Prisma showcase](docs/prisma-demo.gif)

*Video version: [docs/prisma-demo.mp4](docs/prisma-demo.mp4)*

An Anki desktop add-on that makes reading cards more active, on any note type you choose, without touching templates.

## Features

| | Feature | What it does |
|---|---|---|
| 🌈 | **Color gradient (BeeLine)** | Every line of text gets a color gradient; the end of one line has the color of the start of the next, guiding your eye across line breaks. Colors are drawn fresh for each card and stay readable in both light and dark themes. |
| 🅱 | **Bionic reading** | The beginning of each word is bold, anchoring your eye. |
| 🔀 | **Random layout** | Width, alignment, spacing and font size change on every showing, so you memorize the content rather than the visual shape of the card. |
| 🔊 | **Read aloud** | Reads the card with the system's speech synthesis, with **adjustable speed** from 0.5× to 2×, plus pitch, language and voice settings. |
| 🎤 | **Spoken-word highlight** | Karaoke style: the word being read lights up in amber. |
| 👁 | **Progressive reveal** | The text appears word by word, in time with the speech. |

Everything can be turned on or off globally and overridden per note type.

## Two ways to apply it

| Mode | How | Works on |
|---|---|---|
| **Runtime** (default) | The add-on injects the features into each card while it is shown. Templates are never touched. | Anki desktop |
| **Baked** | Tick **Bake (mobile)** for a note type and the add-on writes a marked block (style, preset, script) into that note type's templates. It syncs with the collection like any template edit, is refreshed every time you save the settings, and is removed cleanly when you untick it. | Anki desktop, AnkiDroid, AnkiMobile |

The block sits between `<!--prisma:start-->` and `<!--prisma:end-->` at the end of the template, plus a hidden marker at the top of the back template. Don't edit inside those markers; edit the settings instead.

## Installation

1. Download `prisma.ankiaddon` from the [latest release](https://github.com/drgmb/prisma-anki/releases/latest) (also in [`dist/`](dist/)).
2. In Anki: **Tools → Add-ons → Install from file…** and pick `prisma.ankiaddon`.
3. Restart Anki.
4. Open **Tools → Prisma…** and, on the **Note types** tab, tick the note types to apply it to. No note type is enabled by default.

## Settings

**Tools → Prisma…**

- **General**
  - Enable/disable the add-on; apply to the front and/or the back.
  - Where to apply: reviewer, card previewer, template editor.
  - Global default for each feature.
  - Speech: speed, pitch, language (`en-US`, `pt-BR`…), voice name, how to read a cloze `[...]`, initial delay.
  - Shortcut to toggle the add-on during review (default `Ctrl+Shift+L`; it is not shown in the menu).
- **Note types**
  - An "Enabled" box per note type, a name filter, and buttons to check/uncheck the visible rows.
  - For each feature, `Global` / `On` / `Off` per note type. Example: gradient everywhere, speech only on the English deck.

The same options exist as JSON under **Tools → Add-ons → Config** (documented there).

## Behavior details

- Hidden text, scripts, input fields and buttons are ignored by speech and by the gradient.
- Words you colored by hand in a card keep their color.
- If a note type's template already ships these features (it defines `LEITURA_CONFIG`), the add-on does not apply on top. This can be turned off.
- Switching cards or leaving the reviewer stops any speech in progress.
- The gradient is recomputed when the window is resized.

## Limitations

- The settings window and runtime mode are desktop only. On AnkiDroid and AnkiMobile use baked mode; the preset is frozen into the template at the time you save, so change settings on the desktop and sync.
- On mobile, reading aloud depends on the app's web view. iOS may require a tap before speech can start, and the available voices differ from the desktop.
- Speech depends on the voices installed on the system. On macOS the `Samantha` voice is the default; on other systems leave the voice name empty to use the first voice for the language.
- On heavily structured templates (tables, boxes), the random layout may shift elements. Use the per-note-type override to turn it off where it gets in the way.

## Repository layout

```
prisma/          the add-on (this folder is what gets zipped into prisma.ankiaddon)
dist/            packaged .ankiaddon
docs/            showcase GIF and MP4
demo/            the showcase generator (HTML timeline + headless-Chrome frame recorder)
```

### Add-on layout

```
prisma/
├── __init__.py    menu and shortcut
├── config.py      config load/save and per-note-type resolution
├── injector.py    Anki hooks: injects CSS + JS into the card HTML
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

## Building the package

```bash
cd prisma && zip -r -X ../dist/prisma.ankiaddon . -x meta.json '*.pyc' '__pycache__/*'
```

## Rendering the showcase

```bash
cd demo && npm install && node record.js record demo2.html && ffmpeg -framerate 30 -i frames/f%05d.jpg -c:v libx264 -pix_fmt yuv420p ../docs/prisma-demo.mp4
```
