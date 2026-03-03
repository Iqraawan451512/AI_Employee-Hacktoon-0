#!/usr/bin/env bash
# setup_vault_repo.sh — One-time script to initialize AI_Employee_Vault as a Git repo
# Run this on the cloud VM after cloning the main project repo.
#
# Usage:
#   bash scripts/setup_vault_repo.sh <REMOTE_URL>
#   Example: bash scripts/setup_vault_repo.sh git@github.com:user/ai-employee-vault.git

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_DIR="$PROJECT_ROOT/AI_Employee_Vault"

REMOTE_URL="${1:-}"
BRANCH="${2:-main}"

if [ -z "$REMOTE_URL" ]; then
    echo "Usage: $0 <REMOTE_URL> [BRANCH]"
    echo "  REMOTE_URL: Git remote URL for the vault repo"
    echo "  BRANCH:     Branch name (default: main)"
    exit 1
fi

echo "=== AI Employee Vault Git Setup ==="
echo "Vault:  $VAULT_DIR"
echo "Remote: $REMOTE_URL"
echo "Branch: $BRANCH"
echo ""

# Initialize git repo in vault if not already done
if [ ! -d "$VAULT_DIR/.git" ]; then
    echo "[1/5] Initializing git repo..."
    git init "$VAULT_DIR"
else
    echo "[1/5] Git repo already initialized"
fi

cd "$VAULT_DIR"

# Set up remote
if git remote get-url origin &>/dev/null; then
    echo "[2/5] Updating existing remote..."
    git remote set-url origin "$REMOTE_URL"
else
    echo "[2/5] Adding remote..."
    git remote add origin "$REMOTE_URL"
fi

# Configure git for vault
echo "[3/5] Configuring git..."
git config pull.rebase true
git config push.default current
git config merge.ours.driver true  # For Dashboard.md merge=ours

# Create .gitattributes for merge strategy
cat > .gitattributes << 'EOF'
# Auto detect text files and perform LF normalization
* text=auto

# Dashboard.md: Local always wins on merge conflicts (single-writer rule)
Dashboard.md merge=ours
EOF

# Create .gitignore for vault
cat > .gitignore << 'EOF'
# Obsidian internal
.obsidian/

# OS files
.DS_Store
Thumbs.db

# Conflict backup files
*.conflict
EOF

# Initial commit and push
echo "[4/5] Creating initial commit..."
git add -A
git commit -m "vault: initial setup for Git sync" || echo "Nothing to commit"

echo "[5/5] Pushing to remote..."
git push -u origin "$BRANCH" || {
    echo "Push failed. If this is a new repo, create it first on your Git host."
    echo "Then run: cd $VAULT_DIR && git push -u origin $BRANCH"
}

echo ""
echo "=== Setup Complete ==="
echo "Vault is now a Git repo syncing to: $REMOTE_URL"
echo "Run 'python scripts/vault_sync.py --vault $VAULT_DIR' to start sync loop."
