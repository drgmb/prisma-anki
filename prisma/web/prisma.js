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

  // ------------------------------------------------------------ 1. config
  var cfg = window.__PRISMA_CFG;
  window.__PRISMA_CFG = null;
  if (!cfg) return;

  var hasSpeech = "speechSynthesis" in window;
  if (hasSpeech) { try { speechSynthesis.cancel(); } catch (e) { /* ignore */ } }

  // the card's own template already ships these features: don't apply on top
  if (cfg.skipIfTemplateHasOwn && window.LEITURA_CONFIG) return;

  // baked front block re-rendered on the back side (FrontSide tag): the back has its own block, or none
  if (cfg.baked && cfg.side === "question" && document.getElementById("prisma-answer-marker")) return;

  var F = cfg.features || {};
  var SPEECH = cfg.speech || {};
  var LAYOUT = cfg.layout || {};
  var on = {
    speak: !!F.speech && hasSpeech,
    layout: !!F.randomLayout,
    bionic: !!F.bionic,
    beeline: !!F.beeline
  };
  on.karaoke = on.speak && !!F.karaoke;
  on.reveal = on.speak && !!F.progressiveReveal;

  var root = document.getElementById("qa") || document.body;
  if (!root) return;
  var needsWords = on.speak || on.bionic || on.beeline;
  var sizePct = +cfg.textSizePct; if (isNaN(sizePct) || sizePct <= 0) sizePct = 100;
  var textBase = Math.min(3, Math.max(0.5, sizePct / 100)); // 1 = template size
  if (!needsWords && !on.layout && textBase === 1) return;

  // ------------------------------------------------------------ 2. DOM helpers
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, INPUT: 1, BUTTON: 1, SELECT: 1 };

  function rand(min, max) { return min + Math.random() * (max - min); }
  function num(v, fallback) { v = +v; return isNaN(v) ? fallback : v; }

  function isSkipped(el) {
    for (; el && el !== root; el = el.parentNode) {
      if (el.nodeType !== 1) continue;
      if (SKIP_TAGS[el.tagName] || el.hasAttribute("data-prisma-skip")) return true;
      if (el.classList.contains("kw")) return true; // already processed
    }
    return false;
  }
  function isRendered(el) { return !el || el === root || el.getClientRects().length > 0; }
  function hasOwnColor(el) {
    for (; el && el !== root; el = el.parentNode) {
      if (el.nodeType !== 1) continue;
      if ((el.style && el.style.color) || (el.tagName === "FONT" && el.getAttribute("color"))) return true;
    }
    return false;
  }
  function isDarkTheme() {
    return !!document.querySelector(".night_mode, .nightMode") || document.body.classList.contains("nightMode");
  }

  // ------------------------------------------------------------ 3. random layout
  function randomizeLayout() {
    var s = root.style;
    s.maxWidth = rand(num(LAYOUT.minWidthEm, 24), num(LAYOUT.maxWidthEm, 44)).toFixed(1) + "em";
    s.marginLeft = "auto";
    s.marginRight = "auto";
    s.textAlign = Math.random() < 0.5 ? "left" : "justify";
    s.wordSpacing = rand(0, num(LAYOUT.maxWordSpacingPx, 3)).toFixed(2) + "px";
    s.letterSpacing = rand(0, num(LAYOUT.maxLetterSpacingPx, 1.2)).toFixed(2) + "px";
    s.paddingLeft = rand(0, num(LAYOUT.maxIndentPx, 30)).toFixed(0) + "px";
    s.fontSize = (textBase * rand(num(LAYOUT.minFontPct, 95), num(LAYOUT.maxFontPct, 107))).toFixed(1) + "%";
  }
  function applyTextSize() { root.style.fontSize = (textBase * 100).toFixed(1) + "%"; }

  // ------------------------------------------------------------ 4. word wrapping
  function collectTextNodes() {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    var nodes = [];
    while (walker.nextNode()) {
      var node = walker.currentNode;
      if (!/\S/.test(node.nodeValue)) continue;
      if (isSkipped(node.parentNode) || !isRendered(node.parentElement)) continue;
      nodes.push(node);
    }
    return nodes;
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
  function wrapWords() {
    var spans = [];
    collectTextNodes().forEach(function (node) {
      var colored = hasOwnColor(node.parentNode);
      var frag = document.createDocumentFragment();
      node.nodeValue.split(/(\s+)/).forEach(function (part) {
        if (!part) return;
        if (!part.trim()) { frag.appendChild(document.createTextNode(part)); return; }
        var span = makeWordSpan(part, colored);
        frag.appendChild(span);
        spans.push(span);
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

  /** Groups the spans by visual line (same vertical position on screen). */
  function groupByLine(spans) {
    var lines = [], line = [], lastTop = null;
    spans.forEach(function (s) {
      if (s.dataset.beelineSkip === "1") return;
      var top = s.getBoundingClientRect().top;
      if (lastTop !== null && Math.abs(top - lastTop) >= 2) { lines.push(line); line = []; }
      line.push(s);
      lastTop = top;
    });
    if (line.length) lines.push(line);
    return lines;
  }

  function applyBeeLine(spans) {
    var palette = makePalette();
    function paint() {
      groupByLine(spans).forEach(function (line, li) {
        var from = palette[li % palette.length];
        var to = palette[(li + 1) % palette.length]; // end of a line = start of the next
        var n = line.length;
        line.forEach(function (s, i) { s.style.color = mixRgb(from, to, n > 1 ? i / (n - 1) : 0); });
      });
    }
    paint();
    // lines change when the window is resized: repaint, and detach once the card is gone
    var timer = null;
    function onResize() {
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (document.body.contains(spans[0])) paint();
        else window.removeEventListener("resize", onResize);
      }, 150);
    }
    window.addEventListener("resize", onResize);
  }

  // ------------------------------------------------------------ 6. speech / karaoke / reveal
  function buildUtteranceText(spans) {
    var starts = [], text = "";
    spans.forEach(function (s, i) {
      var w = s.textContent;
      if (w === "[...]") w = SPEECH.blankWord || "blank";
      if (i) text += " ";
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

  function speak(spans) {
    var built = buildUtteranceText(spans);
    function revealAll() { spans.forEach(function (s) { s.classList.remove("kw-active", "kw-hidden"); }); }

    var utt = new SpeechSynthesisUtterance(built.text);
    utt.lang = SPEECH.lang || "en-US";
    utt.rate = Math.min(2, Math.max(0.5, num(SPEECH.rate, 1)));
    utt.pitch = Math.min(2, Math.max(0.5, num(SPEECH.pitch, 1)));

    var current = -1;
    utt.onboundary = function (e) {
      if (e.name !== "word") return;
      var i = spanIndexAt(built.starts, e.charIndex);
      if (i === current) return;
      if (on.karaoke && current >= 0) spans[current].classList.remove("kw-active");
      if (on.reveal) for (var k = 0; k <= i; k++) spans[k].classList.remove("kw-hidden");
      if (on.karaoke) spans[i].classList.add("kw-active");
      current = i;
    };
    utt.onend = revealAll;
    utt.onerror = revealAll;

    var started = false;
    function go() {
      if (started) return;
      started = true;
      var voice = pickVoice(utt.lang);
      if (voice) utt.voice = voice;
      speechSynthesis.cancel();
      speechSynthesis.speak(utt);
      // safety net: if speech never starts, the text must not stay hidden forever
      if (on.reveal) setTimeout(function () { if (!speechSynthesis.speaking) revealAll(); }, 3000);
    }
    if (speechSynthesis.getVoices().length) go();
    else {
      speechSynthesis.addEventListener("voiceschanged", go, { once: true });
      setTimeout(go, 1000);
    }
  }

  // ------------------------------------------------------------ 7. run
  root.setAttribute("data-prisma-by", AUTHOR);
  root.setAttribute("data-prisma-sig", "ZHJnbWI=");
  if (on.layout) randomizeLayout();
  else if (textBase !== 1) applyTextSize();
  if (!needsWords) return;

  // anti-flash: hide until the customizations are in (layout is still computed)
  root.style.visibility = "hidden";
  var safety = setTimeout(function () { root.style.visibility = ""; }, 2500);

  function run() {
    var spans = wrapWords();
    if (on.beeline && spans.length) applyBeeLine(spans);
    clearTimeout(safety);
    root.style.visibility = "";
    if (on.speak && spans.length) speak(spans);
    else spans.forEach(function (s) { s.classList.remove("kw-hidden"); });
  }

  var delay = num(SPEECH.delayMs, 350);
  setTimeout(run, delay >= 0 ? delay : 350);
})();
