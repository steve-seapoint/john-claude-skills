---
name: github-pages-deploy
description: Stand up a new static site (an index.html plus assets) on GitHub Pages from the terminal — creates the repo, pushes, enables Pages, waits for the build, and checks the live URL and its images actually load before handing it over. Also checks the page lays out properly on phones and laptops (no sideways scrolling, no half-empty screen) and tells you how to write the HTML so it does. Use this whenever the user wants to put a static page, landing page, demo, report, or standalone HTML on the web, or says "deploy this", "host this", "publish this page", "put this online", "get me a link I can send someone", or "ship it to GitHub Pages" — including when they never say "GitHub Pages" and just want a public URL. Also use to push updates to a site published this way.
---

# Stand up a site on GitHub Pages

For a new static site in its own directory: one command creates the repo, publishes it, and gives back a URL that has been checked.

This is scoped to new sites. If the directory already has a git remote, stop and ask the user what they want — publishing an existing repo means deciding about its branches and history, which is a different conversation.

## Prerequisites

`git` and `gh` installed, and `gh auth status` showing an authenticated account. If auth fails, ask the user to run `gh auth login` themselves — it's interactive and needs a browser. In Claude Code they can run it inline by typing `! gh auth login`.

For the layout check (optional but worth having): the `playwright` Python package with its Chromium (`pip install playwright && playwright install chromium`), or a Chrome/Chromium/Edge/Brave install. Without either, the check skips itself and says so.

## Writing the page

If you are authoring the HTML (not just publishing a file the user handed over), the page has to work on a phone and on a laptop. Every page this skill has shipped that looked wrong failed in one of two ways, and both are cheap to prevent:

1. **Sideways scrolling on a phone.** The layout ends up wider than the screen, so text is cut off at the right edge and the reader has to pan. Nearly always a grid or flex column that was allowed to grow to fit a long line in a `<pre>`, a table, or a URL.
2. **A half-empty laptop screen.** A reading column with `max-width` but no centering, so it hugs the sidebar and leaves the right third of the window blank.

Rules that prevent them:

- `<meta name="viewport" content="width=device-width, initial-scale=1">` in `<head>`. Without it phones lay the page out at 980px and shrink it.
- **Reading column: cap it *and* center it.** `max-width: 78ch` (roughly 720–860px at body sizes) with `margin-inline: auto`. In a sidebar-plus-content grid, that `margin` centers `<main>` inside its column — that's the piece people forget. A `max-width` alone parks the column on the left.
- **No bare `1fr` or `auto` for a column that holds text.** Bare `1fr` means `minmax(auto, 1fr)`, and `auto` lets one long `<pre>` line or URL push the column past the viewport. Write `minmax(0, 1fr)`, and give flex children `min-width: 0`. This applies inside the mobile breakpoint too — switching to `grid-template-columns: 1fr` there is exactly how the phone bug ships.
- **Anything that can be wider than the screen scrolls inside itself:** `pre, table { overflow-x: auto; max-width: 100% }`. `img, video, svg { max-width: 100%; height: auto }`. `body { overflow-wrap: anywhere }` so long URLs and tokens wrap instead of pushing.
- **One breakpoint at least** (around 900px): a sidebar becomes a stacked block (`position: static; height: auto`, not `100vh`), side padding drops to about 1.25rem, headings shrink. `clamp()` sizes handle most of this without media queries: `h1 { font-size: clamp(1.8rem, 5vw, 2.6rem) }`.
- Body text 17–18px, line-height about 1.6, never below 16px on a phone. Widths in `%`, `ch`, `rem`, `min()` — a pixel width over ~400px is a phone bug waiting to happen.

A skeleton that gets all of this right; start from it rather than from a blank file:

```css
* { box-sizing: border-box; }
body { margin: 0; font-size: 17px; line-height: 1.6; overflow-wrap: anywhere; }
img, video, svg { max-width: 100%; height: auto; }
pre, table { max-width: 100%; overflow-x: auto; }
.layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 100vh; }
aside { position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 2rem 1.5rem; }
main { width: 100%; max-width: 78ch; margin: 0 auto; padding: 3rem 2.5rem 6rem; }
h1 { font-size: clamp(1.8rem, 5vw, 2.6rem); line-height: 1.15; }
@media (max-width: 900px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  aside { position: static; height: auto; padding: 1.25rem; }
  main { padding: 2rem 1.25rem 4rem; }
}
```

Drop the `aside` lines and the 280px column for a page without a sidebar; the rest stays.

Before deploying, run the check yourself and fix whatever it reports:

```bash
python3 <skill-dir>/scripts/layout_check.py <site-dir>
```

It renders the page at 390px and 1440px and prints the numbers: page width versus screen, which elements poke past the edge, and how much empty space sits on each side of the text column. `deploy.sh` runs it too, and refuses to publish a page that overflows on a phone.

## Deploy

```bash
bash <skill-dir>/scripts/deploy.sh --dir <site-dir> --repo <repo-name>
```

That's the whole thing. It audits the site, checks the layout, initializes and commits, creates the repo, enables Pages, waits for the build, and verifies the live URL before printing it. Rerun the same command later to publish updates.

Confirm the repository name with the user first — it becomes the URL path (`https://<owner>.github.io/<repo>/`) and renaming it later breaks any link they've shared. Public is the default; `--private` works but needs a paid GitHub plan, and the published site is world-readable either way, so it buys less than people expect.

## What it does, and why each part is there

Four commands would technically publish a site. These are the parts that make it work on the first try instead of the third:

**Audits the site before pushing** (`scripts/preflight.py`, run automatically). It catches the failures that don't show up until the site is live:

- Root-relative paths like `src="/assets/logo.png"`. On a project site the leading `/` resolves to `https://<owner>.github.io/`, not your repo's subpath, so the image 404s. Use `assets/logo.png`.
- Case-only mismatches — `assets/Logo.png` on disk, `assets/logo.png` in the HTML. macOS doesn't care, the Pages server does. This one is nearly invisible locally.
- References to files that simply aren't there, and a missing `index.html`, which makes the whole site 404.

Errors stop the deploy. If the user knowingly wants to publish anyway, `--force` proceeds.

**Renders the page at phone and laptop widths** (`scripts/layout_check.py`, run automatically). A missing viewport meta or a page wider than a 390px phone is an error and stops the deploy; a text column that leaves a big lopsided gap on a 1440px screen, or body text under 15px on the phone, is a note. It uses Playwright's Chromium if installed, falls back to a Chrome binary with a short timeout (Chrome with a pending update can hang at launch), and skips with a message if neither works.

**Writes `.nojekyll`.** Pages runs everything through Jekyll by default, which silently skips any path starting with `_` or `.` (so `_next/`, `_assets/` never publish) and treats `{{ }}` in HTML as template syntax. The empty `.nojekyll` file turns that off.

**Treats 409 on the Pages API as success**, and retries the Pages call for a few seconds after repo creation — the endpoint 404s briefly while GitHub finishes provisioning the repo.

**Waits for the build, then fetches the site** (`scripts/verify.py`). A fresh build takes 30–90 seconds, during which the URL returns 404 with no holding page. An immediate 404 almost always means "not built yet", so don't interpret one as a failure. Once it's up, verify requests every local file the page references and reports any that don't load.

Report the live URL, the repo URL, and the verify result. Never hand over a URL you haven't seen return 200.

## If something is wrong

- **Page scrolls sideways on a phone, text cut off at the right** — `python3 <skill-dir>/scripts/layout_check.py <site-dir>` names the elements sticking out. If it's a `<pre>`, `<table>`, or `<code>`, the column containing it is bare `1fr`/`auto`: change it to `minmax(0, 1fr)` (or `min-width: 0` on a flex child) and give the element `overflow-x: auto`. If it's a long URL, add `overflow-wrap: anywhere`. If it's an image, `max-width: 100%`.
- **Big blank area on the right of a laptop screen** — the text column has a `max-width` but no `margin: 0 auto`. Add it (or `justify-self: center` in a grid). The check reports the space on each side so you can see it's balanced afterwards.
- **Layout check says SKIP** — no renderer found. `pip install playwright && playwright install chromium`, or set `CHROME_BIN` to a Chrome binary. If Chrome times out, it's usually waiting on its own updater; relaunching Chrome to finish the update clears it.
- **Still 404 after the build says `built`** — check `gh api "repos/$OWNER/$REPO/pages" --jq '.source, .html_url'`. Usually the URL is missing the `/<repo>/` path segment, or `index.html` isn't at the repo root.
- **Page loads, images don't** — rerun `python3 <skill-dir>/scripts/verify.py <url>` to get the exact 404s. Fix the paths, then rerun `deploy.sh` to push and recheck.
- **Build says `errored`** — `gh api "repos/$OWNER/$REPO/pages/builds/latest" --jq .error.message`. Nearly always Jekyll choking on something; confirm `.nojekyll` was committed (`git ls-files .nojekyll`) and force a rebuild with `gh api --method POST "repos/$OWNER/$REPO/pages/builds"`.
- **Repo name already taken** — pick another name; `gh repo view <owner>/<name>` shows what's already there.
