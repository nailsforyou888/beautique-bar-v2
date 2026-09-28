# Beautique Bar – go-live runbook (beautiquebar.com)

Status on 28 Sep 2026: everything is prepared. Nothing live has been changed.

## Already done (no action needed)
- Your own Cloudflare account (nailsforyou888@gmail.com) has beautiquebar.com added, status "Pending".
- All 14 DNS records were copied over and match what the internet sees today (site, www, mail forwarding, email-sending records, Google Search Console verification, DMARC).
- The finished site is ready to publish (opus-site-production).

## The two new nameservers (write these down)
    lauryn.ns.cloudflare.com
    lloyd.ns.cloudflare.com
Old ones (for rollback): aron.ns.cloudflare.com / donald.ns.cloudflare.com

## Step 1 – Put the site online (safe, does not touch beautiquebar.com)
In Finder open the beautique-bar-v2-opus-design folder and double-click **publish-opus-LAUNCH.command**.
When it finishes, open https://beautique-bar.pages.dev on your phone and click through: home, both salons, gallery, Book / Call / Directions buttons.
Re-run the same file any time to update.

## Step 2 – Pick the moment
Choose a quiet time (evening after closing is ideal). Expect roughly 15-30 minutes where the site may be down or flaky. Keep this page open.

## Step 3 – Switch the nameservers (Namecheap)
1. Namecheap > Domain List > Manage beautiquebar.com.
2. Advanced DNS: make sure DNSSEC is OFF.
3. Domain tab > Nameservers > choose **Custom DNS** > enter lauryn.ns.cloudflare.com and lloyd.ns.cloudflare.com > save (green tick).
4. In Cloudflare open beautiquebar.com > Overview > click "Check nameservers now". Wait until the status says **Active** (minutes to a few hours; Cloudflare also emails you).

## Step 4 – Attach the domain to the new site (Cloudflare)
1. Workers & Pages > **beautique-bar** > Custom domains > Set up a custom domain > `beautiquebar.com`.
2. Cloudflare may say a DNS record already exists. In DNS > Records delete the imported A and AAAA records for `beautiquebar.com` and `www` (8 records), then continue. KEEP the MX, TXT, tracking and _domainkey records.
3. Repeat for `www.beautiquebar.com`.
4. Rules > Redirect Rules > new rule: if hostname equals www.beautiquebar.com then redirect (dynamic) to `concat("https://beautiquebar.com", http.request.uri.path)`, status 301. Keep query string.
5. SSL/TLS > Edge Certificates: turn on Always Use HTTPS.

## Step 5 – Test
- https://beautiquebar.com and https://www.beautiquebar.com (should end up on beautiquebar.com)
- A few old links: /shop, /salons, a blog post URL. They should land on a sensible page, not an error.
- /sitemap.xml and /robots.txt open; the page source of the homepage shows no "noindex".
- Book, Call, Text, Directions buttons at both salons.
- Search Console still shows the domain as verified.

## Rollback (if anything looks wrong)
Namecheap > Nameservers > Custom DNS > aron.ns.cloudflare.com and donald.ns.cloudflare.com. The old site comes back once that spreads (minutes to hours). Nothing on the old account is removed by any step above.

## Afterwards
- Leave the old setup alone for about two weeks before cancelling or removing anything.
- Then follow MARKETING-SETUP.md (GTM/GA4/Ads/Search Console sitemap).
- Rotate any logins that were ever shared with the old web manager.

## Heads-up about the old manager
Nothing here messages him. But once the nameservers move, his site stops being served and Cloudflare may email him that the domain left his account. It cannot be fully silent.
