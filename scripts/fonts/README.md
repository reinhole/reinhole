# Fonts

Fira Code, the same typeface the portfolio site sets, subset per role.

`OFL.txt` is the SIL Open Font License 1.1 these files ship under. It has to
travel with them: the woff2 files live in a public repository, so the licence
must permit redistribution. Commercial fonts are not an option here.

| file | covers | used by |
|---|---|---|
| `firacode-ramp.woff2` | the 6 ramp characters | `ascii.svg` |
| `firacode-head.woff2` | latin, semibold | reserved |
| `firacode-400.woff2` | latin, regular | data graphics |
| `firacode-600.woff2` | latin, semibold | data graphics |

## Regenerating

`fira_extract/` holds the upstream release and is **not** committed — the
subsets are. To rebuild them:

```bash
cd scripts/fonts
curl -L -o fira.zip https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip
unzip -q fira.zip -d fira_extract && rm fira.zip
cd ../.. && .venv/bin/python scripts/subset_fonts.py
```

Do not subset from the site's `static/fonts/*.woff2` — those are already
Google-Fonts subsets and re-subsetting them loses glyphs.

Ligatures are stripped (`--layout-features=`). Fira Code would otherwise fuse
ramp pairs into a single glyph and shear the character grid.
