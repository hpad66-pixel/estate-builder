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
    block = size * 0.82 + 48 + (33 if spec.get("label") else 0) + (24 if spec.get("source") else 0)
    base = content_top(spec) + max(0.0, ((H - 108) - content_top(spec) - block) * 0.45) + size * 0.82
    p.append('<text x="%d" y="%.1f" font-family="%s" font-size="%d" fill="%s" '
             'text-anchor="middle" font-weight="700">%s</text>'
             % (W // 2, base, esc(f["display"]), size, c["accent1"], esc(val)))
    y = base + 48
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


SHAPES = {
    "sequence": lambda b, s: draw_sequence(b, s, False),
    "framework": lambda b, s: draw_sequence(b, s, True),
    "comparison": draw_comparison,
    "loop": draw_loop,
    "stat": draw_stat,
    "quote": draw_quote,
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
