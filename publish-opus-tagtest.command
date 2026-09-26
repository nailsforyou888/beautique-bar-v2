#!/bin/bash
# Deploys the TAG-TEST copy (launch build with Google Tag Manager, hidden from search) as a branch preview:
#   https://tag-test.beautique-bar-opus-design-v1.pages.dev
# For testing GTM / GA4 / Google Ads tags before launch. BeautiqueBar.com, DNS and the production project are not touched.
cd "$(dirname "$0")"
export PATH="$PWD/.node/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
W="npx --yes wrangler@latest"
echo "Deploying tag-test preview…"
$W pages deploy opus-site-tagtest --project-name beautique-bar-opus-design-v1 --branch tag-test --commit-dirty=true
echo
echo "Finished. Tag-test preview: https://tag-test.beautique-bar-opus-design-v1.pages.dev"
read -n 1 -s -r -p "Press any key to close"
