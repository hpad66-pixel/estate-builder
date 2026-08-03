# The compiled book

`python3 scripts/build_book.py` writes the finished book here, in the brand set
in brand/brand.json: a title page, contents with word counts, every chapter, your
figures placed where you asked for them, and a provenance appendix showing which
dictations each chapter came from.

  python3 scripts/build_book.py            the HTML
  python3 scripts/build_book.py --pdf      and a PDF, if Chrome or Chromium is installed
  python3 scripts/build_book.py --strict   refuse to build if the voice gate fails
  python3 scripts/build_book.py --draft    include chapters still marked draft

Only chapters marked shaped, gated, or final are included, so a half-written
chapter never quietly ends up in the book. The voice gate runs first, every time.

Files here are built, not written. Anything you edit by hand is overwritten on the
next build. Fix the chapter, or fix the builder.

On paper the book prints on white. A tinted background cannot reach into the page
margin, so it prints as a hard-edged block, and it costs the reader half a toner
cartridge. Your brand stays in the type, the accents, and the figures.
