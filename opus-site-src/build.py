#!/usr/bin/env python3
"""Beautique Bar — Opus site generator.

Builds every inner page of the Opus preview into ../opus-design-v1/ at the SAME paths as the
live beautiquebar.com site (folder/index.html, so Cloudflare Pages serves /path/ and redirects
/path -> /path/ exactly like the live site). The homepage (index.html) stays hand-authored;
this script only refreshes its shared header, footer and booking dialog.

Facts come from the live site's own content files (copied into this folder):
  yonge.md / warden.md   -> location price menus (parsed; nothing is typed in by hand)
  blog/*.md              -> the 17 blog articles
Every price shown on a service page is looked up by exact name in those menus; a name that
does not exist makes the build fail, so no price can be invented.
"""
import html, json, os, re, shutil, datetime
from pathlib import Path
import markdown

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / 'opus-design-v1'
VERSION = '6'
e = html.escape
CUR = ' aria-current="page"'
LAZY = ' loading="lazy"'
def idattr(r):
    return f' id="{r[2]}"' if len(r) > 2 and r[2] else ''

# ----------------------------------------------------------------------------------------------
# Locations (from the live site config: src/lib/site.ts)
LOC = {
  'yonge': dict(
    id='yonge', name='Yonge & York Mills', long='Beautique Bar on Yonge', href='/locations/yonge/',
    area='Toronto', street='3430 Yonge Street', city='Toronto, ON',
    addr='3430 Yonge Street, Toronto, ON',
    phone='416-484-7788', tel='tel:+14164847788', text='437-434-4884', text_tel='sms:+14374344884',
    book='https://www.fresha.com/a/beautique-bar-on-yonge-toronto-3430-yonge-street-e0fzhnga/booking?menu=true',
    maps='https://www.google.com/maps/search/?api=1&query=3430%20Yonge%20St%2C%20Toronto%2C%20ON',
    where='Right on the Yonge line, north of Lawrence Avenue and south of York Mills.',
    serves='Yonge & York Mills, Lawrence Park, Leaside and North Toronto',
    photo=('img/yonge-colour-wall.webp', 1170, 1554, 'Inside Beautique Bar on Yonge: the colour wall, chandelier and stations'),
  ),
  'warden': dict(
    id='warden', name='Bridlewood Mall', long='Beautique Bar on Warden', href='/locations/warden/',
    area='Scarborough', street='2900 Warden Avenue', city='Scarborough, ON',
    addr='Bridlewood Mall, 2900 Warden Avenue, 2nd floor by the library, Scarborough, ON',
    phone='647-770-5232', tel='tel:+16477705232', text='647-770-5232', text_tel='sms:+16477705232',
    book='https://www.fresha.com/book-now/nails-for-you-m7weksrj/all-offer?share&pId=32159',
    maps='https://www.google.com/maps/search/?api=1&query=Beautique%20Bar%2C%20Bridlewood%20Mall%2C%202900%20Warden%20Ave%2C%20Scarborough%2C%20ON',
    where='On the 2nd floor of Bridlewood Mall, by the library.',
    serves='Scarborough, Bridlewood, L’Amoreaux and surrounding communities',
    photo=None,
  ),
}
EMAIL = 'info@beautiquebar.com'
IG = 'https://www.instagram.com/beautiquebar88'
FB = 'https://www.facebook.com/Beautiquebaryonge'
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

MENUS = {k: parse_menu((SRC / f'{k}.md').read_text()) for k in LOC}

def all_items(loc):
    for c in MENUS[loc]:
        yield from c['items']
        for s in c.get('subs', []):
            yield from s['items']

def price(loc, name):
    for it in all_items(loc):
        if it['name'] == name:
            return it['price']
    raise SystemExit(f'Menu item not found at {loc}: {name!r}')

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

# ----------------------------------------------------------------------------------------------
# Blog
def load_posts():
    posts = []
    for f in sorted((SRC / 'blog').glob('*.md')):
        raw = f.read_text()
        _, fm, body = raw.split('---', 2)
        meta = {}
        for line in fm.strip().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip().strip('"')
        posts.append(dict(slug=f.stem, title=meta['title'], desc=meta.get('description', ''),
                          date=datetime.date.fromisoformat(meta['pubDate']), cat=meta.get('category', ''), body=body))
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
# Chrome
NAV = [('Nails', '/nails/'), ('Skin & Lashes', '/skin/'), ('Locations', '/locations/')]

def header(active, tone='light'):
    links = ''.join(f'<a href="{h}"{CUR if active == h else ""}>{e(t)}</a>' for t, h in NAV)
    return f'''<header class="site-header" data-bg="{tone}">
  <a class="wordmark" href="/" aria-label="Beautique Bar — home">Beautique Bar</a>
  <nav class="nav" aria-label="Main">{links}</nav>
  <div class="hdr-actions">
    <button class="book-btn" type="button" data-book aria-label="Book Appointment"><span class="bk-full">Book Appointment</span><span class="bk-short" aria-hidden="true">Book</span></button>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu-panel"><span class="menu-lines" aria-hidden="true"></span><span class="menu-label">Menu</span></button>
  </div>
</header>
<div class="menu-panel" id="menu-panel" hidden>
  <nav aria-label="Mobile">
    <ul class="mp-main">{''.join(f'<li><a href="{h}">{e(t)}</a></li>' for t, h in NAV)}</ul>
    <ul class="mp-sub"><li><a href="/eyelash-extensions/">Eyelash Extensions</a></li><li><a href="/shop/">Shop</a></li><li><a href="/blog/">Blog</a></li><li><a href="/contact/">Contact</a></li></ul>
    <div class="mp-book"><p class="eyebrow">Book online</p>{''.join(f'<a href="{e(l["book"])}" target="_blank" rel="noopener">{e(l["name"])} <span aria-hidden="true">↗</span></a>' for l in LOC.values())}</div>
  </nav>
</div>'''

def footer():
    locs = ''.join(f'''<div class="ft-loc"><p class="ft-h"><a href="{l["href"]}">{e(l["name"])}</a></p>
      <p>{e(l["addr"])}</p><p><a href="{l["tel"]}">Call {e(l["phone"])}</a>{f' · Text {e(l["text"])}' if l["text"] != l["phone"] else ' · Call or text'}</p></div>''' for l in LOC.values())
    return f'''<footer class="site-footer">
  <div class="ft-grid">
    <div class="ft-brand"><a class="wordmark" href="/">Beautique Bar</a><p>Nails, lashes and skin at Yonge &amp; York Mills and Bridlewood Mall.</p></div>
    <div class="ft-locs">{locs}</div>
    <nav class="ft-nav" aria-label="Footer">
      <ul><li><a href="/nails/">Nails</a></li><li><a href="/skin/">Skin &amp; Lashes</a></li><li><a href="/eyelash-extensions/">Eyelash Extensions</a></li><li><a href="/locations/">Locations</a></li></ul>
      <ul><li><a href="/shop/">Shop</a></li><li><a href="/blog/">Blog</a></li><li><a href="/contact/">Contact</a></li><li><a href="mailto:{EMAIL}">{EMAIL}</a></li></ul>
      <ul><li><a href="{IG}" target="_blank" rel="noopener">Instagram ↗</a></li><li><a href="{FB}" target="_blank" rel="noopener">Facebook ↗</a></li></ul>
    </nav>
  </div>
  <div class="ft-base">
    <span>© Beautique Bar · Design preview — not the live site</span>
    <span class="foot-links"><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="#top">Back to top ↑</a><button type="button" class="notes-toggle" aria-pressed="false">Photography notes</button></span>
  </div>
</footer>'''

def dialog():
    rows = ''.join(f'<a href="{e(l["book"])}" target="_blank" rel="noopener"><span>{e(l["name"])}</span><small>{e(l["street"])}, {e(l["area"])} · Book with Fresha ↗</small></a>' for l in LOC.values())
    return f'''<dialog class="book-dialog" aria-labelledby="dlg-title">
  <button type="button" class="dlg-close" aria-label="Close">×</button>
  <p class="eyebrow">Choose your salon</p>
  <h2 id="dlg-title">Where shall we see you?</h2>
  {rows}
</dialog>'''

def page(path, title, desc, body, tone='light', active=None, noindex_extra=False, bodyclass=''):
    canonical = f'https://beautiquebar.com{path}'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&family=Italiana&display=swap">
<link rel="stylesheet" href="/opus.css?v={VERSION}">
<link rel="stylesheet" href="/site.css?v={VERSION}">
<link rel="alternate" type="application/rss+xml" title="Beautique Bar — Beauty Blog" href="/rss.xml">
<script>document.documentElement.classList.add('js')</script>
<script src="/site.js?v={VERSION}" defer></script>
</head>
<body class="inner {bodyclass}">
<a class="skip" href="#main">Skip to content</a>
{header(active, tone)}
<main id="main">
{body}
</main>
{footer()}
{dialog()}
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

def hero(crumb, h1, lead, media=None, h1_class=''):
    side = f'<div class="pg-hero-media">{media}</div>' if media else ''
    return f'''<section class="pg-hero{' has-media' if media else ''}" data-tone="light">
  <div class="pg-hero-text">{crumbs(crumb)}<h1 class="{h1_class}">{h1}</h1><p class="lead">{lead}</p></div>
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
        lis = ''.join(f'<li><span>{e(n)}</span><span class="pr">{e(price(k, n))}</span></li>' for n in items)
        cols.append(f'''<div class="bp-col"><p class="eyebrow">{e(l["name"])}</p>
          <ul class="bp-menu">{lis}</ul>{f'<p class="bp-note">{sub}</p>' if sub else ''}
          <div class="bp-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
          <a class="line-link" href="{l["href"]}#menu">Full menu</a><a class="line-link" href="{l["tel"]}">{e(l["phone"])}</a></div></div>''')
    n = f'<p class="bp-foot">{note}</p>' if note else '<p class="bp-foot">Prices are guides from each salon’s current menu; “+” means from. Your technician will confirm before your service.</p>'
    return f'''<section class="pg-sec book-sec" data-tone="light" aria-labelledby="book-h">
  {sec_head(eyebrow, e(title), 'book-h')}
  <div class="book-pair">{''.join(cols)}</div>{n}
</section>'''

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

# ----------------------------------------------------------------------------------------------
PAGES = {}   # path -> html

def add(path, html_):
    PAGES[path] = html_

# ---- /nails/ ---------------------------------------------------------------------------------
add('/nails/', page('/nails/', 'Nails | Beautique Bar', 'Manicures, pedicures, Shellac, Bio Gel and acrylic at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails',None)], 'Nails.', 'Manicures and pedicures, Shellac, Bio Gel, Gel-X and sculpted sets, at both of our salons. Choose a treatment, then book the salon nearest you.',
      img('img/promo-polish-wall.webp', 2400, 1490, 'Rows of polish colours at Beautique Bar on Yonge', 'frame', '50% 40%', False, 'REAL — Yonge promo video still.'), 'display-xl')}
<section class="pg-sec" data-tone="light" aria-labelledby="t-h">
  {sec_head('Treatments', 'Choose your treatment', 't-h')}
  {svc_list([
    ('Manicure & Pedicure', '/nails/manicure-pedicure/', 'Spa and deluxe treatments for hands and feet, finished with regular polish or Shellac.', BOTH),
    ('Shellac', '/nails/manicure-pedicure/#shellac', 'A glossy gel polish with no drying time, on its own or with a spa manicure or pedicure.', BOTH),
    ('Bio Gel & Gel-X', '/nails/bio-gel/', 'A natural-looking gel overlay or full set with tips; Gel-X full sets and refills.', BOTH),
    ('Acrylic', '/nails/acrylic/', 'Sculpted sets, overlays and refills, shaped and finished to your design.', BOTH),
  ])}
</section>
{quote('sangeetha')}
{book_pair({'yonge': ['Spa Manicure', 'Spa Pedicure', 'Shellac Spa Manicure', 'Bio Gel Full Set', 'Gel-X Full Set'],
            'warden': ['Spa Manicure', 'Spa Pedicure', 'Spa Manicure w/ Shellac', 'Bio Gel Overlay', 'Gel-X Full Set']}, 'A few prices from each menu', 'Prices by salon')}
{reading(['what-are-manicures-and-pedicures', 'what-are-nail-enhancements', 'extend-longevity-nail-art'])}
{close_band()}
''', active='/nails/'))

# ---- /nails/manicure-pedicure/ ---------------------------------------------------------------
add('/nails/manicure-pedicure/', page('/nails/manicure-pedicure/', 'Manicure & Pedicure | Beautique Bar', 'Spa manicures, spa and deluxe pedicures, and Shellac at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Nails','/nails/'),('Manicure & Pedicure',None)], 'Manicure<br>&amp; Pedicure', 'Spa treatments for hands and feet, finished with regular polish or Shellac. Booked on their own or together.',
      img('img/stock-manicure-white.webp', 1920, 1280, 'A finished white manicure resting on satin', 'frame', '50% 50%', False, 'TEMPORARY — existing website image. Final: real Beautique Bar finished manicure.'))}
<section class="pg-sec" data-tone="light" aria-labelledby="ped-h">
  {sec_head('Pedicures', 'Three ways to sit back', 'ped-h')}
  {options([
    ('Spa Pedicure', 'A warm foot soak, nail trimming and shaping, cuticle care, light exfoliation, and a hot-stone foot massage with moisturising lotion. Finished with your choice of polish.'),
    ('Deluxe Spa Pedicure', 'Everything in the Spa Pedicure, plus an exfoliating scrub, an extended foot and lower-leg hot-stone massage, a hydrating foot mask and a hot-towel wrap.'),
    ('Monthly Special Pedicure', 'A seasonal pedicure that changes through the year. Both menus currently list it as the Tropical Deluxe Pedicure; ask in salon for this month’s version.'),
  ])}
</section>
<section class="pg-sec pg-sec--tight" data-tone="light" aria-labelledby="man-h">
  {sec_head('Manicures', 'Hands, finished your way', 'man-h')}
  {options([
    ('Spa Manicure', 'On the menu at both salons, with regular polish or Shellac, and as a manicure-and-pedicure combination.'),
    ('Deluxe Spa Manicure & Russian Manicure', 'On the Bridlewood Mall menu, each also available with Shellac.'),
    ('Gentleman’s Manicure & Pedicure', 'On the menu at both salons.'),
  ])}
  <figure class="inline-ph">{ph('Finished pedicure', 'Feet resting on a warm towel at a Beautique Bar chair, finished polish in a soft neutral. Top-down or low angle; no tools or gloves.', 'frame')}</figure>
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
      img('img/stock-hands-towel.webp', 1920, 1280, 'Hands with a natural, sheer nail finish resting on a soft towel', 'frame', '72% 50%', False, 'TEMPORARY — existing website image. Final: real finished Bio Gel set.'))}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Options', 'How to book it', 'opt-h')}
  {options([
    ('Overlay or full set', 'An overlay strengthens your natural nails; a full set with tips adds length. Both are finished in the colour or design you choose.'),
    ('Refills', 'Refills fill in the growth so the set keeps its shape. Book them on the same menu.'),
    ('Gel-X', 'Both salons also offer Gel-X full sets and refills.'),
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
      ph('Acrylic — sculpted almond set', 'Side-profile macro showing length and curve. Neutral shade, hand on linen or warm stone, soft daylight.', 'frame'))}
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

# ---- /skin/ ----------------------------------------------------------------------------------
add('/skin/', page('/skin/', 'Skin & Lashes | Beautique Bar', 'Eyelash extensions, facials, waxing, threading and piercing at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes',None)], 'Skin<br>&amp; Lashes', 'Lash extensions, facials, waxing and threading, and piercing — alongside your nails, at the salon nearest you.',
      ph('Skin & lashes', 'A calm treatment moment: eyes closed, warm towel, soft light. Real Beautique Bar treatment room; no tools in focus.', 'frame'))}
<section class="pg-sec" data-tone="light" aria-labelledby="t-h">
  {sec_head('Treatments', 'Choose your treatment', 't-h')}
  {svc_list([
    ('Eyelash Extensions', '/eyelash-extensions/', 'Classic, hybrid and volume sets, plus refills.', BOTH),
    ('Facials', '/skin/facials/', 'From a deep-pore cleanse to an anti-wrinkle, hydrating facial.', BOTH),
    ('Facial Hair Removal', '/skin/facial-hair-removal/', 'Waxing and tinting for brows, lip, chin and full face; threading at Yonge.', BOTH),
    ('Body Hair Removal', '/skin/body-hair-removal/', 'Waxing for arms, legs, underarms, back, chest and bikini.', BOTH),
    ('Body Piercing', '/skin/body-piercing/', 'Ear, facial, mouth and body piercing.', 'Yonge &amp; York Mills only'),
  ])}
</section>
{close_band()}
''', active='/skin/'))

# ---- /eyelash-extensions/ --------------------------------------------------------------------
add('/eyelash-extensions/', page('/eyelash-extensions/', 'Eyelash Extensions | Beautique Bar', 'Classic, hybrid and volume eyelash extensions and refills at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Eyelash Extensions',None)], 'Eyelash<br>Extensions', 'Individual extensions applied to suit your eye shape — from a soft, natural set to full volume — with refills to keep them full.',
      ph('Lashes', 'Finished lash set, eyes closed, calm profile crop from brow to cheekbone. Soft light, skin texture visible.', 'frame'))}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('Options', 'Choose your set', 'opt-h')}
  {options([
    ('Classic', 'One extension applied to each natural lash, for definition that still looks like you.'),
    ('Hybrid', 'A mix of classic and volume lashes for texture and fullness.'),
    ('Volume', 'Fans of fine lashes on each natural lash for a fuller, softer look.'),
    ('Refills', 'Top up your set as your natural lashes shed and grow.'),
  ])}
</section>
{book_pair({'yonge': ['Classic Set', 'Hybrid Set', 'Volume Set', 'Refill Classic', 'Refill Hybrid', 'Refill Volume'],
            'warden': ['Individual Classic Set', 'Indiv. Hybrid Set', 'Indiv. Volume Set', 'Bunch Light Volume Set', 'Bunch Wispy Set']})}
{reading(['maintaining-eyelash-extensions'])}
{close_band()}
''', active='/skin/'))

# ---- /skin/facials/ --------------------------------------------------------------------------
add('/skin/facials/', page('/skin/facials/', 'Facials | Beautique Bar', 'Deep-pore cleansing, relaxing, anti-wrinkle and firming facials at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Facials',None)], 'Facials', 'An hour for your skin — a deep-pore cleanse, a relaxing classic, or a hydrating or firming facial with a lifting mask.',
      ph('Facial', 'A relaxed facial in progress: towel wrap, product texture, eyes closed. Overhead, calm symmetry, warm light.', 'frame'))}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('On the menus', 'Choose your facial', 'opt-h')}
  {options([
    ('Deep-pore Cleansing & Relaxing Facial', 'At both salons.'),
    ('Classic Relaxing Facial', 'At Bridlewood Mall.'),
    ('Anti-wrinkle & Hydrating Facial', 'With a lifting mask. At Yonge &amp; York Mills.'),
    ('Regeneration & Firming Facial', 'With a lifting mask. At Yonge &amp; York Mills.'),
    ('Back Facial Exfoliation', 'At Yonge &amp; York Mills.'),
  ])}
</section>
{book_pair({'yonge': ['Deep-pore Cleansing & Relaxing Facial', 'Anti-wrinkle & Hydrating Facial w/ Lifting Mask', 'Regeneration & Firming Facial w/ Lifting Mask', 'Back Facial Exfoliation'],
            'warden': ['Deep-pore Cleansing & Relaxing Facial', 'Classic Relaxing Facial']})}
{reading(['facial-frequency'])}
{close_band()}
''', active='/skin/'))

# ---- /skin/facial-hair-removal/ --------------------------------------------------------------
add('/skin/facial-hair-removal/', page('/skin/facial-hair-removal/', 'Facial Hair Removal | Beautique Bar', 'Eyebrow, lip, chin and full-face waxing, brow tinting and threading at Beautique Bar — Yonge & York Mills and Bridlewood Mall.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Facial Hair Removal',None)], 'Facial Hair<br>Removal', 'Waxing and tinting for brows, lip, chin and full face at both salons, and threading at Yonge &amp; York Mills.',
      ph('Brows', 'A calm finished brow, soft light, towel edge in frame. No wax sticks or gloves.', 'frame'))}
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
      ph('Smooth skin', 'A calm aftercare moment: smooth skin against a warm towel, soft window light. No wax or tools in frame.', 'frame'))}
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

# ---- /skin/body-piercing/ --------------------------------------------------------------------
pierce_min = {}
for c in MENUS['yonge']:
    if 'Piercing' in c['title']:
        pierce_min[c['title']] = min(int(re.sub(r'\D', '', i['price'])) for i in c['items'])
add('/skin/body-piercing/', page('/skin/body-piercing/', 'Body Piercing | Beautique Bar', 'Ear, facial, mouth and body piercing at Beautique Bar on Yonge.', f'''
{hero([('Home','/'),('Skin & Lashes','/skin/'),('Body Piercing',None)], 'Body<br>Piercing', 'Ear, facial, mouth and body piercing, offered at our Yonge &amp; York Mills salon.',
      ph('Piercing', 'A healed ear piercing with a fine gold stud, close crop, soft natural light. No needles or gloves in frame.', 'frame'))}
<section class="pg-sec" data-tone="light" aria-labelledby="opt-h">
  {sec_head('On the Yonge menu', 'Where to pierce', 'opt-h')}
  {options([(t.replace(' Services', ''), f'From ${m} on the Yonge &amp; York Mills menu.') for t, m in pierce_min.items()])}
</section>
{book_pair({'yonge': ['Ear Lobe (Each)', 'Helix', 'Tragus', 'Nostril', 'Septum', 'Navel'],
            'warden': 'Piercing isn’t offered at Bridlewood Mall. Book it at Yonge &amp; York Mills.'}, 'Book at Yonge & York Mills')}
{close_band()}
''', active='/skin/'))

# ---- /locations/ -----------------------------------------------------------------------------
def salon_card(l, head='h2'):
    if l['photo']:
        s, w, h, alt = l['photo']
        fig = f'<figure class="salon-photo" data-brief="REAL — owner photo, colour-corrected."><img src="/{s}" alt="{e(alt)}" width="{w}" height="{h}" loading="lazy" decoding="async" style="object-position:50% 60%"></figure>'
    else:
        fig = ph('Bridlewood Mall salon', 'Wide interior from the entrance, lights warmed, no people. Same framing as the Yonge photo so the two salons read as a pair.', 'salon-photo')
    return f'''<article class="salon">{fig}
  <div class="salon-info"><p class="eyebrow">{e(l["area"])}</p><{head}><a href="{l["href"]}">{e(l["name"])}</a></{head}>
  <p class="addr">{e(l["addr"])}<br><a href="{l["tel"]}">Call {e(l["phone"])}</a>{f' · Text {e(l["text"])}' if l["text"] != l["phone"] else ' · Call or text'}</p>
  <div class="salon-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
  <a class="line-link" href="{l["href"]}">Menu &amp; details</a><a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a></div></div></article>'''

add('/locations/', page('/locations/', 'Locations | Beautique Bar', 'Beautique Bar on Yonge (3430 Yonge St, Toronto) and at Bridlewood Mall (2900 Warden Ave, Scarborough). Book online, call or text.', f'''
{hero([('Home','/'),('Locations',None)], 'Two salons.', 'Walk-ins are welcome, but booking ahead secures your preferred time and technician. Choose the salon nearest you.')}
<section class="pg-sec salons salons--inner" data-tone="light" aria-label="Our salons">
  <div class="salon-pair">{salon_card(LOC['yonge'])}{salon_card(LOC['warden'])}</div>
</section>
''', active='/locations/'))

# ---- /locations/yonge/ & /locations/warden/ --------------------------------------------------
HERE = {
  'yonge': ['Manicures, pedicures and Shellac', 'Crystal Gel, Bio Gel and Gel-X', 'Waxing, brow tinting and threading', 'Facials', 'Eyelash extensions', 'Ear, facial, mouth and body piercing'],
  'warden': ['Manicures, pedicures and Shellac, including Russian manicure and BIAB', 'Gel-X, Bio Gel, Crystal Gel / acrylic and dipping powder', 'Waxing and brow tinting', 'Facials', 'Eyelash extensions'],
}
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
        media = img(s, w, h, alt, 'frame', '50% 60%', False, 'REAL — owner photo, colour-corrected.')
        gallery = f'''<section class="pg-sec gallery" data-tone="light" aria-label="Inside the salon">
  <div class="gal">{img('img/yonge-pedicure-row.webp', 2400, 1800, 'The pedicure row at Beautique Bar on Yonge', 'g1', '50% 58%', True, 'REAL — owner photo.')}
  {img('img/promo-logo-wall.webp', 1100, 1650, 'The Beautique Bar logo lit on the wood-slat wall', 'g2', None, True, 'REAL — Yonge promo still.')}</div></section>'''
    else:
        media = ph('Bridlewood Mall salon', 'Wide interior from the entrance, lights warmed, no people. Must look distinct from Yonge.', 'frame')
        gallery = ''
    monthly = '<p class="mn-note">Monthly special pedicure: ask in salon for this month’s version.</p>'
    add(l['href'], page(l['href'], f'{l["name"]} Nail Salon | Beautique Bar', f'{l["long"]} — {l["addr"]}. Call {l["phone"]}. Book online.', f'''
{hero([('Home','/'),('Locations','/locations/'),(l['name'],None)], e(l['name']), f'{e(l["long"])} — {e(l["where"][0].lower() + l["where"][1:])} Serving {e(l["serves"])}.', media)}
<section class="pg-sec facts-sec" data-tone="light" aria-label="Visit">
  <dl class="facts">
    <div><dt>Address</dt><dd>{e(l["addr"])}</dd></div>
    <div><dt>Call</dt><dd><a href="{l["tel"]}">{e(l["phone"])}</a></dd></div>
    <div><dt>Text</dt><dd><a href="{l["text_tel"]}">{e(l["text"])}</a></dd></div>
    <div><dt>Walk-ins</dt><dd>Welcome — booking ahead secures your time and technician.</dd></div>
  </dl>
  <div class="facts-actions"><a class="btn-solid" href="{e(l["book"])}" target="_blank" rel="noopener">Book {e(l["name"])} <span aria-hidden="true">↗</span></a>
  <a class="line-link" href="{e(l["maps"])}" target="_blank" rel="noopener">Directions <span aria-hidden="true">↗</span></a><a class="line-link" href="#menu">Menu &amp; prices</a></div>
</section>
<section class="pg-sec here" data-tone="light" aria-labelledby="here-h">
  {sec_head('At this salon', 'What you can book here', 'here-h')}
  <ul class="here-list">{''.join(f'<li>{e(x)}</li>' for x in HERE[k])}</ul>
</section>
{gallery}
<section class="pg-sec menu-sec" data-tone="light" aria-labelledby="menu">
  {sec_head('Menu', 'Services &amp; prices', 'menu', '<p class="sec-aside">Prices are guides and may vary with length, design and add-ons. “+” means from. Your technician will confirm before your service.</p>')}
  <nav class="mn-jump" aria-label="Menu sections">{''.join(f'<a href="#{slug(c["title"])}">{e(c["title"])}</a>' for c in MENUS[k])}</nav>
  {monthly}
  <div class="menu">{menu_html(k)}</div>
</section>
<section class="pg-sec other-loc" data-tone="light" aria-label="Our other salon">
  <p class="eyebrow">Our other salon</p><a class="ol-link" href="{other["href"]}"><span>{e(other["name"])}</span><small>{e(other["addr"])}</small><span aria-hidden="true">→</span></a>
</section>
{close_band('Book at<br>' + e(l['name']) + '.', 'Whenever you’re ready')}
''', active='/locations/'))

# ---- /shop/ ----------------------------------------------------------------------------------
PRODUCTS = [
  ('shop-tshirt.webp', 'Beautique Bar Branded T-Shirt', 'Colour: white or black · Size: S, M, L', 'Soft pima cotton tee with the Beautique Bar logo on the front.', '$29.99'),
  ('shop-cuticle-oil.webp', 'Cuticle Oil Pens', 'For hands and feet', 'A pen for applying nourishing cuticle oil on the go; push back the cuticle with the cap and apply with the tip.', '$9.99 · 3 for $24.99'),
  ('shop-topcoat.webp', 'BB Gel Polish Top & Base Coat Combo', '10 ml · compatible with all gel polish colours', 'The base coat cures in 10 seconds under a UV lamp; the top coat finishes the look with a durable, mirror-like shine.', '$29.99'),
]
add('/shop/', page('/shop/', 'Shop | Beautique Bar', 'Beautique Bar products — branded T-shirt, cuticle oil pens and gel top & base coat — available in-store at both Toronto salons.', f'''
{hero([('Home','/'),('Shop',None)], 'Shop.', 'A few Beautique Bar favourites to take home. Available in-store at both salons — ask at the front desk.')}
<section class="pg-sec shop" data-tone="light" aria-label="Products">
  <ul class="products">{''.join(f"""<li class="product">{img('img/' + p[0], 500, 500, p[1], 'pr-img', None, True, 'Existing product photo (500 px). Final: styled product still on linen.')}
    <h2>{e(p[1])}</h2><p class="pr-meta">{e(p[2])}</p><p>{e(p[3])}</p><p class="pr-price">{e(p[4])}</p><p class="pr-avail eyebrow">Available in-store</p></li>""" for p in PRODUCTS)}</ul>
</section>
{close_band('Pick one up<br>at your next visit.', 'In-store at both salons')}
''', active=None))

# ---- /contact/ -------------------------------------------------------------------------------
def contact_col(l):
    return f'''<div class="ct-col"><p class="eyebrow">{e(l["area"])}</p><h2>{e(l["name"])}</h2><p class="addr">{e(l["addr"])}</p>
    <ul class="ct-list"><li><span>Call</span><a href="{l["tel"]}">{e(l["phone"])}</a></li><li><span>Text</span><a href="{l["text_tel"]}">{e(l["text"])}</a></li>
    <li><span>Book</span><a href="{e(l["book"])}" target="_blank" rel="noopener">Book online with Fresha ↗</a></li><li><span>Visit</span><a href="{e(l["maps"])}" target="_blank" rel="noopener">Directions ↗</a></li></ul></div>'''
add('/contact/', page('/contact/', 'Contact | Beautique Bar', 'Call, text or book online with Beautique Bar on Yonge or at Bridlewood Mall. Email info@beautiquebar.com.', f'''
{hero([('Home','/'),('Contact',None)], 'Get in touch.', 'Have a question or want to book? Call, text or book online with the salon nearest you.')}
<section class="pg-sec contact" data-tone="light" aria-label="Contact details">
  <div class="ct-pair">{contact_col(LOC['yonge'])}{contact_col(LOC['warden'])}</div>
  <div class="ct-more"><p class="eyebrow">Anything else</p><p><a class="ct-mail" href="mailto:{EMAIL}">{EMAIL}</a></p><p><a class="line-link" href="{IG}" target="_blank" rel="noopener">Instagram ↗</a> <a class="line-link" href="{FB}" target="_blank" rel="noopener">Facebook ↗</a></p></div>
</section>
''', active=None))

# ---- /privacy/ & /terms/ (legal text as on the live site) ------------------------------------
PRIVACY = f'''<p>This Privacy Policy explains how Beautique Bar (“we”, “us”) collects, uses and safeguards the personal information you provide when you visit our website or book an appointment.</p>
<h2>Information we collect</h2><p>When you contact us through our website form, we collect the details you choose to provide — typically your name, email address, phone number, preferred location and message. We do not collect payment information through this website.</p>
<h2>How we use your information</h2><ul><li>To respond to your enquiries and booking requests.</li><li>To provide and improve our services.</li><li>To contact you about your appointments when you ask us to.</li></ul>
<h2>How we protect it</h2><p>Messages submitted through our website are transmitted securely over HTTPS and delivered directly to our team by email. We retain enquiry information only as long as needed to assist you.</p>
<h2>Third-party services</h2><p>We may use privacy-respecting analytics and spam protection (such as Cloudflare Turnstile) to keep the site secure and understand how it is used. We do not sell your personal information.</p>
<h2>Your choices</h2><p>You may request access to, correction of, or deletion of the personal information you have shared with us by contacting us at <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
<h2>Contact us</h2><p>Questions about this policy? Email <a href="mailto:{EMAIL}">{EMAIL}</a> or reach out via <a href="{IG}" target="_blank" rel="noopener">Instagram</a>.</p>
<p>This policy may be updated from time to time; the latest version always appears on this page.</p>'''
TERMS = f'''<p>These terms apply to your use of the Beautique Bar website and to the services we provide at our Toronto locations. By using this site or booking with us, you agree to the following.</p>
<h2>Appointments &amp; walk-ins</h2><p>We welcome walk-ins and recommend booking in advance to secure your preferred time and technician. Please let us know as early as possible if you need to reschedule or cancel so we can offer the slot to another guest.</p>
<h2>Pricing</h2><p>Prices shown on this website are guides and may vary with nail length, design complexity and add-on services. Prices marked “+” start from the listed rate. We’ll always confirm pricing with you before your service.</p>
<h2>Services &amp; results</h2><p>Our team takes pride in delivering high-quality, hygienic services. If you have any concerns about your service, please tell us before you leave so we can make it right.</p>
<h2>Website content</h2><p>Content on this site is provided for general information. While we keep it as accurate as possible, services, pricing and availability may change without notice.</p>
<h2>Contact</h2><p>Questions about these terms? Email <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>'''
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
<section class="pg-sec" data-tone="light">{svc_list([('Nails', '/nails/', 'Manicures, pedicures, Shellac, Bio Gel and acrylic.', BOTH), ('Skin & Lashes', '/skin/', 'Lashes, facials, waxing, threading and piercing.', BOTH), ('Locations', '/locations/', 'Book, call or get directions.', BOTH)])}</section>''')

# ---- /blog/ & posts --------------------------------------------------------------------------
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
    art = re.sub(r'<h1>(.*?)</h1>', r'<h2>\1</h2>', art)
    note = POST_NOTES.get(p['slug'], '')
    if removed:
        note += PRICE_NOTE
    if p['slug'] in POST_NOTES:
        AUDIT.setdefault(p['slug'], []).append('Covers methods/services not on either salon menu (see note added to the article).')
    if p['date'].year <= 2024:
        AUDIT.setdefault(p['slug'], []).append(f'Written {fmt_date(p["date"])} — check trends and claims are still current.')
    lbl, href = RELATED.get(p['cat'], ('Nails', '/nails/'))
    add(f'/blog/{p["slug"]}/', page(f'/blog/{p["slug"]}/', f'{p["title"]} | Beautique Bar', p['desc'], f'''
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
items = ''.join(f'''<item><title>{e(p["title"])}</title><link>https://beautiquebar.com/blog/{p["slug"]}/</link><guid>https://beautiquebar.com/blog/{p["slug"]}/</guid><description>{e(p["desc"])}</description><pubDate>{datetime.datetime.combine(p["date"], datetime.time()).strftime("%a, %d %b %Y 00:00:00 GMT")}</pubDate></item>''' for p in POSTS)
RSS = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Beautique Bar — Beauty Blog</title><description>Nail, lash and skin care guides from Beautique Bar in Toronto.</description><link>https://beautiquebar.com/</link>{items}</channel></rss>'

# ----------------------------------------------------------------------------------------------
HOME_IMG = {'salon-3': 'stock-hands-rest.webp', 'salon-hero': 'stock-manicure-white.webp', 'salon-mauve': 'stock-manicure-mauve.webp',
            'svc-lashes': 'stock-lashes.webp', 'svc-facials': 'stock-facial.webp', 'blog': 'stock-hands-towel.webp'}

def refresh_home():
    p = OUT / 'index.html'
    s = p.read_text()
    s = re.sub(r'<header class="site-header".*?</header>(\s*<div class="menu-panel".*?</div>\s*</nav>\s*</div>)?', header(None, 'dark'), s, count=1, flags=re.S)
    s = re.sub(r'<footer class="site-footer">.*?</footer>', footer(), s, count=1, flags=re.S)
    s = re.sub(r'<dialog class="book-dialog".*?</dialog>', dialog(), s, count=1, flags=re.S)
    for a, b in HOME_IMG.items():
        s = re.sub(r'https://beautiquebar\.com/_astro/' + a + r'\.[A-Za-z0-9_-]+\.webp', '/img/' + b, s)
    s = s.replace('https://beautiquebar.com/', '/')
    s = re.sub(r'src="img/', 'src="/img/', s)
    s = re.sub(r'href="opus\.css[^"]*"', f'href="/opus.css?v={VERSION}"', s)
    s = re.sub(r'src="opus\.js[^"]*"', f'src="/opus.js?v={VERSION}"', s)
    if 'favicon.svg' not in s:
        s = s.replace('<link rel="preconnect" href="https://fonts.googleapis.com">', '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n<link rel="icon" href="/favicon.ico" sizes="32x32">\n<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n' + '<link rel="preconnect" href="https://fonts.googleapis.com">', 1)
    if '/site.js' not in s:
        s = s.replace('<script src="/opus.js', f'<script src="/site.js?v={VERSION}" defer></script>\n<script src="/opus.js', 1)
    s = re.sub(r'site\.js\?v=\d+', f'site.js?v={VERSION}', s)
    s = s.replace('<a class="skip" href="#nails">', '<a class="skip" href="#nails">')
    p.write_text(s)

def main():
    for path, doc in PAGES.items():
        if path.endswith('.html'):
            f = OUT / path.lstrip('/')
        else:
            f = OUT / path.strip('/') / 'index.html'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(doc)
    (OUT / 'rss.xml').write_text(RSS)
    refresh_home()
    # review file
    lines = ['# Blog audit (generated)', '']
    for p in POSTS:
        notes = AUDIT.get(p['slug'], [])
        lines.append(f'- `/blog/{p["slug"]}/` — ' + ('; '.join(notes) if notes else 'no automatic flags'))
    (SRC / 'BLOG-AUDIT.md').write_text('\n'.join(lines) + '\n')
    json.dump({k: MENUS[k] for k in MENUS}, open(SRC / 'menus.parsed.json', 'w'), indent=1)
    print(f'{len(PAGES)} pages + rss.xml written to {OUT}')

if __name__ == '__main__':
    main()
