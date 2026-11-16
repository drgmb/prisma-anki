# Prisma — by drgmb (https://github.com/drgmb)

Prefer the **Tools → Prisma…** window, which covers every option below.

| Key | Meaning |
|---|---|
| `enabled` | turns the whole add-on on/off |
| `applyIn.review` / `preview` / `cardLayout` | where to apply: reviewer, card previewer, template editor |
| `features.*` | global defaults: `speech` (read aloud), `karaoke` (highlight the spoken word), `progressiveReveal` (reveal word by word), `randomLayout`, `bionic`, `beeline` |
| `speech.rate` | speech speed, 0.5 (slow) to 2.0 (fast) |
| `speech.pitch` / `lang` / `voice` / `delayMs` / `blankWord` | pitch, language, exact voice name (empty = first voice for the language), initial delay, how to read a cloze `[...]` |
| `speech.answerRead` | what to read aloud on the back (the back's look is never changed): `"off"` (default), `"full"` (re-read the whole card) or `"cloze"` (only the revealed cloze answer(s); non-cloze cards: only the text after the answer divider). Baked note types get a speech-only block on the back too |
| `text.sizePct` | text size for the whole card, in percent of the template's size (50–300); per note type: `models[name].textSize` (0 or absent = global) |
| `layout.*` | ranges for the random layout and the bold fraction for bionic reading |
| `skipIfTemplateHasOwn` | don't apply to note types whose template already defines `LEITURA_CONFIG` |
| `defaultModelEnabled` | whether note types not listed in `models` are enabled |
| `models[name].fields` | field names Prisma works on, e.g. `["Text"]`; absent = automatic (every field the front shows; tags, timers and buttons excluded) |
| `models` | per note type: `{"enabled": true, "baked": true, "features": {"beeline": false}}` — `features` overrides only the keys present; `baked` writes the block into the templates (works on mobile) |
| `keyReplayAnswer` / `keyReplayCard` | keys, handled inside the card (so they also work in baked note types on mobile with a keyboard), to read again the cloze answer(s) / the whole card with the answer: `Q`, `Shift + Q`, `Ctrl + 1`…; empty = off. Need Read aloud on |
| `replayButtons` | show two small read-again buttons in the card (useful on touch screens) |
| `toggleShortcut` | shortcut to toggle the add-on on/off (there is no menu item for it) |

---
Prisma is written and maintained by **drgmb** — https://github.com/drgmb
