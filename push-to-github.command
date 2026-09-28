#!/bin/bash
# Backs up the new site to GitHub: commits the launch files and pushes branch opus-site-v1
# to https://github.com/nailsforyou888/beautique-bar-v2 (a new branch; 'main' is not touched).
cd "$(dirname "$0")"
if pgrep -x git >/dev/null; then echo "Another git process is running; close it and retry."; exit 1; fi
rm -f .git/index.lock
git checkout opus-site-v1 || exit 1
git add publish-opus-LAUNCH.command LAUNCH-RUNBOOK.md push-to-github.command
git commit -m "Add launch runbook and launch publish script

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011uDJZcv3nUMo4GhcbkLfZH"
echo
echo "Pushing to GitHub…"
git push -u origin opus-site-v1
echo
git log --oneline -3
read -n 1 -s -r -p "Press any key to close"
