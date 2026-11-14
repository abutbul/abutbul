"""Validate generated artifacts (no deps, run after generate.py)."""
import os
import re
import sys
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "assets")


def main():
    ok = True
    svgs = sorted(f for f in os.listdir(ASSETS) if f.endswith(".svg"))
    for name in svgs:
        path = os.path.join(ASSETS, name)
        try:
            ET.parse(path)
        except Exception as exc:
            print("FAIL %s: %s" % (name, exc))
            ok = False
            continue
        svg = open(path, encoding="utf-8").read()
        if re.search(r"&(?!(amp|lt|gt|quot|apos);)", svg):
            print("FAIL %s has unescaped ampersands" % name)
            ok = False
    print("OK   checked %d SVG screens" % len(svgs))

    readme = open(os.path.join(BASE, "README.md"), encoding="utf-8").read()
    lowered = readme.lower()
    for bad in ("<script", "<style", "style=", "onclick", "javascript:"):
        if bad in lowered:
            print("FAIL README contains forbidden token: %s" % bad)
            ok = False
    print("OK   README has no script/style/inline-style")

    missing = [src for src in re.findall(r'src="([^"]+)"', readme)
               if not os.path.exists(os.path.join(BASE, src))]
    if missing:
        print("FAIL README references missing files: %s" % ", ".join(missing))
        ok = False
    else:
        print("OK   every image the README references exists")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
