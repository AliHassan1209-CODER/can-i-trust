#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  Can I Trust? — One-command setup script                     ║
# ║                                                              ║
# ║  Usage:                                                      ║
# ║    chmod +x setup.sh && ./setup.sh                           ║
# ╚══════════════════════════════════════════════════════════════╝

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${CYAN}${BOLD}  $1${RESET}"
  echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
}
ok()   { echo -e "${GREEN}✓${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $1"; }
err()  { echo -e "${RED}✗${RESET} $1"; exit 1; }

banner "Can I Trust? — Setup"

# ── 1. Check dependencies ────────────────────────────────────────
echo -e "${BOLD}Checking dependencies...${RESET}"
command -v docker        &>/dev/null && ok "Docker found"        || err "Docker not installed"
command -v docker-compose &>/dev/null && ok "Docker Compose found" || \
  docker compose version &>/dev/null && ok "Docker Compose (plugin) found" || \
  err "Docker Compose not installed"

# ── 2. Environment file ──────────────────────────────────────────
banner "Environment Setup"
if [ ! -f .env ]; then
  cp .env.example .env
  ok "Created .env from template"
  warn "Please edit .env and fill in your values before continuing!"
  warn "Required: POSTGRES_PASSWORD, SECRET_KEY, NEWS_API_KEY"
  echo ""
  read -p "Press Enter after editing .env to continue... " _
else
  ok ".env already exists"
fi

# ── 3. Validate critical env vars ────────────────────────────────
source .env
[ -z "$POSTGRES_PASSWORD" ] && err "POSTGRES_PASSWORD is not set in .env"
[ "$POSTGRES_PASSWORD" = "CHANGE_ME_strong_password_here" ] && err "Change POSTGRES_PASSWORD in .env!"
[ -z "$SECRET_KEY" ]        && err "SECRET_KEY is not set in .env"
[ "$SECRET_KEY" = "CHANGE_ME_generate_a_real_secret_key_here" ] && err "Change SECRET_KEY in .env!"
ok "Environment variables validated"

# ── 4. Generate SSL certificates (self-signed for local dev) ─────
banner "SSL Certificate Setup"
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/fullchain.pem ]; then
  echo "Generating self-signed certificate (for local development)..."
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/privkey.pem \
    -out    nginx/ssl/fullchain.pem \
    -subj   "/C=PK/ST=Punjab/L=Lahore/O=CanITrust/CN=localhost" \
    2>/dev/null
  ok "Self-signed SSL certificate generated"
  warn "For production: replace nginx/ssl/ certs with real Let's Encrypt certs"
else
  ok "SSL certificates already exist"
fi

# ── 5. Copy source code into docker context ──────────────────────
banner "Preparing Build Context"
if [ -d "../can_i_trust_backend" ]; then
  rsync -a --exclude '__pycache__' --exclude '*.pyc' \
    ../can_i_trust_backend/ ./backend/
  ok "Backend source copied"
else
  warn "Backend source not found at ../can_i_trust_backend — make sure your code is in ./backend/"
fi

if [ -d "../can_i_trust_frontend" ]; then
  rsync -a --exclude 'node_modules' --exclude 'dist' \
    ../can_i_trust_frontend/ ./frontend/
  ok "Frontend source copied"
else
  warn "Frontend source not found at ../can_i_trust_frontend — make sure your code is in ./frontend/"
fi

# ── 6. Create required directories ──────────────────────────────
mkdir -p backups/postgres logs
ok "Directories created"

# ── 7. Build Docker images ───────────────────────────────────────
banner "Building Docker Images"
echo "Building backend and frontend images (this may take a few minutes)..."
docker compose build --parallel
ok "All images built successfully"

# ── 8. Start services ────────────────────────────────────────────
banner "Starting Services"
docker compose up -d
echo ""
echo "Waiting for services to become healthy..."
sleep 15

# ── 9. Health check ──────────────────────────────────────────────
banner "Health Check"
MAX_RETRIES=12; RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
  if curl -sf http://localhost/health > /dev/null 2>&1; then
    ok "API is healthy!"
    break
  fi
  RETRY=$((RETRY+1))
  echo "Waiting for API... ($RETRY/$MAX_RETRIES)"
  sleep 5
done
[ $RETRY -eq $MAX_RETRIES ] && warn "API health check timed out — check logs: docker compose logs api"

# ── 10. Done ─────────────────────────────────────────────────────
banner "Setup Complete!"
echo -e "${BOLD}Your Can I Trust? stack is running:${RESET}\n"
echo -e "  ${GREEN}🌐 App        :${RESET} https://localhost"
echo -e "  ${GREEN}📡 API        :${RESET} https://localhost/api/v1"
echo -e "  ${GREEN}📚 API Docs   :${RESET} https://localhost/docs"
echo -e "  ${GREEN}❤  Health     :${RESET} https://localhost/health"
echo ""
echo -e "${BOLD}Useful commands:${RESET}"
echo -e "  docker compose logs -f          # stream all logs"
echo -e "  docker compose logs -f api      # backend logs only"
echo -e "  docker compose ps               # service status"
echo -e "  docker compose down             # stop everything"
echo -e "  ./scripts/backup_db.sh          # backup database"
echo ""
