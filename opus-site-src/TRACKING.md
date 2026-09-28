# Ads & tracking — what the live site does today, and the plan for launch

> Setup/how-to for GTM, GA4, Ads, Search Console: see MARKETING-SETUP.md (single source). This file is the original audit/history.


Read-only audit of beautiquebar.com on 24 Sep 2026 (tags observed loading in a browser + the public GTM container files). Nothing in Google Ads, GA4, GTM or Google Business Profile was changed.

## What is running on the live site today

Google Tag Manager container **GTM-M6WHQ2D5** (version 4) loads on every page. It contains:

| Tag | Fires on | Sends to |
|---|---|---|
| Conversion linker | every page | — |
| Google tag **G-36R797LMPD** | every page | GA4 property A; its Google tag also sends to Google Ads **AW-853145914** |
| Google tag **G-RMHQD1ES46** | every page **except** `/yonge/` and `/locations/yonge/` | GA4 property B |
| Google tag **G-VD6ZXDV561** | **only** `/yonge/` and `/locations/yonge/` | GA4 property C; its Google tag also sends to Google Ads **AW-11155179734** |
| Google Ads conversion **AW-853145914 / wf6ECIq0wKAbELry55YD** | click on any link containing `/book-now/nails-for-you` (the Bridlewood Fresha link), any page | Bridlewood Ads account |
| GA4 event `yonge_booking_click` → G-VD6ZXDV561 | click on the Yonge Fresha link **only while on the Yonge location page** | GA4 property C |

A second container, **GTM-T9VVBKJN**, also loads (through a Google tag). It is an unconfigured template: its GA4 destination is the placeholder "-", values are "1200 USD", several tags are paused. It sends nothing useful.

## Problems found

1. **Yonge has no Google Ads conversion tag.** Bridlewood has one; Yonge relies on the GA4 event `yonge_booking_click`, which only fires when the booking click happens on the Yonge location page. A Yonge booking started from the homepage, a service page, the menu or the booking bar is not recorded anywhere for Yonge.
2. **The Yonge analytics property (G-VD6ZXDV561) only loads on the Yonge location page.** If Yonge ads send people to any other page, those visits are invisible to it, and Google Ads can't learn from them.
3. **Data is split across three GA4 properties** (G-36R797LMPD, G-RMHQD1ES46, G-VD6ZXDV561) — reports never add up.
4. **Phone calls and texts are not conversions.** For a salon, calls are often the biggest action.
5. **Conversions count clicks, not bookings.** A click on "Book" that doesn't end in an appointment still counts. (Fresha's own marketing/tracking settings may allow counting completed bookings — check your Fresha plan.)
6. **Leftover template container (GTM-T9VVBKJN)** — noise; remove its link.

Still unknown (need someone signed in): which Ads campaigns point where (final URLs), whether `yonge_booking_click` is imported into the Yonge Ads account, which conversion actions are "primary", and whether auto-tagging is on in both Ads accounts.

## What the new site already does

- Same page addresses, same Fresha links (so the existing Bridlewood conversion keeps working), same GTM container on the launch copy (`opus-site-production/`); the preview has no tracking at all.
- Every booking, call, text, directions and email click pushes a clean event with the salon attached:
  `dataLayer.push({event: 'bb_book' | 'bb_call' | 'bb_text' | 'bb_directions' | 'bb_email', bb_salon: 'yonge' | 'bridlewood', bb_link, bb_placement})`
- Each salon page has "Book [salon] online", "Call" and "Directions" at the top — good ad landing pages:
  - Yonge ads → `https://beautiquebar.com/locations/yonge/`
  - Bridlewood ads → `https://beautiquebar.com/locations/warden/`
- Search: unique titles/descriptions with neighbourhood keywords, NailSalon details for each salon (address, postal code, phone, map, services and prices), breadcrumbs, service and article details, sitemap, share image, fast self-hosted fonts. Lighthouse SEO score 100 on every page tested.

## Launch-day setup (for whoever manages GTM / Ads) — in this order

1. **One GA4 property for the website.** Pick one (or create "Beautique Bar — Website"); keep the others for history but stop sending to them. Put its Google tag on all pages.
2. **In GTM-M6WHQ2D5, add six Custom Event triggers** on the new events:
   - `bb_book` where `bb_salon` = `yonge`; `bb_book` where `bb_salon` = `bridlewood`
   - `bb_call` yonge / bridlewood; `bb_text` yonge / bridlewood (text is Yonge-only in practice — Bridlewood's number is call-or-text)
   (Create a Data Layer Variable `bb_salon` first.)
3. **Google Ads conversion tags per salon, in that salon's Ads account:**
   - Yonge account (AW-11155179734): "Book online — Yonge" on `bb_book`+yonge; "Call — Yonge" on `bb_call`+yonge
   - Bridlewood account (AW-853145914): "Book online — Bridlewood" on `bb_book`+bridlewood (this replaces the old link-click trigger); "Call — Bridlewood" on `bb_call`+bridlewood
   Mark "Book online" as the primary conversion; calls primary too if you bid on calls.
4. **GA4 events** from the same triggers (`booking_click`, `phone_click` with a `salon` parameter) and mark them as key events.
5. **Remove** the path-based Yonge rules (G-VD6ZXDV561 only on Yonge pages, `yonge_booking_click`) and the link to GTM-T9VVBKJN once the new tags are verified.
6. **Test before publishing the GTM version:** GTM Preview / Tag Assistant on the live site — click Book, Call and Text for each salon from the homepage, a service page and each salon page; confirm one conversion per click in the right account.
7. **In each Ads account:** confirm auto-tagging is on; set each salon's campaign final URL to its salon page; add call assets with the salon's number; link each account to its salon's Google Business Profile for location assets.
8. **Search Console:** verify beautiquebar.com, submit `https://beautiquebar.com/sitemap.xml`, and use URL Inspection on the homepage and both salon pages after launch.

## Still needed from you for search

- ~~Opening hours~~ — added 24 Sep 2026 (site pages + salon details for Google). Make sure both Google Business Profiles show the same hours.
- Bridlewood interior and finished-pedicure photos.

## Tag-test preview (26 Sep 2026)

Built to the owner's tracking requirements (GTM-M6WHQ2D5 only; dataLayer schema; fixed salon URLs; sitemap; QR forwards).

- **URL:** https://tag-test.beautique-bar-opus-design-v1.pages.dev — exactly the launch copy (GTM-M6WHQ2D5 on every page, first thing in `<head>`; `<noscript>` iframe straight after `<body>`), but hidden from search (noindex meta + header, robots Disallow). Made by `make_production.py --tagtest`, deployed by `publish-opus-tagtest.command`.
- Testing on it sends real hits to whatever GTM fires (GA4 / Ads) — use GTM Preview / Tag Assistant, and filter or exclude test traffic if needed.
- **No other Google code** in the site: no gtag.js, no G-/AW- IDs, no other containers (checked by search over every file).
- **Events** (automated check: 393 tracked links on 37 pages, each fires exactly one event with the clicked href):
  `bb_book` 236 · `bb_call` 102 · `bb_email` 41 · `bb_directions` 10 · `bb_text` 4
  `bb_placement` values: `header` (none — the header Book button opens the salon chooser, whose links report `booking-dialog`), `booking-dialog`, `mobile-menu`, `hero`, `salon-details`, `salon-card`, `prices`, `closing`, `contact`, `footer`, `body`.
  `bb_salon` is always `yonge` or `bridlewood` for book/call/text/directions. Each salon has its own email (beautiquebar.yonge@ / beautiquebar88@), so email clicks now report the right salon everywhere.
- **QR / short links:** `/yonge`, `/yonge/` → `/locations/yonge/`; `/warden`, `/warden/` → `/locations/warden/` (301). Old WordPress blog paths and `/home/` also forward.
- **Security headers** allow Google Tag Manager, GA4, Google Ads (incl. google.ca endpoints) and GTM Preview / Tag Assistant.
