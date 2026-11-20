#!/usr/bin/env bash
# Lists the most requested missing pages from the nginx access log.
#   deploy/check-404.sh [/var/log/nginx/access.log] [how many]
# Fix the real ones with a redirect, ignore the bots probing for /wp-login.php.
LOG=${1:-/var/log/nginx/access.log}
N=${2:-25}
zcat -f "$LOG" "$LOG".1 "$LOG".*.gz 2>/dev/null \
  | awk '$9 == 404 { print $7 }' \
  | grep -vE '\.(php|env|git|asp|aspx|cgi|bak|sql)($|\?)|/wp-|/cgi-bin/' \
  | sort | uniq -c | sort -rn | head -n "$N"
