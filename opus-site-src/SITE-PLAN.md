# Beautique Bar — Opus site (branch `opus-site-v1`)

Full-site staging build in the approved Opus V5 design. Every public URL of beautiquebar.com is kept at the identical path. Nothing here touches the live site, DNS, the production Cloudflare project, Ads, GA4, tracking, Google Business Profile or Fresha.

- **Output:** `opus-design-v1/` (static; deployed as is). **Generator:** `opus-site-src/build.py` (run `python3 opus-site-src/build.py`).
- **Sources:** `opus-site-src/yonge.md`, `warden.md` (live location menus) and `blog/*.md` (live articles), copied from the live site's source (`beautique-bar-main`). Every price on a service page is looked up by exact name in those menus; the build fails if a name doesn't exist.
- **Preview:** a branch deployment of the Opus Cloudflare Pages project (`opus-site-v1.beautique-bar-opus-design-v1.pages.dev`). The approved V5 link is left unchanged.
- noindex, nofollow on every page (meta tag + `_headers` + `robots.txt`). No analytics or tag manager.

## URL checklist — live path → preview page (paths identical)

| # | Live URL (sitemap) | Preview file | Page |
|---|---|---|---|
| 1 | `/` | `index.html` | Homepage (Opus V5; header, footer and links updated only) |
| 2 | `/nails/` | `nails/index.html` | Nails overview |
| 3 | `/nails/acrylic/` | `nails/acrylic/index.html` | Acrylic |
| 4 | `/nails/bio-gel/` | `nails/bio-gel/index.html` | Bio Gel & Gel-X |
| 5 | `/nails/manicure-pedicure/` | `nails/manicure-pedicure/index.html` | Manicure & Pedicure, incl. `#shellac` |
| 6 | `/skin/` | `skin/index.html` | Skin & Lashes overview |
| 7 | `/skin/facials/` | `skin/facials/index.html` | Facials |
| 8 | `/skin/facial-hair-removal/` | `skin/facial-hair-removal/index.html` | Facial hair removal |
| 9 | `/skin/body-hair-removal/` | `skin/body-hair-removal/index.html` | Body hair removal |
| 10 | `/skin/body-piercing/` | `skin/body-piercing/index.html` | Service discontinued notice (URL kept; links to other treatments) |
| 11 | `/eyelash-extensions/` | `eyelash-extensions/index.html` | Eyelash extensions |
| 12 | `/locations/` | `locations/index.html` | Both salons, once each |
| 13 | `/locations/yonge/` | `locations/yonge/index.html` | Yonge & York Mills + full menu |
| 14 | `/locations/warden/` | `locations/warden/index.html` | Bridlewood Mall + full menu |
| 15 | `/shop/` | — (`_redirects` 301 → `/`) | Retired 24 Sep 2026 |
| 16 | `/contact/` | `contact/index.html` | Contact (call, text, book, email — no form) |
| 17 | `/privacy/` | `privacy/index.html` | Privacy policy (live text) |
| 18 | `/terms/` | `terms/index.html` | Terms (live text) |
| 19 | `/blog/` | `blog/index.html` | Blog index |
| 20–36 | `/blog/<slug>/` × 17 | `blog/<slug>/index.html` | Articles (see audit) |
| — | `/thank-you/` (not in sitemap) | `thank-you/index.html` | Thank-you (noindex) |
| — | `/rss.xml` | `rss.xml` | RSS, 17 items |
| — | unknown paths | `404.html` | 404 page (live site currently returns a 500 error) |

Blog slugs (17): acrylic-nails-costs, acrylic-nails, bio-gel-nails, cost-of-shellac-manicures, costs-of-manicures-and-pedicures, extend-longevity-nail-art, facial-frequency, facial-hair-growth, full-body-laser-hair-removal-costs, maintaining-eyelash-extensions, removing-acrylic-nails, removing-bio-gel-nails, removing-shellac-manicures, top-nail-trends-for-2025-whats-hot-in-the-world-of-nails, toronto-trending-nail-art-design, what-are-manicures-and-pedicures, what-are-nail-enhancements.

Trailing slashes: pages are folders with `index.html`, so `/nails` redirects to `/nails/` and `/nails/index.html` to `/nails/`, as on the live site.

## Content decisions (per owner review)

- Header: **Nails · Skin & Lashes · Locations · Book Appointment**. Shop, Blog, Contact, Eyelash Extensions and legal links sit in the footer (and the phone menu).
- Service pages: what the treatment includes, options, which salon offers it, a few real menu prices per salon with a link to the full menu, and booking. Generic promo paragraphs ("Why choose", "Glow like a celebrity", etc.) and empty "Pricing" headings were not carried over.
- Reviews: one relevant verbatim Google review where one exists (nails pages only) plus a link to Google. Skin pages have none (no skin-specific review on file).
- Locations page: each salon appears once. Salon pages keep their own address, numbers and full menu.
- Contact: no form in staging; call, text, book, email and social instead.
- Blog: URLs and text preserved; generic industry price ranges removed and replaced with a note pointing to the two salon menus; notes added where an article covers services not on either menu.

## Needs owner review

**Facts**
1. Acrylic at Yonge: the Yonge menu lists "Crystal Gel" sets but never the word acrylic (Bridlewood lists "Crystal Gel / Acrylic"). The acrylic page shows Yonge's Crystal Gel prices with "call to confirm acrylic".
2. Menu typo fixed in preview: "Bio Bel Full Set w/ Tips" → "Bio Gel Full Set w/ Tips" (Yonge).
3. Menu items with no price were left out ("Monthly Special Pedicure" labels, Bridlewood "Tropical Pedicure"); a line says "ask in salon for this month's version". "New Service" / "Exclusive New Service!" promo labels dropped.
4. Bridlewood address now reads "2nd floor by the library" everywhere, as on the live site (the earlier Concept C avoided the floor detail pending confirmation).
5. Removed unverified claims from location copy: Yonge "trusted name for over a decade" (the logo says Est. 2017; site config says founded 2013) and Bridlewood "hundreds of five-star Google reviews".
6. Removed service claims not verifiable from the menus: "hypoallergenic, medical-grade adhesives" (lashes), "aftercare services" (piercing), "natural or organic products" (facials), "up to three weeks" and "less damaging" (Bio Gel). Kept: Shellac cured under a lamp, no drying time.
7. Pedicure descriptions (Spa, Deluxe, Monthly Special) are condensed from the live page; manicure options have no descriptions on the live site, so none were written.
8. Live Bridlewood page source also contains a second Fresha link (`nails-for-you-beautique-bar-toronto-2900-warden-avenue-bkuolnwc`) that isn't displayed; the preview uses only the displayed one.
9. Privacy policy still describes the website contact form and email delivery; the live form also stores leads in a database. Update the policy if the form is kept or removed in production.
10. ~~Shop prices~~ — shop retired.

**Blog** (see `BLOG-AUDIT.md`)
- `full-body-laser-hair-removal-costs`: laser isn't on either menu. Decide: keep with the added note, rewrite, or retire.
- Price ranges removed from 7 articles (`costs-of-manicures-and-pedicures` lost 18 items and is now thin on its own topic — rewrite with real menu prices or keep as a general guide).
- `facial-hair-growth` and `what-are-nail-enhancements` discuss methods not on the menus.
- 16 of 17 articles date from Dec 2023–Apr 2024; `top-nail-trends-for-2025` is dated by title.

**Photography still needed (placeholders on the page)**
Skin & lashes overview; lashes; facial; brows; body hair removal. Temporary stock still in use: lash and facial images on the homepage. Stand-ins to replace when better photos exist: Bridlewood interior (currently a Dec 2024 storefront team photo), finished pedicure (currently a low-res pedicure-tray reel cover). Nail imagery is now all from the salons' Instagram (see `INSTAGRAM.md`).

## Change log
- 23 Sep 2026 — Owner confirmed piercing and tattoo services are no longer offered. Piercing removed from the Skin & Lashes page, the Yonge menu and "what you can book here", and the 404 page. `/skin/body-piercing/` kept at the same URL as a short "no longer offered" page linking to other treatments (for production, a 301 redirect to `/skin/` is the alternative — owner's call). No tattoo content existed on the site.
- 23 Sep 2026 — Owner asked to replace the stock nail photos with the salons' own Instagram work and add a gallery. 24 finished sets + a pedicure tray + the Bridlewood storefront team photo pulled from @beautiquebar88 / @beautiquebar_onyonge (see `INSTAGRAM.md`). All four stock nail images are gone (home opening, Manicure, Shellac, Bio Gel; Manicure & Pedicure and Bio Gel heroes); the Pedicure, Acrylic and Bridlewood placeholders now show real photos. New page `/gallery/` (the only new URL) with a keyboard-accessible photo viewer; linked from the footer, phone menu, a new homepage "Our work" strip, the Nails page and the Bridlewood page. Header unchanged. Footer now lists both Instagram accounts. To review: acrylic image is a long sculpted set but the post doesn't say acrylic; Bridlewood photo is a Dec 2024 team shot with holiday decor (people in frame); pedicure tray is a low-res reel cover. Lash and facial stock images on the homepage are unchanged (not nail photos).
- 24 Sep 2026 — Logo added from the Beautique Bar design system (brand book): the round BB seal sits beside the Italiana name in the header on every page (drawn from `seal-ink.png` as a mask, so it follows the header's ink/paper tone) and larger above the name in the footer (`seal-paper.png`). The horizontal lockup isn't used on the site: its files have solid white/black grounds, and the brand book says to place them only on matching white or black areas. Vector versions of the seal and lockup are still needed for print.
- 24 Sep 2026 — Owner supplied a transparent horizontal lockup (2172×724 PNG, no bevel). It now leads the footer in the paper tone (`img/brand-lockup.png`, cropped and resized to 1200 px, used as a mask), replacing the footer seal + typed name. Header keeps the seal + Italiana name. A vector (SVG/PDF) of both marks is still the ideal for print. Owner then asked for the logo wherever the typed name stood in for it: the header now shows the full lockup too (ink or paper to match each section, smaller once scrolled), replacing the seal + Italiana name on every page. Narrow-phone fixes: header fits down to 320 px; the closing booking list no longer overflows at 320–360 px.
- 24 Sep 2026 — Owner supplied three licensed stock photos for the homepage "Beyond nails" block (lashes, hair removal, facial) — the salon doesn't photograph those treatments. They replace the two 500 px stock images and the hair-removal placeholder (`img/skin-*.webp`). The brand book now records this as the one stock exception and lists the transparent lockup as the master logo file.
- 24 Sep 2026 — Owner retired the shop (the products were for a grant). `/shop/` page, its three product images and every Shop link (footer, phone menu) removed; `/shop` and `/shop/` now 301 to the homepage via `_redirects`, so old links and search results land somewhere useful. Do the same 301 on production when the site goes live.
- 24 Sep 2026 — Search & ads readiness. Titles/descriptions rewritten with neighbourhood keywords; NailSalon details for both salons (address, postal code from the salons' Instagram, phone, map, services with menu prices), Organization, Service, BreadcrumbList and BlogPosting data; Open Graph/Twitter cards with a new share image; self-hosted fonts; responsive LCP image on the homepage; contrast fixes; `lang="en-CA"`; "Book [salon] online / Call / Directions" at the top of each salon page; legacy WordPress and QR-code forwards copied from the live site into `_redirects`; click events for booking/call/text/directions tagged by salon. Launch copy (`opus-site-production/`, made by `make_production.py`) adds the live GTM container, indexable robots/sitemap and the live security headers; the preview stays noindex with no tracking. Read-only tracking audit and launch plan: `TRACKING.md`. Lighthouse (mobile, local): SEO 100 on every page tested; accessibility 96–100.
- 24 Sep 2026 — Owner supplied opening hours. Yonge: Mon–Fri 10–8, Sat 10–7, Sun 10–6. Bridlewood: Mon–Fri 10–8, Sat 9–7, Sun 11–6. Shown on both salon pages, Locations, Contact and the homepage salon cards, and in each salon's details for Google (openingHoursSpecification).
- 26 Sep 2026 — Owner photos and decisions. Real lash work (6 photos) on Eyelash Extensions (hero + 'Recent lash sets' strip), Skin & Lashes, Facial Hair Removal and the homepage Lashes panel. Bridlewood storefront (salon page hero) and interior (homepage + Locations cards, salon page gallery, Google salon details) replace the Dec 2024 team photo. Stock by owner's choice: finished pedicure (replaces the Instagram tray), facial, body hair removal. Acrylic photo confirmed as acrylic. Blog: laser article kept with its note; price-range removal approved. Privacy policy: contact-form wording removed. No photo placeholders remain on the site. Still owner's call: piercing notice page vs 301 to /skin/ (kept as notice page). Privacy policy still describes analytics as 'privacy-respecting analytics and spam protection (Cloudflare Turnstile)'; the site now uses Google Analytics / Google Ads via Tag Manager — have the policy wording reviewed.

## 28 Sep — privacy policy draft
- `/privacy/` rewritten (dated 28 Sep 2026): GTM, GA4, Google Ads conversion + remarketing, cookies/identifiers, click events, Fresha as third party, opt-outs, access/correction/withdrawal via email, Turnstile removed (no form on the new site).
- DRAFT: written from the site's actual behaviour, not by a lawyer. Have it reviewed (PIPEDA/CASL) before or soon after launch. If a cookie-consent banner is added later, update the "Cookies" section.
- `/skin/body-piercing/` stays as the "no longer offered" notice page (noindex).

## 28 Sep — emails and homepage fixes
- info@beautiquebar.com removed (does not exist). Yonge = beautiquebar.yonge@gmail.com, Bridlewood = beautiquebar88@gmail.com: contact page (per salon), footer (both), legal pages, per-salon JSON-LD; email click events map to the right salon.
- Homepage frame with the red nails: on phones the frame is wider/taller and the photo is shifted so the nails sit centred; text moved clear of the frame.
- "Beyond nails" (Lashes / Hair removal / Skin) on phones: photo now stays pinned under the header, cross-fades, and each row gets scroll room; switching happens below the photo.
- Homepage red-nails frame on phones: uses a dedicated one-hand crop (work-oxblood-almond-crop.webp), so the second hand no longer appears.
