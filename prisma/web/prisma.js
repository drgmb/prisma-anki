/*
 * Prisma — script injected by the add-on into every card's HTML.
 * Author: drgmb · https://github.com/drgmb
 * Reads window.__PRISMA_CFG (written by the Python side), applies the features to #qa, then cleans up.
 *
 * Sections: 1 config · 2 DOM helpers · 3 random layout · 4 word wrapping
 *           5 BeeLine · 6 speech / karaoke / reveal · 7 run
 */
(function () {
  "use strict";
  var AUTHOR = "drgmb"; // https://github.com/drgmb
  window.__PRISMA_BY = AUTHOR;

  // inline styles Prisma writes on the root; keep in sync with injector.py (_RESET)
  var STYLE_PROPS = ["maxWidth", "marginLeft", "marginRight", "textAlign", "wordSpacing",
                     "letterSpacing", "paddingLeft", "fontSize"];

  // ------------------------------------------------------------ 1. config
  var cfg = window.__PRISMA_CFG;
  window.__PRISMA_CFG = null;
  if (!cfg) return;

  var hasSpeech = "speechSynthesis" in window;
  if (hasSpeech) { try { speechSynthesis.cancel(); } catch (e) { /* ignore */ } }

  var root = document.getElementById("qa") || document.body;
  if (!root) return;

  // baked front block re-rendered on the back side (FrontSide tag): the back gets no Prisma.
  // Step aside without touching the layout, so the answer keeps the question's shape.
  if (cfg.baked && cfg.side === "question" && document.getElementById("prisma-answer-marker")) return;

  // #qa outlives the card: drop what the previous card left behind (observers, timers, inline styles)
  cleanup();

  // desktop add-on says "off" for this card (toggle, note type disabled…): baked blocks obey too
  if (cfg.baked && window.__PRISMA_OFF) return;

  // the card's own template already ships these features: don't apply on top
  if (cfg.skipIfTemplateHasOwn && window.LEITURA_CONFIG) return;

  var F = cfg.features || {};
  var SPEECH = cfg.speech || {};
  var LAYOUT = cfg.layout || {};
  var on = {
    speak: !!F.speech && hasSpeech,
    layout: !!F.randomLayout,
    bionic: !!F.bionic,
    beeline: !!F.beeline
  };
  // every feature stands on its own: with the speech off, highlight and reveal follow a silent pacer
  on.karaoke = !!F.karaoke;
  on.reveal = !!F.progressiveReveal;

  // the back is shown exactly as its template made it: there Prisma only reads aloud (and highlights)
  var backOnly = cfg.side === "answer";
  if (backOnly) {
    if (!on.speak) return;
    on.layout = on.bionic = on.beeline = on.reveal = false;
  }
  // on the back the speech starts by itself only when speech.answerRead asks for it; otherwise the block
  // just stands by for the replay shortcuts
  var autoRead = !backOnly || SPEECH.answerRead === "full" || SPEECH.answerRead === "cloze";
  if (on.speak) { window.__PRISMA_REPLAY = replay; installKeys(); addButtons(); } // read again: keys and buttons inside the card

  var needsWords = on.speak || on.bionic || on.beeline || on.karaoke || on.reveal;
  if (!autoRead) needsWords = false;
  var sizePct = backOnly ? 100 : +cfg.textSizePct; if (isNaN(sizePct) || sizePct <= 0) sizePct = 100;
  var textBase = Math.min(3, Math.max(0.5, sizePct / 100)); // 1 = template size
  if (!needsWords && !on.layout && textBase === 1 && !window.__PRISMA_REPLAY) return; // nothing to do and no replay to serve

  // ------------------------------------------------------------ 2. DOM helpers
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, INPUT: 1, BUTTON: 1, SELECT: 1,
                    SVG: 1, MATH: 1, "ANKI-MATHJAX": 1 };
  // containers that are never reading material, whatever the template calls them exactly
  // (tags-container, prettify-tags, timer, countdown…)
  var NOT_CONTENT = /(^|[^a-z])(tags?|timer|countdown)([^a-z]|$)/i;
  var stops = []; // teardown callbacks for this card
  var stopSpeech = null; // teardown of the speech in progress (shortcuts replay without touching the rest)

  function rand(min, max) { return min + Math.random() * (max - min); }
  function num(v, fallback) { v = +v; return isNaN(v) ? fallback : v; }

  function cleanup() {
    window.__PRISMA_REPLAY = null;
    if (window.__PRISMA_KEYS) { document.removeEventListener("keydown", window.__PRISMA_KEYS); window.__PRISMA_KEYS = null; }
    Array.prototype.forEach.call(document.querySelectorAll(".prisma-replay"), function (b) { b.parentNode.removeChild(b); });
    var prev = window.__PRISMA_STATE;
    window.__PRISMA_STATE = null;
    if (prev && typeof prev.stop === "function") { try { prev.stop(); } catch (e) { /* ignore */ } }
    var styled = Array.prototype.slice.call(document.querySelectorAll("[data-prisma-styled]"));
    styled.forEach(function (el) {
      STYLE_PROPS.forEach(function (p) { el.style[p] = ""; });
      el.removeAttribute("data-prisma-styled");
    });
  }

  function isSkipped(el) {
    for (; el && el !== root; el = el.parentNode) {
      if (el.nodeType !== 1) continue;
      var tag = (el.tagName || "").toUpperCase();
      if (SKIP_TAGS[tag] || tag.indexOf("MJX-") === 0) return true; // rendered MathJax included
      if (el.hasAttribute("data-prisma-skip")) return true;
      if (NOT_CONTENT.test((el.id || "") + " " + (el.getAttribute("class") || ""))) return true;
      if (el.classList.contains("kw")) return true; // already processed
    }
    return false;
  }
  function isRendered(el) {
    // a display:contents wrapper has no box of its own: what counts is the element around it
    while (el && el !== root && el.tagName === "PRISMA-TARGET") el = el.parentElement;
    return !el || el === root || el.getClientRects().length > 0;
  }
  /** Text the author (or the template's cloze styling) colored on purpose keeps its color. */
  function hasOwnColor(el) {
    for (; el && el !== root; el = el.parentNode) {
      if (el.nodeType !== 1) continue;
      if ((el.style && el.style.color) || (el.tagName === "FONT" && el.getAttribute("color"))) return true;
      if (el.classList.contains("cloze") || el.classList.contains("cloze-hint")) return true;
    }
    return false;
  }
  /** Text a template hides with a transparent color (AnKing's countdown timer…) must stay hidden and unread. */
  var transparentCache = typeof Map === "function" ? new Map() : null;
  function isTransparent(el) {
    if (!el || !window.getComputedStyle) return false;
    if (transparentCache && transparentCache.has(el)) return transparentCache.get(el);
    var color = getComputedStyle(el).color || "";
    var m = /^rgba\(.*,\s*([\d.]+)\s*\)$/.exec(color);
    var result = color === "transparent" || (!!m && parseFloat(m[1]) === 0);
    if (transparentCache) transparentCache.set(el, result);
    return result;
  }

  /**
   * Where Prisma applies: what the front of the card shows (and, on the back, that same content
   * again), never tags, timers, fields that only exist on the back, or buttons.
   * 1. prisma-target wrapper elements written by the add-on (runtime) or baked into the template
   *    (helper fields a template keeps in a hidden container are left out);
   * 2. failing that, the whole card (tags and timers are still skipped by name).
   */
  function findTargets() {
    var marked = Array.prototype.slice.call(root.querySelectorAll("prisma-target"));
    marked = marked.filter(function (el) {
      return !isSkipped(el.parentNode) && !(el.parentNode.closest && el.parentNode.closest("prisma-target"));
    });
    var shown = marked.filter(isRendered);
    if (shown.length) return shown;
    if (marked.length) return marked;
    return [root];
  }

  function isDarkTheme() {
    return !!document.querySelector(".night_mode, .nightMode") || document.body.classList.contains("nightMode");
  }
  function isAlive(spans) { return !!spans.length && document.body.contains(spans[0]); }

  // ------------------------------------------------------------ 3. random layout
  /** One draw per card. */
  function drawLayout() {
    return {
      maxWidth: rand(num(LAYOUT.minWidthEm, 24), num(LAYOUT.maxWidthEm, 44)).toFixed(1) + "em",
      textAlign: Math.random() < 0.5 ? "left" : "justify",
      wordSpacing: rand(0, num(LAYOUT.maxWordSpacingPx, 3)).toFixed(2) + "px",
      letterSpacing: rand(0, num(LAYOUT.maxLetterSpacingPx, 1.2)).toFixed(2) + "px",
      indent: +rand(0, num(LAYOUT.maxIndentPx, 30)).toFixed(0),
      fontPct: rand(num(LAYOUT.minFontPct, 95), num(LAYOUT.maxFontPct, 107))
    };
  }

  function randomizeLayout(targets) {
    var L = drawLayout();
    var refWidth = root.clientWidth; // what the template's image rules were written against
    var images = collectImages(targets, refWidth);
    targets.forEach(function (el) {
      var s = el.style;
      s.maxWidth = L.maxWidth;
      s.marginLeft = "auto";
      s.marginRight = "auto";
      s.textAlign = L.textAlign;
      s.wordSpacing = L.wordSpacing;
      s.letterSpacing = L.letterSpacing;
      s.paddingLeft = L.indent + "px";
      // on the root the text size is part of the same property; on a wrapper it multiplies the root's
      s.fontSize = ((el === root ? textBase : 1) * L.fontPct).toFixed(1) + "%";
      el.setAttribute("data-prisma-styled", "1");
    });
    protectImages(images, L.indent);
  }
  function applyTextSize() {
    root.style.fontSize = (textBase * 100).toFixed(1) + "%";
    root.setAttribute("data-prisma-styled", "1");
  }

  /**
   * Images are not part of the reading exercise: the narrower, indented, left/justified text column
   * must not shrink or push them. Each image keeps the size limit its template gave it (resolved
   * against the full card width, before the column narrows) and is centered on the card.
   */
  function collectImages(targets, refWidth) {
    var out = [];
    targets.forEach(function (el) {
      Array.prototype.forEach.call(el.querySelectorAll("img"), function (img) {
        var mw = getComputedStyle(img).maxWidth || "";
        var cap = refWidth;
        if (/%$/.test(mw)) cap = refWidth * parseFloat(mw) / 100;
        else if (/px$/.test(mw)) cap = Math.min(refWidth, parseFloat(mw));
        out.push({ img: img, capRatio: refWidth ? cap / refWidth : 1 });
      });
    });
    return out;
  }
  function protectImages(images, indent) {
    if (!images.length) return;
    function place(item) {
      var img = item.img;
      if (!document.body.contains(img)) return;
      if (img.complete && img.naturalWidth && img.naturalWidth < 64) return; // inline icon / symbol
      img.style.setProperty("max-width", Math.floor(root.clientWidth * item.capRatio) + "px", "important");
      img.style.height = "auto";
      img.style.display = "block";
      img.style.marginRight = "auto";
      var column = img.parentElement ? img.parentElement.clientWidth : 0;
      var width = img.getBoundingClientRect().width;
      // centered on the card, not on the indented column: may be negative when wider than the column
      img.style.marginLeft = (column && width ? ((column - width) / 2 - indent / 2).toFixed(1) + "px" : "auto");
    }
    function placeAll() { images.forEach(place); }
    images.forEach(function (item) {
      if (!item.img.complete) item.img.addEventListener("load", function () { place(item); }, { once: true });
    });
    placeAll();
    reflowCallbacks.push(placeAll);
  }

  // ------------------------------------------------------------ 4. word wrapping
  function collectTextNodes(targets) {
    var nodes = [];
    targets.forEach(function (target) {
      var walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT, null, false);
      while (walker.nextNode()) {
        var node = walker.currentNode;
        if (!/\S/.test(node.nodeValue)) continue;
        if (isSkipped(node.parentNode) || !isRendered(node.parentElement)) continue;
        if (isTransparent(node.parentElement)) continue;
        nodes.push(node);
      }
    });
    return nodes;
  }

  /**
   * MathJax typesets after this script runs, so raw \( … \) and \[ … \] must reach it untouched.
   * Splits `text` into [chunk, isMath] pairs; `state.close` carries an open formula across text nodes.
   */
  var MATH_OPEN = /\\\(|\\\[/;
  function splitMath(text, state) {
    var out = [], pos = 0;
    while (pos < text.length) {
      var from = pos, searchFrom = pos;
      if (!state.close) {
        var m = MATH_OPEN.exec(text.slice(pos));
        if (!m) { out.push([text.slice(pos), false]); break; }
        if (m.index) out.push([text.slice(pos, pos + m.index), false]);
        from = pos + m.index;
        searchFrom = from + 2;
        state.close = m[0] === "\\(" ? "\\)" : "\\]";
      }
      var end = text.indexOf(state.close, searchFrom);
      var upTo = end < 0 ? text.length : end + 2;
      if (end >= 0) state.close = null;
      out.push([text.slice(from, upTo), true]);
      pos = upTo;
    }
    return out;
  }

  function makeWordSpan(word, colored) {
    var span = document.createElement("span");
    span.className = "kw" + (on.reveal ? " kw-hidden" : "");
    span.setAttribute("data-p", AUTHOR);
    if (colored) span.dataset.beelineSkip = "1";
    if (on.bionic && !colored) {
      var ratio = num(LAYOUT.bionicRatio, 0.4);
      var boldLen = Math.min(word.length, Math.max(1, Math.ceil(word.length * ratio)));
      var bold = document.createElement("span");
      bold.style.fontWeight = "700";
      bold.textContent = word.slice(0, boldLen);
      span.appendChild(bold);
      span.appendChild(document.createTextNode(word.slice(boldLen)));
    } else {
      span.textContent = word;
    }
    return span;
  }

  /** Wraps every visible word in <span class="kw">; returns the spans in reading order. */
  function wrapWords(targets) {
    var spans = [], mathState = { close: null };
    collectTextNodes(targets).forEach(function (node) {
      var chunks = splitMath(node.nodeValue, mathState);
      if (!chunks.some(function (c) { return !c[1] && /\S/.test(c[0]); })) return; // formula only
      var colored = hasOwnColor(node.parentNode);
      var frag = document.createDocumentFragment();
      chunks.forEach(function (chunk) {
        if (chunk[1]) { frag.appendChild(document.createTextNode(chunk[0])); return; }
        chunk[0].split(/(\s+)/).forEach(function (part) {
          if (!part) return;
          if (!part.trim()) { frag.appendChild(document.createTextNode(part)); return; }
          var span = makeWordSpan(part, colored);
          frag.appendChild(span);
          spans.push(span);
        });
      });
      node.parentNode.replaceChild(frag, node);
    });
    return spans;
  }

  // ------------------------------------------------------------ 5. BeeLine
  function hslToRgb(h, s, l) {
    s /= 100; l /= 100;
    var c = (1 - Math.abs(2 * l - 1)) * s;
    var x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    var m = l - c / 2;
    var rgb = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
            : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return rgb.map(function (v) { return Math.round((v + m) * 255); });
  }
  function mixRgb(a, b, t) {
    return "rgb(" + [0, 1, 2].map(function (i) { return Math.round(a[i] + (b[i] - a[i]) * t); }).join(",") + ")";
  }

  /** Palette: base → color A → base → color B; lightness locked to a readable band for the theme. */
  function makePalette() {
    var dark = isDarkTheme();
    function readable(hue) {
      var sat = rand(70, 90);
      var light = dark ? rand(65, 80) : rand(25, 40);
      return hslToRgb(hue, sat, light);
    }
    var hue1 = Math.random() * 360;
    var hue2 = (hue1 + 120 + Math.random() * 120) % 360;
    var base = dark ? [235, 235, 235] : [30, 30, 30];
    return [base, readable(hue1), base, readable(hue2)];
  }

  /**
   * Groups the spans by visual line. A span stays on the current line while it overlaps the line's
   * vertical band, so superscripts, subscripts and mixed font sizes don't start a new line.
   */
  function groupByLine(spans) {
    var lines = [], line = [], top = 0, bottom = 0;
    spans.forEach(function (s) {
      if (s.dataset.beelineSkip === "1") return;
      var r = s.getBoundingClientRect();
      if (!r.width && !r.height) return; // not rendered (any more)
      var mid = (r.top + r.bottom) / 2;
      var sameLine = line.length && ((mid > top && mid < bottom) || ((top + bottom) / 2 > r.top && (top + bottom) / 2 < r.bottom));
      if (!sameLine) {
        if (line.length) lines.push(line);
        line = [];
        top = r.top; bottom = r.bottom;
      } else {
        top = Math.min(top, r.top); bottom = Math.max(bottom, r.bottom);
      }
      line.push(s);
    });
    if (line.length) lines.push(line);
    return lines;
  }

  function applyBeeLine(spans, palette) {
    function paint() {
      groupByLine(spans).forEach(function (line, li) {
        var from = palette[li % palette.length];
        var to = palette[(li + 1) % palette.length]; // end of a line = start of the next
        var n = line.length;
        line.forEach(function (s, i) { s.style.color = mixRgb(from, to, n > 1 ? i / (n - 1) : 0); });
      });
    }
    paint();

    reflowCallbacks.push(function () { if (isAlive(spans)) paint(); });
  }

  /** Lines move when the window is resized, images load, MathJax typesets or a hint opens. */
  var reflowCallbacks = [];
  function watchReflow() {
    if (!reflowCallbacks.length) return;
    var timer = null, late = null, observer = null;
    function stop() {
      clearTimeout(timer);
      clearTimeout(late);
      if (observer) observer.disconnect();
      window.removeEventListener("resize", reflow);
    }
    function reflow() {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (!document.body.contains(root) || window.__PRISMA_STATE !== state) { stop(); return; }
        reflowCallbacks.forEach(function (fn) { fn(); });
      }, 150);
    }
    if (window.ResizeObserver) {
      observer = new ResizeObserver(reflow);
      observer.observe(root);
    } else {
      window.addEventListener("resize", reflow);
    }
    late = setTimeout(reflow, 600);
    stops.push(stop);
  }

  // ------------------------------------------------------------ 6. speech / karaoke / reveal
  function buildUtteranceText(spans, groups) {
    var starts = [], text = "";
    spans.forEach(function (s, i) {
      var w = s.textContent;
      if (w.indexOf("[...]") === 0) w = (SPEECH.blankWord || "blank") + w.slice(5);
      // a pause between separate answers (cloze mode): punctuation makes the synthesizer breathe
      if (i) text += groups && groups[i] !== groups[i - 1] ? ". " : " ";
      starts.push(text.length);
      text += w;
    });
    return { text: text, starts: starts };
  }

  /** Index of the span whose word starts at the largest offset ≤ charIndex (binary search). */
  function spanIndexAt(starts, charIndex) {
    var lo = 0, hi = starts.length - 1, best = 0;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (starts[mid] <= charIndex) { best = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return best;
  }

  function pickVoice(lang) {
    var voices = speechSynthesis.getVoices();
    var byName = SPEECH.voice && voices.find(function (v) { return v.name === SPEECH.voice; });
    if (byName) return byName;
    var want = lang.toLowerCase();
    return voices.find(function (v) { return (v.lang || "").replace("_", "-").toLowerCase() === want; }) || null;
  }

  /** Moves the highlight / the reveal to word `i`; shared by the speech and by the silent pacer. */
  function makeStepper(spans) {
    var current = -1;
    return {
      index: function () { return current; },
      to: function (i) {
        if (i === current || i < 0 || i >= spans.length) return;
        if (on.karaoke && current >= 0) spans[current].classList.remove("kw-active");
        if (on.reveal) for (var k = 0; k <= i; k++) spans[k].classList.remove("kw-hidden");
        if (on.karaoke) spans[i].classList.add("kw-active");
        current = i;
      },
      done: function () { spans.forEach(function (s) { s.classList.remove("kw-active", "kw-hidden"); }); }
    };
  }

  /** Reading time of one word at the configured speed: longer words and punctuation take longer. */
  function wordMs(word) {
    var rate = Math.min(2, Math.max(0.5, num(SPEECH.rate, 1)));
    var beat = 60000 / (170 * rate); // ~170 words per minute at 1×, close to the system voices
    var letters = word.replace(/[^0-9A-Za-z\u00C0-\u024F]/g, "").length || 1;
    var ms = beat * (0.55 + 0.09 * Math.min(letters, 14));
    if (/[.!?;:]["')\]]*$/.test(word)) ms += beat * 0.9;
    else if (/,["')\]]*$/.test(word)) ms += beat * 0.4;
    return ms;
  }

  /** Walks the words on a timer, without any sound. Returns a function that stops it. */
  function runPacer(spans, stepper, from) {
    var i = Math.max(0, from), timer = null, stopped = false;
    function tick() {
      if (stopped || !isAlive(spans)) return;
      if (i >= spans.length) { stepper.done(); return; }
      stepper.to(i);
      timer = setTimeout(tick, wordMs(spans[i].textContent));
      i++;
    }
    tick();
    return function () { stopped = true; clearTimeout(timer); };
  }

  function paceSilently(spans) {
    var stopPacer = null, stopped = false;
    var delay = num(SPEECH.delayMs, 350);
    var timer = setTimeout(function () {
      if (!stopped) stopPacer = runPacer(spans, makeStepper(spans), 0);
    }, delay >= 0 ? delay : 350);
    stops.push(function () { stopped = true; clearTimeout(timer); if (stopPacer) stopPacer(); });
  }

  /**
   * What to read on the back (SPEECH.answerRead): "full" re-reads the whole card; "cloze" reads only
   * the revealed cloze answers (non-cloze cards: only the text after the answer divider).
   * Returns { spans, groups } — groups[i] tells which cloze a span belongs to.
   */
  function pickSpoken(all, mode) {
    if (!backOnly || mode !== "cloze") return { spans: all, groups: null };
    var clozes = Array.prototype.slice.call(root.querySelectorAll(".cloze"));
    var picked = [], groups = [];
    if (clozes.length) {
      all.forEach(function (s) {
        for (var i = 0; i < clozes.length; i++) {
          if (clozes[i].contains(s)) { picked.push(s); groups.push(i); return; }
        }
      });
    } else {
      var hr = document.getElementById("answer");
      if (hr) {
        all.forEach(function (s) {
          if (hr.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING) { picked.push(s); groups.push(0); }
        });
      }
    }
    return picked.length ? { spans: picked, groups: groups } : { spans: all, groups: null };
  }

  function speak(all, mode) {
    var sel = pickSpoken(all, mode || SPEECH.answerRead), spans = sel.spans;
    var built = buildUtteranceText(spans, sel.groups);
    var timers = [];
    var stepper = makeStepper(spans), stopPacer = null;
    function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
    function endPacer() { if (stopPacer) { stopPacer(); stopPacer = null; } }
    function revealAll() { endPacer(); stepper.done(); }

    var utt = new SpeechSynthesisUtterance(built.text);
    utt.lang = SPEECH.lang || "en-US";
    utt.rate = Math.min(2, Math.max(0.5, num(SPEECH.rate, 1)));
    utt.pitch = Math.min(2, Math.max(0.5, num(SPEECH.pitch, 1)));

    utt.onboundary = function (e) {
      if (e.name !== "word") return;
      endPacer(); // the engine does report words: it leads
      stepper.to(spanIndexAt(built.starts, e.charIndex));
    };
    utt.onstart = function () {
      // some engines (network voices, Android web views) never report word boundaries:
      // the silent pacer then carries the highlight / the reveal along with the voice
      if (!on.karaoke && !on.reveal) return;
      later(function () {
        if (stepper.index() < 0 && !stopPacer && !stopped) stopPacer = runPacer(spans, stepper, 0);
      }, 700);
    };
    utt.onend = revealAll;
    utt.onerror = revealAll;

    var started = false, stopped = false;
    function go() {
      if (started || stopped) return;
      started = true;
      if (!isAlive(spans)) return; // the card is gone: don't read it over the next one
      var voice = pickVoice(utt.lang);
      if (voice) utt.voice = voice;
      speechSynthesis.cancel();
      speechSynthesis.speak(utt);
      // some web views (Android) expose speechSynthesis but never speak, and iOS waits for a tap:
      // the highlight / the reveal must not wait for a voice that isn't coming
      if (on.karaoke || on.reveal) later(function () {
        if (stepper.index() < 0 && !stopPacer && !stopped && !speechSynthesis.speaking) stopPacer = runPacer(spans, stepper, 0);
      }, 1500);
      // safety net: if nothing is driving the reveal, the text must not stay hidden forever
      if (on.reveal) later(function () { if (!speechSynthesis.speaking && !stopPacer) revealAll(); }, 3000);
    }
    function begin() {
      if (stopped) return;
      if (speechSynthesis.getVoices().length) go();
      else {
        speechSynthesis.addEventListener("voiceschanged", go, { once: true });
        later(go, 1000);
      }
    }

    // keeping a reference stops Chromium from garbage-collecting the utterance mid-speech
    // (which would silence onboundary/onend and leave words hidden)
    window.__PRISMA_UTT = utt;
    stopSpeech = function () {
      stopped = true;
      endPacer();
      timers.forEach(clearTimeout);
      speechSynthesis.removeEventListener("voiceschanged", go);
      if (window.__PRISMA_UTT === utt) window.__PRISMA_UTT = null;
    };
    stops.push(stopSpeech);

    var delay = num(SPEECH.delayMs, 350);
    later(begin, delay >= 0 ? delay : 350);
  }

  /**
   * Read again, on demand (desktop shortcuts). mode "cloze": only the cloze answer(s) — on the back;
   * anything else: the whole card (front and back together when the answer is showing).
   */
  function replay(mode) {
    if (!on.speak) return;
    if (stopSpeech) { try { stopSpeech(); } catch (e) { /* ignore */ } stopSpeech = null; }
    try { speechSynthesis.cancel(); } catch (e) { /* ignore */ }
    var spans = Array.prototype.slice.call(root.querySelectorAll(".kw"));
    if (!spans.length) spans = wrapWords(findTargets()); // the back with no automatic reading: words not wrapped yet
    spans.forEach(function (s) { s.classList.remove("kw-active", "kw-hidden"); });
    if (spans.length) speak(spans, mode === "cloze" ? "cloze" : "full");
  }

  // ------------------------------------------------------------ read again: keys and buttons
  /** "Shift + Q" → function(event) telling whether the event is that key (same idea as AnKing's shortcutMatcher). */
  function keyMatcher(shortcut) {
    var parts = String(shortcut || "").toLowerCase().split("+").map(function (p) { return p.trim(); }).filter(Boolean);
    if (!parts.length) return function () { return false; };
    var main = parts[parts.length - 1];
    var ctrl = parts.indexOf("ctrl") >= 0 || parts.indexOf("cmd") >= 0;
    var shift = parts.indexOf("shift") >= 0, alt = parts.indexOf("alt") >= 0;
    if (main === "ctrl" || main === "cmd" || main === "shift" || main === "alt") return function () { return false; };
    if (main === "space") main = " ";
    return function (e) {
      if (!!(e.ctrlKey || e.metaKey) !== ctrl || !!e.shiftKey !== shift || !!e.altKey !== alt) return false;
      var k = String(e.key || "").toLowerCase();
      if (k === main) return true;
      if (/^[a-z]$/.test(main)) return e.code === "Key" + main.toUpperCase(); // layouts / Alt changing the letter
      if (/^\d$/.test(main)) return e.code === "Digit" + main || e.code === "Numpad" + main;
      return false;
    };
  }

  function installKeys() {
    var K = cfg.keys || {};
    var isAnswer = keyMatcher(K.answer), isCard = keyMatcher(K.card);
    function onKey(e) {
      var t = e.target;
      if (e.repeat || (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)))) return;
      if (isAnswer(e)) replay("cloze");
      else if (isCard(e)) replay("full");
      else return;
      e.preventDefault();
      e.stopPropagation();
    }
    document.addEventListener("keydown", onKey);
    window.__PRISMA_KEYS = onKey;
  }

  function addButtons() {
    var K = cfg.keys || {};
    if (!K.buttons) return;
    var bar = document.createElement("div");
    bar.className = "prisma-replay";
    bar.setAttribute("data-prisma-skip", "1");
    (backOnly ? [["\uD83D\uDD0A Answer", "cloze", K.answer], ["\uD83D\uDD0A Card", "full", K.card]]
              : [["\uD83D\uDD0A Read", "full", K.card]]).forEach(function (b) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b[0];
      if (b[2]) btn.title = "Shortcut: " + b[2];
      btn.addEventListener("click", function () { replay(b[1]); });
      bar.appendChild(btn);
    });
    root.appendChild(bar);
  }

  // ------------------------------------------------------------ 7. run
  var state = {
    stop: function () { stops.forEach(function (fn) { try { fn(); } catch (e) { /* ignore */ } }); }
  };
  window.__PRISMA_STATE = state;
  root.setAttribute("data-prisma-by", AUTHOR);
  root.setAttribute("data-prisma-sig", "ZHJnbWI=");

  if (!autoRead) return; // back with no automatic reading: only the replay shortcuts are served

  // Runs synchronously, before the card's first paint: no flash, no blank wait.
  // Only the speech honors speech.delayMs.
  try {
    var targets = findTargets();
    if (textBase !== 1) applyTextSize();
    if (on.layout) randomizeLayout(targets);
    if (needsWords) {
      var spans = wrapWords(targets);
      if (on.beeline && spans.length) applyBeeLine(spans, makePalette());
      if (on.speak && spans.length) speak(spans);
      else if ((on.karaoke || on.reveal) && spans.length) paceSilently(spans);
      else spans.forEach(function (s) { s.classList.remove("kw-hidden"); });
    }
    watchReflow();
  } catch (e) {
    // whatever went wrong, the card must stay readable: stop everything and show every word
    try { state.stop(); } catch (e2) { /* ignore */ }
    Array.prototype.forEach.call(root.querySelectorAll(".kw-hidden, .kw-active"), function (s) {
      s.classList.remove("kw-hidden", "kw-active");
    });
  }
})();
