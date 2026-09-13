#!/usr/bin/env bash
# ==============================================================================
# update_linux_server.sh - Safe 1-Command Updater for Linux Mint Server
# Preserves active Saxo sessions, pulls latest code, rebuilds Docker containers,
# and verifies end-to-end health.
# ==============================================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🚀 [Akpegis Private Cloud] Linux Mint Server Update & Verification${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Resolve Server & Repo Directories
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
SERVER_DIR="$REAL_HOME/akpegis-server"

if [ -d "$SERVER_DIR/nasdaq-multi-agent" ]; then
    REPO_DIR="$SERVER_DIR/nasdaq-multi-agent"
elif [ -d "$SERVER_DIR" ] && [ -f "$SERVER_DIR/docker-compose.yml" ]; then
    REPO_DIR="$SERVER_DIR"
else
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SERVER_DIR="$(dirname "$REPO_DIR")"
fi

echo -e "📂 Server directory: ${BLUE}$SERVER_DIR${NC}"
echo -e "📂 Codebase directory: ${BLUE}$REPO_DIR${NC}"
mkdir -p "$SERVER_DIR/data"

# 2. Pre-Flight Token & Database Backup
echo ""
echo -e "${YELLOW}[1/5] Extracting live in-memory credentials & database snapshot...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^akpegis_backend$"; then
    echo -e "  -> Flushing in-memory broker tokens from active container..."
    docker exec akpegis_backend python -c "
try:
    from options_lab.api.main import saxo_broker_client
    from options_lab.api import db as database
    if saxo_broker_client.access_token:
        database.save_broker_tokens('saxo', saxo_broker_client.access_token, saxo_broker_client.refresh_token)
        print('  -> In-memory Saxo tokens successfully flushed to host volume.')
    else:
        print('  -> No active in-memory tokens to flush.')
except Exception as e:
    print(f'  -> Token extraction notice: {e}')
" 2>/dev/null || true
fi

if [ -f "$SERVER_DIR/data/optionslab.db" ]; then
    cp -f "$SERVER_DIR/data/optionslab.db" "$SERVER_DIR/data/optionslab_backup_preupdate.db"
    echo -e "  ${GREEN}✓ Created database safety snapshot: optionslab_backup_preupdate.db${NC}"
fi

# 3. Pull Latest Git Changes
echo ""
echo -e "${YELLOW}[2/5] Pulling latest code from GitHub...${NC}"
cd "$REPO_DIR"
git fetch origin nasdaq-multi-agent/auth
git checkout nasdaq-multi-agent/auth
git pull origin nasdaq-multi-agent/auth

# Ensure docker-compose.yml is present in SERVER_DIR
if [ "$REPO_DIR" != "$SERVER_DIR" ]; then
    cp -f "$REPO_DIR/docker-compose.yml" "$SERVER_DIR/docker-compose.yml"
fi

# 4. Build and Restart Containers
echo ""
echo -e "${YELLOW}[3/5] Rebuilding and launching Docker containers...${NC}"
cd "$SERVER_DIR"
docker compose down || true
docker compose up -d --build

# 5. Wait for Initialization and Verify Health
echo ""
echo -e "${YELLOW}[4/5] Verifying backend and frontend health...${NC}"
MAX_WAIT=25
ELAPSED=0
HEALTHY=false

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sSf http://localhost:8000/api/health >/dev/null 2>&1 || curl -sSf http://localhost:3000/api/health >/dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -e "  -> Waiting for services to become healthy... (${ELAPSED}s)"
done

echo ""
echo -e "${BLUE}======================================================================${NC}"
if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}✓ SERVER IS HEALTHY & FULLY OPERATIONAL!${NC}"
else
    echo -e "${RED}⚠️ Health check did not respond within ${MAX_WAIT}s. Inspecting logs:${NC}"
    docker compose logs --tail=20 backend
fi
echo -e "${BLUE}======================================================================${NC}"

HOST_IP=$(hostname -I | awk '{print $1}')
echo -e "🌐 Local Wi-Fi Access:   ${GREEN}http://${HOST_IP}:3000${NC}"
if command -v tailscale &>/dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$TS_IP" ]; then
        echo -e "🔒 Tailscale Mesh Access: ${GREEN}http://${TS_IP}:3000${NC}"
    fi
fi
echo -e "🔌 Direct Backend API:   ${BLUE}http://${HOST_IP}:8000/docs${NC}"
echo -e "📋 Live Container Logs:  ${BLUE}cd $SERVER_DIR && docker compose logs -f${NC}"
echo -e "======================================================================"
