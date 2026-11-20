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
VERSION = '12'
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

# Google rating shown beside each salon's Book buttons. The numbers live in content/reviews.yml (Growth HQ updates that file weekly).
REVIEWS_FILE = SRC.parent / 'content' / 'reviews.yml'
RATING_QUERY = {'yonge': 'Beautique+Bar+on+Yonge+reviews', 'warden': 'Beautique+Bar+Bridlewood+Mall+reviews'}
def load_ratings():
    import yaml
    try:
        data = yaml.safe_load(REVIEWS_FILE.read_text())
    except FileNotFoundError:
        raise SystemExit(f'{REVIEWS_FILE.relative_to(SRC.parent)} is missing. It holds each salon\'s Google rating and review count (yonge and warden).')
    except yaml.YAMLError as err:
        raise SystemExit(f'content/reviews.yml is not valid YAML: {err}')
    if not isinstance(data, dict):
        raise SystemExit('content/reviews.yml must list "yonge" and "warden", each with a rating and a count.')
    out = {}
    for k, q in RATING_QUERY.items():
        row = data.get(k)
        if not isinstance(row, dict):
            raise SystemExit(f'content/reviews.yml: "{k}" must have a rating and a count.')
        rating, count = row.get('rating'), row.get('count')
        if isinstance(rating, bool) or not isinstance(rating, (int, float, str)):
            raise SystemExit(f'content/reviews.yml: {k} rating "{rating}" must be a number such as 4.8.')
        try:
            rating = float(rating)
        except ValueError:
            raise SystemExit(f'content/reviews.yml: {k} rating "{rating}" must be a number such as 4.8.')
        if not 1 <= rating <= 5:
            raise SystemExit(f'content/reviews.yml: {k} rating {rating} must be between 1 and 5.')
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise SystemExit(f'content/reviews.yml: {k} count "{count}" must be a whole number of reviews, 1 or more.')
        out[k] = (f'{rating:.1f}', count, q)
    return out
RATING = load_ratings()
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
