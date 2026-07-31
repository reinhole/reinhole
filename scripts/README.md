# scripts

Everything on the profile page is drawn here. Two groups, and the split matters:

| | when it runs | needs |
|---|---|---|
| `generate_stats.py` | nightly, in CI | standard library only |
| everything else | locally, by hand | `.venv` (pillow, numpy, opencv, fonttools, brotli) |

**Do not regenerate `stats.svg`, `streak.svg` or `year.svg` locally.** The action
owns them. Running the generator on both sides guarantees merge conflicts,
because a run minutes later can legitimately see a different contribution count
and the output stops being byte-identical. If you already did, `git checkout --
stats.svg streak.svg year.svg` and let CI win.

## One-time setup

```bash
python3 -m venv .venv
.venv/bin/pip install pillow numpy opencv-python-headless fonttools brotli
```

Then fetch the upstream font release — see `fonts/README.md`.

## Regenerating

```bash
.venv/bin/python scripts/subset_fonts.py     # fonts/*.woff2   (after a font change)
.venv/bin/python scripts/make_portrait.py    # ascii.svg       (after the site's portrait changes)
.venv/bin/python scripts/make_hero.py        # hero.svg
.venv/bin/python scripts/make_headings.py    # hd-*.svg
.venv/bin/python scripts/make_stack.py       # stack.svg
```

`make_portrait.py` reads the portfolio site's `assets/portrait_ascii.txt`
across a directory boundary — it expects `Personal_Website/portfolio-site/` as
a **sibling of this repo**, i.e. the `~/Developer/Personal/` layout. A clone of
this repo on its own will fail with `missing …/portrait_ascii.txt`, which is
intended: the site is the single source of truth for the portrait, and
vendoring a copy here would let the two drift apart. Check the site out beside
this repo, or skip the step — `ascii.svg` is committed.

`preview_portrait.py` rasterises the portrait at its true 460px README width.
Use it rather than reading the grid in a terminal — the terminal's cell aspect
and font are not the ones that ship.

## Checking a change before committing

The rendering API applies the same sanitiser as the site, so it will tell you
whether markup survives:

```bash
python3 -c "import json;print(json.dumps({'text':open('README.md').read(),'mode':'markdown'}))" \
  > /tmp/md.json
gh api -X POST /markdown --input /tmp/md.json > /tmp/out.html
```

Use `mode: markdown`, **not** `mode: gfm`. The `gfm` mode is comment mode: it
turns every newline into a `<br>`, which double-spaces the hard-wrapped
paragraphs and makes a correct README look broken.

## What GitHub allows

Tested against that endpoint, on this page:

```
STRIPPED   <style> blocks · style="" · class="" · inline <svg> · <script>
           <code> nested inside <samp>
KEPT       <sub> <sup> <samp> <blockquote> <hr> <picture> <b> <a> <br>
           align="" · width="" on <img>
```

Consequences worth remembering: README text cannot be re-fonted, so anything in
Fira Code has to be an image; and animation has to be SMIL inside the SVG,
because scripts are stripped.
