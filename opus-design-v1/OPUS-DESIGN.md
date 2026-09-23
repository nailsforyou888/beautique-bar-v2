# Beautique Bar — opus-design-v1

A separate desktop homepage prototype (Opus 5.5 interpretation) for side-by-side comparison with the approved Concept C. Concept C (`index.html`, `c.html`, `homepage.*`, `shared.*` at the repo root) is untouched.

- Open: `opus-design-v1/index.html` (static, no build step). Review at 1440 × 900.
- Add `?notes` to the URL, or press **Photography notes** in the footer, to overlay the brief for every temporary image.
- `noindex, nofollow` via meta tag, `_headers` (X-Robots-Tag) and `robots.txt`.
- Nothing in production changed: no DNS, Cloudflare production settings, Ads, GA4, tracking, GBP or Fresha. Booking links open the existing Fresha pages.

## Concept — "The threshold"

The whole page is one idea told twice: stepping from the city into your own time.

1. **Opening (the strongest motion).** A hand-care photograph sits whole, a single hairline seam appears down its centre, and the image parts like two doors. The headline is split by meaning: *Outside, the city.* is printed on the outside and leaves with the left door; *Inside, your time.* stays, because it belongs to the room behind. The salon comes up out of darkness, *Come in. Switch off.* surfaces, then the entire room contracts into a single portrait window on warm stone, the interior dissolves into hands at rest, and the line *Your everyday · beauty ritual.* is spoken either side of that window. One continuous, reversible scene; no cuts.
2. **Nails.** A giant sticky *Nails.* with a live index (Manicure → Pedicure → Shellac → Bio Gel → Acrylic) that tracks the editorial image column as you scroll.
3. **Beyond nails.** One sticky photograph, re-masked (wiped upward) as Lashes, Hair removal and Skin pass through the viewport; also responds to hover and keyboard focus.
4. **The salons.** Atmosphere rather than another reveal: a tall interior photograph, an overlapping comfort detail with a gentle parallax, and a real client line about the ambiance. *Settle in. We'll take it from here.* Clean · Calm · Close to home.
5. **Two addresses. One ritual.** Both salons at identical size, side by side, each with Book (solid, strongest), Explore, Directions and phone.
6. **In their words.** One large verbatim review plus three short ones. No stars, counts or awards.
7. **The little details.** Lookbook on a 12-column editorial grid with mixed proportions and one full-width image.
8. **Make time for yourself.** Dark close with both salons as large booking rows.

Motion arc: WOW (opening) → CALM (nails, slow scale-settle only) → DISCOVER (service mask) → TRUST (one gentle parallax, then static) → BOOK (no motion beyond hover).

## Preserved from Concept C

- Palette (#211e1a, #27231f, #b8ab99, #eee9df) plus one lighter linen tint and one soft stone tint for section rhythm.
- Italiana + DM Sans (DM Sans now used at 300 for a lighter editorial texture).
- Split-image opening revealing the salon; *Outside, the city. / Inside, your time.*; *Come in. Switch off.*; stone layer → *Your everyday beauty ritual.*
- Big sticky *Nails.*, the sticky changing service photograph, editorial single review, mixed-proportion lookbook, dark booking close, booking dialog.
- Native scroll, reversible, semantic HTML, reduced-motion fallback, no autoplay.

## Deliberately changed

- **Opening:** the headline now splits by meaning and travels with the doors; a seam line precedes the split; doors push slightly toward the viewer; the stone layer no longer wipes over the room — the room itself shrinks into a window, so the transition is a transformation rather than a cover. The salon image switched to the deep-perspective Bridlewood interior (stronger "step inside" depth).
- **Header:** transparent and section-aware. Light text over dark/photo scenes; ink text with a frosted linen bar over light sections; tone flips mid-opening when the stone appears. Book stays visible throughout (solid ink on light sections).
- **Nails:** five verified services, each with its own image and two-word line, plus a live index — instead of two grouped stories.
- **Services:** masked wipe instead of crossfade; nails removed from this list (they have their own chapter).
- **Salon experience:** a composed place + comfort + client-voice section (pass 2 replaced the earlier aperture reveal).
- **Locations:** equal weight (Concept C staggered them and gave Yonge a taller photo); added phone numbers; Book is a solid button.
- **Reviews:** one lead + three supporting verbatim quotes chosen to cover longevity, cleanliness/relaxation, space and a named technician.
- **Interior grade:** the real salon photos have strong blue LED light; a CSS warm/desaturate grade pulls them into the palette until they are reshot.

## Temporary photography (replace later)

All images are hot-linked from beautiquebar.com and should be licensed, optimised and hosted with the site.

| Where | Current asset | Final shot needed |
| --- | --- | --- |
| Opening doors | salon-apply | Hand-care moment, wide 3:2, centre-weighted so it splits cleanly down the middle |
| Opening room / Bridlewood card | interior-why | Wide interior, lights on, straight down the stations, warm white light (no blue LED cast) |
| Opening window | salon-3 | Hands at rest on fabric, portrait crop |
| Manicure | salon-hero | Finished manicure macro on ivory satin |
| Pedicure | svc-manicure (500px) | Pedicure detail at a Beautique chair, top-down |
| Shellac | salon-mauve | Real Shellac result, muted shade |
| Bio Gel | svc-biogel (500px) | Bio Gel result macro, natural length |
| Acrylic | **FINAL PHOTOGRAPHY REQUIRED** | Sculpted almond set, side-profile macro |
| Lashes / Hair removal / Skin | 500px service images | One art-directed macro per service in the same light |
| The salons | interior-banner | Polish wall + stations, one client mid-appointment, no faces |
| Yonge card | interior-loc | Wide interior from the entrance |
| Lookbook | salon-mauve, blog, svc-shellac, salon-apply | Real client work (with permission), hands, salon details |
| Lookbook material | **FINAL PHOTOGRAPHY REQUIRED** | Extreme macro of polish / chrome texture |

## Special imagery worth producing later

- A locked-off **door-split plate**: one hand-care photograph shot extra wide so both halves read on their own.
- A **15–20 s silent interior loop** (lights warming up, slow push down the stations) to sit behind the doors; copy stays HTML.
- **Macro material loops** (polish being laid down, chrome catching light) for the lookbook — optional.
- One consistent **interior grade** for both salons so they read as one brand.

## Why this may be stronger

- The opening tells a story rather than performing an effect: the words move with the layer they belong to, and the ending *becomes* the next section instead of covering it.
- Nails read unmistakably as the flagship: five named services, largest type on the page, a navigable index.
- One strong motion moment, then masks and a single parallax at decreasing intensity, so the page feels designed as one piece.
- Both salons are commercially equal, and booking is never more than one click away (header, each salon, the close, the dialog).

## Content sources

Services, links, phones and reviews verified on beautiquebar.com on 22 Sep 2026. Reviews are verbatim from the homepage; underlying Google reviews were not independently authenticated. Bridlewood shows only the street address (floor detail left out, as in Concept C). Body piercing exists on the site but was left off the homepage as outside the requested set.

---

## Refinement pass 2 (23 Sep 2026)

Same design, polished for review at 1440 × 900 (also checked at 1280 × 720). Full photo shot list: [`PHOTOGRAPHY.md`](PHOTOGRAPHY.md).

**Timing / motion**
- Opening redistributed within the same 460vh: headline alone for the first 8 %, doors part 8–36 %, *Outside, the city.* gone by 19 % and *Inside, your time.* by 26 %.
- Clean salon moment (26–40 %) with no copy; *Come in. Switch off.* 40–60 % over a slightly deeper veil; another short hold (60–64 %).
- Window contraction 64–82 %, hands dissolve 72–86 %, *Your everyday beauty ritual.* fully readable by 90 % and held to the end.
- Salon section is no longer a second aperture reveal: a static editorial composition (place photo + comfort detail + a real client line) with one gentle parallax on the detail image. It's the only scroll-linked motion after the opening.
- Services: image wipe shortened (0.85 s), the outgoing photo stays underneath so the frame is never empty, service images load eagerly, rows tightened (52vh → 36vh).

**Typography / readability**
- Ritual statement: lighter warm stone ground (#c9bead) and deeper ink; eyebrows darker.
- Small text raised to 11.5 px minimum (eyebrows, captions, numbers, footer); nav 13 px, links 13.5 px, body copy 14–14.5 px; inactive nail/service names 55 % / 50 % opacity (were 42 % / 35 %).
- Larger click targets: nav links, text links, dialog close (44 × 44), Book buttons.
- Header label is now **Book Appointment**; a soft top scrim keeps the light header legible over bright opening photography and fades out when the stone appears.
- Final CTA rows now carry an explicit **Book** button each.

**Deliberately not changed:** Nails section layout and type size, the two-location layout, lookbook grid, final CTA copy, palette, fonts.

---

## V5 targeted refinement (23 Sep 2026)

V4 is the base design; changes are targeted only.
- **Opening:** same 460vh. The salon now settles fully into the frame (61–76 %), the ritual line arrives around the framed salon (72–82 %), then inside the same frame the salon dissolves slowly into the manicure (80–95 %) while both images drift together. Before, the swap happened while the frame was still shrinking.
- **Nails:** only finished-result imagery. Manicure, Shellac and Bio Gel use strong existing finished-nail placeholders; Pedicure and Acrylic are FINAL PHOTOGRAPHY REQUIRED panels. Promo procedure frames (drill, gloves) are removed from Nails.
- **Services:** the hair-removal wax-stick image is replaced by a FINAL PHOTOGRAPHY REQUIRED panel; the selector itself is unchanged. Keyboard focus now reliably wins over scroll selection.
- **Salon experience:** rebuilt as one large real interior (new crop of the Yonge pedicure lounge) with the heading, a single "Clean · Calm · Close to home" line and generous space. The extra quote, the soft walkthrough frame, the overlapping detail and its parallax are removed.
- **Reviews:** one featured review, then a single quiet line of three short verbatim quotes and the Google link. The earlier three-column review row and the salon-section quote are gone.
- **Lookbook:** the pedicure tool tray is replaced by the own-label gel bottles; the grid is unchanged.
- **Bridlewood:** still a photography-required panel. The Drive folder contained only the Yonge photos.
