#!/usr/bin/env bash
# Deployment pre-flight check (Runbook R1/R2).
# Verifies Redis services are reachable and a fresh site backup exists
# BEFORE migrate/deploy. Exit code 0 = safe to deploy, 1 = STOP.
#
# Usage:
#   bash scripts/preflight_check.sh <site-name> [redis_cache_port] [redis_queue_port]
# Example:
#   bash scripts/preflight_check.sh localhost

set -u

SITE="${1:-}"
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CACHE_PORT="${2:-}"
QUEUE_PORT="${3:-}"
FAIL=0

if [ -z "$SITE" ]; then
    echo "Usage: bash scripts/preflight_check.sh <site-name> [cache_port] [queue_port]"
    exit 1
fi

echo "=== Construction ERP deployment pre-flight: site '$SITE' ==="

# 1. Resolve Redis ports from bench config if not given
CONFIG="$BENCH_DIR/sites/common_site_config.json"
if [ -z "$CACHE_PORT" ] && [ -f "$CONFIG" ] && command -v python3 >/dev/null; then
    CACHE_PORT=$(python3 -c "import json,sys;print(json.load(open('$CONFIG')).get('redis_cache','').rsplit(':',1)[-1])" 2>/dev/null)
    QUEUE_PORT=$(python3 -c "import json,sys;print(json.load(open('$CONFIG')).get('redis_queue','').rsplit(':',1)[-1])" 2>/dev/null)
fi
CACHE_PORT="${CACHE_PORT:-13000}"
QUEUE_PORT="${QUEUE_PORT:-11000}"

# 2. PING both Redis services
for entry in "redis_cache:$CACHE_PORT" "redis_queue:$QUEUE_PORT"; do
    name="${entry%%:*}"
    port="${entry##*:}"
    if redis-cli -p "$port" ping 2>/dev/null | grep -q PONG; then
        echo "[PASS] $name answers on port $port"
    else
        echo "[FAIL] $name NOT reachable on port $port."
        echo "       Start it:  redis-server $BENCH_DIR/config/${name}.conf --daemonize yes"
        FAIL=1
    fi
done

# 3. Site exists?
if [ ! -d "$BENCH_DIR/sites/$SITE" ]; then
    echo "[FAIL] Site directory not found: sites/$SITE"
    FAIL=1
else
    echo "[PASS] Site directory found: sites/$SITE"
fi

# 4. Fresh backup? (must be made within the last 24h; check public + private dirs)
BACKUP_DIR="$BENCH_DIR/sites/$SITE/backups"
PRIVATE_BACKUP_DIR="$BENCH_DIR/sites/$SITE/private/backups"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*-database.sql.gz "$PRIVATE_BACKUP_DIR"/*-database.sql.gz 2>/dev/null | head -1 || true)
if [ -z "$LATEST_BACKUP" ]; then
    echo "[WARN] No database backup found in sites/$SITE/backups"
    echo "       Run BEFORE migrate:"
    echo "         bench --site $SITE backup --with-files"
    FAIL=1
else
    AGE_HOURS=$(( ( $(date +%s) - $(stat -c %Y "$LATEST_BACKUP") ) / 3600 ))
    if [ "$AGE_HOURS" -le 24 ]; then
        echo "[PASS] Backup is fresh ($AGE_HOURS h old): $(basename "$LATEST_BACKUP")"
    else
        echo "[WARN] Latest backup is ${AGE_HOURS}h old (>24h). Re-run:"
        echo "         bench --site $SITE backup --with-files"
        FAIL=1
    fi
fi

# 5. Disk space (backups + migrations need headroom; warn under 2GB)
AVAIL_KB=$(df -Pk "$BENCH_DIR/sites" | awk 'NR==2 {print $4}')
if [ "${AVAIL_KB:-0}" -lt 2097152 ]; then
    echo "[WARN] Low disk space: $((AVAIL_KB / 1024)) MB free in sites/ (<2GB)"
    FAIL=1
else
    echo "[PASS] Disk space OK ($((AVAIL_KB / 1024 / 1024)) GB free)"
fi

echo "=================================================="
if [ "$FAIL" -eq 0 ]; then
    echo "RESULT: SAFE TO DEPLOY. Next: migrate → build → restart."
    exit 0
else
    echo "RESULT: DO NOT DEPLOY. Fix the FAIL/WARN items above first."
    exit 1
fi
