"""llms.txt: a plain-text summary of the site for AI assistants (ChatGPT, Perplexity, Gemini, Copilot). See llmstxt.org.

Called by make_production.py after the pages are built. Everything comes from the same sources as the pages,
so it can't drift: site_config.py + content/salons.yml (addresses, phones, hours, booking links),
menus.parsed.json (the price menus build.py just read from content/menus/*.yml) and the built pages themselves
(titles, descriptions, the new-client offer wording).
"""
import html
import json
import re
from pathlib import Path

from site_config import BUSINESS_NAME, EMAILS, HOURS, LOC, SITE_URL

SRC = Path(__file__).resolve().parent
SKIP = {'/thank-you/', '/ig/yonge/', '/back/', '/privacy/', '/terms/', '/skin/body-piercing/'}


def _t(hm):
    h = int(hm[:2])
    return f'{h % 12 or 12} {"am" if h < 12 else "pm"}'


def _grab(doc, pat):
    m = re.search(pat, doc, flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else ''


def build(out_dir, pages):
    """out_dir: the built site folder. pages: indexable paths like '/', '/locations/yonge/'."""
    menus = json.loads((SRC / 'menus.parsed.json').read_text())
    docs = {p: (out_dir / p.lstrip('/') / 'index.html').read_text() for p in pages}
    y, w = LOC['yonge'], LOC['warden']
    out = [f'# {BUSINESS_NAME}', '',
           f'> Nail and beauty salon with two Toronto locations: {y["long"]} at {y["addr"]} (Yonge & York Mills), '
           f'and {BUSINESS_NAME} at {w["addr"]}. Manicures, pedicures, gel and acrylic nail sets, nail art, '
           'eyelash extensions, facials and waxing. Book online on Fresha or call either salon.', '',
           'The two locations are separate salons with their own phone numbers, hours, prices and booking links. '
           'Always say which location a fact belongs to.', '']
    for k, l in LOC.items():
        out += [f'## {l["long"]} ({l["name"]})',
                f'- Address: {l["addr"]} {l["postal"]}',
                f'- Where: {l["where"]}',
                f'- Serves: {l["serves"]}',
                f'- Phone: {l["phone"]}' + (f' (text: {l["text"]})' if l['text'] != l['phone'] else ' (calls and texts)'),
                f'- Email: {EMAILS[k]}',
                f'- Book online: {l["book"]}',
                f'- Google Maps: {l["maps"]}',
                f'- Instagram: {l["ig"]}']
        out += [f'- Hours, {d}: {_t(o)} – {_t(c)}' for d, _, o, c in HOURS[k]]
        page = docs.get(l['href'], '')
        offer = _grab(page, r'class="offer-h"[^>]*>(.*?)</')
        fine = _grab(page, r'class="offer-fine"[^>]*>(.*?)</')
        if offer:
            out.append(f'- New client offer: {offer} {fine}'.rstrip())
        out += [f'- Page: {SITE_URL}{l["href"]}', '']

    site, articles = [], []
    for p in sorted(pages, key=lambda p: (p != '/', p)):
        if p in SKIP:
            continue
        title = _grab(docs[p], r'<title>(.*?)</title>').replace(' | Beautique Bar', '')
        desc = _grab(docs[p], r'<meta name="description" content="(.*?)">')
        if not title:
            continue
        if p.startswith('/blog/') and p != '/blog/':
            articles.append(f'- [{title}]({SITE_URL}{p})')
        else:
            site.append(f'- [{title}]({SITE_URL}{p}): {desc}')
    out += ['## Pages'] + site
    out += ['', '## Prices (CAD)',
            'Prices are starting prices and can vary with length, design, removal or nail condition. '
            'Each location has its own menu; the location pages always show the current one.', '']
    for k, l in LOC.items():
        out.append(f'### {l["long"]}')
        for c in menus.get(k, []):
            items = [it for it in c['items'] if it['price']]
            items += [dict(it, name=f'{it["name"]} (add-on)') for s in c.get('subs', []) for it in s['items'] if it['price']]
            if items:
                out.append(f'- {c["title"]}: ' + '; '.join(f'{it["name"]} {it["price"]}' for it in items))
        out.append('')
    out += ['## Articles'] + articles
    (out_dir / 'llms.txt').write_text('\n'.join(out).rstrip() + '\n')
