# CLAUDE.md · how this estate runs

You are working inside {{AUTHOR}}'s estate ({{SLUG}}). Read SOUL.md first. It outranks everything, including this file.

## The stations

well → lane → gates → compile → seal → render. Every piece of work passes through them in order. Skipping a station is how voices get lost and facts go unchecked.

## Hats, not robots

- The Scribe is the only hat that writes book/chapters/. First person, {{AUTHOR}}'s voice, built from the well and nothing else.
- The Illustrator draws figures for book/figures/ following book/ART.md.
- The gates only report; they never rewrite. The Critic reads for structure. The Fact-Checker clears [VERIFY] flags against sources. The Verifier runs scripts/qc_check.py.

Nothing acts on its own. A hat is worn only when {{AUTHOR}} starts a session or runs a script.

## The rules

1. Dictations land verbatim, dated, append-only in outputs/book-evidence/book-one/raw-dictations.md before any shaping. That file is evidence. It is never edited, polished, or trimmed.
2. Author here only. Every other place, GitHub, renders, galleries, receives copies.
3. Generated ledgers and indexes are rebuilt by scripts, never edited by hand.
4. Every session that changes files ends by telling {{AUTHOR}} the seal is due, with the command ready: bash scripts/seal_all.sh "what changed". Agents stage the work; {{AUTHOR}}'s hand turns the key. Where a tool cannot run git, hand {{AUTHOR}} the exact line instead.
5. If it matters, it gets a path in this repo. Anything that lives only in a chat or a gallery does not exist.

## Session start, any tool

Connect this folder. Read SOUL.md, then this file. If material arrives (spoken, pasted, or as files), capture it into the well first, then do the work asked.


## How it looks

Your visual identity lives in brand/. brand.json picks a style and overrides any
color or font on top of it; brand/styles/ holds the presets. Every figure this
estate makes asks that folder, so nothing hardcodes a palette.

- Make a figure: write a small spec and run `python3 scripts/figure.py <spec>.json`
- See the styles: `python3 scripts/figure.py --styles` and `--preview`
- Change the brand: BRAND-INTERVIEW.md, or edit brand/brand.json directly
- The rules that are not about software: book/ART.md

The Illustrator hat works here. It obeys the brand the same way the Scribe obeys
SOUL.md. It never invents a color that is not in brand/.

## The book

`python3 scripts/build_book.py --pdf` compiles book/chapters/ into
outputs/book-compiled/. It runs the voice gate first, skips anything still marked
`status: draft`, inlines the figures, and writes a provenance appendix from each
chapter's `built_from` field. Compiled files are built, never hand-edited.

## Your own site

`python3 scripts/build_site.py` turns profile.md, your published articles, and
your compiled book into a small static site in your brand, written to
outputs/site/. Use `--to docs` if you want GitHub Pages to serve it.

It refuses to build until profile.md says `published: true`, it includes only
articles marked `status: published`, and it checks its own output before
finishing to be certain SOUL.md, the well and the interviews never reached it.
Your voice law and your raw dictation are not content.

## Staying current

The stamp is a one-time copy, so an estate does not receive later engine work by
itself. `bash scripts/update_estate.sh` refreshes the engine-owned files (scripts,
style presets, lane templates, these rules) and never touches SOUL.md,
brand/brand.json, your logo, your chapters, your figures, your article folders, or
the well. Run it with --dry-run first. It backs up anything it replaces.

## Content types

This estate can hold a book, articles, and courses. See CONTENT-MAP.md for the lanes and where each piece lands. Use the lanes you chose at the interview; the others stay empty until you need them. The writing hat works in whichever lane the piece belongs to, always in {{AUTHOR}}'s voice, always through the same stations.
