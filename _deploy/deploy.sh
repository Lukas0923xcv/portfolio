#!/usr/bin/env bash
# Deploys the built site from the "site" branch to the web root.
#
#   sudo deploy/deploy.sh                 show what changes, ask, then deploy the newest build
#   sudo deploy/deploy.sh -y              same, without asking (used by the timer)
#   sudo deploy/deploy.sh site-2026...    deploy (or roll back to) a tagged build
#   sudo deploy/deploy.sh --list          list the tagged builds
#
# The checkout in $SRC holds the "site" branch, which GitHub Actions fills with the
# contents of dist/. Nothing is built on the server.
set -euo pipefail

SRC=${SRC:-/var/www/portfolio-src}
DEST=${DEST:-/var/www/portfolio}
BRANCH=site
YES=0
REF=""
for arg in "$@"; do
  case "$arg" in
    -y|--yes) YES=1 ;;
    --list) git -C "$SRC" fetch -q --tags origin; git -C "$SRC" tag -l 'site-*' --sort=-creatordate | head -20; exit 0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) REF="$arg" ;;
  esac
done

git -C "$SRC" fetch -q --tags origin "$BRANCH"
REF=${REF:-origin/$BRANCH}
NEW=$(git -C "$SRC" rev-parse --short "$REF^{commit}")
OLD=$(cat "$DEST/.deployed" 2>/dev/null || echo none)

if [[ "$NEW" == "$OLD" && $YES -eq 1 ]]; then
  exit 0   # timer run, nothing new
fi

git -C "$SRC" checkout -q --detach "$REF"

# status.json is written by the lab itself and must survive a deploy
RSYNC=(rsync -a --delete --checksum --exclude .git --exclude _deploy --exclude .deployed --exclude status.json "$SRC/" "$DEST/")

echo "Deploying $NEW (live now: $OLD). Changes:"
"${RSYNC[@]}" --dry-run --itemize-changes | grep -v '^\.' || echo "  (no file changes)"

if [[ $YES -eq 0 ]]; then
  read -r -p "Deploy these changes? [y/N] " answer
  [[ "$answer" == [yY]* ]] || { echo "Cancelled."; exit 1; }
fi

"${RSYNC[@]}"
echo "$NEW" > "$DEST/.deployed"
logger -t portfolio-deploy "deployed $NEW (was $OLD)" 2>/dev/null || true
echo "Done. Live: $NEW"
