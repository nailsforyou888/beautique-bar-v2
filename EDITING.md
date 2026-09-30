# Editing the Beautique Bar website

## Everyday edits — Pages CMS
Go to https://app.pagescms.org, sign in with GitHub, and open **nailsforyou888/beautique-bar-v2** (branch **main**).

| In Pages CMS | What it changes on beautiquebar.com |
|---|---|
| **Prices — Yonge & York Mills** | The Yonge menu page, plus the price examples on service pages |
| **Prices — Bridlewood Mall** | The Bridlewood menu page, plus the price examples on service pages |
| **Salon details & hours** | Phone, texting number, email, Fresha booking link and opening hours, everywhere on the site (homepage, footer, location and contact pages, Google business data) |
| **Blog posts** | Add, edit or hide articles (tick **Draft** to hide one) |

Click **Save**. About 2–3 minutes later the live site is updated. Nothing else to do.

Tips
- Prices are shown exactly as typed: `$26`, `$37+` ("from"), or `$15/$20`.
- Times are 24-hour: `10:00`, `19:00` (7 pm). Tick the days each hours row covers.
- Renaming a service is fine. If a service page was showing it as an example price, it simply drops off that short list (GitHub shows a warning); the full menu is always right.
- If something is typed in a way the site can't use (e.g. a 9-digit phone number), the update is **not** published, the live site stays as it was, and GitHub emails the owner. Fix the typo and save again.

## Where it runs
- Code and content: GitHub `nailsforyou888/beautique-bar-v2`, branch `main`.
- Every change to `main` runs **Actions → Publish website**, which builds the site and uploads it to Cloudflare Pages project `beautique-bar` (beautiquebar.com). To re-publish by hand: GitHub → Actions → Publish website → Run workflow.
- A push to any other branch publishes a preview at `https://<branch>.beautique-bar.pages.dev` instead.
- Editable data: `content/menus/yonge.yml`, `content/menus/warden.yml`, `content/salons.yml`, `opus-site-src/blog/*.md`. Pages CMS setup: `.pages.yml`. Workflow: `.github/workflows/publish.yml`.
- Design, page text and photos are in `opus-site-src/build.py` and `opus-design-v1/` (ask Claude for those changes).
