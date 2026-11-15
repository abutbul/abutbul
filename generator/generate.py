"""Generate the profile README, its banner and a local preview.

Everything is derived from data/profile.json:

  assets/banner.svg     the BBS-style greeting banner
  README.md             the banner followed by plain text sections
  preview/index.html    the same markup for a local look

Usage:  python3 generator/generate.py
Stdlib only.
"""

import json
import os

from ansi import PALETTE, FONT_FAMILY, figlet, xesc

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "data", "profile.json")
ASSETS = os.path.join(BASE, "assets")
PREVIEW = os.path.join(BASE, "preview")

FONT_SIZE = 13
LINE_H = 20
CHAR_W = 0.6          # advance of a monospace glyph, in em
WIDTH = 800
MARGIN_X = 16
COLS = int((WIDTH - 2 * MARGIN_X) / (FONT_SIZE * CHAR_W))
PAD = 20
LOGO_FONT = "ANSI Shadow.flf"
LOGO_COLORS = ["bred", "yellow", "bgreen", "bcyan", "bblue", "bmagenta"]

NL = chr(10)


def fmt(x):
    if isinstance(x, int):
        return str(x)
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return s if s else "0"


# --------------------------------------------------------------------------- #
# Banner
# --------------------------------------------------------------------------- #
class Screen:
    """A block of terminal rows rendered as one static SVG."""

    def __init__(self):
        self.y = PAD
        self.parts = []

    def line(self, segments, center=False, size=FONT_SIZE, step=LINE_H):
        x = WIDTH / 2 if center else MARGIN_X
        anchor = ' text-anchor="middle"' if center else ''
        font = ' font-size="' + str(size) + '"' if size != FONT_SIZE else ''
        spans = "".join('<tspan fill="' + PALETTE.get(col, PALETTE["white"]) + '">'
                        + xesc(txt) + '</tspan>' for txt, col in segments)
        self.parts.append('<text x="' + fmt(x) + '" y="' + fmt(self.y + size * 1.08) + '"'
                          + anchor + font + ' xml:space="preserve">' + spans + '</text>')
        self.y += step
        return self

    def center(self, s, color="white"):
        return self.line([(s, color)], center=True)

    def blank(self, n=1):
        self.y += LINE_H * n
        return self

    def logo(self, text, size):
        """Block lettering, one palette colour per row."""
        rows = figlet(LOGO_FONT, text)
        cols = max(len(r) for r in rows)
        for i, row in enumerate(rows):
            # Pad with no-break spaces so every row is centred as one block.
            row += chr(0xA0) * (cols - len(row))
            self.line([(row, LOGO_COLORS[i % len(LOGO_COLORS)])], center=True,
                      size=size, step=round(size * 1.25))
        return self

    def svg(self):
        h = self.y + PAD
        return NL.join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(WIDTH) + '" height="'
            + str(h) + '" viewBox="0 0 ' + str(WIDTH) + ' ' + str(h) + '" font-family="'
            + FONT_FAMILY + '" font-size="' + str(FONT_SIZE) + '">',
            '<style>text,tspan{white-space:pre}</style>',
            '<rect width="' + str(WIDTH) + '" height="' + str(h) + '" rx="8" fill="#000000"/>',
        ] + self.parts + ['</svg>']) + NL


def logo_size(texts):
    """Largest font size at which the widest logo row still fits the banner."""
    cols = max(len(row) for t in texts for row in figlet(LOGO_FONT, t))
    return min(FONT_SIZE, int((WIDTH - 2 * MARGIN_X) / (cols * CHAR_W)))


def banner(data):
    handle = data["handle"]
    greeting, name = data.get("greeting", "Hi, I am"), data["name"]
    s = Screen()
    s.center("(c) " + str(data.get("year", "")) + " " + handle.upper()
             + " SYSTEMS  ·  ANSI/VT100 16-COLOR", "lgray")
    s.blank()
    size = logo_size([greeting, name])
    s.logo(greeting, size)
    s.blank(0.5)
    s.logo(name, size)
    s.blank()
    if data.get("callsign"):
        s.center("▄▄▄▄  " + " ".join(data["callsign"].upper()) + "  ▄▄▄▄", "bcyan")
        s.blank()

    connect, online = "CONNECT 57600 8N1  ·  ANSI detected", "● ONLINE"
    s.line([(connect, "green"),
            (" " * (COLS - len(connect) - len(online)), "black"),
            (online, "bgreen")])
    s.line([("LOGIN   ", "lgray"), (handle, "bcyan")])
    s.line([("PASSWD  ", "lgray"), ("●" * 9, "dgray")])
    s.line([("* ACCESS GRANTED *", "bred")])
    return s


# --------------------------------------------------------------------------- #
# README sections
# --------------------------------------------------------------------------- #
def nowrap(s):
    return xesc(s).replace(" ", "&nbsp;")


def link(text, url):
    return '<a href="' + xesc(url) + '">' + text + '</a>'


def chips(items):
    return " ".join('<code>' + xesc(i) + '</code>' for i in items)


def section_header(data):
    alt = data.get("greeting", "Hi, I am") + " " + data["name"]
    if data.get("callsign"):
        alt += " — " + data["callsign"].upper()
    parts = [p for p in data.get("title", "").split(" · ") if p]
    headline = " · ".join(['<b>' + xesc(parts[0]) + '</b>'] + [xesc(p) for p in parts[1:]]) \
        if parts else ""
    # <picture> keeps GitHub from wrapping the banner in a link to the file.
    return ['<p align="center"><picture><img src="assets/banner.svg" width="100%" alt="'
            + xesc(alt) + '" /></picture></p>',
            '',
            '<p align="center">' + headline + '</p>',
            '']


def section_about(data):
    return ['<h2>About</h2>',
            '<p>' + " ".join(xesc(line) for line in data.get("about", [])) + '</p>',
            '']


def section_experience(data):
    work = data.get("work", [])
    L = ['<h2>Experience</h2>', '<table>',
         '<tr><th align="left">Role</th><th align="left">Company</th>'
         '<th align="left" width="190">Period</th></tr>']
    for w in work:
        L.append('<tr><td><b>' + xesc(w.get("role", "")) + '</b></td><td>'
                 + xesc(w.get("org", "")) + '</td><td>' + nowrap(w.get("period", ""))
                 + '</td></tr>')
    L.append('</table>')

    # Consecutive roles that share the same description are shown once.
    groups = []
    for w in work:
        if not w.get("bullets"):
            continue
        last = groups[-1] if groups else None
        if last and last["role"] == w.get("role") and last["bullets"] == w["bullets"]:
            last["orgs"].append(w.get("org", ""))
            last["start"] = w.get("period", "").split(" – ")[0]
        else:
            start, _, end = w.get("period", "").partition(" – ")
            groups.append({"role": w.get("role", ""), "orgs": [w.get("org", "")],
                           "bullets": w["bullets"], "start": start, "end": end})
    if groups:
        L.append('<details>')
        L.append('<summary>Role highlights</summary>')
        L.append('<br />')
        for g in groups:
            period = g["start"] + (" – " + g["end"] if g["end"] else "")
            L.append('<p><b>' + xesc(g["role"]) + '</b> · ' + xesc(" / ".join(g["orgs"]))
                     + '<br /><sub>' + xesc(period) + '</sub></p>')
            L.append('<ul>')
            L.extend('<li>' + xesc(bl) + '</li>' for bl in g["bullets"])
            L.append('</ul>')
        L.append('</details>')
    L.append('')
    return L


def section_projects(data):
    notes = data.get("group_notes", {})
    L = ['<h2>Projects</h2>', '<table>',
         '<tr><th align="left" width="230">Project</th><th align="left">What it does</th>'
         '<th align="right">Stars</th></tr>']
    group = None
    for p in data.get("projects", []):
        if p.get("group") and p["group"] != group:
            group = p["group"]
            note = ' <sub>· ' + xesc(notes[group]) + '</sub>' if notes.get(group) else ''
            L.append('<tr><td colspan="3"><b>' + xesc(group) + '</b>' + note + '</td></tr>')
        L.append('<tr><td>' + link('<b>' + xesc(p["name"]) + '</b>', p["url"]) + '</td><td>'
                 + xesc(p.get("desc", "")) + '<br />' + chips(p.get("tags", []))
                 + '</td><td align="right">' + str(p.get("stars", 0)) + '</td></tr>')
    L.extend(['</table>', ''])
    return L


def section_skills(data):
    L = ['<h2>Skills</h2>', '<table>']
    for group, items in data.get("skills", {}).items():
        L.append('<tr><td><b>' + xesc(group.capitalize()) + '</b></td><td>' + chips(items)
                 + '</td></tr>')
    L.extend(['</table>', ''])
    return L


def section_contact(data):
    items = ['<b>' + xesc(c["label"]) + '</b> ' + link(xesc(c["value"]), c["url"])
             for c in data.get("contact", [])]
    return ['<h2>Contact</h2>', '<p>' + (' · ' + NL).join(items) + '</p>', '']


def section_footer():
    return ['<hr />',
            '<p align="center"><sub>Banner drawn in 16-colour ANSI and generated from code — '
            '<code>generator/generate.py</code> · <code>data/profile.json</code></sub></p>',
            '']


def render_readme(data):
    L = ['<!-- Generated by generator/generate.py from data/profile.json. Do not edit. -->']
    L += section_header(data)
    L += section_about(data)
    L += section_experience(data)
    L += section_projects(data)
    L += section_skills(data)
    L += section_contact(data)
    L += section_footer()
    return NL.join(L)


PREVIEW_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<base href="../">
<title>%s — profile preview</title>
<style>
  body { background:#0d1117; color:#e6edf3; margin:0; padding:24px;
         font:16px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif; }
  .markdown-body { max-width:848px; margin:0 auto; }
  .markdown-body img { max-width:100%%; }
  .markdown-body h2 { border-bottom:1px solid #30363d; padding-bottom:.3em; }
  .markdown-body table { border-collapse:collapse; margin-bottom:16px; }
  .markdown-body th, .markdown-body td { border:1px solid #30363d; padding:6px 13px; }
  .markdown-body code { background:#262c36; border-radius:6px; padding:.2em .4em; font-size:85%%; }
  .markdown-body summary { cursor:pointer; }
  .markdown-body a { color:#58a6ff; text-decoration:none; }
  .markdown-body hr { border:0; border-top:1px solid #30363d; }
  .note { max-width:848px; margin:0 auto 16px; color:#8b949e; font-size:13px; }
</style>
</head>
<body>
<p class="note">Local preview of README.md. GitHub's own styling differs slightly.</p>
<div class="markdown-body">
"""


def main():
    with open(DATA_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    for stale in os.listdir(ASSETS):
        if stale.endswith(".svg") and stale != "banner.svg":
            os.remove(os.path.join(ASSETS, stale))
    with open(os.path.join(ASSETS, "banner.svg"), "w", encoding="utf-8") as fh:
        fh.write(banner(data).svg())
    readme = render_readme(data)
    with open(os.path.join(BASE, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)
    with open(os.path.join(PREVIEW, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(PREVIEW_HEAD % xesc(data["name"]) + readme + "</div>" + NL + "</body>" + NL
                 + "</html>" + NL)
    print("wrote README.md, preview/index.html and assets/banner.svg")


if __name__ == "__main__":
    main()
