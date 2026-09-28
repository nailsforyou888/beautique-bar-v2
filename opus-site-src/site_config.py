"""Beautique Bar — the ONE place for site-wide facts and marketing IDs.

Everything the website says about the business (names, addresses, phones, emails, hours, booking links, socials)
and every domain / tracking ID lives here. build.py and make_production.py import it; nothing else hard-codes these.

Tracking architecture (read before adding any ID):
  * Google Tag Manager is the ONLY tag loaded by the website (production build only).
  * GA4, Google Ads conversions/remarketing and any future tags are configured INSIDE the GTM container,
    never added to the site as separate gtag.js snippets — that would double-count pageviews and conversions.
  * So there is deliberately no GA4 / Google Ads ID in this file.

Values can be overridden at build time with environment variables (e.g. for a staging domain):
  BB_SITE_URL, BB_GTM_ID, BB_GOOGLE_SITE_VERIFICATION, BB_BING_SITE_VERIFICATION
"""
import os

# ---- Domain & tracking --------------------------------------------------------------------------
SITE_URL = os.environ.get('BB_SITE_URL', 'https://beautiquebar.com').rstrip('/')   # canonical, sitemap, OG, schema
GTM_ID = os.environ.get('BB_GTM_ID', 'GTM-M6WHQ2D5')                               # owner-supplied container (production build only)
# Search Console: prefer the DNS "Domain property" (no code). If you use the HTML-tag method instead, paste only the
# content="…" value here. Same for Bing Webmaster Tools (or import the site from Search Console, no code needed).
GOOGLE_SITE_VERIFICATION = os.environ.get('BB_GOOGLE_SITE_VERIFICATION', '')
BING_SITE_VERIFICATION = os.environ.get('BB_BING_SITE_VERIFICATION', '')

BUSINESS_NAME = 'Beautique Bar'

# ----------------------------------------------------------------------------------------------
# Locations (from the live site config: src/lib/site.ts)
LOC = {
  'yonge': dict(
    id='yonge', name='Yonge & York Mills', long='Beautique Bar on Yonge', href='/locations/yonge/',
    area='Toronto', street='3430 Yonge Street', city='Toronto, ON',
    addr='3430 Yonge Street, Toronto, ON', postal='M4N 2M9', locality='Toronto', short='Yonge', ig='https://www.instagram.com/beautiquebar_onyonge',
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
    addr='Bridlewood Mall, 2900 Warden Avenue, 2nd floor by the library, Scarborough, ON', postal='M1W 2S8', locality='Scarborough', short='Bridlewood', ig='https://www.instagram.com/beautiquebar88',
    phone='647-770-5232', tel='tel:+16477705232', text='647-770-5232', text_tel='sms:+16477705232',
    book='https://www.fresha.com/a/nails-for-you-beautique-bar-toronto-2900-warden-avenue-bkuolnwc/booking?menu=true&pId=32159',   # direct to the service menu (the old /book-now/…m7weksrj link redirected to a Book/Group/Gift chooser)
    maps='https://www.google.com/maps/search/?api=1&query=Beautique%20Bar%2C%20Bridlewood%20Mall%2C%202900%20Warden%20Ave%2C%20Scarborough%2C%20ON',
    where='On the 2nd floor of Bridlewood Mall, by the library.',
    serves='Scarborough, Bridlewood, L’Amoreaux and surrounding communities',
    photo=('img/bridlewood-interior.webp', 1448, 1086, 'Inside Beautique Bar at Bridlewood Mall: manicure stations, the colour wall and wood-slat walls'),
  ),
}
HOURS = {  # owner-supplied, 24 Sep 2026
  'yonge':  [('Mon–Fri', ['Monday','Tuesday','Wednesday','Thursday','Friday'], '10:00', '20:00'), ('Sat', ['Saturday'], '10:00', '19:00'), ('Sun', ['Sunday'], '10:00', '18:00')],
  'warden': [('Mon–Fri', ['Monday','Tuesday','Wednesday','Thursday','Friday'], '10:00', '20:00'), ('Sat', ['Saturday'], '09:00', '19:00'), ('Sun', ['Sunday'], '11:00', '18:00')],
}

EMAIL_Y = 'beautiquebar.yonge@gmail.com'      # Yonge & York Mills
EMAIL_W = 'beautiquebar88@gmail.com'          # Bridlewood Mall
EMAILS = {'yonge': EMAIL_Y, 'warden': EMAIL_W}
IG = 'https://www.instagram.com/beautiquebar88'
IG_YONGE = 'https://www.instagram.com/beautiquebar_onyonge'
FB = 'https://www.facebook.com/Beautiquebaryonge'
