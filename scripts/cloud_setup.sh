#!/usr/bin/env bash
# cloud_setup.sh — Ubuntu VM setup for AI Employee Cloud Agent
#
# Installs Python 3.13, uv, git, clones repo, creates secrets dir,
# installs systemd services for cloud orchestrator, gmail watcher,
# vault sync, and health monitor.
#
# Usage:
#   bash cloud_setup.sh <REPO_URL> [VAULT_REMOTE_URL]
#   Example: bash cloud_setup.sh git@github.com:user/ai-employee.git git@github.com:user/vault.git

set -euo pipefail

REPO_URL="${1:-}"
VAULT_REMOTE="${2:-}"
INSTALL_DIR="/opt/ai-employee"
USER="ai-employee"

if [ -z "$REPO_URL" ]; then
    echo "Usage: $0 <REPO_URL> [VAULT_REMOTE_URL]"
    exit 1
fi

echo "=== AI Employee Cloud VM Setup ==="
echo "Repo:    $REPO_URL"
echo "Install: $INSTALL_DIR"
echo ""

# 1. System packages
echo "[1/8] Installing system packages..."
apt-get update
apt-get install -y \
    software-properties-common \
    git \
    curl \
    build-essential \
    libssl-dev \
    docker.io \
    docker-compose-plugin \
    nginx \
    certbot \
    python3-certbot-nginx

# 2. Python 3.13 via deadsnakes PPA
echo "[2/8] Installing Python 3.13..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.13 python3.13-venv python3.13-dev

# 3. Install uv
echo "[3/8] Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 4. Create service user
echo "[4/8] Creating service user..."
if ! id "$USER" &>/dev/null; then
    useradd --system --create-home --shell /bin/bash "$USER"
fi

# 5. Clone repository
echo "[5/8] Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists, pulling latest..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
chown -R "$USER:$USER" "$INSTALL_DIR"

# 6. Set up Python environment
echo "[6/8] Setting up Python environment..."
cd "$INSTALL_DIR/watchers"
sudo -u "$USER" uv sync

# 7. Create secrets directory
echo "[7/8] Creating secrets directory..."
mkdir -p "$INSTALL_DIR/secrets"
chmod 700 "$INSTALL_DIR/secrets"
chown "$USER:$USER" "$INSTALL_DIR/secrets"

echo "Place your credentials in $INSTALL_DIR/secrets/:"
echo "  - credentials.json (Google OAuth2)"
echo "  - token.json (Gmail token)"
echo "  - .env (environment variables)"

# 8. Set up vault Git sync (if remote provided)
if [ -n "$VAULT_REMOTE" ]; then
    echo "[8/8] Setting up vault Git sync..."
    sudo -u "$USER" bash "$INSTALL_DIR/scripts/setup_vault_repo.sh" "$VAULT_REMOTE"
else
    echo "[8/8] Skipping vault sync setup (no remote URL provided)"
fi

# 9. Install systemd services
echo "Installing systemd services..."
cp "$INSTALL_DIR/scripts/systemd/"*.service /etc/systemd/system/

# Set install dir in service files
sed -i "s|/opt/ai-employee|$INSTALL_DIR|g" /etc/systemd/system/ai-*.service

systemctl daemon-reload

# Enable services (don't start yet — need credentials first)
systemctl enable ai-cloud-orchestrator.service
systemctl enable ai-vault-sync.service
systemctl enable ai-health-monitor.service

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy credentials to $INSTALL_DIR/secrets/"
echo "  2. Copy Gmail token to $INSTALL_DIR/watchers/token.json"
echo "  3. Start services:"
echo "     systemctl start ai-vault-sync"
echo "     systemctl start ai-cloud-orchestrator"
echo "     systemctl start ai-gmail-watcher"
echo "     systemctl start ai-health-monitor"
echo ""
echo "  4. Check status:"
echo "     systemctl status ai-cloud-orchestrator"
echo "     journalctl -u ai-cloud-orchestrator -f"
