#!/usr/bin/env python3
"""Compile the chapters into a finished book.

Reads book/chapters/*.md in order, renders one HTML file into
outputs/book-compiled/, in the brand you set in brand/brand.json, with a title
page, a contents page, your figures placed where you asked for them, and a
provenance appendix that shows which dictations each chapter was built from.

  python3 scripts/build_book.py                 build the HTML
  python3 scripts/build_book.py --pdf           and a PDF, if a browser is installed
  python3 scripts/build_book.py --strict        refuse to build if the voice gate fails
  python3 scripts/build_book.py --no-provenance leave the appendix out
  python3 scripts/build_book.py --draft         include chapters marked status: draft

By default only chapters whose status is shaped, gated, or final are included,
so a half-written chapter does not quietly end up in the book.

No installs. Python 3 and, for the PDF, a Chrome or Chromium you already have.
"""
import sys, os, re, json, html, glob, shutil, subprocess, tempfile, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(ROOT, "book", "chapters")
OUT = os.path.join(ROOT, "outputs", "book-compiled")
READY = {"shaped", "gated", "final"}


# ------------------------------------------------------------------ brand

def brand():
    b = {}
    p = os.path.join(ROOT, "brand", "brand.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            b = json.load(f)
    name = b.get("style") or "clean"
    sp = os.path.join(ROOT, "brand", "styles", name + ".json")
    st = {}
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            st = json.load(f)
    colors = dict(st.get("colors", {}))
    colors.update(b.get("colors") or {})
    fonts = dict(st.get("fonts", {}))
    fonts.update(b.get("fonts") or {})
    # a book is read for an hour, so it is set on paper even when the figures are dark
    if colors.get("bg", "#fff").lower() in ("#0b0e14", "#0d2137", "#050505"):
        colors["page"] = "#ffffff"
        colors["pageink"] = "#15181f"
    else:
        colors["page"] = colors.get("bg", "#ffffff")
        colors["pageink"] = colors.get("ink", "#111111")
    return {
        "owner": b.get("owner", ""),
        "copyright": b.get("copyright", "") or b.get("owner", ""),
        "colors": colors, "fonts": fonts,
        "style": name, "logo_text": b.get("logo_text", ""),
    }


# ------------------------------------------------------------------ frontmatter

def split_front(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw, body = text[3:end], text[end + 4:]
    meta, key = {}, None
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w_-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                meta[key] = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
            elif val:
                meta[key] = val.strip("'\"")
            else:
                meta[key] = []
        elif line.strip().startswith("- ") and key:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line.strip()[2:].strip().strip("'\""))
    return meta, body


# ------------------------------------------------------------------ markdown

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"<!--IMG:\2|\1-->", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[VERIFY\]", '<span class="verify">[VERIFY]</span>', s)
    return s


def embed_image(src, alt):
    """SVG gets inlined so it survives the PDF. Anything else stays a link on
    disk, which is what a browser wants when it opens the file locally."""
    path = os.path.join(ROOT, src) if not os.path.isabs(src) else src
    cap = '<figcaption>%s</figcaption>' % html.escape(alt) if alt else ""
    if src.lower().endswith(".svg") and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            svg = f.read()
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        return '<figure class="fig">%s%s</figure>' % (svg, cap)
    rel = os.path.relpath(path, OUT)
    return '<figure class="fig"><img src="%s" alt="%s">%s</figure>' % (
        html.escape(rel), html.escape(alt), cap)


def markdown(text):
    # HTML comments are notes to the author, not content. The templates are full
    # of them, so anything that renders markdown has to drop them first or every
    # instruction ends up printed on a public page.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if s.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue

        if not s:
            i += 1
            continue

        if re.match(r"^(---+|\*\*\*+)$", s):
            out.append('<hr class="break">')
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (min(lvl + 1, 6), inline(m.group(2)), min(lvl + 1, 6)))
            i += 1
            continue

        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf)))
            continue

        if re.match(r"^[-*+]\s+", s) or re.match(r"^\d+[.)]\s+", s):
            ordered = bool(re.match(r"^\d+[.)]\s+", s))
            items = []
            while i < len(lines):
                t = lines[i].strip()
                if re.match(r"^[-*+]\s+", t) or re.match(r"^\d+[.)]\s+", t):
                    items.append(inline(re.sub(r"^([-*+]|\d+[.)])\s+", "", t)))
                    i += 1
                elif t and items and not re.match(r"^(#{1,6}\s|>|```)", t):
                    items[-1] += " " + inline(t)
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % x for x in items), tag))
            continue

        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|>|```|---+$|\*\*\*+$|[-*+]\s|\d+[.)]\s)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))

    body = "\n".join(out)
    # images become figures once the paragraph around them is settled
    body = re.sub(r"<p>\s*<!--IMG:([^|]+)\|([^>]*)-->\s*</p>",
                  lambda m: embed_image(m.group(1), m.group(2)), body)
    body = re.sub(r"<!--IMG:([^|]+)\|([^>]*)-->",
                  lambda m: embed_image(m.group(1), m.group(2)), body)
    return body


# ------------------------------------------------------------------ page

def css(b):
    c, f = b["colors"], b["fonts"]
    return """
:root{--page:%(page)s;--ink:%(pageink)s;--muted:%(muted)s;--line:%(line)s;--a1:%(a1)s;--a2:%(a2)s;--a3:%(a3)s}
*{box-sizing:border-box}
body{margin:0;background:#6b6b6b;font-family:%(body)s;color:var(--ink);line-height:1.62;font-size:18px}
.sheet{background:var(--page);max-width:780px;margin:0 auto;padding:76px 84px 96px}
h1,h2,h3,h4{font-family:%(display)s;line-height:1.18;font-weight:700}
h2{font-size:34px;margin:0 0 6px}
h3{font-size:25px;margin:38px 0 10px}
h4{font-size:20px;margin:28px 0 8px}
p{margin:0 0 17px}
blockquote{margin:26px 0;padding:4px 0 4px 24px;border-left:4px solid var(--a1);font-family:%(display)s;font-size:21px;line-height:1.45}
ul,ol{margin:0 0 18px 24px;padding:0}
li{margin-bottom:7px}
code{font-family:%(mono)s;font-size:.9em;background:rgba(128,128,128,.13);padding:1px 5px;border-radius:4px}
pre{background:rgba(128,128,128,.11);padding:15px 17px;border-radius:8px;overflow-x:auto}
pre code{background:none;padding:0}
a{color:var(--a1)}
hr.break{border:none;text-align:center;margin:34px 0}
hr.break::after{content:"* * *";color:var(--muted);letter-spacing:9px;font-size:15px}
.fig{margin:34px 0;text-align:center}
.fig svg,.fig img{max-width:100%%;height:auto;border:1px solid var(--line);border-radius:8px}
.fig figcaption{font-size:14.5px;color:var(--muted);margin-top:10px;font-style:italic}
.verify{background:#ffe9a8;color:#5a4600;padding:1px 6px;border-radius:4px;font-size:.82em;font-weight:700;letter-spacing:.5px}
.titlepage{min-height:74vh;display:flex;flex-direction:column;justify-content:center;text-align:center}
.titlepage .bt{font-family:%(display)s;font-size:60px;line-height:1.06;font-weight:700;margin-bottom:22px}
.titlepage .by{font-size:20px;color:var(--muted);letter-spacing:1px}
.titlepage .rule{width:74px;height:4px;background:var(--a1);margin:30px auto;border-radius:2px}
.colophon{font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:20px;margin-top:44px}
.toc{margin:26px 0 0}
.toc a{display:flex;justify-content:space-between;gap:14px;text-decoration:none;color:var(--ink);padding:9px 0;border-bottom:1px solid var(--line)}
.toc a span:last-child{color:var(--muted);font-family:%(mono)s;font-size:14px;white-space:nowrap}
.toc a:last-child{border-bottom:none}
.chapter{padding-top:26px}
.chapter .num{font-family:%(mono)s;font-size:13px;letter-spacing:3.4px;text-transform:uppercase;color:var(--a1);margin-bottom:9px}
.prov{font-size:14.5px;color:var(--muted)}
.prov table{width:100%%;border-collapse:collapse;margin-top:12px}
.prov td,.prov th{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.prov th{font-family:%(mono)s;font-size:11.5px;letter-spacing:1.4px;text-transform:uppercase;color:var(--muted)}
@media print{
  /* Print on white. A background colour cannot reach into the @page margin, so
     a tinted sheet prints as a hard-edged block floating on white. It also
     costs a reader half a toner cartridge. The brand stays in the type, the
     accents, and the figures, which is where it belongs on paper. */
  html,body{background:#fff;font-size:11.5pt}
  .sheet{max-width:none;margin:0;padding:0;background:transparent}
  .chapter,.titlepage,.appendix{page-break-before:always}
  .titlepage{page-break-before:avoid;min-height:82vh}
  h3,h4{page-break-after:avoid}
  .fig,blockquote,pre{page-break-inside:avoid}
  a{color:inherit;text-decoration:none}
  @page{margin:20mm 18mm}
}
""" % {"page": c["page"], "pageink": c["pageink"], "muted": c.get("muted", "#777"),
       "line": c.get("line", "#ddd"), "a1": c.get("accent1", "#333"),
       "a2": c.get("accent2", "#555"), "a3": c.get("accent3", "#777"),
       "body": f.get("body", "Georgia, serif"), "display": f.get("display", "Georgia, serif"),
       "mono": f.get("mono", "monospace")}


def reading(n):
    m = max(1, round(n / 220))
    return "1 minute" if m == 1 else "%d minutes" % m


def words(t):
    return len(re.findall(r"[A-Za-z0-9'-]+", re.sub(r"<[^>]+>", " ", t)))


def main():
    args = sys.argv[1:]
    want_pdf = "--pdf" in args
    strict = "--strict" in args
    provenance = "--no-provenance" not in args
    drafts = "--draft" in args

    b = brand()
    os.makedirs(OUT, exist_ok=True)

    # the voice gate first. A book is the last place to discover the gate fails.
    gate = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "qc_check.py")],
                          capture_output=True, text=True)
    gate_ok = gate.returncode == 0
    print(gate.stdout.strip() or gate.stderr.strip())
    if not gate_ok:
        if strict:
            sys.exit("\nThe voice gate failed and --strict was set. Nothing was built.")
        print("\nThe voice gate failed. Building anyway, because this is a draft build.\n"
              "Run with --strict when you mean to ship.\n")

    files = sorted(glob.glob(os.path.join(CH, "*.md")))
    files = [f for f in files if os.path.basename(f).lower() != "readme.md"]
    if not files:
        sys.exit("No chapters in book/chapters/ yet. Write one, then build.")

    chapters, skipped = [], []
    for path in files:
        with open(path, encoding="utf-8") as f:
            meta, body = split_front(f.read())
        status = str(meta.get("status", "draft")).lower()
        if status not in READY and not drafts:
            skipped.append((os.path.basename(path), status))
            continue
        title = meta.get("title") or re.sub(r"^\d+[-_]*", "", os.path.basename(path)[:-3]).replace("-", " ").title()
        rendered = markdown(body)
        # figures named in the frontmatter but never placed in the text go at the end
        for fig in (meta.get("figures") or []):
            if fig and os.path.basename(fig) not in rendered:
                rendered += embed_image(fig, "")
        chapters.append({"title": title, "meta": meta, "html": rendered,
                         "words": words(rendered), "file": os.path.basename(path)})

    if not chapters:
        sys.exit("Every chapter is still status: draft. Build with --draft to see them anyway.")

    book_title = ""
    well = os.path.join(ROOT, "outputs", "book-evidence", "book-one", "raw-dictations.md")
    if os.path.exists(well):
        m = re.search(r"Book One · (.+)", open(well, encoding="utf-8").read())
        if m:
            book_title = m.group(1).strip()
    book_title = book_title or "Book One"
    total = sum(c["words"] for c in chapters)
    today = datetime.date.today().isoformat()

    parts = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>%s</title>" % html.escape(book_title),
             "<style>%s</style></head><body><div class='sheet'>" % css(b)]

    parts.append('<section class="titlepage"><div class="bt">%s</div>'
                 '<div class="rule"></div><div class="by">%s</div></section>'
                 % (html.escape(book_title), html.escape(b["owner"])))

    parts.append('<section class="chapter"><h2>Contents</h2><nav class="toc">')
    for n, c in enumerate(chapters, 1):
        parts.append('<a href="#ch%d"><span>%d. %s</span><span>%s words</span></a>'
                     % (n, n, html.escape(c["title"]), "{:,}".format(c["words"])))
    parts.append("</nav>")
    parts.append('<p class="colophon">%s chapters, %s words, about %s of reading. '
                 'Compiled %s from the estate. Every chapter here was built from dictation '
                 'held verbatim in the well.</p></section>'
                 % (len(chapters), "{:,}".format(total), reading(total), today))

    for n, c in enumerate(chapters, 1):
        parts.append('<section class="chapter" id="ch%d"><div class="num">Chapter %d</div>'
                     '<h2>%s</h2>%s</section>' % (n, n, html.escape(c["title"]), c["html"]))

    if provenance:
        parts.append('<section class="appendix chapter"><div class="num">Appendix</div>'
                     '<h2>Provenance</h2><div class="prov">'
                     '<p>Where each chapter came from. Nothing in this book was invented: '
                     'every chapter was built from dictation captured verbatim and dated '
                     'before any shaping.</p><table><tr><th>chapter</th><th>built from</th>'
                     '<th>sources</th></tr>')
        for n, c in enumerate(chapters, 1):
            bf = c["meta"].get("built_from") or []
            src = c["meta"].get("sources") or []
            if isinstance(bf, str):
                bf = [bf]
            if isinstance(src, str):
                src = [src]
            parts.append("<tr><td>%d. %s</td><td>%s</td><td>%s</td></tr>"
                         % (n, html.escape(c["title"]),
                            html.escape(", ".join(bf)) or "<em>not recorded</em>",
                            html.escape(", ".join(src)) or "&mdash;"))
        parts.append("</table></div></section>")

    cr = b["copyright"] or b["owner"]
    parts.append('<section class="colophon"><p>(c) %s %s. Compiled %s by SoulOS.</p></section>'
                 % (datetime.date.today().year, html.escape(cr), today))
    parts.append("</div></body></html>")

    slug = re.sub(r"[^a-z0-9]+", "-", book_title.lower()).strip("-") or "book"
    out_html = os.path.join(OUT, slug + ".html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    print("\nBuilt: %s" % os.path.relpath(out_html, ROOT))
    print("  %d chapters, %s words, about %s of reading"
          % (len(chapters), "{:,}".format(total), reading(total)))
    for name, st in skipped:
        print("  skipped %s (status: %s)" % (name, st))
    if skipped:
        print("  build with --draft to include them")

    if want_pdf:
        pdf = os.path.join(OUT, slug + ".pdf")
        if to_pdf(out_html, pdf):
            print("  PDF: %s" % os.path.relpath(pdf, ROOT))
        else:
            print("\n  No Chrome or Chromium found, so no PDF was made.")
            print("  Open the HTML in any browser and print to PDF; the print styles are")
            print("  already set for page breaks and margins.")


def to_pdf(src, dst):
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/opt/google/chrome/chrome", "/usr/bin/google-chrome",
             "/usr/bin/chromium", "/usr/bin/chromium-browser"]
    exe = next((c for c in cands if os.path.exists(c)), None)
    if not exe:
        return False
    if os.path.exists(dst):
        os.remove(dst)
    # Headless Chrome often writes the PDF and then does not exit. Waiting on the
    # process is how a build hangs for three minutes and then throws. Watch for
    # the file instead, then stop the browser ourselves. A throwaway profile per
    # run, because sharing one deadlocks concurrent headless runs.
    prof = tempfile.mkdtemp(prefix="soulos-pdf-")
    proc = subprocess.Popen(
        [exe, "--headless", "--disable-gpu", "--no-sandbox",
         "--user-data-dir=" + prof, "--no-pdf-header-footer",
         "--print-to-pdf=" + dst, "file://" + os.path.abspath(src)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    size, steady = -1, 0
    try:
        for _ in range(120):                     # up to about a minute
            time.sleep(0.5)
            if os.path.exists(dst):
                now = os.path.getsize(dst)
                steady = steady + 1 if now == size and now > 1000 else 0
                size = now
                if steady >= 3:                  # written and no longer growing
                    break
            if proc.poll() is not None and os.path.exists(dst):
                break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        shutil.rmtree(prof, ignore_errors=True)
    # trust the file, not the exit code: Chrome returns non-zero on harmless noise
    return os.path.exists(dst) and os.path.getsize(dst) > 1000


if __name__ == "__main__":
    main()
