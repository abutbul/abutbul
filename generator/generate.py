"""Generate assets/session.svg and README.md from data/profile.json.

Usage:  python3 generator/generate.py
Stdlib only.
"""

import json
import os
import sys
import urllib.request

from ansi import PALETTE, FONT_FAMILY, figlet, split_runs, xesc, mdesc, truncate

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "data", "profile.json")
ASSETS = os.path.join(BASE, "assets")
CACHE_PATH = os.path.join(BASE, "data", ".stats-cache.json")

FONT_SIZE = 13
LINE_H = 20
FW = FONT_SIZE * 0.6
WIDTH = 800
MARGIN_X = 16
MARGIN_TOP = 20
LINE_DELAY = 0.14
SCENE_PAUSE = 1.5
LINGER = 6.0

NL = chr(10)


def fmt(x):
    if isinstance(x, int):
        return str(x)
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def fmt_frac(x):
    s = ("%.5f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


def reveal(t, T):
    t = max(t, 0.05)
    f1 = min(t / T, 1.0)
    f2 = min((t + 0.08) / T, 1.0)
    if f2 <= f1:
        f1 = max(0.0, f2 - 0.0005)
    return ('<animate attributeName="opacity" values="0;0;1;1" '
            'keyTimes="0;' + fmt_frac(f1) + ';' + fmt_frac(f2) + ';1" '
            'dur="' + fmt(T) + 's" repeatCount="indefinite" calcMode="linear"/>')


def blink(dur=0.8):
    return ('<animate attributeName="opacity" values="1;0;1" '
            'dur="' + fmt(dur) + 's" repeatCount="indefinite"/>')


def _tspans(segments):
    out = []
    for txt, col in segments:
        c = PALETTE.get(col, PALETTE["white"])
        out.append('<tspan fill="' + c + '">' + xesc(txt) + '</tspan>')
    return "".join(out)


def render_text(item, T):
    x = item.get("x", MARGIN_X)
    y = item["y"]
    anchor = ' text-anchor="middle"' if item.get("center") else ''
    anim = reveal(item["t"], T) if item.get("reveal", True) else ''
    return ('<text x="' + fmt(x) + '" y="' + fmt(y) + '" font-size="'
            + str(FONT_SIZE) + '"' + anchor + ' xml:space="preserve">'
            + anim + _tspans(item["segments"]) + '</text>')


def render_blink(item):
    txt = item.get("text", item.get("ch", "█"))
    c = PALETTE.get(item.get("color"), PALETTE["bgreen"])
    anchor = ' text-anchor="middle"' if item.get("center") else ''
    return ('<text x="' + fmt(item.get("x", MARGIN_X)) + '" y="' + fmt(item["y"])
            + '" font-size="' + str(FONT_SIZE) + '"' + anchor
            + ' xml:space="preserve">'
            + '<tspan fill="' + c + '">' + xesc(txt) + '</tspan>'
            + blink(item.get("dur", 0.8)) + '</text>')


def render_marquee(item):
    y = item["y"]
    text = item["text"]
    c = PALETTE.get(item["color"], PALETTE["dgray"])
    tw = len(text) * FW
    gap = tw + FW * 4
    dur = gap / 60.0
    inner = ('<tspan fill="' + c + '">' + xesc(text) + '</tspan>'
             '<tspan dx="' + fmt(gap) + '" fill="' + c + '">' + xesc(text) + '</tspan>')
    anim = ('<animateTransform attributeName="transform" type="translate" '
            'from="0 0" to="' + fmt(-gap) + ' 0" dur="' + fmt(dur)
            + 's" repeatCount="indefinite"/>')
    return ('<text x="0" y="' + fmt(y) + '" font-size="' + str(FONT_SIZE)
            + '" xml:space="preserve">' + inner + anim + '</text>')


def render_rainbow(item):
    y = item["y"]
    n = item["n"]
    colors = ["bred", "yellow", "bgreen", "bcyan", "bblue", "bmagenta"]
    vals = [PALETTE[c] for c in colors]
    cells = []
    for i in range(n):
        base = vals[i % len(vals)]
        anim = ('<animate attributeName="fill" values="'
                + ";".join(vals + [vals[0]]) + '" dur="4s" repeatCount="indefinite" begin="'
                + fmt(i * 0.12) + 's"/>')
        cells.append('<text x="' + fmt(i * FW) + '" y="' + fmt(y)
                     + '" font-size="' + str(FONT_SIZE) + '" fill="' + base
                     + '" xml:space="preserve">█' + anim + '</text>')
    return "".join(cells)


def render_scanline(H):
    return ('<rect x="0" y="-80" width="' + str(WIDTH) + '" height="46" '
            'fill="#ffffff" opacity="0.035">'
            '<animateTransform attributeName="transform" type="translate" '
            'from="0 0" to="0 ' + str(H + 160) + '" dur="9s" repeatCount="indefinite"/>'
            '</rect>')


RENDERERS = {
    "text": render_text,
    "blink": render_blink,
    "marquee": render_marquee,
    "rainbow": render_rainbow,
}


class Builder:
    def __init__(self):
        self.items = []
        self.y = MARGIN_TOP
        self.t = 0.4

    def line(self, segments, x=MARGIN_X, center=False, color=None, reveal=True, delay=LINE_DELAY):
        if color:
            segments = [(t, color) for t, _ in segments]
        self.items.append(dict(kind="text", x=x, y=self.y, segments=segments,
                               center=center, t=self.t, reveal=reveal))
        if reveal:
            self.t += delay
        self.y += LINE_H
        return self

    def text(self, s, x=MARGIN_X, center=False, color="white", reveal=True):
        return self.line([(s, color)], x=x, center=center, reveal=reveal)

    def blank(self, n=1):
        self.y += LINE_H * n
        self.t += LINE_DELAY * 0.5 * n
        return self

    def pause(self, dt):
        self.t += dt
        return self

    def blink_at(self, x, y, ch="█", color="bgreen"):
        self.items.append(dict(kind="blink", x=x, y=y, ch=ch, color=color))
        return self

    def blink_text(self, s, x=MARGIN_X, center=False, color="bgreen"):
        self.items.append(dict(kind="blink", x=x, y=self.y, text=s,
                               center=center, color=color))
        self.y += LINE_H
        return self

    def marquee(self, text, color="dgray"):
        self.items.append(dict(kind="marquee", y=self.y, text=text, color=color))
        self.y += LINE_H
        return self

    def rainbow(self, n=None):
        if n is None:
            n = int((WIDTH - 2 * MARGIN_X) / FW)
        self.items.append(dict(kind="rainbow", y=self.y, n=n))
        self.y += LINE_H
        return self

    def rule(self, color="dgray", ch="─", n=None):
        if n is None:
            n = int((WIDTH - 2 * MARGIN_X) / FW)
        return self.text(ch * n, color=color)

    def prompt(self, key):
        self.text("> " + key, color="bred")
        cy = self.y - LINE_H
        cx = MARGIN_X + len("> " + key) * FW + FW
        self.blink_at(cx, cy)
        return self


def logon(b, data):
    b.blank(2)
    b.text("(c) 1992 ABUTBUL SYSTEMS  ·  ANSI/VT100 16-COLOR", center=True, color="lgray")
    b.blank(1)
    rows = figlet("ANSI Shadow.flf", data["handle"])
    colors = ["bred", "yellow", "bgreen", "bcyan", "bblue", "bmagenta"]
    for i, row in enumerate(rows):
        col = colors[i % len(colors)]
        segs = [(t, col if not shadow else "dgray") for t, shadow in split_runs(row)]
        b.line(segs, x=WIDTH / 2, center=True, reveal=True, delay=0.10)
    b.blank(1)
    b.text("▄▄▄▄  T H E   A B U T B U L   B B S  ▄▄▄▄", center=True, color="bcyan")
    b.blank(2)
    b.line([("CONNECT 57600 8N1  ·  ANSI detected", "green")])
    b.line([("LOGIN   ", "lgray"), (data["handle"], "bcyan")])
    b.line([("PASSWD  ", "lgray"), ("●" * 9, "dgray")])
    b.blank(1)
    b.text("* ACCESS GRANTED *", color="bred")
    b.pause(SCENE_PAUSE)


def _monitor_art():
    return [
        "   ╔══════════════════╗",
        "   ║ abutbul-bbs v1.2 ║",
        "   ║ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ║",
        "   ║ login: abutbul   ║",
        "   ║ pass : ░░░░░░░░  ║",
        "   ║ $ whoami         ║",
        "   ║ > abutbul        ║",
        "   ║ ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ ║",
        "   ╚══════════════════╝",
        "     ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    ]


def _art_color(ch):
    if ch in "╔═╗╚╝║":
        return "lgray"
    if ch in "▄▀█":
        return "bcyan"
    if ch in "░▒▓":
        return "dgray"
    return "bgreen"


def _colorize_art(rows):
    out = []
    for r in rows:
        segs = []
        for ch in r:
            col = _art_color(ch)
            if segs and segs[-1][1] == col:
                segs[-1][0] += ch
            else:
                segs.append([ch, col])
        out.append(segs)
    return out


def _info_line(key, value, maxlen, val_color="white"):
    dots = "·" * (maxlen - len(key) + 3)
    return [(key, "bcyan"), (":", "dgray"), (" " + dots + " ", "dgray"),
            (value, val_color)]


def neofetch(b, data, stats):
    b.blank(2)
    b.text("═" * 30 + " NEOFETCH " + "═" * 30, center=True, color="yellow")
    b.blank(1)
    art = _colorize_art(_monitor_art())
    art_y0 = b.y
    for segs in art:
        b.line(segs, x=MARGIN_X, reveal=True, delay=0.06)
    art_bottom = b.y
    info_x = MARGIN_X + 24 * FW + 24
    nf = data["neofetch"]
    host = nf.get("host", "bbs")
    b.y = art_y0
    b.line([(data["handle"], "bcyan"), ("@", "dgray"), (host, "bcyan")], x=info_x)
    b.line([("─" * 28, "dgray")], x=info_x)
    info_keys = [k for k in nf if k != "host"]
    maxlen = max(len(k) for k in info_keys)
    for k in info_keys:
        b.line(_info_line(k, nf[k], maxlen), x=info_x, reveal=True, delay=0.07)
    b.blank(1)
    b.line([("GitHub Stats", "bred")], x=info_x)
    b.line([("─" * 28, "dgray")], x=info_x)
    if stats:
        stat_labels = [("repos", "Repos"), ("followers", "Followers"),
                       ("following", "Following"), ("stars", "Stars")]
        smax = max(len(lb) for _, lb in stat_labels)
        for key, label in stat_labels:
            val = stats.get(key)
            val = str(val) if val is not None else "—"
            b.line(_info_line(label, val, smax, "yellow"), x=info_x, reveal=True, delay=0.07)
    b.y = max(b.y, art_bottom)
    b.blank(2)
    b.marquee("· WELCOME TO THE ABUTBUL BBS · 24/7 · 16-COLOR ANSI · "
              "· PRESS (A) (P) (W) (S) (C) (Q) ·", color="dgray")
    b.blink_text("● ONLINE", x=WIDTH - 90, color="bgreen")
    b.pause(SCENE_PAUSE)


def menu(b, data):
    b.blank(1)
    b.text("══════════════ MAIN MENU ══════════════", center=True, color="yellow")
    b.blank(1)
    for item in data["menu"]:
        if item["key"] == "Q":
            continue
        b.line([("(" + item["key"] + ")", "bred"), ("  " + item["label"], "white")])
    b.rule()
    b.text("type a command and press ENTER", color="dgray")
    b.pause(SCENE_PAUSE)


def _page_title(b, key, label):
    b.text("[" + label.upper() + "]", color="yellow")
    b.rule()


def page_projects(b, projects):
    _page_title(b, "P", "Projects")
    for p in projects:
        name = p["name"]
        stars = p.get("stars", 0)
        tags = " · ".join(p.get("tags", []))
        b.line([("▸ ", "bred"), (name, "bcyan"), ("  ★ " + str(stars), "yellow"),
                ("  " + tags, "dgray")])
        b.line([("   " + truncate(p.get("desc", ""), 80), "lgray")])
        b.line([("   ↳ " + p.get("url", ""), "dgray")])
        b.blank(1)
    b.pause(SCENE_PAUSE)


def page_work(b, work):
    _page_title(b, "W", "Work Experience")
    for w in work:
        b.line([("▸ ", "bred"), (w.get("role", ""), "bcyan")])
        if w.get("org"):
            seg = [("   " + w["org"], "lgray")]
            if w.get("period"):
                seg.append(("  " + w["period"], "dgray"))
            b.line(seg)
        for bl in w.get("bullets", []):
            b.line([("   - " + bl, "lgray")])
        b.blank(1)
    b.pause(SCENE_PAUSE)


def page_skills(b, skills):
    _page_title(b, "S", "Skills")
    for group, items in skills.items():
        b.line([("▸ ", "bred"), (group, "bred"), (":", "dgray"),
                ("  " + " · ".join(items), "white")])
    b.pause(SCENE_PAUSE)


def page_contact(b, contact):
    _page_title(b, "C", "Contact")
    maxlen = max(len(c["label"]) for c in contact)
    for c in contact:
        dots = "·" * (maxlen - len(c["label"]) + 3)
        b.line([(c["label"], "bred"), (":", "dgray"), (" " + dots + " ", "dgray"),
                (c["value"], "bcyan")])
    b.pause(SCENE_PAUSE)


def page_about(b, about):
    _page_title(b, "A", "About")
    for line in about:
        b.line([("  " + line, "lgray")])
    b.pause(SCENE_PAUSE)


def quit_scene(b, data):
    b.prompt("Q")
    b.text("logging off...", color="dgray")
    b.text("G O O D B Y E  ✦", center=True, color="bred")
    b.blank(2)


def build_session(data, stats):
    b = Builder()
    logon(b, data)
    neofetch(b, data, stats)
    menu(b, data)
    for item in data["menu"]:
        key = item["key"]
        label = item["label"]
        if key == "Q":
            continue
        b.prompt(key)
        if key == "A":
            page_about(b, data.get("about", []))
        elif key == "P":
            page_projects(b, data.get("projects", []))
        elif key == "W":
            page_work(b, data.get("work", []))
        elif key == "S":
            page_skills(b, data.get("skills", {}))
        elif key == "C":
            page_contact(b, data.get("contact", []))
    quit_scene(b, data)
    return b


def render_svg(b):
    H = b.y + MARGIN_TOP
    T = b.t + LINGER
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="' + str(WIDTH)
                 + '" height="' + str(H) + '" font-family="' + FONT_FAMILY
                 + '" font-size="' + str(FONT_SIZE) + '">')
    parts.append('<style>text,tspan{white-space:pre}</style>')
    parts.append('<rect width="' + str(WIDTH) + '" height="' + str(H) + '" fill="#000000"/>')
    parts.append('<rect x="0.5" y="0.5" width="' + fmt(WIDTH - 1) + '" height="'
                 + fmt(H - 1) + '" fill="none" stroke="#1f1f1f" stroke-width="1"/>')
    for it in b.items:
        r = RENDERERS.get(it["kind"])
        if r:
            parts.append(r(it, T) if it["kind"] == "text" else r(it))
    parts.append(render_scanline(H))
    parts.append('</svg>')
    return NL.join(parts)


# --------------------------------------------------------------------------- #
# GitHub stats
# --------------------------------------------------------------------------- #
def fetch_stats(handle):
    try:
        req = urllib.request.Request(
            "https://api.github.com/users/" + handle,
            headers={"User-Agent": "abutbul-readme", "Accept": "application/vnd.github+json"})
        u = json.load(urllib.request.urlopen(req, timeout=10))
        req2 = urllib.request.Request(
            "https://api.github.com/users/" + handle + "/repos?per_page=100",
            headers={"User-Agent": "abutbul-readme"})
        repos = json.load(urllib.request.urlopen(req2, timeout=10))
        stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
        return {"repos": u.get("public_repos"), "followers": u.get("followers"),
                "following": u.get("following"), "stars": stars}
    except Exception as exc:
        print("stats fetch failed: %s" % exc, file=sys.stderr)
        return None


def load_stats(data):
    stats = fetch_stats(data["github"]) if data.get("stats", {}).get("enable") else None
    if stats is None:
        try:
            with open(CACHE_PATH) as fh:
                stats = json.load(fh)
        except Exception:
            stats = {}
    else:
        try:
            with open(CACHE_PATH, "w") as fh:
                json.dump(stats, fh)
        except Exception:
            pass
    return stats


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #
def render_readme(data, stats):
    L = []
    L.append('<div align="center">')
    L.append('')
    L.append('# ' + xesc(data["name"]) + ' — <code>' + xesc(data["handle"]) + '</code> BBS')
    L.append('')
    L.append('<img src="assets/session.svg" width="100%" alt="' + xesc(data["handle"])
             + ' BBS session" />')
    L.append('')
    L.append('<i>' + xesc(data.get("title", "")) + '</i>')
    L.append('</div>')
    L.append('')
    L.append('---')
    L.append('')
    L.append('## ▸ MAIN MENU')
    L.append('')
    cmds = data["menu"]
    names = " · ".join('<code>(' + c["key"] + ')</code> ' + xesc(c["label"]) for c in cmds)
    L.append(names)
    L.append('')
    for c in cmds:
        key = c["key"]
        label = c["label"]
        if key == "Q":
            continue
        open_attr = ' open' if key == "A" else ''
        L.append('<details' + open_attr + '>')
        L.append('<summary><b>(' + key + ') ' + xesc(label) + '</b></summary>')
        L.append('')
        L.append(_section_body(key, data))
        L.append('</details>')
        L.append('')
    L.append('> <sub>(Q) Quit → <a href="https://github.com/' + xesc(data["handle"])
             + '">log off</a></sub>')
    L.append('')
    L.append('---')
    L.append('')
    if stats:
        L.append('<p align="center">')
        L.append('<sub>'
                 + ' repos ' + str(stats.get("repos", "—"))
                 + ' · followers ' + str(stats.get("followers", "—"))
                 + ' · following ' + str(stats.get("following", "—"))
                 + ' · stars ' + str(stats.get("stars", "—"))
                 + ' (live)</sub>')
        L.append('</p>')
    L.append('')
    L.append('<p align="center"><sub>ANSI · 80s–90s BBS scene (ACiD/iCE) · generated from code — '
             + '<code>generator/generate.py</code> · <code>data/profile.json</code></sub></p>')
    L.append('')
    return NL.join(L)


def _section_body(key, data):
    L = []
    if key == "A":
        for line in data.get("about", []):
            L.append('- ' + xesc(line))
        return NL.join(L)
    if key == "P":
        L.append('<table>')
        L.append('<tr><th>Project</th><th>Description</th><th>Stack</th></tr>')
        for p in data.get("projects", []):
            L.append('<tr><td><a href="' + xesc(p["url"]) + '"><b>' + xesc(p["name"])
                     + '</b></a></td><td>' + mdesc(p.get("desc", "")) + '</td><td><sub>'
                     + mdesc(" · ".join(p.get("tags", []))) + '</sub></td></tr>')
        L.append('</table>')
        return NL.join(L)
    if key == "W":
        for w in data.get("work", []):
            L.append('### ' + xesc(w.get("role", "")))
            if w.get("org"):
                L.append('**' + xesc(w["org"]) + '**' + (' — ' + xesc(w["period"]) if w.get("period") else ''))
            for bl in w.get("bullets", []):
                L.append('- ' + xesc(bl))
        return NL.join(L)
    if key == "S":
        for group, items in data.get("skills", {}).items():
            L.append('- **' + xesc(group) + '**: ' + xesc(" · ".join(items)))
        return NL.join(L)
    if key == "C":
        for c in data.get("contact", []):
            L.append('- **' + xesc(c["label"]) + '**: [' + xesc(c["value"]) + '](' + xesc(c["url"]) + ')')
        return NL.join(L)
    return ""


# --------------------------------------------------------------------------- #
def main():
    os.makedirs(ASSETS, exist_ok=True)
    with open(DATA_PATH) as fh:
        data = json.load(fh)
    stats = load_stats(data)
    b = build_session(data, stats)
    svg = render_svg(b)
    with open(os.path.join(ASSETS, "session.svg"), "w") as fh:
        fh.write(svg)
    with open(os.path.join(BASE, "README.md"), "w") as fh:
        fh.write(render_readme(data, stats))
    print("wrote assets/session.svg (%d bytes) and README.md" % len(svg))


if __name__ == "__main__":
    main()
