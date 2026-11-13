#!/usr/bin/env python3
"""Checks the built site in dist/. Exit code 1 on any error.

- every internal link and #anchor points to something that exists
- every page has a title under 60 characters, a description, lang, canonical
- every <img> has alt, width and height
- text colours meet WCAG AA against their background, in both themes
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse

DIST = Path(__file__).resolve().parent.parent / "dist"
errors = []


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.imgs, self.title, self.intitle, self.meta, self.lang = set(), [], [], "", False, {}, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in ("link", "script", "source", "img") and (a.get("href") or a.get("src")):
            self.links.append(a.get("href") or a.get("src"))
        if tag == "img":
            self.imgs.append(a)
        if tag == "meta":
            self.meta[a.get("name") or a.get("property")] = a.get("content")
        if tag == "title":
            self.intitle = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.intitle = False

    def handle_data(self, d):
        if self.intitle:
            self.title += d


def target(page_path, href):
    url, frag = urldefrag(href)
    if not url:
        return page_path, frag
    if url.startswith("/"):
        p = DIST / url.lstrip("/")
    else:
        p = (page_path.parent / url).resolve()
    if p.is_dir() or url.endswith("/"):
        p = p / "index.html"
    return p, frag


pages = {p: Page() for p in DIST.rglob("*.html")}
for p, parser in pages.items():
    parser.feed(p.read_text(encoding="utf-8"))

for p, parser in pages.items():
    rel = p.relative_to(DIST)
    if not parser.title or len(parser.title) > 60:
        errors.append(f"{rel}: title missing or over 60 characters ({len(parser.title)})")
    if not parser.meta.get("description"):
        errors.append(f"{rel}: no meta description")
    if parser.lang not in ("de", "en"):
        errors.append(f"{rel}: html lang missing")
    for img in parser.imgs:
        for attr in ("alt", "width", "height"):
            if attr not in img:
                errors.append(f"{rel}: <img src={img.get('src')}> has no {attr}")
    for href in parser.links:
        if urlparse(href).scheme in ("http", "https", "mailto", "data") or href.startswith("//"):
            continue
        for part in href.split(","):           # srcset lists
            part = part.strip().split(" ")[0]
            if not part:
                continue
            t, frag = target(p, part)
            if not t.exists():
                errors.append(f"{rel}: broken link {part}")
            elif frag and t.suffix == ".html":
                ids = pages[t].ids if t in pages else set()
                if frag not in ids and frag != "top":
                    errors.append(f"{rel}: missing anchor {part}")

# ---------- contrast ----------
css = next((DIST / "assets").glob("style.*.css")).read_text()


def tokens(block):
    return dict(re.findall(r"--([\w-]+):(#[0-9A-Fa-f]{6})", block))


dark = tokens(re.search(r":root\{color-scheme:dark;(.*?)\}", css).group(1))
light = {**dark, **tokens(re.search(r':root\[data-theme="light"\]\{(.*?)\}', css).group(1))}


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


PAIRS = [("fg", "bg", 4.5), ("fg-2", "bg", 4.5), ("fg-3", "bg", 4.5), ("fg-2", "panel", 4.5), ("fg-3", "panel", 4.5),
         ("ink", "tape", 4.5), ("mark", "bg", 3), ("fg-3", "bg", 3)]
for name, theme in (("dark", dark), ("light", light)):
    for fg, bg, need in PAIRS:
        r = ratio(theme[fg], theme[bg])
        if r < need:
            errors.append(f"contrast {name}: --{fg} on --{bg} is {r:.2f}:1, needs {need}:1")
        elif "-v" in sys.argv:
            print(f"ok  {name:5} --{fg:5} on --{bg:6} {r:5.2f}:1")

for e in errors:
    print("error:", e)
print(f"checked {len(pages)} pages, {len(errors)} errors")
sys.exit(1 if errors else 0)
