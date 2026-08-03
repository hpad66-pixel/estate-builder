# ART.md · how figures get made here

Figures are SVG, one file each, made by `scripts/figure.py` from a small spec, in
whatever brand `brand/brand.json` says. Nothing here hardcodes a palette. If you
want a different look, change the brand, not the drawings.

Start here:

```
python3 scripts/figure.py --styles     # the five styles and what each is for
python3 scripts/figure.py --preview    # see all five before you choose
```

Then set your style in `brand/brand.json`. Read `brand/README.md` when you want
to change colors, fonts, your mark, or your copyright line, or build a style of
your own. The estate ships with sketchbook, editorial, blueprint, clean, and
press. None of them is the house style. Pick the one that sounds like you, the
same way SOUL.md is how you sound.

## Making a figure

Write a spec, render it:

```json
{
  "type": "framework",
  "kicker": "the method",
  "name": "The Curve Test",
  "title": "Three questions before you buy the instrument",
  "items": ["Who hears it first?", "What does the curve cost?", "Who is accountable at 3am?"],
  "caption": "If you cannot answer all three, you are buying a dashboard."
}
```

```
python3 scripts/figure.py book/figures/03-curve-test.json
```

The six shapes:

| type | what it draws | give it |
|---|---|---|
| `sequence` | numbered steps, left to right | `items` |
| `framework` | the same, with a named model above it | `items`, `name` |
| `comparison` | two columns, this against that | `left`, `right` |
| `loop` | a feedback cycle | `items`, three to five |
| `stat` | one number, made large | `value`, `label`, `source` |
| `quote` | a pull quote card | `quote`, `attribution` |

All of them also take `title`, `kicker`, and `caption`.

## The rules that are not about software

Every figure gets a caption in plain words. If the caption is hard to write, the
figure is doing something the text has not earned yet.

No figure ships that the text does not earn. A drawing that repeats the sentence
above it is decoration.

One idea per figure. If it needs two, it is two figures.

Keep the color code steady across the whole body of work. `accent1` for the main
idea, `accent2` for the second thread, `accent3` used sparingly for cost and
risk. A reader learns this once, and only if you do not move it.

A full page plate may open a chapter. Inline figures sit beside the paragraph
they serve.

## Checking your work

SVG is a text file, which means it can break in ways that still leave you a file.
After making a batch, parse every one:

```
python3 -c "import glob,xml.dom.minidom as m; [m.parse(f) for f in glob.glob('book/figures/*.svg')]; print('all valid')"
```

Then open them and look. Text wrapping in SVG is estimated rather than measured,
so the engine errs toward short lines. A long title will still tell you something
the arithmetic did not. Look at every figure before it ships.
