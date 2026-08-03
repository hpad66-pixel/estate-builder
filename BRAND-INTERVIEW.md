# The Brand Interview

SOUL.md decides how you sound. This decides how you look. Paste everything below
the line into an AI session opened inside your estate folder. About fifteen
minutes.

Run `python3 scripts/figure.py --preview` first and actually open the five files
it makes. Choosing between five pictures is easier than answering questions about
color in the abstract.

---

You are setting up the visual identity for the owner of this estate. The result
is `brand/brand.json`, which every figure this estate ever makes will obey.

Before you ask anything, run `python3 scripts/figure.py --preview` and tell them
to open `brand/preview/`. Five files, five styles. Ask them to look before they
answer.

Then ask these, one at a time, waiting for each answer.

1. Which of the five previews felt most like you? Say what you liked, and what
   you would change about it.
2. Which one felt least like you? What is wrong with it? This is often the more
   useful answer.
3. Where will most people see your figures: on a phone in a feed, on a laptop in
   a document, or printed and handed across a table?
4. Do you already have brand colors you must use, from an employer, a company, or
   a book cover? If so, give the hex values, or describe them and we will find
   them.
5. Do you want your name on every figure, a wordmark, a logo image, or nothing at
   all?
6. What should the copyright line say? Your name, a company, or a license if you
   would rather people reuse your diagrams with credit.
7. Light background or dark? Say which one you would want to look at for an hour.
8. Is there a look you actively want to avoid, because everyone in your field
   already uses it?

From the answers, write `brand/brand.json`:

- Set `style` to the preset they picked.
- Put any color or font they specified into `colors` or `fonts`, which override
  the preset. Do not edit the preset files themselves; overrides are how a person
  keeps their own brand while still receiving preset improvements later.
- Set `copyright` and either `logo_text` or `logo`.
- If they wanted something none of the five presets can reach, copy the closest
  preset to `brand/styles/<their-name>.json`, change the values, and point
  `style` at it. Keep every key name exactly as it was.

Then render proof, do not describe it. Make one figure of each type in their new
brand, put them somewhere they can open, and ask: does this look like your work?
Revise until they say yes.

Three things to tell them at the end:

- Three accents, not five. A reader learns a color code once, and only if it
  stays still.
- The brand is one file. Change it in a year and everything made after that
  follows, with nothing to go back and fix.
- If they later want a second look for a different audience, that is a new style
  file, not a new estate.
