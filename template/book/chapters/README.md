# The writing lane

Chapters live here as .md files, numbered, first person, in the voice SOUL.md
defines, built from the well and nothing else.

Naming: `01-the-morning-the-pump-failed.md`. Number first so the book has an
order on disk, slug after so you can find one without opening it.

## The one rule of this lane

The Scribe builds from `outputs/book-evidence/` and from nothing else. Not from
memory, not from the internet, not from what would make a better story. If
{{AUTHOR}} did not say it happened, it did not happen. A chapter that needs a
detail {{AUTHOR}} has not given yet is a chapter that is not ready. Ask for the
detail, get it into the well, then write.

## What a chapter carries

```
---
title:
number:
status: draft | shaped | gated | final
built_from:            # the dated well entries this chapter is made of
sources: []            # anything external, with a link
figures: []            # figure files in book/figures/
---
```

`built_from` matters more than it looks. It answers, two years later, the
question "where did this story come from," and it is what makes keeping the well
worth the trouble.

## How a chapter gets made

1. Read the well entries it is built from. All of them, not a summary.
2. Draft in first person, in {{AUTHOR}}'s voice, at the length the material
   actually supports. A short honest chapter beats a padded one.
3. Keep {{AUTHOR}}'s own phrasing wherever the well already says it well. The
   well is not raw material to be improved. It is the voice.
4. Flag anything uncertain with [VERIFY] and leave it flagged until it clears.
5. Run `python3 scripts/qc_check.py`.
6. Read it out loud. This catches what the gate cannot.

## The gates

They report. They never rewrite. The Critic reads for structure and says what is
weak. The Fact-Checker clears [VERIFY] flags against sources. The Verifier runs
the voice gate. None of them may edit a chapter on their own. That is
{{AUTHOR}}'s call, every time.
