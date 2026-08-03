#!/usr/bin/env python3
"""The figure engine. Renders branded SVG figures from a small spec.

Your brand lives in brand/brand.json. It picks one of the presets in
brand/styles/ and may override any color or font on top of it. Change the brand
once and every figure you make from then on inherits it. Nothing here hardcodes
a palette.

  python3 scripts/figure.py --styles              list the presets
  python3 scripts/figure.py --preview             render one figure in every preset
  python3 scripts/figure.py spec.json             render a figure
  python3 scripts/figure.py spec.json -o out.svg  render it somewhere specific
  python3 scripts/figure.py spec.json --style press   try a preset without switching

A spec is a small JSON file. The 'type' decides the shape:

  sequence     numbered steps            {"items": ["...", "..."]}
  framework    named steps on a napkin   {"items": [...], "name": "The Curve Test"}
  comparison   two columns               {"left": {...}, "right": {...}}
  loop         a feedback cycle          {"items": [...]}   (3 to 5 reads best)
  stat         one big number            {"value": "34", "label": "..."}
  quote        a pull quote              {"quote": "...", "attribution": "..."}
  matrix       a two by two trade-off    {"x": "...", "y": "...", "quadrants": [4]}
  stack        layers, foundation first  {"items": [...]}
  timeline     dated marks on a line     {"items": [{"when": "", "what": ""}]}
  balance      a weighing beam           {"left": {...}, "right": {...}, "tilt": 0.16}
  chain        links, the weak one named {"items": [...], "weak": 2}
  gap          two levels and the space  {"high": {...}, "low": {...}, "gap": "..."}
  network      nodes and the lines       {"items": [...], "links": [[0,1]], "hub": 0}
  iceberg      seen against unseen       {"above": "...", "below": [...]}
  funnel       what survives to the end  {"items": [{"label": "", "value": ""}]}
  curve        two trajectories          {"a": {...}, "b": {...}, "x": "", "y": ""}
  venn         two sets and the overlap  {"left": "", "right": "", "overlap": ""}

Every type also takes: title, kicker, caption.

SVG on purpose. It stays sharp anywhere, it is a text file your estate can keep
under version control, and it needs no fonts installed on your machine.
"""
import sys, os, json, math, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join(ROOT, "brand")
STYLES = os.path.join(BRAND, "styles")
W, H = 1200, 675


# ---------------------------------------------------------------- brand

def load_styles():
    out = {}
    if not os.path.isdir(STYLES):
        return out
    for f in sorted(os.listdir(STYLES)):
        if f.endswith(".json"):
            try:
                with open(os.path.join(STYLES, f), encoding="utf-8") as fh:
                    d = json.load(fh)
                out[d.get("name", f[:-5])] = d
            except Exception as e:
                print("skipping " + f + ": " + str(e), file=sys.stderr)
    return out


def load_brand(style_override=None):
    brand = {}
    path = os.path.join(BRAND, "brand.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            brand = json.load(fh)
    styles = load_styles()
    if not styles:
        sys.exit("No styles found in brand/styles/.")
    name = style_override or brand.get("style") or "clean"
    if name not in styles:
        sys.exit("Unknown style '" + name + "'. Available: " + ", ".join(sorted(styles)))
    st = styles[name]
    colors = dict(st.get("colors", {}))
    colors.update(brand.get("colors") or {})       # your overrides win
    fonts = dict(st.get("fonts", {}))
    fonts.update(brand.get("fonts") or {})
    return {
        "style": name,
        "label": st.get("label", name),
        "colors": colors,
        "fonts": fonts,
        "rules": st.get("rules", {}),
        "owner": brand.get("owner", ""),
        "copyright": brand.get("copyright", ""),
        "logo": brand.get("logo", ""),
        "logo_text": brand.get("logo_text", ""),
    }


# ---------------------------------------------------------------- helpers

def esc(s):
    """XML-escape. Always call this LAST, after any upper() or slicing.
    Escaping first and casing after turns &amp; into &AMP;, which is not a
    real entity and breaks the whole file."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# Rough advance widths as a fraction of font size. SVG gives no text metrics,
# so wrapping is estimated. Erring wide is correct: a short line is fine, an
# overflowing line is a broken figure.
def text_width(s, size, bold=False):
    narrow = "iljI.,:;'!|()[]{}t f"
    wide = "MWmw@%"
    total = 0.0
    for ch in str(s):
        if ch in narrow:
            total += 0.34
        elif ch in wide:
            total += 0.92
        elif ch.isupper():
            total += 0.68
        else:
            total += 0.545
    return total * size * (1.06 if bold else 1.0)


def wrap(s, size, max_w, bold=False, max_lines=None):
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(trial, size, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, len(lines[-1]) - 1)] + "..."
    return lines


def tspan(lines, x, y, size, fill, font, lh=1.32, anchor="start", weight="400"):
    out = []
    for i, ln in enumerate(lines):
        out.append(
            '<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" fill="%s" '
            'font-weight="%s" text-anchor="%s">%s</text>'
            % (x, y + i * size * lh, esc(font), size, fill, weight, anchor, esc(ln))
        )
    return "".join(out)


# ---------------------------------------------------------------- chrome

def content_top(spec):
    """Where the drawing may start, given how many lines the title took.
    Fixed offsets look fine until somebody writes a long title, and then two
    things sit on top of each other."""
    t = spec.get("title", "")
    if not t:
        return 150
    n = len(wrap(t, 44, W - 140, bold=True, max_lines=2))
    return 146 + (n - 1) * 52 + 62


def vcenter(spec, block):
    """Sit a short drawing in the space the title left, instead of jamming it to
    the top with a third of the canvas empty underneath."""
    t = content_top(spec)
    return max(0.0, ((H - 112) - t - block) * 0.42)


def chrome(b, spec):
    c, r, f = b["colors"], b["rules"], b["fonts"]
    parts = []
    parts.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, c["bg"]))

    if r.get("grid"):
        parts.append('<g stroke="%s" stroke-width="1" opacity="0.35">' % c["line"])
        for x in range(0, W, 40):
            parts.append('<line x1="%d" y1="0" x2="%d" y2="%d"/>' % (x, x, H))
        for y in range(0, H, 40):
            parts.append('<line x1="0" y1="%d" x2="%d" y2="%d"/>' % (y, W, y))
        parts.append("</g>")

    if r.get("top_rule"):
        parts.append('<rect x="0" y="0" width="%d" height="9" fill="%s"/>' % (W, c["accent1"]))

    if r.get("border"):
        parts.append(
            '<rect x="22" y="22" width="%d" height="%d" fill="none" stroke="%s" '
            'stroke-width="2" rx="%d"/>' % (W - 44, H - 44, c["line"], r.get("radius", 8))
        )

    kicker = spec.get("kicker", "")
    if kicker:
        k = kicker.upper() if r.get("uppercase_kicker") else kicker
        parts.append(
            '<text x="64" y="86" font-family="%s" font-size="17" fill="%s" '
            'letter-spacing="3" font-weight="600">%s</text>'
            % (esc(f["mono"]), c["accent1"], esc(k))
        )

    title = spec.get("title", "")
    if title:
        lines = wrap(title, 44, W - 140, bold=True, max_lines=2)
        parts.append(tspan(lines, 64, 146, 44, c["ink"], f["display"], 1.18, weight="700"))

    cap = spec.get("caption", "")
    if cap:
        lines = wrap(cap, 17, W - 340, max_lines=2)
        parts.append(tspan(lines, 64, H - 58, 17, c["muted"], f["body"], 1.3))

    # signature block: logo text if given, otherwise the owner, plus copyright
    sig = b.get("logo_text") or b.get("owner") or ""
    if sig:
        parts.append(
            '<text x="%d" y="%d" font-family="%s" font-size="16" fill="%s" '
            'text-anchor="end" font-weight="600">%s</text>'
            % (W - 64, H - 74, esc(f["body"]), c["ink2"], esc(sig))
        )
    cr = b.get("copyright") or ""
    if cr:
        year = spec.get("year", "")
        line = ("(c) " + str(year) + " " + cr).replace("  ", " ").strip() if year else "(c) " + cr
        parts.append(
            '<text x="%d" y="%d" font-family="%s" font-size="13" fill="%s" '
            'text-anchor="end">%s</text>'
            % (W - 64, H - 52, esc(f["mono"]), c["muted"], esc(line))
        )
    return parts


def defs(b):
    """The roughening filter that makes lines read as drawn rather than plotted.
    Only emitted when the active style asks for it."""
    if not b["rules"].get("roughen"):
        return ""
    return (
        '<defs><filter id="rough" x="-6%" y="-6%" width="112%" height="112%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.032" numOctaves="2" seed="7" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" '
        'xChannelSelector="R" yChannelSelector="G"/></filter></defs>'
    )


def rough(b):
    return ' filter="url(#rough)"' if b["rules"].get("roughen") else ""


# ---------------------------------------------------------------- shapes

def draw_sequence(b, spec, named=False):
    c, f, r = b["colors"], b["fonts"], b["rules"]
    items = spec.get("items", [])[:5]
    if not items:
        return []
    p = []
    name = spec.get("name", "")
    top = content_top(spec)
    if named and name:
        p.append('<text x="64" y="%d" font-family="%s" font-size="23" fill="%s" '
                 'font-style="italic">%s</text>'
                 % (top + 4, esc(f["display"]), c["accent2"], esc(name)))
        top += 34
    n = len(items)
    gap = 22
    bw = (W - 128 - gap * (n - 1)) / n
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    bh = H - top - 150
    for i, it in enumerate(items):
        x = 64 + i * (bw + gap)
        a = accents[i % 3]
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" stroke="%s" '
                 'stroke-width="2" rx="%d"%s/>'
                 % (x, top, bw, bh, c["panel"], a, r.get("radius", 8), rough(b)))
        p.append('<circle cx="%.1f" cy="%d" r="19" fill="%s"%s/>' % (x + 34, top + 36, a, rough(b)))
        p.append('<text x="%.1f" y="%d" font-family="%s" font-size="19" fill="%s" '
                 'text-anchor="middle" font-weight="700">%d</text>'
                 % (x + 34, top + 43, esc(f["body"]), c["bg"], i + 1))
        lines = wrap(it, 19, bw - 46, max_lines=5)
        p.append(tspan(lines, x + 22, top + 86, 19, c["ink"], f["body"], 1.34))
        if i < n - 1:
            ax = x + bw + gap / 2
            p.append('<path d="M %.1f %d L %.1f %d M %.1f %d L %.1f %d M %.1f %d L %.1f %d" '
                     'stroke="%s" stroke-width="3" fill="none" stroke-linecap="round"%s/>'
                     % (ax - 7, top + bh / 2, ax + 7, top + bh / 2,
                        ax + 1, top + bh / 2 - 6, ax + 7, top + bh / 2,
                        ax + 1, top + bh / 2 + 6, ax + 7, top + bh / 2, c["muted"], rough(b)))
    return p


def draw_comparison(b, spec):
    c, f, r = b["colors"], b["fonts"], b["rules"]
    left, right = spec.get("left", {}), spec.get("right", {})
    p = []
    top = content_top(spec)
    bh = H - top - 150
    cw = (W - 128 - 30) / 2
    for i, (col, accent) in enumerate(((left, c["accent3"]), (right, c["accent1"]))):
        x = 64 + i * (cw + 30)
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" stroke="%s" '
                 'stroke-width="2" rx="%d"%s/>'
                 % (x, top, cw, bh, c["panel"], accent, r.get("radius", 8), rough(b)))
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="6" fill="%s" rx="3"/>'
                 % (x, top, cw, accent))
        head = wrap(col.get("title", ""), 26, cw - 48, bold=True, max_lines=2)
        p.append(tspan(head, x + 24, top + 54, 26, c["ink"], f["display"], 1.2, weight="700"))
        y = top + 54 + len(head) * 31 + 16
        for it in col.get("items", [])[:5]:
            lines = wrap(it, 18, cw - 66, max_lines=2)
            p.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (x + 30, y - 6, accent))
            p.append(tspan(lines, x + 46, y, 18, c["ink2"], f["body"], 1.3))
            y += len(lines) * 24 + 12
    return p


def draw_loop(b, spec):
    c, f = b["colors"], b["fonts"]
    items = spec.get("items", [])[:5]
    if not items:
        return []
    p = []
    cx = W / 2
    cy = min(372.0, content_top(spec) + 148)
    rad = 112
    n = len(items)
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    p.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="none" stroke="%s" stroke-width="2" '
             'stroke-dasharray="7 9"%s/>' % (cx, cy, rad, c["line"], rough(b)))
    for i, it in enumerate(items):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        a = accents[i % 3]
        p.append('<circle cx="%.1f" cy="%.1f" r="27" fill="%s"%s/>' % (x, y, a, rough(b)))
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="20" fill="%s" '
                 'text-anchor="middle" font-weight="700">%d</text>'
                 % (x, y + 7, esc(f["body"]), c["bg"], i + 1))
        # label pushed outward from the ring
        lx = cx + (rad + 66) * math.cos(ang)
        ly = cy + (rad + 66) * math.sin(ang)
        anchor = "middle"
        if math.cos(ang) > 0.35:
            anchor = "start"
        elif math.cos(ang) < -0.35:
            anchor = "end"
        lines = wrap(it, 18, 230, max_lines=3)
        for j, ln in enumerate(lines):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="18" fill="%s" '
                     'text-anchor="%s">%s</text>'
                     % (lx, ly + j * 24 - (len(lines) - 1) * 11, esc(f["body"]),
                        c["ink"], anchor, esc(ln)))
    return p


def draw_stat(b, spec):
    c, f = b["colors"], b["fonts"]
    p = []
    val = str(spec.get("value", ""))
    size = 190 if len(val) <= 4 else (140 if len(val) <= 7 else 100)
    # the gap under the number has to scale with it: a hand-lettered face at 190px
    # has descenders deep enough to sit on top of a fixed 48px offset
    gap = size * 0.48 + 20
    block = size * 0.82 + gap + (33 if spec.get("label") else 0) + (24 if spec.get("source") else 0)
    base = content_top(spec) + max(0.0, ((H - 108) - content_top(spec) - block) * 0.45) + size * 0.82
    p.append('<text x="%d" y="%.1f" font-family="%s" font-size="%d" fill="%s" '
             'text-anchor="middle" font-weight="700">%s</text>'
             % (W // 2, base, esc(f["display"]), size, c["accent1"], esc(val)))
    y = base + gap
    lbl = spec.get("label", "")
    if lbl:
        lines = wrap(lbl, 25, W - 260, max_lines=2)
        p.append(tspan(lines, W // 2, y, 25, c["ink"], f["body"], 1.3, anchor="middle"))
        y += len(lines) * 33
    src = spec.get("source", "")
    if src:
        p.append('<text x="%d" y="%.1f" font-family="%s" font-size="14" fill="%s" '
                 'text-anchor="middle">%s</text>'
                 % (W // 2, y + 10, esc(f["mono"]), c["muted"], esc("source: " + src)))
    return p


def draw_quote(b, spec):
    c, f, r = b["colors"], b["fonts"], b["rules"]
    p = []
    q = spec.get("quote", "")
    size = 40 if len(q) < 110 else (33 if len(q) < 190 else 27)
    lines = wrap(q, size, W - 220, max_lines=6)
    top = content_top(spec)
    # the rule sits beside the quote and is exactly as tall as it, attribution included
    bar_h = len(lines) * size * 1.3 + (46 if spec.get("attribution", b.get("owner", "")) else 8)
    top += max(0.0, ((H - 108) - top - bar_h) * 0.45)   # sit it in the space, not at the top of it
    p.append('<rect x="64" y="%.1f" width="10" height="%.1f" fill="%s" rx="5"/>'
             % (top - 8, bar_h, c["accent1"]))
    p.append(tspan(lines, 104, top + size * 0.82, size, c["ink"], f["display"], 1.3, weight="600"))
    who = spec.get("attribution", b.get("owner", ""))
    if who:
        y = top + size * 0.82 + len(lines) * size * 1.3 + 20
        label = who.upper() if r.get("uppercase_kicker") else who
        p.append('<text x="104" y="%.1f" font-family="%s" font-size="16" fill="%s" '
                 'letter-spacing="2.5" font-weight="600">%s</text>'
                 % (y, esc(f["mono"]), c["accent1"], esc(label)))
    return p


def draw_matrix(b, spec):
    """Two axes, four quadrants. The shape for risk against regret, effort
    against value, anything where the point is the trade-off."""
    c, f, r = b["colors"], b["fonts"], b["rules"]
    p = []
    top = content_top(spec)
    mw = W - 236                      # leave room for the rotated y label
    mh = min(H - top - 122, 344)
    x0, y0 = 172.0, float(top + 4)
    accents = [c["accent3"], c["accent2"], c["accent2"], c["accent1"]]
    quads = (spec.get("quadrants") or [])[:4]
    for i in range(4):
        col, row = i % 2, i // 2
        qx, qy = x0 + col * mw / 2, y0 + row * mh / 2
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" '
                 'stroke-width="1.5" opacity="0.96"%s/>'
                 % (qx, qy, mw / 2, mh / 2, c["panel"], c["line"], rough(b)))
        if i < len(quads) and quads[i]:
            lines = wrap(quads[i], 18, mw / 2 - 60, max_lines=3)
            p.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (qx + 22, qy + 30, accents[i]))
            p.append(tspan(lines, qx + 38, qy + 35, 18, c["ink"], f["body"], 1.3))
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"%s/>'
             % (x0 + mw / 2, y0, x0 + mw / 2, y0 + mh, c["muted"], rough(b)))
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"%s/>'
             % (x0, y0 + mh / 2, x0 + mw, y0 + mh / 2, c["muted"], rough(b)))
    lab = lambda t: t.upper() if r.get("uppercase_kicker") else t
    if spec.get("x"):
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="14" fill="%s" '
                 'text-anchor="middle" letter-spacing="2">%s</text>'
                 % (x0 + mw / 2, y0 + mh + 30, esc(f["mono"]), c["accent1"], esc(lab(spec["x"]))))
    if spec.get("y"):
        p.append('<text transform="translate(%.1f,%.1f) rotate(-90)" font-family="%s" '
                 'font-size="14" fill="%s" text-anchor="middle" letter-spacing="2">%s</text>'
                 % (x0 - 30, y0 + mh / 2, esc(f["mono"]), c["accent1"], esc(lab(spec["y"]))))
    return p


def draw_stack(b, spec):
    """Layers, foundation at the bottom. Read from the ground up, which is the
    point: the thing everyone talks about sits on the thing nobody funds."""
    c, f, r = b["colors"], b["fonts"], b["rules"]
    items = spec.get("items", [])[:5]
    if not items:
        return []
    p = []
    top = content_top(spec)
    avail = H - top - 130
    n = len(items)
    bh = min(64.0, (avail - (n - 1) * 10) / n)
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    for i, it in enumerate(reversed(items)):          # first item is the foundation
        idx = n - 1 - i
        y = top + i * (bh + 10)
        inset = 34 * (n - 1 - i) * 0.42     # widest at the bottom, where the foundation is
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" '
                 'stroke-width="2" rx="%d"%s/>'
                 % (64 + inset, y, W - 128 - inset * 2, bh, c["panel"],
                    accents[idx % 3], r.get("radius", 8), rough(b)))
        p.append('<rect x="%.1f" y="%.1f" width="6" height="%.1f" fill="%s" rx="3"/>'
                 % (64 + inset, y, bh, accents[idx % 3]))
        lines = wrap(it, 18, W - 200 - inset * 2, max_lines=2)
        p.append(tspan(lines, 64 + inset + 24, y + bh / 2 + (6 if len(lines) == 1 else -3),
                       18, c["ink"], f["body"], 1.3))
    p.append('<text x="%d" y="%.1f" font-family="%s" font-size="12" fill="%s" '
             'letter-spacing="2">%s</text>'
             % (64, top + n * (bh + 10) + 16, esc(f["mono"]), c["muted"],
                esc("FOUNDATION" if r.get("uppercase_kicker") else "foundation")))
    return p


def draw_timeline(b, spec):
    """A line with dated marks. Accepts {"when":..,"what":..} or "1948 | text"."""
    c, f = b["colors"], b["fonts"]
    raw = spec.get("items", [])[:5]
    items = []
    for it in raw:
        if isinstance(it, dict):
            items.append((str(it.get("when", "")), str(it.get("what", ""))))
        else:
            parts = str(it).split("|", 1)
            items.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""))
    if not items:
        return []
    p = []
    top = content_top(spec)
    y = top + max(74.0, (H - top - 120) * 0.42)
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    p.append('<line x1="64" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="3"%s/>'
             % (y, W - 64, y, c["line"], rough(b)))
    n = len(items)
    step = (W - 128) / max(1, n - 1) if n > 1 else 0
    for i, (when, what) in enumerate(items):
        x = 64 + i * step if n > 1 else W / 2
        a = accents[i % 3]
        p.append('<circle cx="%.1f" cy="%.1f" r="11" fill="%s"%s/>' % (x, y, a, rough(b)))
        p.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (x, y, c["bg"]))
        anchor = "middle"
        if i == 0:
            anchor = "start"
        elif i == n - 1:
            anchor = "end"
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="19" fill="%s" '
                 'text-anchor="%s" font-weight="700">%s</text>'
                 % (x, y - 26, esc(f["display"]), a, anchor, esc(when)))
        for j, ln in enumerate(wrap(what, 16, step * 0.94 if n > 1 else 420, max_lines=4)):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="16" fill="%s" '
                     'text-anchor="%s">%s</text>'
                     % (x, y + 36 + j * 22, esc(f["body"]), c["ink"], anchor, esc(ln)))
    return p


def _pan(b, cx, cy, w):
    c = b["colors"]
    return ('<path d="M %.1f %.1f Q %.1f %.1f %.1f %.1f" fill="none" stroke="%s" '
            'stroke-width="3" stroke-linecap="round"%s/>'
            % (cx - w, cy, cx, cy + w * 0.52, cx + w, cy, c["ink2"], rough(b)))


def draw_balance(b, spec):
    """A weighing beam. Two things on a scale, and the beam tips. The shape for
    an argument where one side is countable and the other is not."""
    c, f = b["colors"], b["fonts"]
    p = []
    top = content_top(spec)
    cx = W / 2
    py = top + 42 + vcenter(spec, 316)
    L = 340.0
    t = float(spec.get("tilt", 0.16))
    ly, ry = py - t * L * 0.30, py + t * L * 0.30
    base = py + 172

    p.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s"%s/>'
             % (cx - 34, base, cx + 34, base, cx, py + 8, c["muted"], rough(b)))
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3.5" '
             'stroke-linecap="round"%s/>' % (cx - 46, base, cx + 46, base, c["ink2"], rough(b)))
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="4.5" '
             'stroke-linecap="round"%s/>' % (cx - L, ly, cx + L, ry, c["accent2"], rough(b)))
    p.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s"/>' % (cx, py + 8, c["accent2"]))

    sides = [(cx - L, ly, spec.get("left"), c["accent1"], "left"),
             (cx + L, ry, spec.get("right"), c["accent3"], "right")]
    for ex, ey, item, accent, side in sides:
        if isinstance(item, dict):
            title, note = str(item.get("title", "")), str(item.get("note", ""))
        else:
            title, note = str(item or ""), ""
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"%s/>'
                 % (ex, ey, ex, ey + 58, c["muted"], rough(b)))
        p.append(_pan(b, ex, ey + 58, 78))
        p.append('<ellipse cx="%.1f" cy="%.1f" rx="34" ry="17" fill="%s" opacity="0.9"%s/>'
                 % (ex, ey + 44, accent, rough(b)))
        for i, ln in enumerate(wrap(title, 20, 300, max_lines=2)):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="20" fill="%s" '
                     'text-anchor="middle" font-weight="700">%s</text>'
                     % (ex, ey + 118 + i * 26, esc(f["display"]), c["ink"], esc(ln)))
        if note:
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="14" fill="%s" '
                     'text-anchor="middle">%s</text>'
                     % (ex, ey + 118 + 26 * len(wrap(title, 20, 300, max_lines=2)) + 4,
                        esc(f["mono"]), accent, esc(note)))
    if spec.get("verdict"):
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s" '
                 'text-anchor="middle" font-style="italic">%s</text>'
                 % (cx, base + 44, esc(f["display"]), c["muted"], esc(spec["verdict"])))
    return p


def draw_chain(b, spec):
    """Links in a line, with the weak one named. A chain is only as strong as
    the link nobody looked at."""
    c, f = b["colors"], b["fonts"]
    items = spec.get("items", [])[:5]
    if not items:
        return []
    p = []
    top = content_top(spec)
    n = len(items)
    weak = spec.get("weak", -1)
    if isinstance(weak, str):
        weak = items.index(weak) if weak in items else -1
    gap = 16.0
    lw = (W - 128 - gap * (n - 1)) / n
    lh = 108.0
    y = top + 26 + vcenter(spec, 168)
    for i, it in enumerate(items):
        x = 64 + i * (lw + gap)
        broken = (i == weak)
        col = c["accent3"] if broken else c["accent1"]
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="none" '
                 'stroke="%s" stroke-width="9"%s%s/>'
                 % (x, y, lw, lh, lh / 2, col,
                    ' stroke-dasharray="16 11"' if broken else "", rough(b)))
        if i < n - 1:
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                     'stroke-width="7" stroke-linecap="round"%s/>'
                     % (x + lw - 4, y + lh / 2, x + lw + gap + 4, y + lh / 2,
                        c["accent3"] if (broken or i + 1 == weak) else c["accent1"], rough(b)))
        for j, ln in enumerate(wrap(it, 17, lw - 46, max_lines=3)):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s" '
                     'text-anchor="middle">%s</text>'
                     % (x + lw / 2, y + lh / 2 - (len(wrap(it, 17, lw - 46, max_lines=3)) - 1) * 11
                        + j * 22 + 6, esc(f["body"]), c["ink"], esc(ln)))
        if broken and spec.get("weak_note"):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="14" fill="%s" '
                     'text-anchor="middle" letter-spacing="1.4">%s</text>'
                     % (x + lw / 2, y + lh + 30, esc(f["mono"]), c["accent3"],
                        esc(spec["weak_note"])))
    return p


def draw_gap(b, spec):
    """Two levels and the distance between them. The gap is the argument."""
    c, f = b["colors"], b["fonts"]
    p = []
    top = content_top(spec)
    hi, lo = spec.get("high") or {}, spec.get("low") or {}
    if isinstance(hi, str):
        hi = {"label": hi}
    if isinstance(lo, str):
        lo = {"label": lo}
    off = vcenter(spec, 256)
    y1 = top + 34 + off
    y2 = top + 210 + off
    for y, d, accent in ((y1, hi, c["accent1"]), (y2, lo, c["accent3"])):
        p.append('<rect x="64" y="%.1f" width="%d" height="30" rx="6" fill="%s" '
                 'opacity="0.92"%s/>' % (y, W - 128, accent, rough(b)))
        p.append('<text x="80" y="%.1f" font-family="%s" font-size="19" fill="%s" '
                 'font-weight="700">%s</text>'
                 % (y - 12, esc(f["body"]), c["ink"], esc(str(d.get("label", "")))))
        if d.get("value"):
            p.append('<text x="%d" y="%.1f" font-family="%s" font-size="19" fill="%s" '
                     'text-anchor="end" font-weight="700">%s</text>'
                     % (W - 80, y - 12, esc(f["mono"]), accent, esc(str(d["value"]))))
    mx = W / 2
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5" '
             'stroke-dasharray="8 8"%s/>' % (mx, y1 + 34, mx, y2 - 4, c["muted"], rough(b)))
    for yy, dy in ((y1 + 34, 1), (y2 - 4, -1)):
        p.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f" fill="none" stroke="%s" '
                 'stroke-width="2.5"%s/>'
                 % (mx - 7, yy + 9 * dy, mx, yy, mx + 7, yy + 9 * dy, c["muted"], rough(b)))
    if spec.get("gap"):
        lines = wrap(str(spec["gap"]), 21, 340, max_lines=3)
        for i, ln in enumerate(lines):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="21" fill="%s" '
                     'text-anchor="middle" font-style="italic">%s</text>'
                     % (mx, (y1 + y2) / 2 - (len(lines) - 1) * 14 + i * 28, esc(f["display"]),
                        c["ink"], esc(ln)))
    return p


def draw_network(b, spec):
    """Nodes and the lines between them. Everything is a graph once you draw it."""
    c, f = b["colors"], b["fonts"]
    items = spec.get("items", [])[:7]
    if not items:
        return []
    p = []
    top = content_top(spec)
    cx = W / 2
    cy = min(top + 168, H - 236)
    rad = 148.0
    n = len(items)
    pts = []
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        pts.append((cx + rad * 1.85 * math.cos(a), cy + rad * math.sin(a)))
    links = spec.get("links")
    if not links:
        links = [[i, (i + 1) % n] for i in range(n)] + [[0, i] for i in range(2, n - 1)]
    for a, z in links:
        if 0 <= a < n and 0 <= z < n:
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                     'stroke-width="2" opacity="0.75"%s/>'
                     % (pts[a][0], pts[a][1], pts[z][0], pts[z][1], c["line"], rough(b)))
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    hub = spec.get("hub", -1)
    for i, (x, y) in enumerate(pts):
        r = 24 if i == hub else 17
        p.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s"%s/>'
                 % (x, y, r, accents[i % 3] if i != hub else c["accent2"], rough(b)))
        lines = wrap(items[i], 15, 210, max_lines=2)
        anchor = "middle"
        off = r + 20
        dy = off if y >= cy else -(off - 4)
        if x > cx + 120:
            anchor, dy = "start", 5
        elif x < cx - 120:
            anchor, dy = "end", 5
        for j, ln in enumerate(lines):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="15" fill="%s" '
                     'text-anchor="%s">%s</text>'
                     % (x + (r + 12 if anchor == "start" else (-(r + 12) if anchor == "end" else 0)),
                        y + dy + j * 19, esc(f["body"]), c["ink"], anchor, esc(ln)))
    return p


def draw_iceberg(b, spec):
    """What everyone argues about, and what is actually holding it up."""
    c, f = b["colors"], b["fonts"]
    p = []
    top = content_top(spec)
    cx = W / 2
    water = top + 96
    p.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s"%s/>'
             % (cx, top + 6, cx - 96, water, cx + 96, water, c["accent1"], rough(b)))
    depth = min(H - water - 128, 268)
    p.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s" '
             'opacity="0.55"%s/>'
             % (cx - 96, water, cx + 96, water, cx + 236, water + depth,
                cx - 236, water + depth, c["accent2"], rough(b)))
    p.append('<line x1="40" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="2.5" '
             'stroke-dasharray="12 8"%s/>' % (water, W - 40, water, c["muted"], rough(b)))
    if spec.get("above"):
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="20" fill="%s" '
                 'text-anchor="end" font-weight="700">%s</text>'
                 % (cx - 128, top + 56, esc(f["display"]), c["ink"], esc(str(spec["above"]))))
    if spec.get("waterline"):
        p.append('<text x="%d" y="%.1f" font-family="%s" font-size="13" fill="%s" '
                 'text-anchor="end" letter-spacing="1.6">%s</text>'
                 % (W - 44, water - 10, esc(f["mono"]), c["muted"], esc(str(spec["waterline"]))))
    below = spec.get("below", [])[:4]
    for i, it in enumerate(below):
        y = water + 44 + i * 52
        p.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (cx - 200, y - 5, c["accent3"]))
        for j, ln in enumerate(wrap(it, 17, 360, max_lines=2)):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s">%s</text>'
                     % (cx - 184, y + j * 21, esc(f["body"]), c["ink"], esc(ln)))
    return p


def draw_funnel(b, spec):
    """What goes in at the top, what survives to the bottom."""
    c, f = b["colors"], b["fonts"]
    raw = spec.get("items", [])[:5]
    if not raw:
        return []
    items = [(str(x.get("label", "")), str(x.get("value", ""))) if isinstance(x, dict)
             else (str(x), "") for x in raw]
    p = []
    top = content_top(spec)
    n = len(items)
    bh = min(62.0, (H - top - 150) / n - 8)
    accents = [c["accent1"], c["accent2"], c["accent3"]]
    wide, narrow = W - 380, 280.0     # the right column carries the values
    for i, (label, val) in enumerate(items):
        t0 = i / n
        t1 = (i + 1) / n
        w0 = wide - (wide - narrow) * t0
        w1 = wide - (wide - narrow) * t1
        y = top + i * (bh + 8)
        p.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s" '
                 'stroke="%s" stroke-width="2" opacity="0.9"%s/>'
                 % (W / 2 - w0 / 2, y, W / 2 + w0 / 2, y, W / 2 + w1 / 2, y + bh,
                    W / 2 - w1 / 2, y + bh, c["panel"], accents[i % 3], rough(b)))
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="18" fill="%s" '
                 'text-anchor="middle">%s</text>'
                 % (W / 2, y + bh / 2 + 6, esc(f["body"]), c["ink"],
                    esc(wrap(label, 18, w1 - 30, max_lines=1)[0] if label else "")))
        if val:
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s" '
                     'text-anchor="start" font-weight="700">%s</text>'
                     % (W / 2 + w0 / 2 + 18, y + bh / 2 + 6, esc(f["mono"]), accents[i % 3],
                        esc(val)))
    return p


def draw_curve(b, spec):
    """Two trajectories on the same axes. The argument is the shape, not the number."""
    c, f = b["colors"], b["fonts"]
    p = []
    top = content_top(spec)
    x0, x1 = 118.0, W - 150.0
    y1 = min(H - 150, top + 300)
    y0 = top + 18
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"%s/>'
             % (x0, y0, x0, y1, c["muted"], rough(b)))
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"%s/>'
             % (x0, y1, x1, y1, c["muted"], rough(b)))
    SHAPES_ = {"rise": lambda t: t ** 2, "steep": lambda t: t ** 3,
               "flat": lambda t: 0.12 + 0.06 * t, "fall": lambda t: max(0.0, 0.75 - t ** 1.6),
               "sag": lambda t: 0.5 - 0.42 * math.sin(math.pi * t) + 0.32 * t,
               "linear": lambda t: t}
    curves = [(spec.get("a") or {}, c["accent1"]), (spec.get("b") or {}, c["accent3"])]
    for idx, (cv, col) in enumerate(curves):
        if not cv:
            continue
        fn = SHAPES_.get(str(cv.get("shape", "rise")), SHAPES_["rise"])
        pts = []
        for k in range(41):
            t = k / 40
            pts.append((x0 + t * (x1 - x0), y1 - fn(t) * (y1 - y0) * 0.94))
        p.append('<path d="M %s" fill="none" stroke="%s" stroke-width="4" '
                 'stroke-linecap="round"%s/>'
                 % (" L ".join("%.1f %.1f" % q for q in pts), col, rough(b)))
        ex, ey = pts[-1]
        p.append('<circle cx="%.1f" cy="%.1f" r="7" fill="%s"/>' % (ex, ey, col))
        if cv.get("label"):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s" '
                     'font-weight="700">%s</text>'
                     % (ex + 14, ey + 5, esc(f["body"]), col, esc(str(cv["label"]))))
    if spec.get("x"):
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="14" fill="%s" '
                 'text-anchor="middle" letter-spacing="2">%s</text>'
                 % ((x0 + x1) / 2, y1 + 34, esc(f["mono"]), c["muted"], esc(str(spec["x"]))))
    if spec.get("y"):
        p.append('<text transform="translate(%.1f,%.1f) rotate(-90)" font-family="%s" '
                 'font-size="14" fill="%s" text-anchor="middle" letter-spacing="2">%s</text>'
                 % (x0 - 30, (y0 + y1) / 2, esc(f["mono"]), c["muted"], esc(str(spec["y"]))))
    return p


def draw_venn(b, spec):
    """Two things and the part that belongs to both. The overlap is the point."""
    c, f = b["colors"], b["fonts"]
    p = []
    top = content_top(spec)
    cy = min(top + 148 + vcenter(spec, 300), H - 220)
    r = 132.0
    cxl, cxr = W / 2 - r * 0.56, W / 2 + r * 0.56
    p.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.42" stroke="%s" '
             'stroke-width="2.5"%s/>' % (cxl, cy, r, c["accent1"], c["accent1"], rough(b)))
    p.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.42" stroke="%s" '
             'stroke-width="2.5"%s/>' % (cxr, cy, r, c["accent3"], c["accent3"], rough(b)))
    # labels sit outside their circle. Centring them inside puts them straight
    # through the overlap label, which is the one word the figure exists to say.
    for cxx, key, anchor in ((cxl - r - 20, "left", "end"), (cxr + r + 20, "right", "start")):
        val = spec.get(key)
        if not val:
            continue
        lines = wrap(str(val), 18, 300, max_lines=3)
        for i, ln in enumerate(lines):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="18" fill="%s" '
                     'text-anchor="%s" font-weight="700">%s</text>'
                     % (cxx, cy - (len(lines) - 1) * 12 + i * 23, esc(f["body"]), c["ink"],
                        anchor, esc(ln)))
    if spec.get("overlap"):
        for i, ln in enumerate(wrap(str(spec["overlap"]), 16, r * 0.86, max_lines=3)):
            p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="16" fill="%s" '
                     'text-anchor="middle" font-weight="700">%s</text>'
                     % (W / 2, cy - 6 + i * 21, esc(f["body"]), c["ink"], esc(ln)))
    if spec.get("note"):
        p.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="17" fill="%s" '
                 'text-anchor="middle" font-style="italic">%s</text>'
                 % (W / 2, cy + r + 46, esc(f["display"]), c["muted"], esc(str(spec["note"]))))
    return p


SHAPES = {
    "sequence": lambda b, s: draw_sequence(b, s, False),
    "framework": lambda b, s: draw_sequence(b, s, True),
    "comparison": draw_comparison,
    "loop": draw_loop,
    "stat": draw_stat,
    "quote": draw_quote,
    "matrix": draw_matrix,
    "stack": draw_stack,
    "timeline": draw_timeline,
    "balance": draw_balance,
    "chain": draw_chain,
    "gap": draw_gap,
    "network": draw_network,
    "iceberg": draw_iceberg,
    "funnel": draw_funnel,
    "curve": draw_curve,
    "venn": draw_venn,
}


def render(spec, style=None):
    b = load_brand(style)
    kind = spec.get("type", "sequence")
    if kind not in SHAPES:
        sys.exit("Unknown figure type '" + kind + "'. Try: " + ", ".join(sorted(SHAPES)))
    body = chrome(b, spec) + SHAPES[kind](b, spec)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
            % (W, H, W, H)) + defs(b) + "".join(body) + "</svg>"


# ---------------------------------------------------------------- cli

PREVIEW = {
    "type": "sequence",
    "kicker": "how it works",
    "title": "Your figures, in your brand",
    "items": ["Pick a style, or write your own",
              "Set your colors and your name",
              "Every figure inherits it"],
    "caption": "Change brand/brand.json once. Everything you draw after that follows.",
}


def main():
    args = sys.argv[1:]
    if "--styles" in args:
        styles = load_styles()
        active = load_brand()["style"]
        print("\nFigure styles available in this estate:\n")
        for n in sorted(styles):
            d = styles[n]
            mark = "  <- yours" if n == active else ""
            print("  " + d.get("label", n) + " (" + n + ")" + mark)
            print("    " + d.get("description", ""))
            print("    Best for: " + d.get("best_for", "") + "\n")
        print("Set your style in brand/brand.json, or copy one in brand/styles/ and")
        print("change the values to make your own. Names are yours to invent.\n")
        return

    if "--preview" in args:
        out = os.path.join(ROOT, "brand", "preview")
        os.makedirs(out, exist_ok=True)
        for n in sorted(load_styles()):
            svg = render(dict(PREVIEW, kicker=n), style=n)
            path = os.path.join(out, n + ".svg")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(svg)
            print("wrote " + os.path.relpath(path, ROOT))
        print("\nOpen them, pick the one that feels like you, then set it in brand/brand.json.")
        return

    specs = [a for a in args if not a.startswith("-")]
    if not specs:
        print(__doc__)
        return
    style = None
    if "--style" in args:
        style = args[args.index("--style") + 1]
    out = None
    if "-o" in args:
        out = args[args.index("-o") + 1]

    with open(specs[0], encoding="utf-8") as fh:
        spec = json.load(fh)
    svg = render(spec, style)
    if not out:
        out = os.path.splitext(specs[0])[0] + ".svg"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("wrote " + out)


if __name__ == "__main__":
    main()
