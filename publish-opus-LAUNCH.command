#!/bin/bash
# The website now publishes itself from GitHub: every save in Pages CMS (or push to "main") rebuilds beautiquebar.com.
# This old one-click upload is switched off so it can never overwrite newer edits with an outdated copy.
# To re-publish by hand: GitHub > nailsforyou888/beautique-bar-v2 > Actions > Publish website > Run workflow.
echo "Publishing now happens automatically from GitHub (see EDITING.md)."
echo "To re-publish by hand: GitHub > Actions > Publish website > Run workflow."
read -n 1 -s -r -p "Press any key to close"
