#!/usr/bin/env python3
"""Make the launch-ready copy of the site in ../opus-site-production/ from the preview in ../opus-design-v1/.

The preview stays hidden from search engines. This copy is what would go on beautiquebar.com:
  - search engines allowed (noindex kept only on thank-you, the retired piercing page and 404)
  - Google Tag Manager container GTM-M6WHQ2D5 (the live site's container: GA4 + Google Ads) on every page
  - robots.txt + sitemap.xml for beautiquebar.com
  - the live site's security headers (CSP allows only self-hosted fonts and Google's tag/ads domains)
  - preview-only bits removed: photography notes, "design preview" footer label, internal .md docs
Run AFTER build.py:  python3 opus-site-src/make_production.py            (launch copy)
                     python3 opus-site-src/make_production.py --tagtest  (same, but hidden from search: for testing tags on a preview URL)
Nothing here is deployed automatically.
"""
import datetime, re, shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent
PREVIEW = SRC.parent / 'opus-design-v1'
OUT = SRC.parent / 'opus-site-production'
SITE = 'https://beautiquebar.com'
GTM = 'GTM-M6WHQ2D5'
NOINDEX = {'thank-you/index.html', 'skin/body-piercing/index.html', '404.html'}

GTM_HEAD = ("<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});"
            "var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;"
            "j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})"
            f"(window,document,'script','dataLayer','{GTM}');</script>")
GTM_BODY = (f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM}" height="0" width="0" '
            'style="display:none;visibility:hidden" title="gtm"></iframe></noscript>')

HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Cross-Origin-Opener-Policy: same-origin-allow-popups
  Permissions-Policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  Content-Security-Policy: default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://tagmanager.google.com https://fonts.googleapis.com; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://tagmanager.google.com https://tagassistant.google.com https://www.googleadservices.com https://www.google.com https://pagead2.googlesyndication.com https://googleads.g.doubleclick.net; connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://tagassistant.google.com https://*.g.doubleclick.net https://*.doubleclick.net https://*.google.com https://google.com https://*.google.ca https://pagead2.googlesyndication.com https://www.googleadservices.com https://googleads.g.doubleclick.net; frame-src https://www.googletagmanager.com https://tagassistant.google.com https://td.doubleclick.net; upgrade-insecure-requests

/fonts/*
  Cache-Control: public, max-age=31536000, immutable

/img/*
  Cache-Control: public, max-age=86400, stale-while-revalidate=604800
"""

def main():
    import sys
    tagtest = '--tagtest' in sys.argv
    global OUT
    if tagtest:
        OUT = SRC.parent / 'opus-site-tagtest'
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PREVIEW, OUT, ignore=shutil.ignore_patterns('*.md', '.DS_Store'))
    pages = []
    for f in sorted(OUT.rglob('*.html')):
        rel = f.relative_to(OUT).as_posix()
        s = f.read_text()
        robots = '<meta name="robots" content="noindex,nofollow">\n' if tagtest else ('<meta name="robots" content="noindex,follow">\n' if rel in NOINDEX else '')
        s = s.replace('<meta name="robots" content="noindex,nofollow">\n', robots)
        assert tagtest or 'noindex,nofollow' not in s, rel
        assert s.count('<head>\n') == 1 and s.count('<body') == 1, rel
        s = s.replace('<head>\n', '<head>\n' + GTM_HEAD + '\n', 1)
        s = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + '\n' + GTM_BODY, s, count=1)
        s = re.sub(r' data-brief="[^"]*"', '', s)
        s = re.sub(r'<button type="button" class="notes-toggle"[^>]*>.*?</button>', '', s)
        s = s.replace('© Beautique Bar · Design preview — not the live site', f'© {datetime.date.today().year} Beautique Bar')
        f.write_text(s)
        if rel not in NOINDEX and rel.endswith('index.html'):
            pages.append('/' + rel[:-len('index.html')])
    if tagtest:
        (OUT / '_headers').write_text(HEADERS.replace('/*\n', '/*\n  X-Robots-Tag: noindex, nofollow\n', 1))
        (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    else:
        (OUT / '_headers').write_text(HEADERS)
        (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    today = datetime.date.today().isoformat()
    urls = ''.join(f'<url><loc>{SITE}{p}</loc><lastmod>{today}</lastmod></url>' for p in pages)
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print(f'{len(pages)} pages in sitemap; {"TAG-TEST (noindex)" if tagtest else "production"} copy written to {OUT}')

if __name__ == '__main__':
    main()
