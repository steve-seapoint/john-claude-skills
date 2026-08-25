#!/usr/bin/env python3
"""Render a page in headless Chrome at phone and desktop widths and measure it.

Static checks can't tell you the page overflows sideways on a phone or leaves
half of a laptop screen blank. This one renders it. It reports:

  ERROR  horizontal overflow — the page is wider than the phone's screen, so
         text runs off the right edge and the user has to pan. Names the
         elements that stick out so you can fix the actual culprit.
  ERROR  no viewport meta — phones render the page at ~980px and shrink it.
  NOTE   lopsided desktop layout — the main text column hugs one side of the
         space available to it (usually a max-width with no margin: auto,
         leaving the right third of the screen empty).
  NOTE   tiny body text on the phone.

Renders with Playwright's Chromium if the `playwright` Python package and its
browser are installed (pip install playwright && playwright install chromium),
otherwise with a Chrome/Chromium/Edge/Brave binary found on the machine. If
neither works it prints SKIP and exits 0 so the deploy is not blocked.

Usage:
    python3 layout_check.py <site-dir-or-index.html> [--json]

Exit status: 0 if clean (or skipped), 1 if there are errors.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIEWPORTS = [
    ("phone", 390, 844),
    ("desktop", 1440, 900),
]

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "brave-browser",
]

# A JS expression that measures the laid-out page and evaluates to a plain
# object. Playwright evaluates it directly; the raw-Chrome path wraps it.
MEASURE_JS = r"""
(function () {
    var vw = window.innerWidth;
    var de = document.documentElement;
    var out = { vw: vw, scrollWidth: Math.max(de.scrollWidth, document.body.scrollWidth) };

    // Elements poking past the right edge, widest first, skipping ancestors
    // that are only wide because a child is.
    var over = [];
    var all = document.body.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var r = el.getBoundingClientRect();
      if (r.width === 0 || r.right <= vw + 1) continue;
      var childWider = false;
      for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
        var cr = c.getBoundingClientRect();
        if (cr.right >= r.right - 1 && cr.width > 0) { childWider = true; break; }
      }
      if (childWider) continue;
      over.push({ tag: describe(el), right: Math.round(r.right), width: Math.round(r.width) });
    }
    over.sort(function (a, b) { return b.right - a.right; });
    out.overflowing = over.slice(0, 5);

    // Find the main text container: descend from body, following the child
    // that holds most of the text, until no single child holds >= 70% of it.
    var node = document.body;
    while (true) {
      var total = textLen(node), best = null, bestLen = 0;
      for (var k = node.firstElementChild; k; k = k.nextElementSibling) {
        if (/^(script|style|nav|aside|header|footer)$/i.test(k.tagName)) continue;
        var l = textLen(k);
        if (l > bestLen) { bestLen = l; best = k; }
      }
      if (!best || total === 0 || bestLen < total * 0.7) break;
      node = best;
    }
    // Walk back up to the first ancestor that is meaningfully wider — that is
    // the box the column is supposed to sit inside.
    var col = node, colRect = col.getBoundingClientRect();
    var box = col.parentElement, boxRect = box ? box.getBoundingClientRect() : colRect;
    while (box && box !== document.documentElement) {
      boxRect = box.getBoundingClientRect();
      if (boxRect.width > colRect.width * 1.05) break;
      col = box; colRect = boxRect; box = box.parentElement;
    }
    var availL = boxRect.left, availR = boxRect.right;
    // Siblings sitting beside the column (a sidebar) reduce the available space.
    for (var s = box ? box.firstElementChild : null; s; s = s.nextElementSibling) {
      if (s === col) continue;
      var sr = s.getBoundingClientRect();
      if (sr.width === 0 || sr.bottom < colRect.top || sr.top > colRect.bottom) continue;
      if (sr.right <= colRect.left + 1) availL = Math.max(availL, sr.right);
      else if (sr.left >= colRect.right - 1) availR = Math.min(availR, sr.left);
    }
    out.column = {
      tag: describe(node),
      left: Math.round(colRect.left), right: Math.round(colRect.right),
      availLeft: Math.round(availL), availRight: Math.round(availR),
      spaceLeft: Math.round(colRect.left - availL),
      spaceRight: Math.round(availR - colRect.right)
    };

    var sizes = [];
    var ps = document.querySelectorAll('p, li');
    for (var j = 0; j < ps.length; j++) {
      if (ps[j].getBoundingClientRect().width > 0) sizes.push(parseFloat(getComputedStyle(ps[j]).fontSize));
    }
    sizes.sort(function (a, b) { return a - b; });
    out.bodyFontPx = sizes.length ? sizes[Math.floor(sizes.length / 2)] : null;

    return out;

  function textLen(el) { return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').length; }
  function describe(el) {
    var s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    else if (el.className && typeof el.className === 'string') s += '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.');
    return s;
  }
})()
"""


def find_chrome() -> str | None:
    for cand in CHROME_CANDIDATES:
        if not cand:
            continue
        if os.path.isabs(cand) and os.access(cand, os.X_OK):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def render_playwright(html_path: Path, width: int, height: int) -> dict | None:
    """Measure with Playwright's bundled Chromium. Returns None if unavailable."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=30000)
                page.wait_for_timeout(300)  # let fonts and late layout settle
                return page.evaluate(MEASURE_JS)
            finally:
                browser.close()
    except Exception as exc:  # browser not installed, launch failure, etc.
        print(f"note: playwright render failed ({str(exc).splitlines()[0][:120]}); trying Chrome", file=sys.stderr)
        return None


def render_chrome(chrome: str, html_path: Path, width: int, height: int) -> dict | None:
    """Measure with a raw Chrome binary via --dump-dom and an injected script."""
    src = html_path.read_text(encoding="utf-8", errors="replace")
    inject = (
        "<script>window.addEventListener('load',function(){"
        "var out=" + MEASURE_JS + ";"
        "var t=document.createElement('script');t.type='application/json';"
        "t.id='__layout_check__';t.textContent=JSON.stringify(out);"
        "document.documentElement.appendChild(t);});</script>"
    )
    # Inject before </body> so the real stylesheet is already parsed; fall back
    # to appending. The copy lives beside the original so relative assets load.
    if re.search(r"</body>", src, re.IGNORECASE):
        patched = re.sub(r"</body>", lambda m: inject + m.group(0), src, count=1, flags=re.IGNORECASE)
    else:
        patched = src + inject
    fd, tmp_name = tempfile.mkstemp(prefix=".layout-check-", suffix=".html", dir=html_path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(patched)
        with tempfile.TemporaryDirectory(prefix="layout-check-profile-") as profile:
            cmd = [
                chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                "--hide-scrollbars", f"--user-data-dir={profile}",
                f"--window-size={width},{height}", "--virtual-time-budget=4000",
                "--dump-dom", tmp.resolve().as_uri(),
            ]
            try:
                # Chrome can wedge on its own updater at launch; don't let that hang a deploy.
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            except subprocess.TimeoutExpired:
                print("note: Chrome did not respond within 25s (a pending Chrome update can cause this).", file=sys.stderr)
                return None
    finally:
        tmp.unlink(missing_ok=True)
    m = re.search(
        r'<script type="application/json" id="__layout_check__">(.*?)</script>',
        proc.stdout, re.DOTALL,
    )
    if not m:
        return None
    return json.loads(m.group(1))


def render(html_path: Path, width: int, height: int, chrome: str | None) -> dict | None:
    data = render_playwright(html_path, width, height)
    if data is None and chrome:
        data = render_chrome(chrome, html_path, width, height)
    return data


def has_viewport_meta(html: str) -> bool:
    head = html[:20000]
    return re.search(r'<meta[^>]+name=["\']viewport["\']', head, re.IGNORECASE) is not None


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    want_json = "--json" in sys.argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(args) == 1 else 2

    target = Path(args[0]).expanduser().resolve()
    html_path = target / "index.html" if target.is_dir() else target
    if not html_path.is_file():
        print(f"error: {html_path} not found", file=sys.stderr)
        return 2

    errors: list[str] = []
    notes: list[str] = []
    results: dict[str, dict] = {}

    if not has_viewport_meta(html_path.read_text(encoding="utf-8", errors="replace")):
        errors.append(
            "index.html has no <meta name=\"viewport\"> tag. Phones will lay the page out "
            "at ~980px and shrink it to fit, so the text is unreadably small. Add "
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> to <head>."
        )

    chrome = find_chrome()
    rendered_any = False
    for name, w, h in VIEWPORTS:
        data = render(html_path, w, h, chrome)
        if data is None:
            break
        rendered_any = True
        results[name] = data
        vw = data["vw"]
        overflow = data["scrollWidth"] - vw
        if overflow > 2:
            culprits = ", ".join(f"{o['tag']} ({o['width']}px wide)" for o in data["overflowing"][:3]) or "unknown"
            errors.append(
                f"{name} ({vw}px): the page is {overflow}px wider than the screen, so it "
                f"scrolls sideways and text is cut off at the right edge. Sticking out: {culprits}. "
                "Usual causes: a grid/flex column of bare 1fr or auto (use minmax(0, 1fr) or "
                "min-width: 0), a <pre>/<table> without overflow-x: auto, a fixed pixel width, "
                "or a long URL/token without overflow-wrap: anywhere."
            )
        col = data.get("column") or {}
        if name == "desktop" and col:
            sl, sr = col.get("spaceLeft", 0), col.get("spaceRight", 0)
            big, small = max(sl, sr), min(sl, sr)
            if big > vw * 0.15 and big > 2.5 * max(small, 1):
                side = "right" if sr > sl else "left"
                notes.append(
                    f"desktop ({vw}px): the main text column ({col['tag']}, "
                    f"{col['right'] - col['left']}px wide) hugs the {'left' if side == 'right' else 'right'} side, "
                    f"leaving {big}px empty on the {side}. Centre it in its space with "
                    "margin: 0 auto (or justify-self: center in a grid), or widen it."
                )
        if name == "phone" and data.get("bodyFontPx") and data["bodyFontPx"] < 15:
            notes.append(
                f"phone: body text is {data['bodyFontPx']:.0f}px; 16px or more reads better on a phone."
            )

    if not rendered_any:
        print(
            "SKIP: could not render the page. Install a renderer to enable this check: "
            "pip install playwright && playwright install chromium (or set CHROME_BIN)."
        )

    if want_json:
        print(json.dumps({"errors": errors, "notes": notes, "measurements": results}, indent=2))
        return 1 if errors else 0

    for name, data in results.items():
        col = data.get("column") or {}
        print(
            f"{name}: viewport {data['vw']}px, page {data['scrollWidth']}px wide; "
            f"text column {col.get('tag', '?')} at {col.get('left', '?')}–{col.get('right', '?')}px "
            f"(space left {col.get('spaceLeft', '?')}px, right {col.get('spaceRight', '?')}px); "
            f"body text {data.get('bodyFontPx') or '?'}px"
        )
    for item in errors:
        print(f"ERROR: {item}")
    for item in notes:
        print(f"NOTE: {item}")
    if rendered_any and not errors and not notes:
        print("OK: no horizontal overflow on the phone; desktop column is balanced.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
