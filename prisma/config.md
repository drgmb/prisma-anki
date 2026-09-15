# Prisma — by drgmb (https://github.com/drgmb)

Prefer the **Tools → Prisma…** window, which covers every option below.

| Key | Meaning |
|---|---|
| `enabled` | turns the whole add-on on/off |
| `applyOn.question` / `applyOn.answer` | apply to the front / to the back |
| `applyIn.review` / `preview` / `cardLayout` | where to apply: reviewer, card previewer, template editor |
| `features.*` | global defaults: `speech` (read aloud), `karaoke` (highlight the spoken word), `progressiveReveal` (reveal word by word), `randomLayout`, `bionic`, `beeline` |
| `speech.rate` | speech speed, 0.5 (slow) to 2.0 (fast) |
| `speech.pitch` / `lang` / `voice` / `delayMs` / `blankWord` | pitch, language, exact voice name (empty = first voice for the language), initial delay, how to read a cloze `[...]` |
| `layout.*` | ranges for the random layout and the bold fraction for bionic reading |
| `skipIfTemplateHasOwn` | don't apply to note types whose template already defines `LEITURA_CONFIG` |
| `defaultModelEnabled` | whether note types not listed in `models` are enabled |
| `models` | per note type: `{"enabled": true, "baked": true, "features": {"beeline": false}}` — `features` overrides only the keys present; `baked` writes the block into the templates (works on mobile) |
| `toggleShortcut` | shortcut to toggle the add-on on/off (there is no menu item for it) |

---
Prisma is written and maintained by **drgmb** — https://github.com/drgmb
