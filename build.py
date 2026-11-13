#!/usr/bin/env python3
"""Build the portfolio from src/ into dist/.

    python3 build.py            build dist/
    python3 build.py --cv       also write the CV pages to build-cv/ (see tools/make-cv.mjs)

German pages are written to /, English pages to /en/, both from the same
source file. Every element with data-en="..." gets that text in the English
version. Needs Python 3.10+, Pillow, fontTools and brotli
(pip install -r requirements.txt).
"""
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import brotli
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
SITE = json.loads((SRC / "site.json").read_text(encoding="utf-8"))
BASE = SITE["base_url"].rstrip("/")
LANGS = ("de", "en")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
WARNINGS = []

MONTHS = {
    "de": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sept.", "Okt.", "Nov.", "Dez."],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

# Words in the other language, marked with lang="..." so screen readers pronounce them right.
FOREIGN = {
    "de": ["Single Sign-on", "Reverse Proxy", "Best Practices", "Open Source", "Identity Provider"],
    "en": ["Informatiker EFZ", "Fachrichtung Plattformentwicklung", "Technische Fachschule Bern",
           "Technischen Fachschule Bern", "Netzwächter"],
}

T = {  # interface strings that are not part of any page source
    "skip": ("Zum Inhalt springen", "Skip to content"),
    "nav": ("Navigation", "Navigation"),
    "projects": ("Projekte", "Projects"),
    "about": ("Über mich", "About me"),
    "path": ("Werdegang", "So far"),
    "contact": ("Kontakt", "Contact"),
    "lang": ("Sprache", "Language"),
    "theme": ("Farbschema wechseln", "Switch colour scheme"),
    "top": ("Nach oben", "Back to top"),
    "selfhosted": ("Selbst gehostet in der Schweiz, in der DMZ meines Homelabs",
                   "Self-hosted in Switzerland, in the DMZ of my homelab"),
    "updated": ("Zuletzt aktualisiert", "Last updated"),
    "privacy": ("Impressum und Datenschutz", "Imprint and privacy"),
    "prev": ("Vorheriges Projekt", "Previous project"),
    "next": ("Nächstes Projekt", "Next project"),
    "all": ("Alle Projekte", "All projects"),
    "crumb": ("Seitenpfad", "Breadcrumb"),
    "more": ("Weitere Projekte", "More projects"),
    "toc": ("Auf dieser Seite", "On this page"),
    "anchor": ("Link zu diesem Abschnitt", "Link to this section"),
    "lastlab": ("Zuletzt im Lab", "Latest in the lab"),
    "mail_btn": ("E-Mail schreiben", "Write an e-mail"),
    "at": ("[at]", "[at]"),
    "job": ("Informatiker EFZ in Ausbildung", "Apprentice IT specialist (Informatiker EFZ)"),
}


def t(key, lang):
    return T[key][LANGS.index(lang)]


def esc(s):
    return html.escape(s, quote=True)


def fmt_date(iso, lang):
    d = dt.date.fromisoformat(iso)
    m = MONTHS[lang][d.month - 1]
    return f"{d.day}. {m} {d.year}" if lang == "de" else f"{d.day} {m} {d.year}"


def digest(data):
    return hashlib.sha256(data).hexdigest()[:10]


def slugify(text):
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


# --------------------------------------------------------------------------
# Language: one source, two outputs
# --------------------------------------------------------------------------
class Localize(HTMLParser):
    """Rewrites a fragment for one language and strips the data-en attributes."""

    def __init__(self, lang):
        super().__init__(convert_charrefs=False)
        self.lang, self.out, self.skip = lang, [], []

    def tag(self, tag, attrs, close=""):
        attrs = dict(attrs)
        en = attrs.pop("data-en", None)
        alt_en = attrs.pop("data-alt-en", None)
        if self.lang == "en" and alt_en is not None:
            attrs["alt"] = html.unescape(alt_en)
        parts = [tag] + [k if v is None else f'{k}="{esc(html.unescape(v))}"' for k, v in attrs.items()]
        self.out.append("<" + " ".join(parts) + close + ">")
        return en

    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag == self.skip[-1][0] and tag not in VOID:
                self.skip[-1][1] += 1
            return
        en = self.tag(tag, attrs)
        if en is not None and self.lang == "en" and tag not in VOID:
            self.out.append(html.unescape(en) if "&lt;" in en or "&gt;" in en else en)
            self.skip.append([tag, 1])

    def handle_startendtag(self, tag, attrs):
        if not self.skip:
            self.tag(tag, attrs)

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1][0]:
                self.skip[-1][1] -= 1
                if self.skip[-1][1] == 0:
                    self.skip.pop()
                    self.out.append(f"</{tag}>")
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)

    def handle_entityref(self, n):
        if not self.skip:
            self.out.append(f"&{n};")

    def handle_charref(self, n):
        if not self.skip:
            self.out.append(f"&#{n};")

    def handle_comment(self, d):
        if not self.skip:
            self.out.append(f"<!--{d}-->")


def localize(fragment, lang):
    p = Localize(lang)
    p.feed(fragment)
    p.close()
    return "".join(p.out)


def mark_foreign(body, lang):
    other = "en" if lang == "de" else "de"
    for term in FOREIGN[lang]:
        # only in text between tags, never inside attributes or existing lang spans
        body = re.sub(r">([^<]*?)(?<![\w-])(" + re.escape(term) + r")(?![\w-])",
                      lambda m: f'>{m.group(1)}<span lang="{other}">{m.group(2)}</span>', body)
    return body


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------
class Assets:
    def __init__(self):
        self.map = {}       # logical name -> published path ("/assets/…")
        self.images = {}    # source image name -> dict(width, height, variants)

    def put(self, logical, data, ext):
        stem = Path(logical).stem
        name = f"assets/{Path(logical).parent.as_posix() + '/' if Path(logical).parent.as_posix() != '.' else ''}{stem}.{digest(data)}.{ext}"
        out = DIST / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        self.map[logical] = "/" + name
        return "/" + name

    def build_images(self):
        for src in sorted((SRC / "assets/img").glob("*.webp")):
            im = Image.open(src)
            w, h = im.size
            widths = sorted({x for x in (480, 800, 1200) if x < w} | {w})
            variants = {"avif": [], "webp": []}
            for width in widths:
                r = im if width == w else im.resize((width, round(h * width / w)), Image.LANCZOS)
                for fmt in ("avif", "webp"):
                    buf = io.BytesIO()
                    r.save(buf, fmt.upper(), quality=62 if fmt == "avif" else 80)
                    path = self.put(f"img/{src.stem}-{width}.{fmt}", buf.getvalue(), fmt)
                    variants[fmt].append((path, width))
            self.images[src.name] = {"width": w, "height": h, "variants": variants}


def picture(m, assets, first_image):
    attrs = dict(re.findall(r'([\w-]+)(?:="([^"]*)")?', m.group(1)))
    name = Path(attrs.pop("src")).name
    info = assets.images.get(name)
    if not info:
        WARNINGS.append(f"no image data for {name}")
        return m.group(0)
    sizes = attrs.pop("data-sizes", "(max-width: 820px) 100vw, 760px")
    priority = "data-priority" in attrs
    attrs.pop("data-priority", None)
    attrs.pop("loading", None)
    attrs.pop("width", None)
    attrs.pop("height", None)
    v = info["variants"]
    srcset = lambda fmt: ", ".join(f"{p} {w}w" for p, w in v[fmt])
    largest = v["webp"][-1][0]
    extra = ' fetchpriority="high" loading="eager"' if priority else ' loading="lazy" decoding="async"'
    rest = " ".join(f'{k}="{val}"' for k, val in attrs.items())
    return (f'<picture><source type="image/avif" srcset="{srcset("avif")}" sizes="{sizes}">'
            f'<img src="{largest}" srcset="{srcset("webp")}" sizes="{sizes}" width="{info["width"]}" '
            f'height="{info["height"]}" {rest}{extra}></picture>')


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    return css.replace(";}", "}").strip()


def minify_js(js):
    out = []
    for line in js.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        out.append(s)
    return "\n".join(out)


def font_instance(wght, wdth):
    f = TTFont(SRC / "assets/fonts/archivo-variable.woff2")
    inst = instancer.instantiateVariableFont(f, {"wght": wght, "wdth": wdth})
    buf = io.BytesIO()
    inst.flavor = None
    inst.save(buf)
    buf.seek(0)
    return buf


def subset_font(text):
    chars = set(text) | set(" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
                            "ÄÖÜäöüßéèàçâêëïîôûÉÈÀ«»–—‘’“”„…·×©°↑")
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "tnum", "lnum"]
    opts.name_IDs = [1, 2]
    opts.notdef_outline = True
    f = TTFont(SRC / "assets/fonts/archivo-variable.woff2")
    s = subset.Subsetter(opts)
    s.populate(unicodes=[ord(c) for c in chars if ord(c) > 31])
    s.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    return buf.getvalue()


def fallback_metrics():
    """size-adjust and overrides so Arial/Liberation Sans takes the same space as Archivo."""
    sample = "Netzwerke, Server, Betrieb. Ich arbeite im Netzwerkbereich und betreibe ein Homelab."
    arch = ImageFont.truetype(font_instance(400, 100), 1000)
    ref = None
    for cand in ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "Arial.ttf"):
        try:
            ref = ImageFont.truetype(cand, 1000)
            break
        except OSError:
            continue
    ratio = arch.getlength(sample) / ref.getlength(sample) if ref else 1.1
    f = TTFont(SRC / "assets/fonts/archivo-variable.woff2")
    upm, asc, desc = f["head"].unitsPerEm, f["hhea"].ascent, -f["hhea"].descent
    return {"size": ratio * 100, "ascent": asc / upm / ratio * 100, "descent": desc / upm / ratio * 100}


def og_image(title, sub, lang, fonts):
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), "#141413")
    d = ImageDraw.Draw(im)
    big, small, label = fonts
    d.rectangle([80, 80, 80 + d.textlength("server-lukas.com", font=label) + 28, 80 + 46], fill="#F5C518")
    d.text((94, 88), "server-lukas.com", font=label, fill="#141413")
    # wrap the title to the width
    words, lines, line = title.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if d.textlength(test, font=big) > W - 160 and line:
            lines.append(line)
            line = w
        else:
            line = test
    lines.append(line)
    y = H - 110 - len(lines) * 96
    for ln in lines:
        d.text((80, y), ln, font=big, fill="#F1EFE8")
        y += 96
    d.text((80, H - 92), sub, font=small, fill="#BDBAB0")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def icons(assets):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#F5C518"/>'
           '<rect x="12" y="40" width="40" height="6" fill="#141413"/><rect x="12" y="18" width="6" height="22" fill="#141413"/>'
           '<rect x="28" y="18" width="6" height="22" fill="#141413"/><rect x="34" y="18" width="12" height="6" fill="#141413"/>'
           '<rect x="34" y="34" width="12" height="6" fill="#141413"/><rect x="46" y="22" width="6" height="14" fill="#141413"/></svg>')
    (DIST / "favicon.svg").write_text(svg)
    im = Image.new("RGB", (180, 180), "#F5C518")
    d = ImageDraw.Draw(im)
    s = 180 / 64
    for x, y, w, h in ((12, 40, 40, 6), (12, 18, 6, 22), (28, 18, 6, 22), (34, 18, 12, 6), (34, 34, 12, 6), (46, 22, 6, 14)):
        d.rectangle([x * s, y * s, (x + w) * s - 1, (y + h) * s - 1], fill="#141413")
    im.save(DIST / "apple-touch-icon.png", optimize=True)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def load_pages():
    pages = []
    for f in sorted((SRC / "pages").rglob("*.html")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"<!--meta\n(.*?)\n-->\n", raw, re.S)
        meta = json.loads(m.group(1))
        meta["rel"] = f.relative_to(SRC / "pages").as_posix()
        meta["body"] = raw[m.end():]
        pages.append(meta)
    return pages


def url_for(rel, lang):
    path = "" if rel == "index.html" else rel
    return f"/{path}" if lang == "de" else f"/en/{path}"


def git_date():
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip() or dt.date.today().isoformat()
    except (OSError, subprocess.CalledProcessError):
        return dt.date.today().isoformat()


def mail(kind, lang):
    u, d = SITE["email_user"], SITE["email_domain"]
    shown = f"{u} {t('at', lang)} {d}"
    if kind == "big":
        return f'<a class="big mail" href="#contact" data-u="{u}" data-d="{d}">{shown}</a>'
    if kind == "inline":
        return f'<a class="mail" href="#" data-u="{u}" data-d="{d}">{shown}</a>'
    return f'<a class="btn mail" href="#contact" data-u="{u}" data-d="{d}" data-label>{t("mail_btn", lang)}</a>'


def changelog(lang):
    items = "".join(f'\n          <li><time datetime="{c["date"]}">{fmt_date(c["date"], lang)}</time><span>{esc(c[lang])}</span></li>'
                    for c in SITE["changelog"])
    return f'<ol class="log">{items}\n        </ol>'


def section_ids(body, lang):
    """Readable ids for case-study sections, plus a link icon on each heading."""
    ids = {}

    def repl(m):
        attrs, inner = m.group(1), m.group(2)
        old = re.search(r'id="([^"]+)"', attrs)
        new = slugify(inner)
        if old:
            ids[old.group(1)] = new
        return (f'<h2 id="{new}">{inner}<a class="anchor" href="#{new}" '
                f'aria-label="{t("anchor", lang)}"><span aria-hidden="true">#</span></a></h2>')

    body = re.sub(r"<h2((?: [^>]*)?)>(.*?)</h2>", repl, body)
    for old, new in ids.items():
        body = body.replace(f'aria-labelledby="{old}"', f'aria-labelledby="{new}"')
    return body


def toc(body, lang):
    heads = re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)<a class="anchor"', body)
    items = "".join(f'<li><a href="#{i}">{txt}</a></li>' for i, txt in heads)
    return f'<nav class="toc" aria-label="{t("toc", lang)}"><h2 class="toc-h">{t("toc", lang)}</h2><ol>{items}</ol></nav>'


def project_nav(page, projects, lang, where):
    i = projects.index(page)
    prev = projects[i - 1] if i > 0 else None
    nxt = projects[i + 1] if i + 1 < len(projects) else None
    home = url_for("index.html", lang) + "#projects"
    short = lambda p: esc(p[f"short_{lang}"])
    href = lambda p: url_for(p["rel"], lang)
    if where == "top":
        links = []
        if prev:
            links.append(f'<a href="{href(prev)}" rel="prev"><span class="vh">{t("prev", lang)}: </span>← {short(prev)}</a>')
        if nxt:
            links.append(f'<a href="{href(nxt)}" rel="next"><span class="vh">{t("next", lang)}: </span>{short(nxt)} →</a>')
        return (f'<div class="crumbs"><nav aria-label="{t("crumb", lang)}"><ol class="crumb">'
                f'<li><a href="{home}">{t("projects", lang)}</a></li>'
                f'<li><a href="{href(page)}" aria-current="page">{short(page)}</a></li></ol></nav>'
                f'<div class="pager">{"".join(links)}</div></div>')
    left = (f'<a href="{href(prev)}" rel="prev"><small>{t("prev", lang)}</small>{short(prev)}</a>' if prev
            else f'<a href="{home}"><small>{t("all", lang)}</small>{t("projects", lang)}</a>')
    right = (f'<a class="right" href="{href(nxt)}" rel="next"><small>{t("next", lang)}</small>{short(nxt)}</a>' if nxt
             else f'<a class="right" href="{home}"><small>{t("all", lang)}</small>{t("projects", lang)}</a>')
    return f'<nav class="next" aria-label="{t("more", lang)}">{left}{right}</nav>'


def json_ld(page, lang):
    person = {"@type": "Person", "name": SITE["name"], "url": BASE + "/", "jobTitle": t("job", lang),
              "sameAs": [SITE["github"]], "knowsLanguage": ["de", "en"],
              "address": {"@type": "PostalAddress", "addressCountry": "CH"}}
    if page["type"] == "home":
        data = {"@context": "https://schema.org", **person}
    elif page["type"] == "project":
        data = {"@context": "https://schema.org", "@type": page.get("schema", "CreativeWork"),
                "name": page[f"short_{lang}"], "description": page[f"desc_{lang}"], "inLanguage": lang,
                "url": BASE + url_for(page["rel"], lang), "author": person}
        if page.get("repo"):
            data["codeRepository"] = page["repo"]
    else:
        return ""
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>\n'


def header(page, lang):
    home = url_for("index.html", lang)
    pre = "" if page["type"] == "home" else home
    cur = ' aria-current="true"' if page["type"] == "project" else ""
    langs = (f'<a href="{url_for(page["rel"], "de")}" hreflang="de" lang="de"{" aria-current=\"true\"" if lang == "de" else ""}>DE<span class="vh"> Deutsch</span></a>'
             f'<a href="{url_for(page["rel"], "en")}" hreflang="en" lang="en"{" aria-current=\"true\"" if lang == "en" else ""}>EN<span class="vh"> English</span></a>')
    return f'''<a class="skip" href="#main">{t("skip", lang)}</a>
<div class="bar" id="bar">
  <div class="page"><header class="top">
    <a class="brand" href="{home}">Lukas Dalloz</a>
    <div class="right">
      <nav class="mainnav" aria-label="{t("nav", lang)}">
        <a href="{pre}#projects"{cur}>{t("projects", lang)}</a>
        <a href="{pre}#about">{t("about", lang)}</a>
        <a href="{pre}#path">{t("path", lang)}</a>
        <a href="{pre}#contact">{t("contact", lang)}</a>
      </nav>
      <div class="tools">
        <div class="lang" role="group" aria-label="{t("lang", lang)}">{langs}</div>
        <button type="button" class="theme" id="theme" aria-label="{t("theme", lang)}" title="{t("theme", lang)}"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z"/></svg></button>
      </div>
    </div>
  </header></div>
</div>'''


def footer(lang, updated):
    privacy = url_for("datenschutz.html", lang)
    return f'''<footer>
  <div class="page">
    <p class="note"><span class="ch" aria-hidden="true"></span><span>{t("selfhosted", lang)}</span></p>
    <p class="meta"><span>&copy; {updated[:4]} {SITE["name"]}</span><span>{t("updated", lang)}: <time datetime="{updated}">{fmt_date(updated, lang)}</time></span><a href="{privacy}">{t("privacy", lang)}</a><a href="#top">{t("top", lang)}</a></p>
  </div>
</footer>'''


def head(page, lang, css, js_theme):
    title = page[f"title_{lang}"]
    desc = page[f"desc_{lang}"]
    canonical = BASE + url_for(page["rel"], lang)
    if len(title) > 60:
        WARNINGS.append(f"title over 60 characters: {title}")
    noindex = page.get("noindex")
    alts = "" if noindex else "".join(
        f'<link rel="alternate" hreflang="{l}" href="{BASE + url_for(page["rel"], l)}">\n' for l in LANGS
    ) + f'<link rel="alternate" hreflang="x-default" href="{BASE + url_for(page["rel"], "de")}">\n'
    og = f'{BASE}/og/{lang}-{page["slug"]}.png'
    verify = ""
    if SITE.get("google_site_verification") and page["type"] == "home":
        verify += f'<meta name="google-site-verification" content="{esc(SITE["google_site_verification"])}">\n'
    if SITE.get("bing_site_verification") and page["type"] == "home":
        verify += f'<meta name="msvalidate.01" content="{esc(SITE["bing_site_verification"])}">\n'
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{'<meta name="robots" content="noindex">' + chr(10) if noindex else ''}<link rel="canonical" href="{canonical}">
{alts}<meta property="og:type" content="{'profile' if page['type'] == 'home' else 'article' if page['type'] == 'project' else 'website'}">
<meta property="og:site_name" content="{SITE['name']}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{'de_CH' if lang == 'de' else 'en_GB'}">
<meta property="og:locale:alternate" content="{'en_GB' if lang == 'de' else 'de_CH'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#141413" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#F4F4F1" media="(prefers-color-scheme: light)">
{verify}<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="__FONT__" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{css}">
<script src="{js_theme}"></script>
__SCRIPTS__
{json_ld(page, lang)}</head>'''


def render(page, lang, projects, updated):
    body = localize(page["body"], lang)
    body = mark_foreign(body, lang)
    for key in ("looking_for", "geoguessr_detail"):
        val = SITE.get(f"{key}_{lang}", "").strip()
        body = body.replace(f"<!--opt:{key}-->", f'<p class="{key.replace("_", "-")}">{esc(val)}</p>' if val else "")
    body = body.replace("<!--mail:big-->", mail("big", lang)).replace("<!--mail:btn-->", mail("btn", lang)).replace("<!--mail:inline-->", mail("inline", lang))
    body = body.replace("<!--changelog-->", changelog(lang))
    if SITE["changelog"]:
        c = SITE["changelog"][0]
        body = body.replace("<!--latest-change-->",
                            f'{t("lastlab", lang)}, <time datetime="{c["date"]}">{fmt_date(c["date"], lang)}</time>: {esc(c[lang])}')
    # links inside the source are written for the German tree; the English tree mirrors it
    body = re.sub(r'href="(\.\./)?index\.html(#[^"]*)?"', lambda m: f'href="{url_for("index.html", lang)}{m.group(2) or ""}"', body)
    body = re.sub(r'href="(?:\.\./)?projekte/([\w-]+\.html)"', lambda m: f'href="{url_for("projekte/" + m.group(1), lang)}"', body)
    body = re.sub(r'href="([\w-]+\.html)"', lambda m: f'href="{url_for("projekte/" + m.group(1), lang)}"' if page["type"] == "project" else m.group(0), body)
    if lang == "en":
        body = body.replace('href="/cv/lebenslauf-lukas-dalloz.pdf">CV (PDF)', 'href="/cv/cv-lukas-dalloz-en.pdf">CV (PDF)')
    if page["type"] == "project":
        body = section_ids(body, lang)
        top = project_nav(page, projects, lang, "top")
        body = body.replace('<div class="case-hero">', top + '\n  <div class="case-hero">', 1)
        if page.get("toc"):
            i = body.index("</div>", body.index("</dl>", body.index('<div class="case-hero">'))) + len("</div>")
            body = body[:i] + "\n\n  " + toc(body, lang) + body[i:]
        i = body.rindex("</div>")
        body = body[:i] + "  " + project_nav(page, projects, lang, "bottom") + "\n  " + body[i:]
    return body


def page_html(page, lang, body, assets, updated, scripts):
    first = [True]
    body = re.sub(r'<img ([^>]*\bsrc="(?:\.\./)?assets/img/[^"]+"[^>]*)>',
                  lambda m: picture(m, assets, first), body)
    scripts_html = "".join(f'<script src="{s}" defer></script>\n' for s in scripts)
    doc = (head(page, lang, assets.map["style.css"], assets.map["js/theme.js"]).replace("__SCRIPTS__\n", scripts_html)
           + f'\n<body class="{page["type"]}">\n' + header(page, lang)
           + f'\n<div class="page" id="top">\n<main id="main">\n{body}</main>\n</div>\n' + footer(lang, updated)
           + "\n</body>\n</html>\n")
    return doc


def write(path, text):
    p = DIST / path.lstrip("/")
    if p.suffix == "" or str(path).endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def compress():
    for f in DIST.rglob("*"):
        if f.suffix in {".html", ".css", ".js", ".svg", ".xml", ".txt", ".json"} and f.is_file():
            data = f.read_bytes()
            (f.parent / (f.name + ".gz")).write_bytes(gzip.compress(data, 9, mtime=0))
            (f.parent / (f.name + ".br")).write_bytes(brotli.compress(data, quality=11))


def main():
    cv = "--cv" in sys.argv
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    updated = git_date()
    pages = load_pages()
    projects = sorted([p for p in pages if p["type"] == "project"], key=lambda p: p["order"])

    assets = Assets()
    assets.build_images()
    for js in ("theme.js", "site.js", "homelab.js"):
        assets.put(f"js/{js}", minify_js((SRC / "assets/js" / js).read_text(encoding="utf-8")).encode(), "js")

    # first pass: render bodies to learn which characters the font needs
    bodies = {(p["rel"], l): render(p, l, projects, updated) for p in pages for l in LANGS}
    chrome = "".join(header(p, l) + footer(l, updated) for p in pages for l in LANGS) + "".join(v for pair in T.values() for v in pair)
    text = html.unescape(re.sub(r"<[^>]+>", " ", "".join(bodies.values()) + chrome))
    font = assets.put("fonts/archivo.woff2", subset_font(text), "woff2")

    m = fallback_metrics()
    css = (SRC / "assets/style.css").read_text(encoding="utf-8")
    css = css.replace("__FONT__", font)
    css = css.replace("__SIZE_ADJUST__", f"{m['size']:.2f}%").replace("__ASCENT__", f"{m['ascent']:.2f}%").replace("__DESCENT__", f"{m['descent']:.2f}%")
    assets.put("style.css", minify_css(css).encode(), "css")

    big = ImageFont.truetype(font_instance(800, 112), 84)
    small = ImageFont.truetype(font_instance(400, 100), 30)
    label = ImageFont.truetype(font_instance(700, 100), 26)
    (DIST / "og").mkdir()
    for p in pages:
        for l in LANGS:
            title = p.get(f"og_{l}") or p.get(f"short_{l}") or p[f"title_{l}"]
            (DIST / "og" / f"{l}-{p['slug']}.png").write_bytes(og_image(title, f"{SITE['name']}, {t('job', l)}", l, (big, small, label)))
    icons(assets)

    for p in pages:
        for l in LANGS:
            scripts = [assets.map["js/site.js"]] + ([assets.map["js/homelab.js"]] if p.get("slug") == "homelab" else [])
            doc = page_html(p, l, bodies[(p["rel"], l)], assets, updated, scripts).replace("__FONT__", font)
            write(url_for(p["rel"], l), doc)

    # CV PDFs, published under stable names so links can be shared
    cvdir = SRC / "assets/cv"
    if cvdir.exists():
        (DIST / "cv").mkdir()
        for pdf in cvdir.glob("*.pdf"):
            shutil.copy(pdf, DIST / "cv" / pdf.name)

    sitemap(pages, updated)
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /404.html\nDisallow: /en/404.html\n\nSitemap: {BASE}/sitemap.xml\n")
    expires = (dt.date.today() + dt.timedelta(days=330)).isoformat()
    (DIST / ".well-known").mkdir()
    (DIST / ".well-known/security.txt").write_text(
        f"Contact: mailto:{SITE['email_user']}@{SITE['email_domain']}\nExpires: {expires}T00:00:00.000Z\n"
        f"Preferred-Languages: de, en\nCanonical: {BASE}/.well-known/security.txt\n")
    compress()

    if cv:
        cv_pages(updated)
    for w in WARNINGS:
        print("warning:", w)
    print(f"built {sum(1 for _ in DIST.rglob('*.html'))} pages into {DIST.relative_to(ROOT)}/")


def sitemap(pages, updated):
    rows = []
    for p in pages:
        if p.get("noindex"):
            continue
        for l in LANGS:
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{a}" href="{BASE + url_for(p["rel"], a)}"/>' for a in LANGS)
            rows.append(f"<url><loc>{BASE + url_for(p['rel'], l)}</loc><lastmod>{updated}</lastmod>{alts}</url>")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")


def cv_pages(updated):
    """Plain HTML versions of the CV, turned into PDFs by tools/make-cv.mjs."""
    out = ROOT / "build-cv"
    out.mkdir(exist_ok=True)
    tpl = (ROOT / "tools/cv.html").read_text(encoding="utf-8")
    font = next((DIST / "assets/fonts").glob("*.woff2"))
    for l in LANGS:
        doc = localize(tpl, l).replace("__FONT__", font.as_uri()).replace("__UPDATED__", fmt_date(updated, l))
        doc = doc.replace("__MAIL__", f"{SITE['email_user']}@{SITE['email_domain']}")
        (out / f"cv-{l}.html").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    main()
