# brand/ · every color, font, and mark in one place

This is the single source of truth for how {{AUTHOR}}'s work looks. Nothing in
this estate hardcodes a hex value. Everything asks this folder. Change a color
here and every figure you make from then on inherits it.

## The two files that matter

**`brand.json`** is yours. It picks a style and overrides anything you want:

```json
{
  "owner": "{{AUTHOR}}",
  "style": "sketchbook",
  "copyright": "{{AUTHOR}}",
  "logo_text": "",
  "colors": { "accent1": "#2f6f6a" },
  "fonts":  { "display": "Fraunces, Georgia, serif" }
}
```

Anything in `colors` or `fonts` beats the style preset. That is the point: start
from a preset that is close, then make it yours, without editing the preset.

**`styles/*.json`** are the presets. Five ship with the estate:

| Style | Looks like | Reach for it when |
|---|---|---|
| `sketchbook` | Hand drawn on warm paper | Memoir, field stories, teaching by drawing |
| `editorial` | Navy and gold, serif with a spine | Essays, Substack, a book that wants to look authored |
| `blueprint` | Cyan on deep blue, faint grid | Engineering, infrastructure, process work |
| `clean` | White, one accent, no ornament | Consulting, reports, employers with opinions |
| `press` | Newsprint, one spot color, heavy | Social cards and pull quotes that must stop a thumb |

See them rather than read about them:

```
python3 scripts/figure.py --styles     # what each one is for
python3 scripts/figure.py --preview    # renders one figure in every style
```

## Make your own style

1. Copy the closest preset to `brand/styles/<yourname>.json`.
2. Change the values. Keep the key names, because the engine asks for names, not
   values.
3. Set `"style": "<yourname>"` in `brand.json`.

The keys the engine expects: `bg`, `panel`, `ink`, `ink2`, `muted`, `line`,
`accent1`, `accent2`, `accent3` for colors, and `display`, `body`, `mono` for
fonts. The `rules` block turns features on and off: `roughen` for the hand drawn
line filter, `grid` for the drafting grid, `top_rule` for the bar across the top,
`border`, `radius`, and `uppercase_kicker`.

Three accents, not five. A reader learns a color code once, and only if it stays
the same. Use `accent1` for the main idea, `accent2` for the second thread, and
`accent3` sparingly for cost, risk, and warnings.

## Your mark and your copyright

`logo_text` puts a wordmark in the corner of every figure. Leave it empty and
your name is used instead.

`copyright` sets the line under it. It defaults to your name. Change it to your
company, or to a license if you would rather your figures travel: some people put
`{{AUTHOR}} · CC BY 4.0` there so their diagrams can be reused with credit.

Drop an image logo in `brand/logo/`. Keep an SVG version if you have one, because
it stays sharp at any size, and it is a text file so your estate can version it
like everything else.

## Fonts

Font names are CSS font stacks. They render if the machine or the browser has
them. Keep a plain fallback at the end of every stack, the way the presets do,
so a figure never falls back to something ugly on somebody else's screen.

## The rule

One brand, every channel. The book, the articles, the Substack cuts, the
LinkedIn carousels: all of them ask this folder. That is what makes a body of
work look like a body of work instead of a pile of files.
