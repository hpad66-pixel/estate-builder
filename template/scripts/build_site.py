#!/usr/bin/env python3
"""Build a personal site from the estate, in your own brand.

Reads profile.md, your articles, and your compiled book, and writes a small
static site into outputs/site/: a home page, one page per article, a writing
index, a book page, an about page, and an RSS feed. Your colours, your
typeface, your mark, your copyright.

  python3 scripts/build_site.py               build into outputs/site/
  python3 scripts/build_site.py --to docs     build into docs/ for GitHub Pages
  python3 scripts/build_site.py --drafts      include articles not marked published

What it will never publish: SOUL.md, the well, anything under
outputs/book-evidence/, and any article that is not explicitly published. Your
voice law and your raw dictation are yours. They are not content.

No installs. Python 3, and the same markdown renderer the book compiler uses.
"""
import sys, os, re, json, html, glob, shutil, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_book import split_front, markdown, brand as load_brand   # one renderer, not two

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEVER = ("SOUL.md", "outputs/book-evidence", "INTERVIEW", "BRAND-INTERVIEW")


# ------------------------------------------------------------------ helpers

def font_link(fonts):
    """Best effort Google Fonts request for the families the brand names. A
    family that is not hosted there simply does not load, and the stack falls
    back, which is why every preset keeps a plain fallback at the end."""
    fams, seen = [], set()
    for stack in fonts.values():
        first = stack.split(",")[0].strip().strip("'\"")
        if not first or first.lower() in ("system-ui", "monospace", "serif", "sans-serif"):
            continue
        if first.lower() in ("georgia", "impact", "helvetica", "arial", "courier new"):
            continue
        if first not in seen:
            seen.add(first)
            fams.append(first.replace(" ", "+"))
    if not fams:
        return ""
    q = "&".join("family=%s:wght@400;600;700" % f for f in fams)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?%s&display=swap" rel="stylesheet">' % q)


def css(b):
    c, f = b["colors"], b["fonts"]
    return """
:root{--bg:%(bg)s;--panel:%(panel)s;--ink:%(ink)s;--ink2:%(ink2)s;--muted:%(muted)s;--line:%(line)s;--a1:%(a1)s;--a2:%(a2)s;--a3:%(a3)s}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:%(body)s;font-size:18px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto;padding:0 26px}
a{color:var(--a1);text-decoration:none}a:hover{text-decoration:underline}
h1,h2,h3{font-family:%(display)s;font-weight:700;line-height:1.16}
h1{font-size:46px;margin-bottom:14px}
h2{font-size:30px;margin:44px 0 12px}
h3{font-size:22px;margin:32px 0 8px}
p{margin-bottom:17px}
ul,ol{margin:0 0 18px 22px}li{margin-bottom:7px}
blockquote{margin:26px 0;padding:4px 0 4px 22px;border-left:4px solid var(--a1);font-family:%(display)s;font-size:21px}
code{font-family:%(mono)s;font-size:.9em;background:rgba(128,128,128,.13);padding:1px 5px;border-radius:4px}
pre{background:rgba(128,128,128,.11);padding:14px 16px;border-radius:8px;overflow-x:auto}
hr.break{border:none;text-align:center;margin:32px 0}
hr.break::after{content:"* * *";color:var(--muted);letter-spacing:9px;font-size:15px}
figure.fig{margin:32px 0;text-align:center}
figure.fig svg,figure.fig img{max-width:100%%;height:auto;border:1px solid var(--line);border-radius:8px}
figure.fig figcaption{font-size:14px;color:var(--muted);margin-top:9px;font-style:italic}
.verify{background:#ffe9a8;color:#5a4600;padding:1px 6px;border-radius:4px;font-size:.82em;font-weight:700}
header.site{border-bottom:1px solid var(--line);padding:22px 0;margin-bottom:52px}
header.site .wrap{display:flex;align-items:baseline;gap:20px;flex-wrap:wrap}
header.site .me{font-family:%(display)s;font-weight:700;font-size:20px;color:var(--ink)}
header.site nav{margin-left:auto;display:flex;gap:20px;font-size:15px}
header.site nav a{color:var(--muted)}header.site nav a:hover{color:var(--ink);text-decoration:none}
.hero{margin-bottom:16px}
.hero .role{font-family:%(mono)s;font-size:12.5px;letter-spacing:2.6px;text-transform:uppercase;color:var(--a1);margin-bottom:16px}
.hero .tagline{font-size:21px;color:var(--ink2);margin-bottom:22px}
.meta{font-family:%(mono)s;font-size:13px;color:var(--muted);display:flex;gap:16px;flex-wrap:wrap}
.list{margin-top:8px;border-top:1px solid var(--line)}
.list a.item{display:block;padding:20px 0;border-bottom:1px solid var(--line);color:var(--ink)}
.list a.item:hover{text-decoration:none}
.list a.item .t{font-family:%(display)s;font-weight:700;font-size:22px;margin-bottom:5px}
.list a.item:hover .t{color:var(--a1)}
.list a.item .d{font-family:%(mono)s;font-size:12.5px;color:var(--muted)}
.list a.item .s{color:var(--ink2);font-size:16px;margin-top:6px}
article.post .head{margin-bottom:34px;padding-bottom:20px;border-bottom:1px solid var(--line)}
article.post .head .d{font-family:%(mono)s;font-size:12.5px;color:var(--muted);margin-bottom:10px}
.bookcard{border:1px solid var(--line);border-radius:14px;padding:28px;background:var(--panel);margin-top:10px}
.bookcard .bt{font-family:%(display)s;font-weight:700;font-size:30px;margin-bottom:8px}
.btn{display:inline-block;background:var(--a1);color:%(bg)s;border-radius:9px;padding:11px 20px;font-weight:700;font-size:15px;margin-top:16px}
.btn:hover{text-decoration:none;opacity:.9}
footer.site{margin-top:76px;border-top:1px solid var(--line);padding:26px 0 60px;font-size:14px;color:var(--muted)}
footer.site .wrap{display:flex;gap:18px;flex-wrap:wrap;align-items:baseline}
footer.site .built{margin-left:auto;font-family:%(mono)s;font-size:12px}
@media(max-width:640px){h1{font-size:34px}body{font-size:17px}header.site nav{margin-left:0;width:100%%}}
""" % {"bg": c["bg"], "panel": c["panel"], "ink": c["ink"], "ink2": c.get("ink2", c["ink"]),
       "muted": c.get("muted", "#777"), "line": c.get("line", "#ddd"),
       "a1": c.get("accent1", "#333"), "a2": c.get("accent2", "#555"),
       "a3": c.get("accent3", "#777"), "body": f.get("body", "Georgia, serif"),
       "display": f.get("display", "Georgia, serif"), "mono": f.get("mono", "monospace")}


def page(b, prof, title, body, depth=0, desc=""):
    up = "../" * depth
    nav = "".join('<a href="%s%s">%s</a>' % (up, href, label) for href, label in
                  (("index.html", "Home"), ("writing.html", "Writing"),
                   ("book.html", "The book"), ("about.html", "About")))
    mark = b.get("logo_text") or prof.get("name", "")
    cr = b.get("copyright") or prof.get("name", "")
    year = datetime.date.today().year
    return ("""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><meta name="description" content="%s">
<link rel="alternate" type="application/rss+xml" href="%sfeed.xml">
%s<style>%s</style></head><body>
<header class="site"><div class="wrap"><a class="me" href="%sindex.html">%s</a><nav>%s</nav></div></header>
<main class="wrap">%s</main>
<footer class="site"><div class="wrap"><span>&copy; %s %s</span>
<span class="built">built from the estate &middot; <a href="%sfeed.xml">rss</a></span></div></footer>
</body></html>""" % (html.escape(title), html.escape(desc), up, font_link(b["fonts"]), css(b),
                     up, html.escape(mark), nav, body, year, html.escape(cr), up))


def article_slug(path):
    return os.path.basename(os.path.dirname(path))


def load_articles(include_drafts):
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "articles", "*", "article.md"))):
        if os.sep + "_template" + os.sep in path:
            continue
        with open(path, encoding="utf-8") as f:
            meta, body = split_front(f.read())
        status = str(meta.get("status", "draft")).lower()
        if status != "published" and not include_drafts:
            continue
        out.append({"meta": meta, "body": body, "slug": article_slug(path),
                    "title": meta.get("title") or article_slug(path).replace("-", " ").title(),
                    "date": str(meta.get("date", "")) or article_slug(path)[:10],
                    "status": status})
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def rss(prof, arts, site_title):
    items = []
    for a in arts[:20]:
        items.append("<item><title>%s</title><link>writing/%s.html</link>"
                     "<guid isPermaLink=\"false\">%s</guid><pubDate>%s</pubDate>"
                     "<description>%s</description></item>"
                     % (html.escape(a["title"]), a["slug"], a["slug"], a["date"],
                        html.escape(first_para(a["body"]))))
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            '<title>%s</title><link>index.html</link><description>%s</description>%s'
            '</channel></rss>' % (html.escape(site_title),
                                  html.escape(prof.get("tagline", "")), "".join(items)))


def first_para(body, limit=220):
    for block in body.split("\n\n"):
        t = re.sub(r"<!--.*?-->", "", block, flags=re.S).strip()
        if t and not t.startswith(("#", "<!--", "!", ">", "-", "*")):
            t = re.sub(r"[*`\[\]]", "", t)
            return (t[:limit] + "...") if len(t) > limit else t
    return ""


# ------------------------------------------------------------------ build

def main():
    args = sys.argv[1:]
    drafts = "--drafts" in args
    out_dir = os.path.join(ROOT, "outputs", "site")
    if "--to" in args:
        out_dir = os.path.join(ROOT, args[args.index("--to") + 1])

    pfile = os.path.join(ROOT, "profile.md")
    if not os.path.exists(pfile):
        sys.exit("No profile.md in the estate. That is the file this site is built from.")
    with open(pfile, encoding="utf-8") as f:
        prof, pbody = split_front(f.read())
    if str(prof.get("published", "false")).lower() not in ("true", "yes"):
        sys.exit("profile.md says published: false. Fill it in, set it to true, and run this again.\n"
                 "Nothing about you goes on a public page by accident.")

    b = load_brand()
    name = prof.get("name") or b.get("owner") or ""
    site_title = prof.get("site_title") or name
    arts = load_articles(drafts)

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "writing"), exist_ok=True)

    # home
    links = prof.get("links") or []
    if isinstance(links, str):
        links = [links]
    linkhtml = " ".join('<a href="%s">%s</a>' % (html.escape(u.strip()), html.escape(l.strip()))
                        for l, u in
                        (x.split("|", 1) for x in links if "|" in x))
    meta_bits = [x for x in (prof.get("location", ""), prof.get("email", "")) if x]
    home = '<section class="hero"><h1>%s</h1>' % html.escape(name)
    if prof.get("title"):
        home = ('<section class="hero"><div class="role">%s</div><h1>%s</h1>'
                % (html.escape(str(prof["title"])), html.escape(name)))
    if prof.get("tagline"):
        home += '<p class="tagline">%s</p>' % html.escape(str(prof["tagline"]))
    if meta_bits or linkhtml:
        home += ('<div class="meta">%s%s</div>'
                 % ("".join("<span>%s</span>" % html.escape(str(m)) for m in meta_bits), linkhtml))
    home += "</section>"
    home += markdown(pbody.split("## Credentials")[0])
    if arts:
        home += "<h2>Writing</h2><div class='list'>"
        for a in arts[:5]:
            home += ('<a class="item" href="writing/%s.html"><div class="d">%s</div>'
                     '<div class="t">%s</div><div class="s">%s</div></a>'
                     % (a["slug"], html.escape(a["date"]), html.escape(a["title"]),
                        html.escape(first_para(a["body"], 150))))
        home += "</div>"
        if len(arts) > 5:
            home += '<p style="margin-top:18px"><a href="writing.html">Everything I have written</a></p>'
    write(out_dir, "index.html", page(b, prof, site_title, home, 0, prof.get("tagline", "")))

    # about
    about = "<h1>About</h1>" + markdown(pbody)
    write(out_dir, "about.html", page(b, prof, "About &middot; " + site_title, about, 0))

    # writing index
    wi = "<h1>Writing</h1><div class='list'>"
    for a in arts:
        wi += ('<a class="item" href="writing/%s.html"><div class="d">%s</div>'
               '<div class="t">%s</div><div class="s">%s</div></a>'
               % (a["slug"], html.escape(a["date"]), html.escape(a["title"]),
                  html.escape(first_para(a["body"], 170))))
    wi += "</div>"
    if not arts:
        wi = "<h1>Writing</h1><p>Nothing published yet.</p>"
    write(out_dir, "writing.html", page(b, prof, "Writing &middot; " + site_title, wi, 0))

    # one page per article
    for a in arts:
        body = ('<article class="post"><div class="head"><div class="d">%s</div>'
                '<h1>%s</h1></div>%s</article>'
                % (html.escape(a["date"]), html.escape(a["title"]), markdown(a["body"])))
        write(os.path.join(out_dir, "writing"), a["slug"] + ".html",
              page(b, prof, a["title"], body, 1, first_para(a["body"], 150)))

    # the book
    compiled = sorted(glob.glob(os.path.join(ROOT, "outputs", "book-compiled", "*.html")))
    bk = "<h1>The book</h1>"
    if compiled:
        src = compiled[0]
        title = os.path.basename(src)[:-5].replace("-", " ").title()
        shutil.copy2(src, os.path.join(out_dir, "book-read.html"))
        pdf = src[:-5] + ".pdf"
        haspdf = os.path.exists(pdf)
        if haspdf:
            shutil.copy2(pdf, os.path.join(out_dir, "book.pdf"))
        bk += ('<div class="bookcard"><div class="bt">%s</div>'
               '<p>Compiled from the estate. Every chapter was built from dictation held '
               'verbatim, and the provenance is printed at the back.</p>'
               '<a class="btn" href="book-read.html">Read it</a>%s</div>'
               % (html.escape(title),
                  ' <a class="btn" href="book.pdf">Download the PDF</a>' if haspdf else ""))
    else:
        bk += ("<p>Not compiled yet. Run <code>python3 scripts/build_book.py --pdf</code> "
               "and build this site again.</p>")
    write(out_dir, "book.html", page(b, prof, "The book &middot; " + site_title, bk, 0))

    write(out_dir, "feed.xml", rss(prof, arts, site_title))

    # a last guard: nothing private may have reached the output
    leaked = []
    for root, _, fs in os.walk(out_dir):
        for fn in fs:
            p = os.path.join(root, fn)
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            if "banned-words" in t or "POLICY: VERBATIM" in t or "the voice law of" in t:
                leaked.append(os.path.relpath(p, out_dir))
    if leaked:
        sys.exit("STOPPED. Private material reached the output: " + ", ".join(leaked))

    print("Built: %s" % os.path.relpath(out_dir, ROOT))
    print("  %d article%s, %s" % (len(arts), "" if len(arts) == 1 else "s",
                                  "the book is on it" if compiled else "no compiled book yet"))
    if not drafts:
        total = len(load_articles(True))
        if total > len(arts):
            print("  %d article(s) held back, because they are not marked published"
                  % (total - len(arts)))
    print("  the well, SOUL.md and the interviews were never read")
    print("\nOpen %s/index.html to look at it." % os.path.relpath(out_dir, ROOT))
    print("To put it online, push this estate and point GitHub Pages or Cloudflare")
    print("Pages at that folder. The push is yours to make, the same as the seal.")


def write(d, name, text):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
