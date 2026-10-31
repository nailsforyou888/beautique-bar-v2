#!/usr/bin/env python3
"""Beautique Bar — Opus site generator.

Builds every inner page of the Opus preview into ../opus-design-v1/ at the SAME paths as the
live beautiquebar.com site (folder/index.html, so Cloudflare Pages serves /path/ and redirects
/path -> /path/ exactly like the live site). The homepage (index.html) stays hand-authored;
this script only refreshes its shared header, footer and booking dialog.

Facts come from the live site's own content files (copied into this folder):
  ../content/menus/*.yml -> location price menus; ../content/salons.yml -> phones, emails, booking links, hours (Pages CMS)
  blog/*.md              -> the 17 blog articles
Every price shown on a service page is looked up by exact name in those menus, so no price can be invented.
If the owner renames or removes a service in Pages CMS, that line is left off the service-page teaser and the
publish log shows a warning; the full salon menu always shows exactly what is in the menu file.
"""
import html, json, os, re, shutil, datetime
from pathlib import Path
import markdown

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / 'opus-design-v1'
VERSION = '11'
e = html.escape
CUR = ' aria-current="page"'
LAZY = ' loading="lazy"'
EAGER = ' fetchpriority="high"'
def idattr(r):
    return f' id="{r[2]}"' if len(r) > 2 and r[2] else ''

from site_config import *   # LOC, HOURS, EMAILS, socials, SITE_URL, GTM_ID … (single source of truth)

def _t(hm):
    h = int(hm[:2]); return f'{h % 12 or 12} {"am" if h < 12 else "pm"}'
def hours_rows(k):
    return [(d, f'{_t(o)} – {_t(c)}') for d, _, o, c in HOURS[k]]
def hours_inline(k):
    return ' · '.join(f'{d} {t}' for d, t in hours_rows(k))
def hours_dl(k):
    return '<ul class="hours">' + ''.join(f'<li><span>{d}</span><span>{t}</span></li>' for d, t in hours_rows(k)) + '</ul>'

PHOTO_BRIEF = {'yonge': 'REAL — owner photo, colour-corrected.',
               'warden': 'REAL — owner photo, Bridlewood interior.'}
REVIEWS_URL = 'https://www.google.com/search?q=Beautique+Bar+Toronto+reviews'

# ----------------------------------------------------------------------------------------------
# Menus — parsed from the live location pages
TYPO_FIXES = {'Bio Bel Full Set w/ Tips': 'Bio Gel Full Set w/ Tips'}   # flagged for review
PRICE = re.compile(r'^\$\d')

def parse_menu(md_text):
    body = md_text.split('---', 2)[2]
    body = body.split('## clients.')[0]
    cats, cur, pending = [], None, None
    for raw in body.splitlines():
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line or line.startswith('!['):
            continue
        if line.startswith('## '):
            title = line[3:].strip()
            if title == 'Add-on Services' and cats:
                cur = {'title': 'Add-ons', 'items': []}
                cats[-1].setdefault('subs', []).append(cur)
            else:
                cur = {'title': title, 'items': []}
                cats.append(cur)
            pending = None
            continue
        if line.startswith('**'):          # promo labels ("New Service", "Monthly Special Pedicure")
            pending = None
            continue
        if PRICE.match(line):
            if pending:
                cur['items'].append({'name': pending, 'price': line})
                pending = None
            continue
        if pending:                          # previous name had no price -> dropped (flagged)
            pass
        pending = TYPO_FIXES.get(line, line)
    return cats

DISCONTINUED = ('Piercing',)   # owner, 23 Sep 2026: piercing and tattoo services no longer offered
def load_menu(k):
    """Price menus live in /content/menus/<salon>.yml (edited in Pages CMS). Same shape the pages always used."""
    import yaml
    f = SRC.parent / 'content' / 'menus' / f'{k}.yml'
    data = yaml.safe_load(f.read_text()) or {}
    cats = []
    for c in data.get('categories') or []:
        title = str(c.get('title') or '').strip()
        if not title or any(d in title for d in DISCONTINUED):
            continue
        def rows(lst):
            out = []
            for i in lst or []:
                name, pr = str(i.get('name') or '').strip(), str(i.get('price') or '').strip()
                if not name:
                    continue
                if pr and not pr.startswith('$'):
                    pr = '$' + pr
                out.append({'name': name, 'price': pr})
            return out
        cat = {'title': title, 'items': rows(c.get('items'))}
        if c.get('addons'):
            cat['subs'] = [{'title': 'Add-ons', 'items': rows(c['addons'])}]
        cats.append(cat)
    if not cats:
        raise SystemExit(f'content/menus/{k}.yml has no categories')
    return cats

MENUS = {k: load_menu(k) for k in LOC}
WARNINGS = []   # shown in the GitHub publish log; never block a price edit

def all_items(loc):
    for c in MENUS[loc]:
        yield from c['items']
        for s in c.get('subs', []):
            yield from s['items']

def price(loc, name):
    for it in all_items(loc):
        if it['name'] == name:
            return it['price']
    WARNINGS.append(f'Service page teaser: "{name}" is no longer on the {LOC[loc]["name"]} menu, so it was left off that list (full menu is unaffected).')
    return None

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ----------------------------------------------------------------------------------------------
# Reviews — verbatim from the live site (src/data/reviews.ts)
REV = {
  'sangeetha': ('I’ve had my nails done here for almost two decades. The quality and care keep me coming back.', 'Sangeetha J'),
  'samantha': ('Just had a pedicure done by Michelle and it was absolutely perfect. So relaxing and so clean.', 'Samantha C'),
  'julia': ('I love this nail salon! Hanna is a true artist — my acrylics always look incredible.', 'Julia Brown'),
  'danielle': ('Iris did an amazing job rebuilding three of my broken nails. They look completely natural.', 'Danielle Kalaidjian'),
  'valerie': ('The space is beautiful, classy and clean, and the staff are so welcoming. A lovely experience every time.', 'Valerie'),
}

# Google rating shown beside each salon's Book buttons — copied from the live Google listings, 21 Oct 2026. Update every few months.
RATING = {'yonge': ('4.8', 268, 'Beautique+Bar+on+Yonge+reviews'), 'warden': ('4.3', 568, 'Beautique+Bar+Bridlewood+Mall+reviews')}
LOC_REVIEW = {'yonge': 'samantha', 'warden': 'sangeetha'}   # which REV quote sits beside each salon's Book buttons (owner to confirm)

def proof(k):
    r, n, q = RATING[k]
    t, who = REV[LOC_REVIEW[k]]
    return f'''<p class="proof"><a href="https://www.google.com/search?q={q}" target="_blank" rel="noopener"><span aria-hidden="true">★</span> {r} from {n} Google reviews</a>
  <span class="pf-q">“{e(t)}” — {e(who)}</span></p>'''

# ----------------------------------------------------------------------------------------------
# Blog
def load_posts():
    posts = []
    for f in sorted((SRC / 'blog').glob('*.md')):
        raw = f.read_text()
        _, fm, body = raw.split('---', 2)
        import yaml
        meta = yaml.safe_load(fm) or {}
        if meta.get('draft'):
            continue
        d = meta.get('pubDate')
        d = d if isinstance(d, datetime.date) else datetime.date.fromisoformat(str(d)[:10])
        if isinstance(d, datetime.datetime):
            d = d.date()
        posts.append(dict(slug=f.stem, title=str(meta['title']), seo_title=str(meta.get('seoTitle') or ''), desc=str(meta.get('description') or ''),
                          date=d, cat=str(meta.get('category') or ''), body=body))
    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts

POSTS = load_posts()
PBY = {p['slug']: p for p in POSTS}

PRICE_NOTE = ('<aside class="note" role="note"><p class="eyebrow">Beautique Bar prices</p><p>General industry price ranges from '
              'the original article have been removed. For current prices, see the '
              '<a href="/locations/yonge/#menu">Yonge &amp; York Mills menu</a> or the '
              '<a href="/locations/warden/#menu">Bridlewood Mall menu</a>.</p></aside>')
POST_NOTES = {
  'full-body-laser-hair-removal-costs': '<aside class="note" role="note"><p class="eyebrow">Please note</p><p>Laser hair removal is not on either Beautique Bar menu. '
      'Our salons offer waxing, and threading at Yonge &amp; York Mills — see <a href="/skin/body-hair-removal/">Body hair removal</a>.</p></aside>',
  'facial-hair-growth': '<aside class="note" role="note"><p class="eyebrow">Please note</p><p>This article covers several hair-removal methods. Beautique Bar offers waxing at both salons and threading at Yonge &amp; York Mills — see <a href="/skin/facial-hair-removal/">Facial hair removal</a>.</p></aside>',
}
AUDIT = {}   # slug -> list of review notes (written to SITE-REVIEW.md)

def strip_prices(slug_, body):
    removed = 0
    out_lines = []
    for line in body.splitlines():
        if re.search(r'\$\d', line):
            if re.match(r'\s*([-*]|\d+\.)\s', line):
                removed += 1
                continue
            sents = re.split(r'(?<=[.!?])\s+', line)
            keep = [s for s in sents if not re.search(r'\$\d', s)]
            removed += len(sents) - len(keep)
            line = ' '.join(keep)
            if not line.strip():
                continue
        out_lines.append(line)
    # drop lead-in lines ("Average Cost Ranges:") whose list was removed entirely
    cleaned = []
    for idx, line in enumerate(out_lines):
        if line.strip().strip('*').endswith(':') and not line.lstrip().startswith('#') and removed:
            nxt = next((x for x in out_lines[idx + 1:] if x.strip()), '')
            if not re.match(r'\s*([-*]|\d+\.)\s', nxt):
                continue
        cleaned.append(line)
    out_lines = cleaned
    # drop headings left with no content before the next heading of the same or higher level
    res, i = [], 0
    L = out_lines
    while i < len(L):
        m = re.match(r'^(#{2,4})\s', L[i])
        if m:
            lvl = len(m.group(1)); j = i + 1
            while j < len(L) and not L[j].strip():
                j += 1
            nm = re.match(r'^(#{2,4})\s', L[j]) if j < len(L) else None
            if j >= len(L) or (nm and len(nm.group(1)) <= lvl):
                i = j; continue
        res.append(L[i]); i += 1
    if removed:
        AUDIT.setdefault(slug_, []).append(f'{removed} sentence(s)/list item(s) with generic industry prices removed; replaced by a note linking to the two salon menus.')
    return '\n'.join(res), removed

# ----------------------------------------------------------------------------------------------
# WhatsApp: one number for both salons; every button opens a plain chat and the assistant asks which salon
WA_NUMBER = '16477705232'
WA = f'https://wa.me/{WA_NUMBER}'
WA_ICON = '<svg class="wa-ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91C21.96 6.45 17.5 2 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.22 8.22 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 4.54 0 8.24 3.7 8.24 8.24 0 4.55-3.7 8.24-8.24 8.24Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.13-.15.17-.25.25-.42.08-.16.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.42h-.48c-.17 0-.43.06-.66.31-.23.25-.87.85-.87 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.48-.29Z"/></svg>'

# ----------------------------------------------------------------------------------------------
# Chrome
NAV = [('Nails', '/nails/'), ('Skin & Lashes', '/skin/'), ('Locations', '/locations/')]

def header(active, tone='light'):
    links = ''.join(f'<a href="{h}"{CUR if active == h else ""}>{e(t)}</a>' for t, h in NAV)
    return f'''<header class="site-header" data-bg="{tone}">
  <a class="wordmark" href="/" aria-label="Beautique Bar — home"><span class="lockup" aria-hidden="true"></span></a>
  <nav class="nav" aria-label="Main">{links}</nav>
  <div class="hdr-actions">
    <button class="book-btn" type="button" data-book aria-label="Book Appointment"><span class="bk-full">Book Appointment</span><span class="bk-short" aria-hidden="true">Book</span></button>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu-panel"><span class="menu-lines" aria-hidden="true"></span><span class="menu-label">Menu</span></button>
  </div>
</header>
<div class="menu-panel" id="menu-panel" hidden>
  <nav aria-label="Mobile">
    <ul class="mp-main">{''.join(f'<li><a href="{h}">{e(t)}</a></li>' for t, h in NAV)}</ul>
    <ul class="mp-sub"><li><a href="/gallery/">Gallery</a></li><li><a href="/eyelash-extensions/">Eyelash Extensions</a></li><li><a href="/blog/">Blog</a></li><li><a href="/contact/">Contact</a></li></ul>
    <div class="mp-book"><p class="eyebrow">Book online</p>{''.join(f'<a href="{e(l["book"])}" target="_blank" rel="noopener">{e(l["name"])} <span aria-hidden="true">↗</span></a>' for l in LOC.values())}</div>
    <div class="mp-book mp-wa"><p class="eyebrow">Questions?</p><a href="{WA}" target="_blank" rel="noopener">WhatsApp us <span aria-hidden="true">↗</span></a></div>
  </nav>
</div>'''

def footer(path=None):
    locs = ''.join(f'''<div class="ft-loc"><p class="ft-h"><a href="{l["href"]}">{e(l["name"])}</a></p>
      <p>{e(l["addr"])}</p><p><a href="{l["tel"]}">Call {e(l["phone"])}</a>{f' · Text {e(l["text"])}' if l["text"] != l["phone"] else ' · Call or text'}</p></div>''' for l in LOC.values())
    fab = f'<a class="wa-fab" href="{WA}" target="_blank" rel="noopener" aria-label="Message Beautique Bar on WhatsApp" data-placement="floating-button">{WA_ICON}<span><span class="wa-q">Questions? </span>WhatsApp us</span></a>'
    mbar = f'<div class="m-bar" data-placement="mobile-book-bar"><button type="button" class="m-book" data-book>Book appointment</button><a class="m-wa" href="{WA}" target="_blank" rel="noopener" aria-label="WhatsApp us">{WA_ICON}</a></div>'
    return f'''<footer class="site-footer">
  {fab}{mbar}
  <div class="ft-grid">
    <div class="ft-brand"><a class="ft-lockup" href="/" aria-label="Beautique Bar — home"></a><p>Nails, lashes and skin at Yonge &amp; York Mills and Bridlewood Mall.</p></div>
    <div class="ft-locs">{locs}</div>
    <nav class="ft-nav" aria-label="Footer">
      <ul><li><a href="/nails/">Nails</a></li><li><a href="/skin/">Skin &amp; Lashes</a></li><li><a href="/eyelash-extensions/">Eyelash Extensions</a></li><li><a href="/locations/">Locations</a></li></ul>
      <ul><li><a href="/gallery/">Gallery</a></li><li><a href="/blog/">Blog</a></li><li><a href="/contact/">Contact</a></li><li><a href="{WA}" target="_blank" rel="noopener">WhatsApp us ↗</a></li><li><a href="mailto:{EMAIL_Y}">{EMAIL_Y}</a></li><li><a href="mailto:{EMAIL_W}">{EMAIL_W}</a></li></ul>
      <ul><li><a href="{IG}" target="_blank" rel="noopener">Instagram · Bridlewood ↗</a></li><li><a href="{IG_YONGE}" target="_blank" rel="noopener">Instagram · Yonge ↗</a></li><li><a href="{FB}" target="_blank" rel="noopener">Facebook ↗</a></li></ul>
    </nav>
  </div>
  <div class="ft-base">
    <span>© Beautique Bar · Design preview — not the live site</span>
    <span class="foot-links"><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="#top">Back to top ↑</a><button type="button" class="notes-toggle" aria-pressed="false">Photography notes</button></span>
  </div>
</footer>'''

DLG_WHERE = {'yonge': '3430 Yonge Street, Toronto', 'warden': 'Bridlewood Mall, Unit 244 (2nd floor), Scarborough'}
DLG_NOTE = {'/nails/acrylic/': {'yonge': 'This salon’s menu lists acrylic sets as Crystal Gel. Call {tel} to confirm before you book.'}}

def dialog(path=None):
    """The Book window. On a service page it knows which salons offer that service (SERVICE_AT) and any
    per-salon note (DLG_NOTE); both salons are always listed, in the same order."""
    at = SERVICE_AT.get(path, list(LOC))
    svc = SERVICE_NAMES.get(path)
    rows = []
    for k, l in LOC.items():
        tel = f'<a href="{l["tel"]}">{e(l["phone"])}</a>'
        hours = f'<small class="dlg-hours">{e(hours_inline(k))}</small>'
        if k not in at:
            rows.append(f'''<div class="dlg-row is-off"><p class="dlg-name">{e(l["name"])}</p>
    <p class="dlg-note">{e(svc or 'This treatment')} isn’t on this salon’s menu. Call {tel} or <a href="{WA}" target="_blank" rel="noopener">WhatsApp us</a> to ask what’s available.</p></div>''')
            continue
        note = DLG_NOTE.get(path, {}).get(k)
        rows.append(f'''<div class="dlg-row"><a class="dlg-go" href="{e(l["book"])}" target="_blank" rel="noopener"><span>{e(l["name"])}</span><small>{e(DLG_WHERE[k])} · Book with Fresha ↗</small>{hours}</a>{f'<p class="dlg-note">{note.format(tel=tel)}</p>' if note else ''}</div>''')
    return f'''<dialog class="book-dialog" aria-labelledby="dlg-title">
  <button type="button" class="dlg-close" aria-label="Close">×</button>
  <p class="eyebrow">Choose your salon</p>
  <h2 id="dlg-title">Where shall we see you?</h2>
  <p class="dlg-sub">Fresha opens next, where you choose your service and time.</p>
  <div class="dlg-rows">{''.join(rows)}</div>
  <p class="dlg-wa">{WA_ICON} Questions before you book? <a href="{WA}" target="_blank" rel="noopener">WhatsApp us</a></p>
</dialog>'''

OG_IMAGE = '/img/og-default.jpg'
# Search titles/descriptions: local keywords + both neighbourhoods; titles <= ~60 chars, descriptions <= 160.
SEO = {
  '/nails/': ('Nails: Manicures, Shellac, Bio Gel & Acrylic | Beautique Bar',
              'Manicures, pedicures, Shellac, Bio Gel, Gel-X and acrylic at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Book online.'),
  '/nails/manicure-pedicure/': ('Manicure & Pedicure in Toronto & Scarborough | Beautique Bar',
              'Spa manicures, spa and deluxe pedicures and Shellac at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Book online.'),
  '/nails/bio-gel/': ('Bio Gel Nails in Toronto & Scarborough | Beautique Bar',
              'Bio Gel overlays, full sets with tips, refills and Gel-X at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Book online.'),
  '/nails/acrylic/': ('Acrylic Nails in Toronto & Scarborough | Beautique Bar',
              'Acrylic and Crystal Gel full sets, overlays and refills at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Book online.'),
  '/nails/gel-x/': ('Gel-X Nails in Toronto & Scarborough | Beautique Bar',
              'Gel-X full sets and refills at Beautique Bar — Bridlewood Mall, Scarborough and Yonge & York Mills, Toronto. Prices, refills, removal and booking.'),
  '/nails/biab/': ('BIAB Nails at Bridlewood Mall, Scarborough | Beautique Bar',
              'BIAB builder gel (Strong Shellac) to strengthen natural nails, on its own or with a spa manicure, at Beautique Bar, Bridlewood Mall, Scarborough.'),
  '/nails/russian-manicure/': ('Russian Manicure in Scarborough | Beautique Bar',
              'Russian manicure with detailed cuticle work, with regular polish or Shellac, at Beautique Bar, Bridlewood Mall, Scarborough. Prices and booking.'),
  '/nails/pedicure/': ('Pedicures in Toronto & Scarborough | Beautique Bar',
              'Spa, deluxe and tropical pedicures with polish or Shellac at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/nails/nail-art/': ('Nail Art in Toronto & Scarborough | Beautique Bar',
              'French, chrome and custom designs on Shellac or a set at Beautique Bar — Yonge & York Mills and Bridlewood Mall. Send us your idea on WhatsApp.'),
  '/skin/': ('Lashes, Facials & Waxing in Toronto | Beautique Bar',
              'Eyelash extensions, facials, waxing and threading at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/eyelash-extensions/': ('Eyelash Extensions in Toronto & Scarborough | Beautique Bar',
              'Classic, hybrid and volume eyelash extensions and refills at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Book online.'),
  '/skin/facials/': ('Facials in Toronto & Scarborough | Beautique Bar',
              'Cleansing and deep-cleansing facials, plus relaxing facials, at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/skin/facial-hair-removal/': ('Eyebrow Waxing & Threading in Toronto | Beautique Bar',
              'Eyebrow, lip, chin and full-face waxing, brow tinting and threading at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/skin/body-hair-removal/': ('Body Waxing in Toronto & Scarborough | Beautique Bar',
              'Waxing for arms, legs, underarms, back, chest and bikini at Beautique Bar — Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/locations/': ('Nail Salons in Toronto & Scarborough | Beautique Bar',
              'Beautique Bar at 3430 Yonge St, Toronto (Yonge & York Mills) and Bridlewood Mall, 2900 Warden Ave, Scarborough. Book online, call or text.'),
  '/locations/yonge/': ('Nail Salon at Yonge & York Mills, Toronto | Beautique Bar',
              'Beautique Bar on Yonge, 3430 Yonge St, Toronto — manicures, pedicures, Shellac, gel nails, lashes, waxing and facials. Call 416-484-7788 or book online.'),
  '/locations/warden/': ('Nail Salon at Bridlewood Mall, Scarborough | Beautique Bar',
              'Beautique Bar at Bridlewood Mall, 2900 Warden Ave, Scarborough — manicures, pedicures, gel and acrylic nails, lashes and waxing. Call 647-770-5232.'),
  '/gallery/': ('Nail Art Gallery | Beautique Bar',
              'Recent nail sets by Beautique Bar technicians at Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/blog/': ('Nail, Lash & Skin Care Blog | Beautique Bar',
              'Nail, lash and skin care guides from Beautique Bar — the nail salon at Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough.'),
  '/contact/': ('Contact Beautique Bar | Yonge & Bridlewood Mall',
              'Call, text or book online with Beautique Bar on Yonge (Toronto) or at Bridlewood Mall (Scarborough).'),
}
NOINDEX_PROD = {'/thank-you/', '/skin/body-piercing/', '/404.html'}
SERVICE_NAMES = {'/nails/manicure-pedicure/': 'Manicure and pedicure', '/nails/bio-gel/': 'Bio Gel nails', '/nails/acrylic/': 'Acrylic nails',
                 '/eyelash-extensions/': 'Eyelash extensions', '/skin/facials/': 'Facials', '/skin/facial-hair-removal/': 'Facial hair removal',
                 '/skin/body-hair-removal/': 'Body waxing', '/nails/gel-x/': 'Gel-X nail extensions', '/nails/biab/': 'BIAB builder gel',
                 '/nails/russian-manicure/': 'Russian manicure', '/nails/pedicure/': 'Pedicure', '/nails/nail-art/': 'Nail art'}
SERVICE_AT = {'/nails/biab/': ['warden'], '/nails/russian-manicure/': ['warden']}   # services on one salon's menu only
SERVICE_FAQ = {}   # path -> [(question, answer)], shown on the page and as FAQPage data

def _price_amount(raw):
    m = re.match(r'^\$(\d+(?:\.\d{1,2})?)\+?$', (raw or '').strip())
    return m.group(1) if m else None

def business_ld(k):
    l = LOC[k]
    cats = []
    for c in MENUS[k]:
        items = c['items'] + [i for sub in c.get('subs', []) for i in sub['items']]
        offers = []
        for i in items:
            a = _price_amount(i['price'])
            if a and i['price'].strip().endswith('+'):   # "$37+" is a starting price, not a fixed one
                price = {'priceSpecification': {'@type': 'PriceSpecification', 'minPrice': a, 'priceCurrency': 'CAD'}}
            else:
                price = {'price': a, 'priceCurrency': 'CAD'} if a else {}
            offers.append({'@type': 'Offer', 'name': i['name'], **price})
        cats.append({'@type': 'OfferCatalog', 'name': c['title'], 'itemListElement': offers})
    street = '2900 Warden Avenue, Unit 244' if k == 'warden' else l['street']
    gmaps = f'https://maps.google.com/?cid={l["cid"]}'
    d = {'@context': 'https://schema.org', '@type': 'NailSalon', '@id': f'{SITE_URL}{l["href"]}#business',
         'name': f'Beautique Bar — {l["name"]}', 'url': f'{SITE_URL}{l["href"]}',
         'image': [f'{SITE_URL}/{l["photo"][0]}'] + ([f'{SITE_URL}/img/bridlewood-storefront.webp'] if k == 'warden' else []),
         'telephone': '+1-' + l['phone'], 'email': EMAILS[k], 'priceRange': '$$',
         'address': {'@type': 'PostalAddress', 'streetAddress': street, 'addressLocality': l['locality'], 'addressRegion': 'ON',
                     'postalCode': l['postal'], 'addressCountry': 'CA'},
         'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': days, 'opens': o, 'closes': c} for _, days, o, c in HOURS[k]],
         'geo': {'@type': 'GeoCoordinates', 'latitude': l['geo'][0], 'longitude': l['geo'][1]},
         'hasMap': gmaps, 'sameAs': [gmaps, l['ig']] + [u for u in (l['fb'], l['fresha']) if u],
         'parentOrganization': {'@id': f'{SITE_URL}/#organization'},
         'potentialAction': {'@type': 'ReserveAction', 'target': l['book'], 'name': 'Book online'},
         'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Services & prices', 'itemListElement': cats}}
    if k == 'warden':
        d['containedInPlace'] = {'@type': 'ShoppingCenter', 'name': 'Bridlewood Mall'}
    return d

def org_ld():
    return {'@context': 'https://schema.org', '@type': 'HealthAndBeautyBusiness', '@id': f'{SITE_URL}/#organization',
            'name': 'Beautique Bar', 'url': SITE_URL + '/', 'logo': f'{SITE_URL}/img/brand-lockup.png', 'image': f'{SITE_URL}{OG_IMAGE}',
            'sameAs': [IG, IG_YONGE, FB],
            'subOrganization': [{'@id': f'{SITE_URL}{l["href"]}#business'} for l in LOC.values()]}

def crumbs_ld(body):
    m = re.search(r'<nav class="crumbs[^>]*>(.*?)</nav>', body, re.S)
    if not m:
        return None
    items = re.findall(r'<a href="([^"]+)">(.*?)</a>|<span aria-current="page">(.*?)</span>', m.group(1))
    out = []
    for i, (h, t, cur) in enumerate(items, 1):
        name = html.unescape(t or cur)
        out.append({'@type': 'ListItem', 'position': i, 'name': name, **({'item': SITE_URL + h} if h else {})})
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': out}

def page_ld(path, title, desc, body):
    lds = []
    c = crumbs_ld(body)
    if c:
        lds.append(c)
    for k, l in LOC.items():
        if path == l['href']:
            lds.append(business_ld(k))
            lds.append(faq_ld(k))
    if path in SERVICE_NAMES:
        at = SERVICE_AT.get(path, list(LOC))
        lds.append({'@context': 'https://schema.org', '@type': 'Service', 'name': SERVICE_NAMES[path], 'serviceType': SERVICE_NAMES[path],
                    'description': desc, 'url': SITE_URL + path, 'provider': [{'@id': f'{SITE_URL}{LOC[k]["href"]}#business'} for k in at],
                    'areaServed': [{'@type': 'City', 'name': n} for n in (['Scarborough'] if at == ['warden'] else ['Toronto', 'North York', 'Scarborough'])]})
    if path in SERVICE_FAQ:
        lds.append(faq_data(SERVICE_FAQ[path]))
    m = re.match(r'^/blog/([^/]+)/$', path)
    if m and m.group(1) in PBY:
        p = PBY[m.group(1)]
        lds.append({'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': p['title'], 'description': p['desc'],
                    'datePublished': p['date'].isoformat(), 'url': SITE_URL + path, 'mainEntityOfPage': SITE_URL + path,
                    'image': f'{SITE_URL}{OG_IMAGE}', 'author': {'@id': f'{SITE_URL}/#organization'}, 'publisher': {'@id': f'{SITE_URL}/#organization'}})
    lds.append(org_ld())
    return ''.join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False, separators=(",", ":"))}</script>\n' for d in lds)

def head_common(path, title, desc, og_type='website'):
    """Shared <head> tags: fonts (self-hosted), social cards. Title/description/canonical are set by the caller."""
    url = SITE_URL + path
    return f'''<link rel="preload" href="/fonts/italiana-latin.woff2" as="font" type="font/woff2" crossorigin>
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Beautique Bar">
<meta property="og:locale" content="en_CA">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Beautique Bar — nails at Yonge &amp; York Mills and Bridlewood Mall">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#211e1a">'''

def gl_book(path):
    """Book buttons inside an "At a glance" card: one per salon that offers the page's service, Yonge first."""
    at = SERVICE_AT.get(path, list(LOC))
    return '<div class="gl-actions">' + ''.join(
        f'<a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["short"])} <span aria-hidden="true">↗</span></a>'
        for k, l in LOC.items() if k in at) + '</div>'

def page(path, title, desc, body, tone='light', active=None, noindex_extra=False, bodyclass=''):
    body = body.replace('<!--GL-BOOK-->', gl_book(path))
    if path in SEO:
        title, desc = SEO[path]
    canonical = f'{SITE_URL}{path}'
    og_type = 'article' if path.startswith('/blog/') and path != '/blog/' else 'website'
    return f'''<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{head_common(path, title, desc, og_type)}
<link rel="stylesheet" href="/opus.css?v={VERSION}">
<link rel="stylesheet" href="/site.css?v={VERSION}">
<link rel="alternate" type="application/rss+xml" title="Beautique Bar — Beauty Blog" href="/rss.xml">
<script>document.documentElement.classList.add('js')</script>
<script src="/site.js?v={VERSION}" defer></script>
{page_ld(path, title, desc, body)}</head>
<body class="inner {bodyclass}">
<a class="skip" href="#main">Skip to content</a>
{header(active, tone)}
<main id="main">
{body}
</main>
{footer(path)}
{dialog(path)}
</body>
</html>
'''

# ----------------------------------------------------------------------------------------------
# Building blocks
def img(src, w, h, alt, cls='', pos=None, lazy=True, brief=None):
    style = f' style="object-position:{pos}"' if pos else ''
    b = f' data-brief="{e(brief)}"' if brief else ''
    return (f'<figure class="{cls}"{b}><img src="/{src}" alt="{e(alt)}" width="{w}" height="{h}"'
            f'{LAZY if lazy else ""} decoding="async"{style}></figure>')

def ph(title, text, cls=''):
    return (f'<figure class="{cls} placeholder" aria-label="Final photography required: {e(title)}"><div>'
            f'<p class="eyebrow">Final photography required</p><p class="ph-title">{e(title)}</p><p>{e(text)}</p></div></figure>')

def crumbs(items):
    parts = [f'<a href="{h}">{e(t)}</a>' if h else f'<span aria-current="page">{e(t)}</span>' for t, h in items]
    return f'<nav class="crumbs eyebrow" aria-label="Breadcrumb">{" <i>/</i> ".join(parts)}</nav>'

def hero(crumb, h1, lead, media=None, h1_class='', actions=''):
    side = f'<div class="pg-hero-media">{media}</div>' if media else ''
    return f'''<section class="pg-hero{' has-media' if media else ''}" data-tone="light">
  <div class="pg-hero-text">{crumbs(crumb)}<h1 class="{h1_class}">{h1}</h1><p class="lead">{lead}</p>{actions}</div>
  {side}
</section>'''

def sec_head(eyebrow, h2, id_=None, aside=''):
    i = f' id="{id_}"' if id_ else ''
    return f'<div class="sec-head"><p class="eyebrow">{e(eyebrow)}</p><h2{i}>{h2}</h2>{aside}</div>'

def options(rows):
    return '<div class="options">' + ''.join(
        f'<div class="opt"{idattr(r)}><h3>{e(r[0])}</h3><p>{r[1]}</p></div>' for r in rows) + '</div>'

def book_pair(spec, title='Book at either salon', eyebrow='Where to book', note=None):
    """spec: {loc: [item names] | str (not offered text)}"""
    cols = []
    for k, l in LOC.items():
        v = spec[k]
        if isinstance(v, str):
            other = [x for x in LOC.values() if x['id'] != k][0]
            cols.append(f'''<div class="bp-col is-off"><p class="eyebrow">{e(l["name"])}</p><p class="bp-off">{v}</p>
              <div class="bp-actions"><a class="line-link" href="{other['href']}">{e(other['name'])} <span aria-hidden="true">→</span></a></div></div>''')
            continue
        items, sub = (v, None) if isinstance(v, list) else (v['items'], v.get('note'))
        lis = ''.join(f'<li><span>{e(n)}</span><span class="pr">{e(pr)}</span></li>' for n in items if (pr := price(k, n)) is not None)
        cols.append(f'''<div class="bp-col"><p class="eyebrow">{e(l["name"])}</p>
          <ul class="bp-menu">{lis}</ul>{f'<p class="bp-note">{sub}</p>' if sub else ''}
          <div class="bp-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
          <a class="line-link" href="{l["href"]}#menu">Full menu</a><a class="line-link" href="{l["tel"]}">{e(l["phone"])}</a></div></div>''')
    n = f'<p class="bp-foot">{note}</p>' if note else '<p class="bp-foot">Prices are guides from each salon’s current menu; “+” means from. Your technician will confirm before your service.</p>'
    return f'''<section class="pg-sec book-sec" data-tone="light" aria-labelledby="book-h">
  {sec_head(eyebrow, e(title), 'book-h')}
  <div class="book-pair">{''.join(cols)}</div>{n}
</section>'''

def faq_block(qs, eyebrow='Questions', title='Good to know'):
    rows = ''.join(f'<details class="faq-q"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qs)
    return f'''<section class="pg-sec faq-sec" data-tone="light" aria-labelledby="faq">
  {sec_head(eyebrow, e(title), 'faq')}
  <div class="faq">{rows}</div>
</section>'''

def faq_data(qs):
    return {'@context': 'https://schema.org', '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in qs]}

def quote(key):
    t, who = REV[key]
    return f'''<section class="pg-quote" data-tone="light" aria-label="Client review">
  <figure><blockquote><p>“{e(t)}”</p></blockquote><figcaption>{e(who)} · Google review</figcaption></figure>
  <a class="line-link" href="{REVIEWS_URL}" target="_blank" rel="noopener">Read more reviews on Google <span aria-hidden="true">↗</span></a>
</section>'''

def reading(slugs, title='Further reading'):
    rows = ''.join(f'<li><a href="/blog/{s}/"><span class="rd-cat">{e(PBY[s]["cat"])}</span><span class="rd-t">{e(PBY[s]["title"])}</span><span aria-hidden="true">→</span></a></li>' for s in slugs)
    return f'''<section class="pg-sec reading" data-tone="light" aria-labelledby="rd-h">
  {sec_head('From the blog', e(title), 'rd-h')}<ul class="rd-list">{rows}</ul></section>'''

def close_band(h='Make time<br>for yourself.', eyebrow='Whenever you’re ready'):
    rows = ''.join(f'<li><a href="{e(l["book"])}" target="_blank" rel="noopener"><span class="cl-name">{e(l["name"])}</span><span class="cl-meta">{e(l["street"])} · Book with Fresha</span><span class="cl-book">Book <span aria-hidden="true">↗</span></span></a></li>' for l in LOC.values())
    return f'''<section class="close close--inner" data-tone="dark" aria-labelledby="close-title">
  <p class="eyebrow">{e(eyebrow)}</p><h2 id="close-title">{h}</h2><ul class="close-list">{rows}</ul></section>'''

def svc_list(rows):
    out = []
    for i, (name, href, blurb, avail) in enumerate(rows, 1):
        out.append(f'''<li class="svc"><a href="{href}"><span class="n">{i:02d}</span><span class="name">{e(name)}</span><span class="arr" aria-hidden="true">→</span></a>
          <p>{blurb}</p><p class="avail">{avail}</p></li>''')
    return '<ol class="svc-list">' + ''.join(out) + '</ol>'

BOTH = 'Yonge &amp; York Mills · Bridlewood Mall'

# Our work — finished sets from the salons' own photos (see opus-site-src/INSTAGRAM.md), listed newest first in
# /content/gallery.yml. The weekly Tuesday task adds one photo from the "Nails" Google Drive folder there.
def load_gallery():
    import yaml
    f = Path(__file__).resolve().parent.parent / 'content' / 'gallery.yml'
    rows = (yaml.safe_load(f.read_text()) or {}).get('photos') or []
    out = []
    for r in rows:
        stem = r['file']
        for suffix in ('', '-sm'):
            if not (OUT / 'img' / f'work-{stem}{suffix}.webp').exists():
                raise SystemExit(f'content/gallery.yml: image opus-design-v1/img/work-{stem}{suffix}.webp is missing')
        out.append((stem, int(r['width']), int(r['height']), str(r['caption'])))
    if len({w[0] for w in out}) != len(out):
        raise SystemExit('content/gallery.yml: the same file is listed twice')
    return out
WORK = load_gallery()  # (file stem, width, height, caption)
WORK_BY = {w[0]: w for w in WORK}
WORK_BRIEF = 'REAL — Beautique Bar Instagram.'

def work_fig(stem, cls='wk', lazy=True):
    n, w, h, cap = WORK_BY[stem]
    th = round(h * 720 / w) if w > 720 else h
    tw = min(w, 720)
    return (f'<figure class="{cls}" data-brief="{WORK_BRIEF}"><a href="/img/work-{n}.webp" data-lightbox="{e(cap)}" aria-label="{e(cap)} — view larger">'
            f'<img src="/img/work-{n}-sm.webp" alt="Nails by Beautique Bar: {e(cap.lower())}" width="{tw}" height="{th}"{LAZY if lazy else ""} decoding="async"></a>'
            f'<figcaption>{e(cap)}</figcaption></figure>')

LASHES = [('lash-1', 1574, 1430, 'Full volume'), ('lash-2', 1334, 1199, 'Soft wispy set'), ('lash-3', 1600, 1450, 'Fluffy volume'),
          ('lash-4', 1127, 1503, 'Natural hybrid'), ('lash-5', 1544, 1158, 'Classic volume'), ('lash-6', 1600, 1200, 'Wispy hybrid')]
def lash_strip():
    figs = ''.join(f'<figure class="wk"><a href="/img/{n}.webp" data-lightbox="{e(c)}" aria-label="{e(c)} — view larger">'
                   f'<img src="/img/{n}-sm.webp" alt="Eyelash extensions by Beautique Bar: {e(c.lower())}" width="720" height="{round(h*720/w)}"{LAZY} decoding="async"></a>'
                   f'<figcaption>{e(c)}</figcaption></figure>' for n, w, h, c in LASHES)
    return f'<div class="work-strip work-strip--3">{figs}</div>'

def work_strip(stems):
    return f'<div class="work-strip">{"".join(work_fig(x) for x in stems)}</div>'


# ----------------------------------------------------------------------------------------------
PAGES = {}   # path -> html

def add(path, html_):
    PAGES[path] = html_

def pfrom(k, name):
    """'$65+' -> 'from $65'; fixed prices unchanged; None if the service isn't on that salon's menu."""
    p = price(k, name)
    return None if p is None else (f'from {p[:-1]}' if p.endswith('+') else p)

def qa(*rows):
    """Keep only the questions whose answer could be written (answer is None when a price is missing)."""
    return [(q, a) for q, a in rows if a]

def both(fmt, y, w):
    return fmt.format(y=y, w=w) if y and w else None

def gl_price(where, p):
    """One salon-and-price line in an "At a glance" box."""
    return f'<span class="gl-p"><span>{where}</span> <b>{e(p)}</b></span>' if p else None

def at_both(y_name, w_name=None):
    """Both salons' prices from their menus, Yonge first like the price lists; None if either is missing."""
    y, w = pfrom('yonge', y_name), pfrom('warden', w_name or y_name)
    if not (y and w):
        return None
    return gl_price('At both salons', y) if y == w else gl_price('Yonge &amp; York Mills', y) + gl_price('Bridlewood Mall', w)

def only_at(k, name, label=None):
    """A service on one salon's menu: 'Bridlewood Mall only · $50'."""
    return gl_price(label or f'{LOC[k]["name"]} only', pfrom(k, name))

# "At a glance" quick answer near the top of each service page, for clients and AI answers (27 Oct 2026).
# The date is the last change to the price menus in git (Pages CMS saves are commits), so it only moves when prices do.
def _prices_updated():
    import subprocess
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', 'content/menus/'], cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True, timeout=10).stdout.strip()
        return datetime.date.fromisoformat(out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None

PRICES_UPDATED = _prices_updated()

def prices_updated_html(cls='glance-date'):
    d = PRICES_UPDATED
    return f'<p class="{cls}">Prices from our current menus, last updated <time datetime="{d.isoformat()}">{d.strftime("%B %-d, %Y")}</time>.</p>' if d else ''

def prices_updated_inline():
    d = PRICES_UPDATED
    return f' Last updated <time datetime="{d.isoformat()}">{d.strftime("%B %-d, %Y")}</time>.' if d else ''

def glance(rows, h2='Before you book', dated=True):
    """A compact card: small labels, prices as the largest text. rows: (label, html); a row whose html is
    None (price missing from a menu) is left out. Links down to the page's "Where to book" prices."""
    items = ''.join(f'<div class="gl-row"><dt>{e(t)}</dt><dd>{v}</dd></div>' for t, v in rows if v)
    foot = f'{prices_updated_html() if dated else ""}<a class="line-link gl-book" href="#book-h">All prices <span aria-hidden="true">↓</span></a>'
    return f'''<section class="pg-sec glance" data-tone="light" aria-labelledby="glance-h">
  <div class="gl-card"><p class="eyebrow">At a glance</p><h2 id="glance-h">{h2}</h2>
  <dl class="gl-list">{items}</dl>
  <!--GL-BOOK-->
  <div class="gl-foot">{foot}</div></div>
</section>'''

# ---- /nails/ ---------------------------------------------------------------------------------
add('/nails/', page('/nails/', 'Nails | Beautique Bar', 'Manicures, pedicures, Shellac, Bio Gel and acrylic at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails',None)], 'Nails.', 'Manicures and pedicures, Shellac, Bio Gel, Gel-X and sculpted sets, at both of our salons. Choose a treatment, then book the salon nearest you.',
      img('img/promo-polish-wall.webp', 2400, 1490, 'Rows of polish colours at Beautique Bar on Yonge', 'frame', '50% 40%', False, 'REAL — Yonge promo video still.'), 'display-xl')}
<section class="pg-sec" data-tone="light" aria-labelledby="t-h">
  {sec_head('Treatments', 'Choose your treatment', 't-h')}
  {svc_list([
    ('Manicure & Pedicure', '/nails/manicure-pedicure/', 'Spa and deluxe treatments for hands and feet, finished with regular polish or Shellac.', BOTH),
    ('Pedicures', '/nails/pedicure/', 'Spa, deluxe and seasonal pedicures, with regular polish or Shellac.', BOTH),
    ('Shellac', '/nails/manicure-pedicure/#shellac', 'A glossy gel polish with no drying time, on its own or with a spa manicure or pedicure.', BOTH),
    ('Russian Manicure', '/nails/russian-manicure/', 'A detailed manicure with careful cuticle work, with polish or Shellac.', 'Bridlewood Mall'),
    ('BIAB', '/nails/biab/', 'A builder gel that strengthens your natural nails without adding length.', 'Bridlewood Mall'),
    ('Gel-X', '/nails/gel-x/', 'Soft-gel tips that cover the whole nail, for length in any colour or design.', BOTH),
    ('Bio Gel', '/nails/bio-gel/', 'A natural-looking gel overlay, or a full set with tips.', BOTH),
    ('Acrylic', '/nails/acrylic/', 'Sculpted sets, overlays and refills, shaped and finished to your design.', BOTH),
    ('Nail Art', '/nails/nail-art/', 'French, chrome and custom designs, on Shellac or a set.', BOTH),
  ])}
</section>
{quote('sangeetha')}
<section class="pg-sec" data-tone="light" aria-labelledby="work-h">
  {sec_head('Our work', 'Recent sets', 'work-h', '<a class="line-link" href="/gallery/">See the gallery <span aria-hidden="true">→</span></a>')}
  {work_strip(['white-french-gold', 'burgundy-gloss', 'pink-french-flower', 'silver-chrome-almond'])}
</section>
{book_pair({'yonge': ['Spa Manicure', 'Spa Pedicure', 'Shellac Spa Manicure', 'Bio Gel Full Set', 'Gel-X Full Set'],
            'warden': ['Spa Manicure', 'Spa Pedicure', 'Spa Manicure w/ Shellac', 'Bio Gel Overlay', 'Gel-X Full Set']}, 'A few prices from each menu', 'Prices by salon')}
{reading(['what-are-manicures-and-pedicures', 'what-are-nail-enhancements', 'extend-longevity-nail-art'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/manicure-pedicure/ ---------------------------------------------------------------
add('/nails/manicure-pedicure/', page('/nails/manicure-pedicure/', 'Manicure & Pedicure | Beautique Bar', 'Spa manicures, spa and deluxe pedicures, and Shellac at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Manicure & Pedicure',None)], 'Manicure<br>&amp; Pedicure', 'Spa treatments for hands and feet, finished with regular polish or Shellac. Booked on their own or together.',
      img('img/work-white-french-gold.webp', 1269, 1600, 'A white French manicure with a fine gold accent, resting on satin', 'frame', '50% 45%', False, WORK_BRIEF))}
{glance([
    ('What it is', 'Spa care for hands and feet, finished with regular polish or Shellac. Book a manicure, a pedicure, or both together.'),
    ('Spa manicure', at_both('Spa Manicure')),
    ('Spa pedicure', at_both('Spa Pedicure')),
    ('Manicure & pedicure together', at_both('Spa Manicure & Pedicure')),
    ('Shellac spa manicure', at_both('Shellac Spa Manicure', 'Spa Manicure w/ Shellac')),
    ('Where', 'Both salons. The Russian and deluxe spa manicures are on the Bridlewood Mall menu.'),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="ped-h">
  {sec_head('Pedicures', 'Three ways to sit back', 'ped-h')}
  {options([
    ('Spa Pedicure', 'A warm foot soak, nail trimming and shaping, cuticle care, light exfoliation, and a hot-stone foot massage with moisturising lotion. Finished with your choice of polish.'),
    ('Deluxe Spa Pedicure', 'Everything in the Spa Pedicure, plus an exfoliating scrub, an extended foot and lower-leg hot-stone massage, a hydrating foot mask and a hot-towel wrap.'),
    ('Monthly Special Pedicure', 'A seasonal pedicure that changes through the year. Both menus currently list it as the Tropical Deluxe Pedicure; ask in salon for this month’s version. All pedicure prices are on the <a href="/nails/pedicure/">pedicures page</a>.'),
  ])}
</section>
<section class="pg-sec pg-sec--tight" data-tone="light" aria-labelledby="man-h">
  {sec_head('Manicures', 'Hands, finished your way', 'man-h')}
  {options([
    ('Spa Manicure', 'On the menu at both salons, with regular polish or Shellac, and as a manicure-and-pedicure combination.'),
    ('Deluxe Spa Manicure & Russian Manicure', 'On the Bridlewood Mall menu, each also available with Shellac. See <a href="/nails/russian-manicure/">Russian manicure</a>.'),
    ('Gentleman’s Manicure & Pedicure', 'On the menu at both salons.'),
  ])}
  <div class="inline-ph">{img('img/stock-pedicure.webp', 1448, 1086, 'A finished pedicure in soft pink, feet resting on a white towel', 'frame', '50% 50%', True, 'Licensed stock chosen by the owner.')}</div>
</section>
<section class="pg-sec pg-sec--tight" data-tone="light" aria-labelledby="shellac">
  {sec_head('Shellac', 'Gloss that keeps up', 'shellac')}
  {options([
    ('Shellac manicure or pedicure', 'Shellac is a gel polish cured under a lamp, so there is no drying time. Book it with a spa manicure or pedicure, as a polish application on its own, or as a colour change on artificial nails.'),
    ('Removal', 'Shellac removal is available on its own or with another service.'),
  ])}
</section>
{book_pair({'yonge': ['Spa Manicure', 'Spa Pedicure', 'Deluxe Spa Pedicure', 'Spa Manicure & Pedicure', 'Shellac Spa Manicure', 'Shellac Spa Pedicure', 'Shellac Removal Only'],
            'warden': ['Spa Manicure', 'Russian Manicure', 'Spa Pedicure', 'Deluxe Spa Pedicure', 'Spa Manicure & Pedicure', 'Spa Manicure w/ Shellac', 'Shellac Removal']})}
{quote('samantha')}
{reading(['what-are-manicures-and-pedicures', 'cost-of-shellac-manicures', 'removing-shellac-manicures'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/bio-gel/ -------------------------------------------------------------------------
add('/nails/bio-gel/', page('/nails/bio-gel/', 'Bio Gel Nails | Beautique Bar', 'Bio Gel overlays, full sets with tips and refills, plus Gel-X, at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Bio Gel',None)], 'Bio Gel', 'A gel that looks and feels close to your natural nail — as an overlay on your own nails or as a full set with tips.',
      img('img/work-milky-almond.webp', 1356, 1600, 'Milky almond nails with a sheer, natural finish', 'frame', '50% 45%', False, WORK_BRIEF + ' Service type not stated on the post.'))}
{glance([
    ('What it is', 'A gel that looks close to your natural nail, brushed over your own nails for strength, or over tips for length.'),
    ('Overlay', at_both('Bio Gel Full Set', 'Bio Gel Overlay')),
    ('Full set with tips', at_both('Bio Gel Full Set w/ Tips')),
    ('Refill', at_both('Bio Gel Refill')),
    ('Where', 'Both salons. The Yonge &amp; York Mills menu lists the overlay as Bio Gel Full Set. Length and design can change the price; your technician confirms it first.'),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Options', 'How to book it', 'opt-h')}
  {options([
    ('Overlay or full set', 'An overlay strengthens your natural nails; a full set with tips adds length. Both are finished in the colour or design you choose.'),
    ('Refills', 'Refills fill in the growth so the set keeps its shape. Book them on the same menu.'),
    ('Gel-X', 'Both salons also offer <a href="/nails/gel-x/">Gel-X</a> full sets and refills.'),
    ('Removal', 'Artificial nail removal is available at both salons.'),
  ])}
</section>
{book_pair({'yonge': ['Bio Gel Full Set', 'Bio Gel Full Set w/ Tips', 'Bio Gel Refill', 'Gel-X Full Set', 'Gel-X Refill', 'Artificial Nail Removal Only'],
            'warden': ['Bio Gel Overlay', 'Bio Gel Full Set w/ Tips', 'Bio Gel Refill', 'Gel-X Full Set', 'Gel-X Refill', 'Artificial Nail Removal Only']})}
{quote('danielle')}
{reading(['bio-gel-nails', 'removing-bio-gel-nails', 'what-are-nail-enhancements'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/acrylic/ -------------------------------------------------------------------------
add('/nails/acrylic/', page('/nails/acrylic/', 'Acrylic Nails | Beautique Bar', 'Acrylic and Crystal Gel sets, overlays and refills at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Acrylic',None)], 'Acrylic', 'Sculpted sets for length and shape, finished in the colour or design you choose — from a clean French to full nail art.',
      img('img/work-silver-chrome-almond.webp', 1290, 1290, 'Long sculpted almond nails in silver chrome', 'frame', '50% 50%', False, WORK_BRIEF + ' Acrylic set (confirmed by owner).'))}
{glance([
    ('What it is', 'Sculpted nails for length and shape, as a full set with tips or as an overlay on your own nails.'),
    ('Full set with tips', at_both('Crystal Gel Full Set w/Tips', 'Crystal Gel / Acrylic Set w/Tips')),
    ('Overlay', at_both('Crystal Gel Full Set', 'Crystal Gel / Acrylic Overlay')),
    ('Refill', at_both('Crystal Gel Refill', 'Crystal Gel / Acrylic Refill')),
    ('Where', 'Both salons. The Yonge &amp; York Mills menu lists these sets as Crystal Gel, so call to confirm acrylic before booking there.'),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Options', 'Full sets, overlays, refills', 'opt-h')}
  {options([
    ('Full set with tips', 'Adds length and shape, sculpted to the look you want.'),
    ('Overlay', 'Acrylic over your natural nails for strength without extra length.'),
    ('Refills', 'Fill in the growth every few weeks to keep the set looking fresh.'),
    ('Finishes', 'French, chrome, ombré and custom designs are listed as add-ons on both menus.'),
  ])}
</section>
{book_pair({'yonge': {'items': ['Crystal Gel Full Set', 'Crystal Gel Full Set w/Tips', 'Crystal Gel Refill', 'Chrome/Ombre/Unicorn', 'French on Artificial Nails'],
                      'note': 'The Yonge menu lists these sets as Crystal Gel. Call to confirm acrylic before booking.'},
            'warden': ['Crystal Gel / Acrylic Overlay', 'Crystal Gel / Acrylic Set w/Tips', 'Crystal Gel / Acrylic Refill', 'Designs', 'Chrome / Unicorn']})}
{quote('julia')}
{reading(['acrylic-nails', 'acrylic-nails-costs', 'removing-acrylic-nails'])}
{close_band()}
''', active='/nails/'))

# ---- Service pages added 22 Oct 2026: one page per service people search for by name ------------
# Every price is read from the salon menus; a question is left out if its price isn't on the menu.

# ---- /nails/gel-x/ ---------------------------------------------------------------------------
gx = {k: pfrom(k, 'Gel-X Full Set') for k in LOC}
gxr = {k: pfrom(k, 'Gel-X Refill') for k in LOC}
SERVICE_FAQ['/nails/gel-x/'] = qa(
    ('How much is a Gel-X full set?', both('A Gel-X full set is {w} at Bridlewood Mall and {y} at Yonge & York Mills. The final price depends on length and design, and your technician confirms it before starting.', gx['yonge'], gx['warden'])),
    ('How much is a Gel-X refill?', both('A Gel-X refill is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', gxr['yonge'], gxr['warden'])),
    ('How often do I need a refill?', 'Most clients come back every three to four weeks, as the natural nail grows out under the set. Your technician can suggest timing for your nails.'),
    ('Gel-X or Bio Gel: which should I choose?', 'Gel-X uses full-cover tips, so it is the way to add length. Bio Gel is usually applied over your own nails for strength, or with tips if you want length too. If you are unsure, ask your technician at the start of your appointment.'),
    ('Can I add nail art to Gel-X?', 'Yes. French, chrome and designs can be added to any set. See the nail art page for how design pricing works.'),
    ('Do you remove Gel-X?', both('Yes. Artificial nail removal is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', pfrom('yonge', 'Artificial Nail Removal Only'), pfrom('warden', 'Artificial Nail Removal Only'))),
)
add('/nails/gel-x/', page('/nails/gel-x/', 'Gel-X Nails | Beautique Bar', 'Gel-X full sets and refills at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Gel-X',None)], 'Gel-X', 'Soft-gel tips that cover the whole nail, shaped to the length you want and finished in any colour or design. At both salons.',
      img('img/work-gold-chrome-lines.webp', 1440, 1440, 'Long nails with fine gold chrome lines', 'frame', '50% 50%', False, WORK_BRIEF + ' Service type not stated on the post.'))}
{glance([
    ('What it is', 'Each Gel-X tip covers the whole nail. It is bonded with gel, cured under a lamp, then shaped and finished, so you get length without a sculpted acrylic set.'),
    ('Full set', at_both('Gel-X Full Set')),
    ('Refill', at_both('Gel-X Refill')),
    ('Finishes', 'French, chrome, ombré and custom designs can be added. See <a href="/nails/nail-art/">nail art</a>.'),
  ])}
{book_pair({'yonge': ['Gel-X Full Set', 'Gel-X Refill', 'Chrome/Ombre/Unicorn', 'French on Artificial Nails', 'Artificial Nail Removal Only'],
            'warden': ['Gel-X Full Set', 'Gel-X Refill', 'Designs', 'Chrome / Unicorn', 'Artificial Nail Removal Only']})}
<section class="pg-sec" data-tone="light" aria-labelledby="work-h">
  {sec_head('Our work', 'Recent sets', 'work-h', '<a class="line-link" href="/gallery/">See the gallery <span aria-hidden="true">→</span></a>')}
  {work_strip(['jewelled-red-stiletto', 'caramel-coffin', 'oxblood-almond', 'pink-3d-details'])}
</section>
{faq_block(SERVICE_FAQ['/nails/gel-x/'])}
{reading(['what-are-nail-enhancements', 'extend-longevity-nail-art'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/biab/ (Bridlewood menu only: "BIAB (Strong Shellac)") ------------------------------
bi, bim = pfrom('warden', 'BIAB (Strong Shellac) no Manicure'), pfrom('warden', 'BIAB (Strong Shellac) w Spa Manicure')
SERVICE_FAQ['/nails/biab/'] = qa(
    ('What is BIAB?', 'BIAB is a builder gel: a thicker layer of gel that strengthens your natural nails without adding length. Our Bridlewood Mall menu lists it as Strong Shellac.'),
    ('How much is BIAB?', both('BIAB is {w} on its own, or {y} with a spa manicure, at Bridlewood Mall.', bim, bi)),
    ('Is BIAB the same as Shellac?', 'No. Shellac is a thin gel polish for colour. BIAB is a thicker builder gel that adds strength, which helps if your nails bend or break easily.'),
    ('Can I get BIAB at Yonge & York Mills?', 'BIAB is on the Bridlewood Mall menu only. At Yonge & York Mills, a Bio Gel overlay is the closest option.'),
    ('How long does BIAB last?', 'Most clients rebook every three to four weeks as the nail grows out. Your technician can suggest timing for your nails.'),
)
add('/nails/biab/', page('/nails/biab/', 'BIAB | Beautique Bar', 'BIAB builder gel at Beautique Bar, Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('BIAB',None)], 'BIAB', 'A builder gel that strengthens your natural nails without adding length. On our Bridlewood Mall menu as Strong Shellac.',
      img('img/work-short-sparkle.webp', 1200, 1600, 'Short square nails with sparkling 3D details', 'frame', '50% 50%', False, WORK_BRIEF + ' Service type not stated on the post.'))}
{glance([
    ('What it is', 'A thicker gel than Shellac, built up over your own nails for strength and a smooth shape, then finished in colour.'),
    ('Who it suits', 'Clients who want to keep their natural length but find their nails bend, peel or break.'),
    ('On its own', only_at('warden', 'BIAB (Strong Shellac) no Manicure', 'Bridlewood Mall')),
    ('With a spa manicure', only_at('warden', 'BIAB (Strong Shellac) w Spa Manicure', 'Bridlewood Mall')),
    ('Where', 'Bridlewood Mall only. At Yonge &amp; York Mills, ask for a <a href="/nails/bio-gel/">Bio Gel</a> overlay.'),
  ])}
{book_pair({'yonge': 'BIAB is on the Bridlewood Mall menu. At Yonge &amp; York Mills, a Bio Gel overlay is the closest option.',
            'warden': ['BIAB (Strong Shellac) no Manicure', 'BIAB (Strong Shellac) w Spa Manicure', 'Shellac Removal w/ Service', 'French / Designs']})}
{faq_block(SERVICE_FAQ['/nails/biab/'])}
{reading(['what-are-nail-enhancements', 'bio-gel-nails'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/russian-manicure/ (Bridlewood menu only) -----------------------------------------
ru, rus = pfrom('warden', 'Russian Manicure'), pfrom('warden', 'Russian Manicure w/ Shellac')
SERVICE_FAQ['/nails/russian-manicure/'] = qa(
    ('What is a Russian manicure?', 'A detailed manicure focused on careful cuticle work, so the polish can sit close to the cuticle and grows out neatly.'),
    ('How much is a Russian manicure?', both('A Russian manicure is {y} at Bridlewood Mall, or {w} with Shellac.', ru, rus)),
    ('How is it different from a spa manicure?', 'A spa manicure includes a soak and a relaxing finish. A Russian manicure is a dry, detail-focused service that takes extra care around the cuticles.'),
    ('Can I get a Russian manicure at Yonge & York Mills?', 'It is on the Bridlewood Mall menu only. Yonge & York Mills offers spa and Shellac spa manicures.'),
)
add('/nails/russian-manicure/', page('/nails/russian-manicure/', 'Russian Manicure | Beautique Bar', 'Russian manicure at Beautique Bar, Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Russian Manicure',None)], 'Russian<br>Manicure', 'A detailed manicure with careful cuticle work, finished with regular polish or Shellac. At Bridlewood Mall.',
      img('img/work-red-maple.webp', 1280, 1600, 'Short red nails with hand-painted maple leaves', 'frame', '50% 50%', False, WORK_BRIEF + ' Service type not stated on the post.'))}
{glance([
    ('What it is', 'Careful, detailed cuticle work and shaping, so colour can be applied close to the cuticle for a clean finish.'),
    ('Russian manicure', only_at('warden', 'Russian Manicure', 'Bridlewood Mall')),
    ('With Shellac', only_at('warden', 'Russian Manicure w/ Shellac', 'Bridlewood Mall')),
    ('Where', 'Bridlewood Mall only. At Yonge &amp; York Mills, see <a href="/nails/manicure-pedicure/">spa manicures</a>.'),
  ])}
{book_pair({'yonge': 'The Russian manicure is on the Bridlewood Mall menu. Yonge &amp; York Mills offers spa and Shellac spa manicures.',
            'warden': ['Russian Manicure', 'Russian Manicure w/ Shellac', 'Spa Manicure', 'Deluxe Spa Manicure']})}
{faq_block(SERVICE_FAQ['/nails/russian-manicure/'])}
{reading(['what-are-manicures-and-pedicures', 'cost-of-shellac-manicures'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/pedicure/ ------------------------------------------------------------------------
sp = {k: pfrom(k, 'Spa Pedicure') for k in LOC}
dp = {k: pfrom(k, 'Deluxe Spa Pedicure') for k in LOC}
ssp = {'yonge': pfrom('yonge', 'Shellac Spa Pedicure'), 'warden': pfrom('warden', 'Spa Pedicure w/Shellac')}
gp = {k: pfrom(k, "Gentleman's Pedicure") for k in LOC}
SERVICE_FAQ['/nails/pedicure/'] = qa(
    ('How much is a pedicure?', both('A spa pedicure is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', sp['yonge'], sp['warden'])),
    ('What is the difference between a spa and a deluxe pedicure?', 'The deluxe adds an exfoliating scrub, a longer hot-stone massage for the foot and lower leg, a hydrating foot mask and a hot-towel wrap.'),
    ('How much is a deluxe pedicure?', both('A deluxe spa pedicure is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', dp['yonge'], dp['warden'])),
    ('Can I get Shellac on my toes?', both('Yes. A spa pedicure with Shellac is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', ssp['yonge'], ssp['warden'])),
    ('Do you do pedicures for men?', both('Yes. A gentleman’s pedicure is {w} at Bridlewood Mall and {y} at Yonge & York Mills.', gp['yonge'], gp['warden'])),
    ('Do I need to book?', 'Walk-ins are welcome at both salons. Booking ahead secures your time and technician.'),
)
add('/nails/pedicure/', page('/nails/pedicure/', 'Pedicures | Beautique Bar', 'Spa, deluxe and tropical pedicures at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Pedicures',None)], 'Pedicures', 'Spa, deluxe and seasonal pedicures in a massage chair, finished with regular polish or Shellac. At both salons.',
      img('img/promo-pedicure-chair.webp', 1600, 993, 'A pedicure chair at Beautique Bar on Yonge, with the care products ready on the tray', 'frame', '50% 50%', False, 'REAL — Yonge promo still.'))}
{glance([
    ('What it is', 'A foot soak, nail and cuticle care, light exfoliation and a hot-stone massage in a massage chair, finished with your choice of polish.'),
    ('Spa pedicure', at_both('Spa Pedicure')),
    ('Deluxe spa pedicure', at_both('Deluxe Spa Pedicure')),
    ('Spa pedicure with Shellac', at_both('Shellac Spa Pedicure', 'Spa Pedicure w/Shellac')),
    ('Walk-ins', 'Welcome at both salons. Booking ahead secures your time and technician.'),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="ped-h">
  {sec_head('Pedicures', 'Choose your pedicure', 'ped-h')}
  {options([
    ('Spa Pedicure', 'A warm foot soak, nail trimming and shaping, cuticle care, light exfoliation, and a hot-stone foot massage with moisturising lotion. Finished with your choice of polish.'),
    ('Deluxe Spa Pedicure', 'Everything in the Spa Pedicure, plus an exfoliating scrub, an extended foot and lower-leg hot-stone massage, a hydrating foot mask and a hot-towel wrap.'),
    ('Monthly special', 'A seasonal pedicure that changes through the year, currently the Tropical Deluxe Pedicure on both menus. Ask in salon for this month’s version.'),
    ('With Shellac', 'Spa, deluxe and tropical pedicures can each be finished with Shellac for long-lasting, glossy colour on your toes.'),
    ('Gentleman’s Pedicure', 'On the menu at both salons, on its own or with a manicure.'),
  ])}
</section>
{book_pair({'yonge': ['Spa Pedicure', 'Deluxe Spa Pedicure', 'Tropical Deluxe Pedicure', 'Shellac Spa Pedicure', "Gentleman's Pedicure", 'Spa Manicure & Pedicure'],
            'warden': ['Spa Pedicure', 'Deluxe Spa Pedicure', 'Tropical Deluxe Pedicure', 'Spa Pedicure w/Shellac', "Gentleman's Pedicure", 'Spa Manicure & Pedicure']})}
<section class="pg-sec gallery" data-tone="light" aria-label="Inside the salon">
  <div class="gal gal--one">{img('img/yonge-pedicure-row.webp', 2400, 1800, 'The row of pedicure chairs at Beautique Bar on Yonge', 'g1', '50% 58%', True, 'REAL — owner photo.')}</div>
</section>
{quote('samantha')}
{faq_block(SERVICE_FAQ['/nails/pedicure/'])}
{reading(['what-are-manicures-and-pedicures', 'costs-of-manicures-and-pedicures'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/nail-art/ ------------------------------------------------------------------------
SERVICE_FAQ['/nails/nail-art/'] = qa(
    ('How much does nail art cost?', both('Designs are priced by detail and added to your manicure or set. At Bridlewood Mall, French or simple designs start {w}; at Yonge & York Mills, chrome, ombré or unicorn finishes are {y}. Your technician confirms the price before starting.', pfrom('yonge', 'Chrome/Ombre/Unicorn'), pfrom('warden', 'French / Designs'))),
    ('Can I bring a picture of the design I want?', 'Yes. Send it to us on WhatsApp before your visit so we can tell you the price and how much time to book.'),
    ('Can I get nail art on my natural nails?', 'Yes. Designs can be added to a Shellac manicure, or to a set such as Gel-X, Bio Gel or acrylic if you want length.'),
    ('Do both salons do nail art?', 'Yes. French and chrome finishes are on the menu at both salons, and design add-ons are on the Bridlewood Mall menu. For a hand-painted or detailed design, send us a photo first so we can confirm the price and the salon.'),
)
add('/nails/nail-art/', page('/nails/nail-art/', 'Nail Art | Beautique Bar', 'Nail art at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Nail Art',None)], 'Nail Art', 'French tips, chrome and custom designs, added to Shellac or to a set. Send us your idea and we will price it before you book.',
      img('img/work-painted-florals-green.webp', 900, 1600, 'Hand-painted florals on long nails', 'frame', '50% 40%', False, WORK_BRIEF))}
{glance([
    ('Bring your idea', f'Send a photo of the design you want on <a href="{WA}" target="_blank" rel="noopener">WhatsApp</a> before your visit. We will tell you the price and how much time to book.'),
    ('On your own nails or a set', 'Designs go on a Shellac manicure, or on <a href="/nails/gel-x/">Gel-X</a>, <a href="/nails/bio-gel/">Bio Gel</a> or <a href="/nails/acrylic/">acrylic</a> if you want length.'),
    ('Priced by detail', 'A French tip or a simple accent costs less than full hand-painted art. Design prices are added to your manicure or set, and your technician confirms the total before starting.'),
  ], 'How nail art works', dated=False)}
<section class="pg-sec" data-tone="light" aria-labelledby="work-h">
  {sec_head('Our work', 'Recent designs', 'work-h', '<a class="line-link" href="/gallery/">See the gallery <span aria-hidden="true">→</span></a>')}
  {work_strip(['plum-chrome-gems', 'pink-french-flower', 'almond-painted-flowers', 'leopard-tips'])}
</section>
{book_pair({'yonge': ['Add-on : French', 'Chrome/Ombre/Unicorn', 'French on Artificial Nails', 'Shellac Spa Manicure', 'Gel-X Full Set'],
            'warden': ['French / Designs', 'Designs', 'Chrome / Unicorn', 'Airbrush', 'Gel-X Full Set']})}
{quote('julia')}
{faq_block(SERVICE_FAQ['/nails/nail-art/'])}
{reading(['extend-longevity-nail-art', 'toronto-trending-nail-art-design'])}
{close_band('Seen something<br>you love?')}
''', active='/nails/'))

# ---- /skin/ ----------------------------------------------------------------------------------
add('/skin/', page('/skin/', 'Skin & Lashes | Beautique Bar', 'Eyelash extensions, facials, waxing and threading at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes',None)], 'Skin<br>&amp; Lashes', 'Lash extensions, facials, waxing and threading — alongside your nails, at the salon nearest you.',
      img('img/lash-3.webp', 1600, 1450, 'A full, fluffy set of eyelash extensions with a groomed brow', 'frame', '50% 45%', False, 'REAL — Beautique Bar lash work (owner photo).'))}
<section class="pg-sec" data-tone="light" aria-labelledby="t-h">
  {sec_head('Treatments', 'Choose your treatment', 't-h')}
  {svc_list([
    ('Eyelash Extensions', '/eyelash-extensions/', 'Classic, hybrid and volume sets, plus refills.', BOTH),
    ('Facials', '/skin/facials/', 'From a quick cleansing facial to a deep cleanse with massage and a custom mask.', BOTH),
    ('Facial Hair Removal', '/skin/facial-hair-removal/', 'Waxing and tinting for brows, lip, chin and full face; threading at Yonge.', BOTH),
    ('Body Hair Removal', '/skin/body-hair-removal/', 'Waxing for arms, legs, underarms, back, chest and bikini.', BOTH),
  ])}
</section>
{close_band()}
''', active='/skin/'))

# ---- /eyelash-extensions/ --------------------------------------------------------------------
add('/eyelash-extensions/', page('/eyelash-extensions/', 'Eyelash Extensions | Beautique Bar', 'Classic, hybrid and volume eyelash extensions and refills at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Eyelash Extensions',None)], 'Eyelash<br>Extensions', 'Individual extensions applied to suit your eye shape — from a soft, natural set to full volume — with refills to keep them full.',
      img('img/lash-5.webp', 1544, 1158, 'A volume set of eyelash extensions on a brown eye', 'frame', '45% 50%', False, 'REAL — Beautique Bar lash work (owner photo).'))}
{glance([
    ('What it is', 'Individual extensions applied to your natural lashes, as a classic, hybrid or volume set.'),
    ('Classic set', at_both('Classic Set', 'Individual Classic Set')),
    ('Volume set', at_both('Volume Set', 'Indiv. Volume Set')),
    ('Classic refill', (lambda r: r and r + gl_price('Bridlewood Mall', 'Ask when you book'))(only_at('yonge', 'Refill Classic', 'Yonge &amp; York Mills'))),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Options', 'Choose your set', 'opt-h')}
  {options([
    ('Classic', 'One extension applied to each natural lash, for definition that still looks like you.'),
    ('Hybrid', 'A mix of classic and volume lashes for texture and fullness.'),
    ('Volume', 'Fans of fine lashes on each natural lash for a fuller, softer look.'),
    ('Refills', 'Top up your set as your natural lashes shed and grow.'),
  ])}
</section>
<section class="pg-sec" data-tone="light" aria-labelledby="lash-work">
  {sec_head('Our work', 'Recent lash sets', 'lash-work')}
  {lash_strip()}
</section>
{book_pair({'yonge': ['Classic Set', 'Hybrid Set', 'Volume Set', 'Refill Classic', 'Refill Hybrid', 'Refill Volume'],
            'warden': ['Individual Classic Set', 'Indiv. Hybrid Set', 'Indiv. Volume Set', 'Bunch Light Volume Set', 'Bunch Wispy Set']})}
{reading(['maintaining-eyelash-extensions'])}
{close_band()}
''', active='/skin/'))

# ---- /skin/facials/ --------------------------------------------------------------------------
add('/skin/facials/', page('/skin/facials/', 'Facials | Beautique Bar', 'Cleansing, deep-cleansing and relaxing facials at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Facials',None)], 'Facials', 'A quick cleanse for a fresh face, or a full hour of deep cleansing, massage and a mask chosen for your skin.',
      img('img/skin-facial.webp', 1536, 1024, 'A relaxing facial with a cream mask, eyes closed', 'frame', '45% 50%', False, 'Licensed stock chosen by the owner.'))}
{glance([
    ('Yonge & York Mills', (lambda a, b: a and b and a + b)(gl_price('Facial cleansing, 30 min', pfrom('yonge', 'Facial Cleansing Service (30 min)')), gl_price('Deep facial cleansing, 1 hr', pfrom('yonge', 'Deep Facial Cleansing Service (1 hr)')))),
    ('Bridlewood Mall', (lambda a, b: a and b and a + b)(gl_price('Classic relaxing facial', pfrom('warden', 'Classic Relaxing Facial')), gl_price('Deep-pore cleansing &amp; relaxing', pfrom('warden', 'Deep-pore Cleansing & Relaxing Facial')))),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('On the menus', 'Choose your facial', 'opt-h')}
  {options([
    ('Facial Cleansing Service · 30 min', 'Cleanse, exfoliate, extractions if you want them, then moisturiser and SPF for a fresh finish. At Yonge &amp; York Mills.'),
    ('Deep Facial Cleansing Service · 1 hr', 'A deep cleanse with exfoliation and steam, extractions, a face, neck and shoulder massage, a mask chosen for your skin, then serums and moisturiser. At Yonge &amp; York Mills.'),
    ('Deep-pore Cleansing & Relaxing Facial', 'At Bridlewood Mall.'),
    ('Classic Relaxing Facial', 'At Bridlewood Mall.'),
  ])}
</section>
{book_pair({'yonge': ['Facial Cleansing Service (30 min)', 'Deep Facial Cleansing Service (1 hr)'],
            'warden': ['Deep-pore Cleansing & Relaxing Facial', 'Classic Relaxing Facial']})}
{reading(['facial-frequency'])}
{close_band()}
''', active='/skin/'))

# ---- /skin/facial-hair-removal/ --------------------------------------------------------------
add('/skin/facial-hair-removal/', page('/skin/facial-hair-removal/', 'Facial Hair Removal | Beautique Bar', 'Eyebrow, lip, chin and full-face waxing, brow tinting and threading at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Facial Hair Removal',None)], 'Facial Hair<br>Removal', 'Waxing and tinting for brows, lip, chin and full face at both salons, and threading at Yonge &amp; York Mills.',
      img('img/lash-2.webp', 1334, 1199, 'A shaped, tinted brow above a set of lash extensions', 'frame', '50% 40%', False, 'REAL — Beautique Bar lash work (owner photo).'))}
{glance([
    ('Eyebrow wax', at_both('Eyebrow Wax')),
    ('Upper lip wax', at_both('Upper Lip')),
    ('Full face wax', at_both('Full Face')),
    ('Eyebrow threading', only_at('yonge', 'Eyebrow Threading')),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Methods', 'Waxing, tinting, threading', 'opt-h')}
  {options([
    ('Waxing', 'Eyebrows, sideburns, upper lip, chin and full face, at both salons.'),
    ('Brow tinting', 'On its own, or with an eyebrow wax at Yonge &amp; York Mills.'),
    ('Threading', 'Eyebrow, lip, chin and full-face threading, at Yonge &amp; York Mills.'),
  ])}
</section>
{book_pair({'yonge': ['Eyebrow Wax', 'Eyebrow Wax & Tint', 'Upper Lip', 'Full Face', 'Eyebrow Threading', 'Full Face Threading'],
            'warden': {'items': ['Eyebrow Wax', 'Eyebrow Tinting', 'Upper Lip', 'Chin', 'Full Face'], 'note': 'Threading is on the Yonge &amp; York Mills menu.'}})}
{reading(['facial-hair-growth'])}
{close_band()}
''', active='/skin/'))

# ---- /skin/body-hair-removal/ ----------------------------------------------------------------
add('/skin/body-hair-removal/', page('/skin/body-hair-removal/', 'Body Hair Removal | Beautique Bar', 'Waxing for arms, legs, underarms, back, chest and bikini at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Body Hair Removal',None)], 'Body Hair<br>Removal', 'Waxing for arms, legs, underarms, back, chest, stomach and bikini, at both salons.',
      img('img/skin-hair-removal.webp', 1536, 1024, 'Smooth legs resting on a white towel', 'frame', '40% 50%', False, 'Licensed stock chosen by the owner.'))}
{glance([
    ('Underarms', at_both('Under Arms')),
    ('Full legs', at_both('Full Legs')),
    ('Brazilian', at_both('Brazilian')),
  ])}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Waxing', 'Areas on the menu', 'opt-h')}
  {options([
    ('Arms & underarms', 'Underarms, half arms and full arms.'),
    ('Legs', 'Lower or half legs, upper legs at Yonge &amp; York Mills, and full legs.'),
    ('Back, chest & stomach', 'At both salons.'),
    ('Bikini', 'Bikini line, bikini with legs, and Brazilian.'),
  ])}
</section>
{book_pair({'yonge': ['Under Arms', 'Full Arms', 'Full Legs', 'Full Back', 'Bikini Line', 'Brazilian'],
            'warden': ['Under Arms', 'Full Arms', 'Full Legs', 'Back', 'Bikini Line', 'Brazilian']})}
{close_band()}
''', active='/skin/'))

# ---- /skin/body-piercing/ (service discontinued; URL kept so existing links still work) --------
add('/skin/body-piercing/', page('/skin/body-piercing/', 'Body Piercing | Beautique Bar', 'Beautique Bar no longer offers piercing. See our nail, lash, facial and hair removal services at Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Body Piercing',None)], 'Body<br>Piercing', 'Beautique Bar no longer offers piercing services at either salon. Thank you to everyone who trusted us with theirs.')}
<section class="pg-sec" data-tone="light" aria-labelledby="t-h">
  {sec_head('Still at both salons', 'Explore our other treatments', 't-h')}
  {svc_list([
    ('Eyelash Extensions', '/eyelash-extensions/', 'Classic, hybrid and volume sets, plus refills.', BOTH),
    ('Facials', '/skin/facials/', 'From a quick cleansing facial to a deep cleanse with massage and a custom mask.', BOTH),
    ('Facial Hair Removal', '/skin/facial-hair-removal/', 'Waxing and tinting for brows, lip, chin and full face; threading at Yonge.', BOTH),
    ('Nails', '/nails/', 'Manicures, pedicures, Shellac, Bio Gel and acrylic.', BOTH),
  ])}
</section>
{close_band()}
''', active='/skin/'))

# ---- /locations/ -----------------------------------------------------------------------------
def salon_card(l, head='h2', lazy=True):
    if l['photo']:
        s, w, h, alt = l['photo']
        fig = f'<figure class="salon-photo" data-brief="{e(PHOTO_BRIEF[l["id"]])}"><img src="/{s}" alt="{e(alt)}" width="{w}" height="{h}"{LAZY if lazy else EAGER} decoding="async" style="object-position:{"50% 60%" if l["id"] == "yonge" else "56% 50%"}"></figure>'
    else:
        fig = ph('Bridlewood Mall salon', 'Wide interior from the entrance, lights warmed, no people. Same framing as the Yonge photo so the two salons read as a pair.', 'salon-photo')
    return f'''<article class="salon">{fig}
  <div class="salon-info"><p class="eyebrow">{e(l["area"])}</p><{head}><a href="{l["href"]}">{e(l["name"])}</a></{head}>
  <p class="addr">{e(l["addr"])}<br><a href="{l["tel"]}">Call {e(l["phone"])}</a>{f' · Text {e(l["text"])}' if l["text"] != l["phone"] else ' · Call or text'}</p>
  <p class="hours-line">{e(hours_inline(l["id"]))}</p>
  <div class="salon-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
  <a class="line-link" href="{l["href"]}">Menu &amp; details</a><a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a></div></div></article>'''

add('/locations/', page('/locations/', 'Locations | Beautique Bar', 'Beautique Bar on Yonge (3430 Yonge St, Toronto) and at Bridlewood Mall (2900 Warden Ave, Scarborough). Book online, call or text.', f'''
{hero([('Home','/'),('Locations',None)], 'Two salons.', 'Walk-ins are welcome, but booking ahead secures your preferred time and technician. Choose the salon nearest you.')}
<section class="pg-sec salons salons--inner" data-tone="light" aria-label="Our salons">
  <div class="salon-pair">{salon_card(LOC['yonge'], lazy=False)}{salon_card(LOC['warden'])}</div>
</section>
''', active='/locations/'))

# ---- /locations/yonge/ & /locations/warden/ --------------------------------------------------
HERE = {
  'yonge': ['Manicures, pedicures and Shellac', 'Crystal Gel, Bio Gel and Gel-X', 'Waxing, brow tinting and threading', 'Facials', 'Eyelash extensions'],
  'warden': ['Manicures, pedicures and Shellac, including Russian manicure and BIAB', 'Gel-X, Bio Gel, Crystal Gel / acrylic and dipping powder', 'Waxing and brow tinting', 'Facials', 'Eyelash extensions'],
}
HERE_LINKS = {  # the service pages for what each salon is known for
  'yonge': [('Gel-X', '/nails/gel-x/'), ('Nail art', '/nails/nail-art/'), ('Pedicures', '/nails/pedicure/'), ('Bio Gel', '/nails/bio-gel/')],
  'warden': [('Russian manicure', '/nails/russian-manicure/'), ('BIAB', '/nails/biab/'), ('Gel-X', '/nails/gel-x/'), ('Nail art', '/nails/nail-art/'), ('Pedicures', '/nails/pedicure/')],
}
# Descriptive headings (proposed 15 Oct, approved 22 Oct 2026) — say what the page is and where, for search and AI answers.
H1_LOC = {'yonge': 'Nail Salon on Yonge at York Mills', 'warden': 'Nail Salon at Bridlewood Mall, Scarborough'}
H2_HERE = {'yonge': 'Manicures, pedicures & nails on Yonge', 'warden': 'Russian manicure, Gel-X, BIAB & more at Bridlewood Mall'}

def faq_items(k):
    """Location FAQ: every answer comes from salons.yml, the menu file or the site's terms; a question is left out if its price isn't on the menu."""
    l = LOC[k]
    first = lambda *names: next(((n, p) for n in names for i in all_items(k) if i['name'] == n and (p := i['price'])), None)
    contact = f'call {l["phone"]}' + (f', text {l["text"]}' if l['text'] != l['phone'] else '')
    qs = [('Do you take walk-ins?', 'Yes. Walk-ins are welcome. Booking ahead secures your preferred time and technician.'),
          ('What are your hours?', hours_inline(k).replace(' · ', '. ') + '.'),
          ('How do I book?', f'Book online with Fresha, {contact}, or message us on WhatsApp.'),
          ('Where are you?', f'{l["street"]}, {l["city"]}. {l["where"]}')]
    if (g := first("Gentleman's Manicure", "Gentleman's Pedicure")):
        qs.append(('Do you do manicures and pedicures for men?', f'Yes. A {g[0]} is {g[1]}.'))
    if (s := first('Shellac Spa Pedicure')):
        qs.append(('Can I get Shellac on my toes?', f'Yes. A Shellac Spa Pedicure is {s[1]}.'))
    refills = [f'{n} {p}' for n in ('Crystal Gel Refill', 'Crystal Gel / Acrylic Refill', 'Bio Gel Refill', 'Gel-X Refill') if (r := first(n)) and (p := r[1])]
    if refills:
        qs.append(('Do you do refills?', 'Yes. ' + ', '.join(refills) + '.'))
    qs += [('Why do some prices say “+”?', 'Those are starting prices. The total depends on length, design and add-ons, and your technician will confirm the price before your service.'),
           ('How do I cancel or reschedule?', f'Please let us know as early as possible so we can offer the time to another guest: {contact}.'),
           ('What if I’m not happy with my service?', 'Tell us before you leave so we can make it right.')]
    return qs

def faq_html(k):
    return faq_block(faq_items(k))

def faq_ld(k):
    return faq_data(faq_items(k))

def menu_html(k):
    blocks = []
    for c in MENUS[k]:
        def rows(items):
            return ''.join(f'<li><span>{e(i["name"])}</span><span class="pr">{e(i["price"])}</span></li>' for i in items)
        subs = ''.join(f'<h4>{e(s["title"])}</h4><ul class="mn-list">{rows(s["items"])}</ul>' for s in c.get('subs', []))
        blocks.append(f'<div class="mn-cat" id="{slug(c["title"])}"><h3>{e(c["title"])}</h3><ul class="mn-list">{rows(c["items"])}</ul>{subs}</div>')
    return ''.join(blocks)

for k, l in LOC.items():
    other = LOC['warden' if k == 'yonge' else 'yonge']
    if l['photo']:
        s, w, h, alt = l['photo']
        media = img(s, w, h, alt, 'frame', '50% 60%', False, PHOTO_BRIEF[k]) if k == 'yonge' else img('img/bridlewood-storefront.webp', 1448, 1086, 'The Beautique Bar storefront at Bridlewood Mall', 'frame', '40% 50%', False, 'REAL — owner photo, Bridlewood storefront.')
    if k == 'yonge':
        gallery = f'''<section class="pg-sec gallery" data-tone="light" aria-label="Inside the salon">
  <div class="gal">{img('img/yonge-pedicure-row.webp', 2400, 1800, 'The pedicure row at Beautique Bar on Yonge', 'g1', '50% 58%', True, 'REAL — owner photo.')}
  {img('img/promo-logo-wall.webp', 1100, 1650, 'The Beautique Bar logo lit on the wood-slat wall', 'g2', None, True, 'REAL — Yonge promo still.')}</div></section>'''
    else:
        gallery = f'''<section class="pg-sec gallery" data-tone="light" aria-label="Inside the salon">
  <div class="gal gal--one">{img(s, w, h, alt, 'g1', '50% 55%', True, PHOTO_BRIEF[k])}</div></section>
<section class="pg-sec" data-tone="light" aria-labelledby="bw-work">
  {sec_head('From our Instagram', 'Recent sets', 'bw-work', '<a class="line-link" href="/gallery/">See the gallery <span aria-hidden="true">→</span></a>')}
  {work_strip(['plum-chrome-gems', 'burgundy-gloss', 'brown-french', 'leopard-tips'])}
</section>'''
    monthly = '<p class="mn-note">Monthly special pedicure: ask in salon for this month’s version.</p>'
    add(l['href'], page(l['href'], f'{l["name"]} Nail Salon | Beautique Bar', f'{l["long"]} — {l["addr"]}. Call {l["phone"]}. Book online.', f'''
{hero([('Home','/'),('Locations','/locations/'),(l['name'],None)], e(H1_LOC[k]), f'{e(l["long"])} — {e(l["where"][0].lower() + l["where"][1:])} Serving {e(l["serves"])}.', media,
      actions=f'{proof(k)}<div class="hero-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["short"])} online <span aria-hidden="true">↗</span></a><a class="line-link wa-link" href="{WA}" target="_blank" rel="noopener">{WA_ICON}WhatsApp us</a><a class="line-link" href="{l["tel"]}">Call {e(l["phone"])}</a><a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a></div>')}
<section class="pg-sec facts-sec" data-tone="light" aria-label="Visit">
  <dl class="facts">
    <div><dt>Address</dt><dd>{e(l["addr"])} {e(l["postal"])}</dd></div>
    <div><dt>Call</dt><dd><a href="{l["tel"]}">{e(l["phone"])}</a></dd></div>
    <div><dt>Text</dt><dd><a href="{l["text_tel"]}">{e(l["text"])}</a></dd></div>
    <div><dt>WhatsApp</dt><dd><a href="{WA}" target="_blank" rel="noopener">Message us — quick answers on prices &amp; hours</a></dd></div>
    <div><dt>Hours</dt><dd>{hours_dl(k)}</dd></div>
    <div><dt>Walk-ins</dt><dd>Welcome — booking ahead secures your time and technician.</dd></div>
  </dl>
  <div class="facts-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
  <a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a><a class="line-link" href="#menu">Menu &amp; prices</a></div>
  {proof(k)}
</section>
<section class="pg-sec here" data-tone="light" aria-labelledby="here-h">
  {sec_head('At this salon', e(H2_HERE[k]), 'here-h')}
  <ul class="here-list">{''.join(f'<li>{e(x)}</li>' for x in HERE[k])}</ul>
  <div class="facts-actions">{''.join(f'<a class="line-link" href="{h}">{e(t)} <span aria-hidden="true">→</span></a>' for t, h in HERE_LINKS[k])}</div>
</section>
{gallery}
<section class="pg-sec menu-sec" data-tone="light" aria-labelledby="menu">
  {sec_head('Menu', 'Services &amp; prices', 'menu', '<p class="sec-aside">Prices are guides and may vary with length, design and add-ons. “+” means from. Your technician will confirm before your service.' + prices_updated_inline() + '</p>')}
  <nav class="mn-jump" aria-label="Menu sections">{''.join(f'<a href="#{slug(c["title"])}">{e(c["title"])}</a>' for c in MENUS[k])}</nav>
  {monthly}
  <div class="menu">{menu_html(k)}</div>
</section>
{faq_html(k)}
<section class="pg-sec other-loc" data-tone="light" aria-label="Our other salon">
  <p class="eyebrow">Our other salon</p><a class="ol-link" href="{other["href"]}"><span>{e(other["name"])}</span><small>{e(other["addr"])}</small><span aria-hidden="true">→</span></a>
</section>
{close_band('Book at<br>' + e(l['name']) + '.', 'Whenever you’re ready')}
''', active='/locations/'))

# ---- /ig/yonge/ — Instagram bio landing page (@beautiquebar_onyonge) --------------------------
# Reached only from the Instagram bio: no header, nav, footer or gallery, and linked from nowhere on the site.
# make_production.py keeps it noindex, nofollow and out of the sitemap. Prices, hours, phone and booking link
# come from the same content files as /locations/yonge/. GTM (production) receives ig_landing_view on load and
# ig_book_click / ig_call_click on taps.
IG_PRICES = {'yonge': [('Bio Gel Full Set', None), ('Bio Gel Refill', None), ('Gel-X Full Set', None), ('Gel-X Refill', None),
                       ('Shellac Spa Manicure', None), ('Spa Pedicure', None), ('Spa Manicure & Pedicure', None), ('Classic Set', 'Classic Set (lashes)')]}
IG_CSS = '''.ig{max-width:440px;min-height:100vh;min-height:100svh;margin:0 auto;padding:20px 16px calc(20px + env(safe-area-inset-bottom,0px));display:flex;flex-direction:column}
.ig .lockup{width:156px}
.ig h1{font-size:32px;line-height:1.1;margin-top:16px}
.ig-where{font-size:14.5px;margin-top:6px}
.ig .hours{margin-top:12px;gap:2px;font-size:14.5px;line-height:1.5}
.ig-prices{margin-top:18px}
.ig-prices .eyebrow{margin-bottom:6px}
.ig .mn-list li{padding:6px 0;line-height:1.5}
.ig-note{font-size:12.5px;opacity:.75;margin-top:6px}
.ig-actions{display:grid;gap:10px;margin-top:18px}
.ig-actions .btn-solid{justify-content:center;min-height:58px;font-size:13px}
.ig-call{display:flex;justify-content:center;align-items:center;min-height:52px;border:1px solid currentColor;font-size:12px;letter-spacing:.18em;text-transform:uppercase;transition:background-color .35s}
.ig-call:hover{background:rgba(33,30,26,.06)}
.ig-actions .line-link{justify-self:center;margin-top:4px}
.ig-foot{margin-top:auto;padding-top:14px;text-align:center}
@media (min-width:721px){.ig{justify-content:center}.ig-foot{margin-top:0}}'''
IG_JS = '''(() => {
  const dl = window.dataLayer = window.dataLayer || [];
  dl.push({event: 'ig_landing_view', location: '%s'});
  document.addEventListener('click', ev => {
    const a = ev.target.closest && ev.target.closest('a[data-ig]');
    if (a) dl.push({event: 'ig_' + a.dataset.ig + '_click', location: '%s'});
  }, true);
})();'''

def ig_landing(k):
    l = LOC[k]
    menu = {i['name']: i['price'] for i in all_items(k)}
    rows = []
    for name, label in IG_PRICES[k]:
        if name not in menu:
            WARNINGS.append(f'Instagram page: "{name}" is no longer on the {l["name"]} menu, so it was left off /ig/{k}/ (full menu is unaffected).')
            continue
        rows.append(f'<li><span>{e(label or name)}</span><span class="pr">{e(menu[name])}</span></li>')
    days = {d for _, ds, _, _ in HOURS[k] for d in ds}
    path, title = f'/ig/{k}/', f'{l["long"]} | Hours, prices & booking'
    desc = f'{l["long"]}, {l["street"]} at York Mills, Toronto. Hours, prices and online booking.'
    return f'''<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{head_common(path, title, desc)}
<link rel="stylesheet" href="/opus.css?v={VERSION}">
<link rel="stylesheet" href="/site.css?v={VERSION}">
<style>{IG_CSS}</style>
<script>{IG_JS % (k, k)}</script>
</head>
<body class="ig-page">
<main class="ig" id="main">
  <span class="lockup" role="img" aria-label="Beautique Bar"></span>
  <h1>{e(l["long"])}</h1>
  <p class="ig-where">{e(l["street"])}, at York Mills{' · Open 7 days' if len(days) == 7 else ''}</p>
  {hours_dl(k)}
  <section class="ig-prices" aria-labelledby="ig-prices-h">
    <p class="eyebrow" id="ig-prices-h">Prices</p>
    <ul class="mn-list">{''.join(rows)}</ul>
    <p class="ig-note">“+” means from.</p>
  </section>
  <div class="ig-actions">
    <a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener" data-ig="book">Book now <span aria-hidden="true">↗</span></a>
    <a class="ig-call" href="{l["tel"]}" data-ig="call">Call {e(l["phone"])}</a>
    <a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a>
  </div>
  <p class="ig-foot"><a class="line-link" href="{l["href"]}">Full price list</a></p>
</main>
</body>
</html>
'''

add('/ig/yonge/', ig_landing('yonge'))

# ---- /back/ — COMEBACK15 win-back text landing page (added 31 Oct 2026) -------------------------
# Reached only from the win-back text message: beautiquebar.com/back 302s here with
# utm_source=sms&utm_medium=text&utm_campaign=comeback15 (opus-design-v1/_redirects), so GA4 credits the visit to the text.
# Linked from nowhere on the site; make_production.py keeps it noindex, nofollow and out of the sitemap.
# GTM (production) receives winback_view on load, winback_code_copy on Copy, and the usual
# bb_book / bb_call (bb_salon 'bridlewood', bb_placement 'winback') so the existing GA4/Ads wiring counts them.
WB_CODE, WB_ENDS = 'COMEBACK15', 'November 30, 2026'
WB_CSS = IG_CSS + '''
.wb-offer{font-size:16px;line-height:1.5;margin-top:12px}
.wb-code{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:18px;padding:14px 16px;border:1px dashed currentColor}
.wb-code strong{font-size:24px;letter-spacing:.12em}
.wb-copy{min-height:44px;padding:0 16px;border:1px solid currentColor;background:none;color:inherit;font:inherit;font-size:12px;letter-spacing:.18em;text-transform:uppercase;cursor:pointer}
.wb-how{font-size:14px;line-height:1.5;margin-top:10px}
.wb-fine{font-size:12.5px;opacity:.75;margin-top:14px;line-height:1.5}'''
WB_JS = '''(() => {
  const dl = window.dataLayer = window.dataLayer || [];
  dl.push({event: 'winback_view', campaign: 'comeback15'});
  document.addEventListener('click', ev => {
    const a = ev.target.closest && ev.target.closest('[data-wb]');
    if (!a) return;
    const kind = a.dataset.wb;
    if (kind === 'copy') {
      const done = () => { a.textContent = 'Copied'; };
      try { navigator.clipboard.writeText('%s').then(done, done); } catch (_) { done(); }
      dl.push({event: 'winback_code_copy', campaign: 'comeback15'});
    } else {
      dl.push({event: 'bb_' + kind, bb_salon: 'bridlewood', bb_link: a.href, bb_placement: 'winback'});
    }
  }, true);
})();'''

def winback_landing():
    l = LOC['warden']
    path, title = '/back/', 'Welcome back | 15% off at Beautique Bar Bridlewood'
    desc = f'15% off your next visit of $50 or more at Beautique Bar & Nails For You, Bridlewood Mall. Code {WB_CODE}.'
    return f'''<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{head_common(path, title, desc)}
<link rel="stylesheet" href="/opus.css?v={VERSION}">
<link rel="stylesheet" href="/site.css?v={VERSION}">
<style>{WB_CSS}</style>
<script>{WB_JS % WB_CODE}</script>
</head>
<body class="ig-page">
<main class="ig" id="main">
  <span class="lockup" role="img" aria-label="Beautique Bar"></span>
  <h1>Welcome back.</h1>
  <p class="wb-offer">We’ve missed you. Take <strong>15% off</strong> your next visit of $50 or more at Beautique Bar &amp; Nails For You, {e(l["name"])}.</p>
  <div class="wb-code"><strong>{WB_CODE}</strong><button type="button" class="wb-copy" data-wb="copy">Copy code</button></div>
  <p class="wb-how">Enter the code at checkout when you book online, or mention it at the front desk.</p>
  <div class="ig-actions">
    <a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener" data-wb="book">Book now <span aria-hidden="true">↗</span></a>
    <a class="ig-call" href="{l["tel"]}" data-wb="call">Call {e(l["phone"])}</a>
  </div>
  <p class="wb-fine">Valid on services until {WB_ENDS}. One use per client, minimum sale $50. {e(l["addr"])}.</p>
</main>
</body>
</html>
'''

add('/back/', winback_landing())

# ---- /shop/ — retired 24 Sep 2026 (products were for a grant); /shop/ 301s to / via _redirects.

# ---- /contact/ -------------------------------------------------------------------------------
def contact_col(l):
    return f'''<div class="ct-col"><p class="eyebrow">{e(l["area"])}</p><h2>{e(l["name"])}</h2><p class="addr">{e(l["addr"])}</p>
    <ul class="ct-list"><li><span>Call</span><a href="{l["tel"]}">{e(l["phone"])}</a></li><li><span>Text</span><a href="{l["text_tel"]}">{e(l["text"])}</a></li><li><span>WhatsApp</span><a href="{WA}" data-bb-salon="{'yonge' if l['id'] == 'yonge' else 'bridlewood'}" target="_blank" rel="noopener">Message us ↗</a></li><li><span>Email</span><a href="mailto:{EMAILS[l["id"]]}">{EMAILS[l["id"]]}</a></li>
    <li><span>Book</span><a href="{e(l["book"])}" target="_blank" rel="noopener">Book online with Fresha ↗</a></li><li><span>Visit</span><a href="{e(l["maps"])}" target="_blank" rel="noopener">Directions ↗</a></li><li><span>Hours</span><em class="ct-val">{e(hours_inline(l["id"]))}</em></li></ul></div>'''
# ---- /gallery/ (new page) -------------------------------------------------------------------
add('/gallery/', page('/gallery/', 'Gallery | Beautique Bar', 'Recent nail sets by Beautique Bar technicians at Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Gallery',None)], 'Our work.', f'Recent sets by our technicians, with a new one added every week. See more at <a href="{IG}" target="_blank" rel="noopener">@beautiquebar88</a> and <a href="{IG_YONGE}" target="_blank" rel="noopener">@beautiquebar_onyonge</a>.')}
<section class="pg-sec pg-sec--flush" data-tone="light" aria-label="Nail sets">
  <div class="work-grid">{''.join(work_fig(w[0], 'wk', i > 5) for i, w in enumerate(WORK))}</div>
</section>
{close_band('Seen something<br>you love?')}
''', active=None))

add('/contact/', page('/contact/', 'Contact | Beautique Bar', 'Call, text or book online with Beautique Bar on Yonge or at Bridlewood Mall.', f'''
{hero([('Home','/'),('Contact',None)], 'Get in touch.', 'Have a question or want to book? Call, text or book online with the salon nearest you.')}
<section class="pg-sec contact" data-tone="light" aria-label="Contact details">
  <div class="ct-pair">{contact_col(LOC['yonge'])}{contact_col(LOC['warden'])}</div>
  <div class="ct-more"><p class="eyebrow">Follow us</p><p><a class="line-link" href="{IG}" target="_blank" rel="noopener">Instagram ↗</a> <a class="line-link" href="{FB}" target="_blank" rel="noopener">Facebook ↗</a></p></div>
</section>
''', active=None))

# ---- /privacy/ & /terms/ (legal text as on the live site) ------------------------------------
PRIVACY = f'''<p class="legal-date">Last updated: 28 September 2026</p>
<p>This Privacy Policy explains how Beautique Bar (“we”, “us”), operating salons at 3430 Yonge Street, Toronto and 2900 Warden Avenue (Bridlewood Mall), Scarborough, collects, uses and safeguards personal information when you visit beautiquebar.com or contact us to book an appointment.</p>
<h2>Information we collect</h2>
<p><strong>Information you give us.</strong> If you call, text, email or message us on social media, we receive what you choose to share, such as your name, phone number, email address and appointment details.</p>
<p><strong>Information collected automatically.</strong> When you use this website, our analytics and advertising tools may collect your IP address, device and browser type, approximate location, the pages you view, how you arrived on the site, and which buttons or links you select (for example Book, Call, Text, Directions or Email). This information is collected using cookies and similar technologies.</p>
<p>We do not collect payment information through this website.</p>
<h2>How we use your information</h2>
<ul><li>To respond to your enquiries and manage your appointments.</li><li>To understand how the website is used and to improve it.</li><li>To measure and improve our advertising, including showing our ads to people who have visited our site.</li><li>To keep the website secure and working properly.</li></ul>
<h2>Cookies, analytics and advertising</h2>
<p>This website uses the following Google services, loaded through Google Tag Manager:</p>
<ul><li><strong>Google Analytics 4</strong> to measure visits and interactions, such as page views and clicks on our booking, call, text, directions and email links.</li><li><strong>Google Ads conversion tracking and remarketing</strong> to measure which of our ads lead to bookings and enquiries, and to show our ads to people who previously visited the site.</li></ul>
<p>These services set cookies or use identifiers on your device and send information to Google, which may process it outside Canada, including in the United States. Google’s use of this information is described at <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener">policies.google.com/technologies/partner-sites</a>.</p>
<p>You can control this in several ways: change your browser settings to block or delete cookies; use Google’s <a href="https://adssettings.google.com" target="_blank" rel="noopener">Ads Settings</a> to opt out of personalized advertising; or install the <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener">Google Analytics opt-out browser add-on</a>. Blocking cookies will not stop you from using the site.</p>
<h2>Booking with Fresha</h2>
<p>Online bookings are made through Fresha, a third-party booking platform. When you select Book, you leave our website and go to Fresha, where the information you enter is collected and handled under Fresha’s own privacy policy and terms. We receive the details of your booking so we can serve you.</p>
<h2>Sharing your information</h2>
<p>We do not sell your personal information. We share it only with the service providers described above (Google and Fresha), with providers who host and secure this website, and where required by law.</p>
<h2>How we protect it</h2>
<p>This website is served securely over HTTPS. We keep enquiry and booking information only as long as needed to assist you or as required by law.</p>
<h2>Your choices and rights</h2>
<p>You may ask to see, correct or delete the personal information we hold about you, or withdraw your consent to how we use it, by contacting us at <a href="mailto:{EMAIL_Y}">{EMAIL_Y}</a> (Yonge &amp; York Mills) or <a href="mailto:{EMAIL_W}">{EMAIL_W}</a> (Bridlewood Mall). If you would rather not receive promotional messages from us, tell us and we will stop.</p>
<h2>Contact us</h2><p>Questions about this policy? Email <a href="mailto:{EMAIL_Y}">{EMAIL_Y}</a> (Yonge &amp; York Mills) or <a href="mailto:{EMAIL_W}">{EMAIL_W}</a> (Bridlewood Mall), or reach out via <a href="{IG}" target="_blank" rel="noopener">Instagram</a>.</p>
<p>We may update this policy from time to time. The latest version, with its date, always appears on this page.</p>'''
TERMS = f'''<p>These terms apply to your use of the Beautique Bar website and to the services we provide at our Toronto locations. By using this site or booking with us, you agree to the following.</p>
<h2>Appointments &amp; walk-ins</h2><p>We welcome walk-ins and recommend booking in advance to secure your preferred time and technician. Please let us know as early as possible if you need to reschedule or cancel so we can offer the slot to another guest.</p>
<h2>Pricing</h2><p>Prices shown on this website are guides and may vary with nail length, design complexity and add-on services. Prices marked “+” start from the listed rate. We’ll always confirm pricing with you before your service.</p>
<h2>Services &amp; results</h2><p>Our team takes pride in delivering high-quality, hygienic services. If you have any concerns about your service, please tell us before you leave so we can make it right.</p>
<h2>Website content</h2><p>Content on this site is provided for general information. While we keep it as accurate as possible, services, pricing and availability may change without notice.</p>
<h2>Contact</h2><p>Questions about these terms? Email <a href="mailto:{EMAIL_Y}">{EMAIL_Y}</a> (Yonge &amp; York Mills) or <a href="mailto:{EMAIL_W}">{EMAIL_W}</a> (Bridlewood Mall).</p>'''
for path, t, d, body in [('/privacy/', 'Privacy Policy', 'How Beautique Bar collects, uses and protects your personal information.', PRIVACY),
                         ('/terms/', 'Terms & Services', 'The terms that apply to your use of the Beautique Bar website and services.', TERMS)]:
    add(path, page(path, f'{t} | Beautique Bar', d, f'''
{hero([('Home','/'),(t,None)], e(t) + '.', 'Legal')}
<section class="pg-sec" data-tone="light"><div class="prose">{body}</div></section>'''))

# ---- /thank-you/ -----------------------------------------------------------------------------
add('/thank-you/', page('/thank-you/', 'Thank You | Beautique Bar', 'Thanks for getting in touch with Beautique Bar.', f'''
{hero([('Home','/'),('Thank you',None)], 'Thank you.', 'Your message is on its way. We’ll get back to you as soon as we can — usually within one business day.')}
<section class="pg-sec" data-tone="light"><div class="prose"><p>Need a faster answer? Call or text us directly:</p><ul>{''.join(f'<li>{e(l["name"])}: <a href="{l["tel"]}">{e(l["phone"])}</a></li>' for l in LOC.values())}</ul><p><a class="line-link" href="/">← Back to home</a></p></div></section>'''))

# ---- 404 -------------------------------------------------------------------------------------
PAGES['/404.html'] = page('/404/', 'Page Not Found | Beautique Bar', 'This page could not be found.', f'''
{hero([('Home','/'),('Not found',None)], 'Page not<br>found.', 'The page you’re looking for has moved or doesn’t exist. Try one of these instead.')}
<section class="pg-sec" data-tone="light">{svc_list([('Nails', '/nails/', 'Manicures, pedicures, Shellac, Bio Gel and acrylic.', BOTH), ('Skin & Lashes', '/skin/', 'Lashes, facials, waxing and threading.', BOTH), ('Locations', '/locations/', 'Book, call or get directions.', BOTH)])}</section>''')

# ---- /blog/ & posts --------------------------------------------------------------------------
def seo_title(p):
    """Search title for a post: front-matter seoTitle if set, else the headline + brand when that fits (~65 chars)."""
    t = p['seo_title'] or p['title']
    return t if len(t) + 16 > 65 else f'{t} | {BUSINESS_NAME}'

def fix_heading_levels(html_):
    """Article bodies sit under the page H1: make their headings start at H2 and never skip a level."""
    out, stack = [], []          # stack of (source level, output level)
    def sub(m):
        close, lv = m.group(1), int(m.group(2))
        if close:
            return f'</h{out.pop()}{m.group(3)}' if out else m.group(0)
        while stack and stack[-1][0] >= lv:
            stack.pop()
        new = min((stack[-1][1] + 1) if stack else 2, 6)
        stack.append((lv, new)); out.append(new)
        return f'<h{new}{m.group(3)}'
    return re.sub(r'<(/?)h([1-6])([ >])', sub, html_)

def fmt_date(d):
    return d.strftime('%B %-d, %Y')

rows = ''.join(f'''<li><a href="/blog/{p["slug"]}/"><span class="bl-meta"><time datetime="{p["date"].isoformat()}">{fmt_date(p["date"])}</time><span>{e(p["cat"])}</span></span>
  <span class="bl-title">{e(p["title"])}</span><span class="bl-desc">{e(p["desc"])}</span></a></li>''' for p in POSTS)
add('/blog/', page('/blog/', 'Beauty Blog | Beautique Bar', 'Nail, lash and skin care guides from Beautique Bar in Toronto.', f'''
{hero([('Home','/'),('Blog',None)], 'Blog.', 'Guides to nails, lashes and skin care from the Beautique Bar team.')}
<section class="pg-sec blog" data-tone="light" aria-label="Articles"><ul class="bl-list">{rows}</ul></section>''', active=None))

RELATED = {  # post -> (service label, href)
  'Acrylic Nails': ('Acrylic', '/nails/acrylic/'), 'Bio Gel Nails': ('Bio Gel', '/nails/bio-gel/'), 'Manicure and Pedicure': ('Manicure & Pedicure', '/nails/manicure-pedicure/'),
  'Shellac Manicure': ('Shellac', '/nails/manicure-pedicure/#shellac'), 'Nail Enhancements': ('Nails', '/nails/'), 'Beauty Tips': ('Nails', '/nails/'),
  'Eyelash Extensions': ('Eyelash Extensions', '/eyelash-extensions/'), 'Facials': ('Facials', '/skin/facials/'),
  'Facial Hair': ('Facial Hair Removal', '/skin/facial-hair-removal/'), 'Body Hair': ('Body Hair Removal', '/skin/body-hair-removal/'),
}
MD = markdown.Markdown(extensions=['tables', 'sane_lists'])
for p in POSTS:
    body, removed = strip_prices(p['slug'], p['body'])
    MD.reset()
    art = MD.convert(body)
    art = fix_heading_levels(art)
    note = POST_NOTES.get(p['slug'], '')
    if removed:
        note += PRICE_NOTE
    if p['slug'] in POST_NOTES:
        AUDIT.setdefault(p['slug'], []).append('Covers methods/services not on either salon menu (see note added to the article).')
    if p['date'].year <= 2024:
        AUDIT.setdefault(p['slug'], []).append(f'Written {fmt_date(p["date"])} — check trends and claims are still current.')
    lbl, href = RELATED.get(p['cat'], ('Nails', '/nails/'))
    add(f'/blog/{p["slug"]}/', page(f'/blog/{p["slug"]}/', seo_title(p), p['desc'], f'''
<article class="post">
  <header class="pg-hero post-head" data-tone="light"><div class="pg-hero-text">{crumbs([('Home','/'),('Blog','/blog/'),(p['cat'] or 'Article',None)])}
    <h1>{e(p["title"])}</h1><p class="lead">{e(p["desc"])}</p><p class="post-meta eyebrow"><time datetime="{p["date"].isoformat()}">{fmt_date(p["date"])}</time> · {e(p["cat"])}</p></div></header>
  <div class="pg-sec post-body" data-tone="light"><div class="prose">{note}{art}</div></div>
</article>
<section class="pg-sec post-cta" data-tone="light" aria-label="Related service">
  <p class="eyebrow">Related</p><a class="ol-link" href="{href}"><span>{e(lbl)}</span><small>Treatments, salons and prices</small><span aria-hidden="true">→</span></a>
  <p><a class="line-link" href="/blog/">← All articles</a></p>
</section>
{close_band()}''', active=None, bodyclass='is-post'))

# ---- RSS -------------------------------------------------------------------------------------
items = ''.join(f'''<item><title>{e(p["title"])}</title><link>{SITE_URL}/blog/{p["slug"]}/</link><guid>{SITE_URL}/blog/{p["slug"]}/</guid><description>{e(p["desc"])}</description><pubDate>{datetime.datetime.combine(p["date"], datetime.time()).strftime("%a, %d %b %Y 00:00:00 GMT")}</pubDate></item>''' for p in POSTS)
RSS = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Beautique Bar — Beauty Blog</title><description>Nail, lash and skin care guides from Beautique Bar in Toronto.</description><link>{SITE_URL}/</link>{items}</channel></rss>'

# ----------------------------------------------------------------------------------------------
HOME_IMG = {'salon-3': 'stock-hands-rest.webp', 'salon-hero': 'stock-manicure-white.webp', 'salon-mauve': 'stock-manicure-mauve.webp',
            'svc-lashes': 'stock-lashes.webp', 'svc-facials': 'stock-facial.webp', 'blog': 'stock-hands-towel.webp'}

HOME_TITLE = 'Beautique Bar | Nail Salon in Toronto & Scarborough'
HOME_DESC = 'Nail salon at Yonge & York Mills, Toronto and Bridlewood Mall, Scarborough. Manicures, pedicures, Shellac, gel and acrylic nails, lashes and facials.'

def home_head():
    website = {'@context': 'https://schema.org', '@type': 'WebSite', '@id': f'{SITE_URL}/#website', 'name': BUSINESS_NAME,
               'url': SITE_URL + '/', 'inLanguage': 'en-CA', 'publisher': {'@id': f'{SITE_URL}/#organization'}}
    ld = [website, org_ld()] + [business_ld(k) for k in LOC]
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False, separators=(",", ":"))}</script>\n' for d in ld)
    return f'''<meta name="robots" content="noindex,nofollow">
<title>{e(HOME_TITLE)}</title>
<meta name="description" content="{e(HOME_DESC)}">
<link rel="canonical" href="{SITE_URL}/">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{head_common('/', HOME_TITLE, HOME_DESC)}
<link rel="preload" as="image" href="/img/yonge-pedicure-row-1600.webp" imagesrcset="/img/yonge-pedicure-row-800.webp 800w, /img/yonge-pedicure-row-1200.webp 1200w, /img/yonge-pedicure-row-1600.webp 1600w, /img/yonge-pedicure-row.webp 2400w" imagesizes="(max-aspect-ratio:4/3) 134vh, 100vw" fetchpriority="high">
<link rel="stylesheet" href="/opus.css?v={VERSION}">
{lds}<!--/HEAD-->'''

def refresh_home():
    p = OUT / 'index.html'
    s = p.read_text()
    s = s.replace('<html lang="en">', '<html lang="en-CA">')
    s = re.sub(r'<header class="site-header".*?</header>(\s*<div class="menu-panel".*?</div>\s*</nav>\s*</div>)?', header(None, 'dark'), s, count=1, flags=re.S)
    s = re.sub(r'<footer class="site-footer">.*?</footer>', footer(), s, count=1, flags=re.S)
    s = re.sub(r'<dialog class="book-dialog".*?</dialog>', dialog(), s, count=1, flags=re.S)
    for a, b in HOME_IMG.items():
        s = re.sub(r'https://beautiquebar\.com/_astro/' + a + r'\.[A-Za-z0-9_-]+\.webp', '/img/' + b, s)
    s = s.replace('https://beautiquebar.com/', '/')
    s = re.sub(r'src="img/', 'src="/img/', s)
    s = re.sub(r'href="/?opus\.css[^"]*"', f'href="/opus.css?v={VERSION}"', s)
    s = re.sub(r'src="/?opus\.js[^"]*"', f'src="/opus.js?v={VERSION}"', s)
    if 'favicon.ico' not in s:
        s = s.replace('<link rel="preconnect" href="https://fonts.googleapis.com">', '<link rel="icon" href="/favicon.ico" sizes="any">\n<link rel="icon" href="/favicon.ico" sizes="32x32">\n<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n' + '<link rel="preconnect" href="https://fonts.googleapis.com">', 1)
    if '/site.js' not in s:
        s = s.replace('<script src="/opus.js', f'<script src="/site.js?v={VERSION}" defer></script>\n<script src="/opus.js', 1)
    s = re.sub(r'site\.js\?v=\d+', f'site.js?v={VERSION}', s)
    s = s.replace('<a class="skip" href="#nails">', '<a class="skip" href="#nails">')
    home_work = f'''<!--WORK-->
<!-- 08 · OUR WORK — finished sets from the salons' own Instagram. -->
<section class="home-work" id="work" data-tone="light" aria-labelledby="work-title">
  <div class="look-head">
    <div><p class="eyebrow">08 — Our work</p><h2 id="work-title">Fresh from<br>the table.</h2></div>
    <a class="line-link" href="/gallery/">See the gallery <span aria-hidden="true">→</span></a>
  </div>
  {work_strip(['plum-chrome-gems', 'white-french-gold', 'painted-florals-green', 'leopard-tips'])}
</section>
<!--/WORK-->'''
    s = re.sub(r'<!--WORK-->.*?<!--/WORK-->', lambda m: home_work, s, count=1, flags=re.S)
    # The visual headline stays a tagline; the page's one H1 says what the business is (approved 22 Oct 2026).
    s = s.replace('<p class="kicker eyebrow">Beautique Bar <i>/</i> Yonge &amp; York Mills <i>/</i> Bridlewood Mall</p>',
                  '<h1 class="kicker eyebrow">Nail salons <i>/</i> Yonge &amp; York Mills <i>/</i> Bridlewood Mall</h1>')
    s = re.sub(r'<h1 class="title" id="opening-title">(.*?)</h1>', r'<p class="title display" id="opening-title">\1</p>', s, count=1, flags=re.S)
    s = patch_home_facts(s)
    # the generated <head> block sits between the robots meta and <!--/HEAD--> (or <!--HEADSLOT--> once cleared)
    if '<!--HEADSLOT-->' in s:
        s = s.replace('<!--HEADSLOT-->', home_head(), 1)
    else:
        i, j = s.index('<meta name="robots"'), s.rindex('<!--/HEAD-->') + len('<!--/HEAD-->')
        s = s[:i] + home_head() + s[j:]
    p.write_text(s)

# ---- Responsive images ----------------------------------------------------------------------
# Phones get smaller files; desktops keep the full-size image. Variants are generated from the originals in /img
# (never edited by hand) and every <img> in the output gets a srcset automatically, so new pages need nothing extra.
IMG = OUT / 'img'
SIZES_PHOTO = '(max-width:720px) 100vw, 90vw'           # desktop always resolves to the original (no quality change)
SIZES_THUMB = '(max-width:520px) 48vw, (max-width:1100px) 33vw, 25vw'

def make_variants():
    from PIL import Image
    made = 0
    for f in sorted(IMG.glob('*.webp')):
        stem = f.stem
        if re.search(r'-(xs|\d{3,4})$', stem):
            continue
        w, h = Image.open(f).size
        targets = [(f'{stem[:-3]}-xs', 400)] if stem.endswith('-sm') else [(f'{stem}-{n}', n) for n in (800, 1200) if w >= n + 300]
        for name, tw in targets:
            out = IMG / f'{name}.webp'
            if out.exists() and out.stat().st_mtime >= f.stat().st_mtime:
                continue
            im = Image.open(f); im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
            im.resize((tw, round(h * tw / w)), Image.LANCZOS).save(out, 'WEBP', quality=80, method=6)
            made += 1
    return made

def add_srcset(doc):
    def one(m):
        tag = m.group(0)
        if 'srcset=' in tag or ' data-nosrcset' in tag:
            return tag
        src = re.search(r'src="/img/([^"]+)\.webp"', tag)
        wm = re.search(r'width="(\d+)"', tag)
        if not src or not wm:
            return tag
        stem, w = src.group(1), int(wm.group(1))
        if stem.endswith('-sm'):
            cands = [(f'{stem[:-3]}-xs', 400)]
            sizes = SIZES_THUMB
        else:
            cands = [(f'{stem}-{n}', n) for n in (800, 1200)]
            sizes = SIZES_PHOTO
        from PIL import Image
        full = Image.open(IMG / f'{stem}.webp').size[0] if (IMG / f'{stem}.webp').exists() else w
        parts = [f'/img/{n}.webp {nw}w' for n, nw in cands if (IMG / f'{n}.webp').exists()]
        if not parts:
            return tag
        parts.append(f'/img/{stem}.webp {full}w')
        return tag.replace(src.group(0), f'{src.group(0)} srcset="{", ".join(parts)}" sizes="{sizes}"', 1)
    # leave <picture> fallbacks alone (their <source> already chooses the file)
    chunks = re.split(r'(<picture>.*?</picture>)', doc, flags=re.S)
    return ''.join(c if c.startswith('<picture>') else re.sub(r'<img\b[^>]*>', one, c) for c in chunks)

def patch_home_facts(s):
    """The homepage body is hand-authored. Keep its salon phone, hours and booking links in step with
    /content/salons.yml, so an edit in Pages CMS shows up on the homepage too."""
    for k, l in LOC.items():
        disp = l['phone'].replace('-', ' ')
        def block(m):
            b = m.group(0)
            b = re.sub(r'href="tel:[^"]*">[^<]*</a>', f'href="{l["tel"]}">{e(disp)}</a>', b)
            b = re.sub(r'<p class="hours-line">.*?</p>', lambda _: f'<p class="hours-line">{e(hours_inline(k))}</p>', b)
            b = re.sub(r'href="https://www\.fresha\.com[^"]*"', lambda _: f'href="{e(l["book"])}"', b)
            b = re.sub(r'href="https://(?:www\.google\.[a-z.]+/maps|maps\.google\.com/)[^"]*"', lambda _: f'href="{e(l["maps"])}"', b)
            return b
        s, n = re.subn(r'<h3>' + re.escape(e(l['name'])) + r'</h3>.*?<div class="salon-actions">.*?</div>', block, s, count=1, flags=re.S)
        assert n == 1, f'homepage salon block for {l["name"]} not found'
        def li(m):
            t = m.group(0)
            if f'cl-meta">{e(l["street"])} ' in t:
                t = re.sub(r'href="https://www\.fresha\.com[^"]*"', lambda _: f'href="{e(l["book"])}"', t)
            return t
        s = re.sub(r'<li><a [^>]*>.*?</li>', li, s, flags=re.S)
    return s

def check_home_facts(s):
    """The homepage body is hand-authored: fail the build if its contact links or hours drift from site_config."""
    body = re.sub(r'<(header|footer|dialog)\b.*?</\1>', '', s[s.index('<body'):], flags=re.S)
    ok = {v for l in LOC.values() for v in (l['tel'], l['text_tel'], html.escape(l['book']), html.escape(l['maps']))}
    bad = [u for u in re.findall(r'href="((?:tel:|sms:|https://www\.fresha|https://www\.google\.[a-z.]+/maps)[^"]*)"', body) if u not in ok]
    bad += [h for h in re.findall(r'<p class="hours-line">(.*?)</p>', body) if h not in {e(hours_inline(k)) for k in LOC}]
    assert not bad, f'Homepage has contact details / hours that differ from site_config.py: {bad}'

def space_br(doc):
    """Line breaks inside headings are for the eye only: give text readers a space so "Make time<br>for" isn't read as "timefor"."""
    return re.sub(r'<(h[1-3]|p class="[^"]*(?:title|display)[^"]*")([^>]*)>(.*?)</', lambda m: m.group(0).replace('<br>', ' <br>').replace('  <br>', ' <br>'), doc, flags=re.S)

def main():
    n = make_variants()
    for path in list(PAGES):
        PAGES[path] = space_br(add_srcset(PAGES[path]))
    for path, doc in PAGES.items():
        if path.endswith('.html'):
            f = OUT / path.lstrip('/')
        else:
            f = OUT / path.strip('/') / 'index.html'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(doc)
    (OUT / 'rss.xml').write_text(RSS)
    refresh_home()
    home = OUT / 'index.html'
    check_home_facts(home.read_text())
    home.write_text(space_br(add_srcset(home.read_text())))
    print(f'{n} responsive image variants generated')
    # review file
    lines = ['# Blog audit (generated)', '']
    for p in POSTS:
        notes = AUDIT.get(p['slug'], [])
        lines.append(f'- `/blog/{p["slug"]}/` — ' + ('; '.join(notes) if notes else 'no automatic flags'))
    (SRC / 'BLOG-AUDIT.md').write_text('\n'.join(lines) + '\n')
    json.dump({k: MENUS[k] for k in MENUS}, open(SRC / 'menus.parsed.json', 'w'), indent=1)
    print(f'{len(PAGES)} pages + rss.xml written to {OUT}')
    for w in dict.fromkeys(WARNINGS):
        print('WARNING:', w)
        if os.environ.get('GITHUB_ACTIONS'):
            print(f'::warning title=Price menu::{w}')

if __name__ == '__main__':
    main()
