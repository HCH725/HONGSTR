#!/bin/bash

# SECURITY NOTE: This script uses 'curl | bash' to install upstream tooling.
# Review the remote script URL before running in production environments.
# Prefer pinned versions and verified checksums where possible.
set -e
cd ~/Projects/HONGSTR
# --- Ensure Node 18+ (NO brew) ---
export NVM_DIR="$HOME/.nvm"
# Install NVM if not present
if [ ! -d "$NVM_DIR" ]; then
  echo "Installing NVM..."
  mkdir -p "$NVM_DIR"
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
# Load nvm
echo "Loading NVM..."
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
echo "Installing Node 20..."
nvm install 20
nvm use 20
nvm alias default 20
echo "Node Version: $(node -v)"
echo "NPM Version: $(npm -v)"
echo "NPX Version: $(npx -v)"
# --- C6 init (Next.js dashboard) ---
if [ ! -d "web" ]; then
  echo "Initializing Next.js app in web/..."
  # Adding --yes and other flags to avoid interactive prompts which cause hangs
  # Defaulting to App Router, SRC dir, etc. to match standard expectations if not prompted
  npx -y create-next-app@latest web \
    --typescript \
    --tailwind \
    --eslint \
    --yes
else
  echo "web/ directory already exists. Skipping create-next-app."
fi
cd web
echo "Installing dependencies..."
npm install
echo "Building project..."
npm run build
echo "C6 Init Complete."