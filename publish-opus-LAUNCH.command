#!/bin/bash
# STEP 1 OF LAUNCH: puts the finished production site into its own Cloudflare Pages project
# (in the nailsforyou888 Cloudflare account) at https://beautique-bar.pages.dev
# It does NOT touch beautiquebar.com, DNS or the old site. Safe to run any time; re-run to update.
# Attaching the real domain is a separate step (see LAUNCH-RUNBOOK.md).
cd "$(dirname "$0")"
export PATH="$PWD/.node/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
W="npx --yes wrangler@latest"
echo "Making sure the project exists (an 'already exists' message is fine)…"
$W pages project create beautique-bar --production-branch main
echo
echo "Deploying the production site…"
$W pages deploy opus-site-production --project-name beautique-bar --branch main --commit-dirty=true
echo
echo "Finished. Check it here: https://beautique-bar.pages.dev"
read -n 1 -s -r -p "Press any key to close"
