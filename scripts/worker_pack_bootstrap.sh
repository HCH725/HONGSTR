#!/usr/bin/env bash
# HONGSTR Worker Pack Bootstrap (macOS-only)
# Installs prerequisites, clones repository, sets up local venv, and caches skills.
set -euo pipefail

echo "== HONGSTR Worker Pack Bootstrap =="

# 1. Prerequisites Check
if ! xcode-select -p &>/dev/null; then
  echo "=> Installing Xcode Command Line Tools..."
  xcode-select --install
  echo "Please complete the GUI installation, then re-run this script."
  exit 1
fi

if ! command -v brew &>/dev/null; then
  echo "=> Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 2. Repo Clone & Directory Setup
TARGET_DIR="${HOME}/Projects/HONGSTR"
if [ ! -d "$TARGET_DIR" ]; then
  echo "=> Cloning repository to $TARGET_DIR..."
  mkdir -p "${HOME}/Projects"
  cd "${HOME}/Projects"
  # This assumes read-only deploy key or standard user auth is already setup
  git clone git@github.com:HCH725/HONGSTR.git
fi

cd "$TARGET_DIR"

# 3. Virtual Environment & Dependencies
if [ ! -d ".venv" ]; then
  echo "=> Creating Python virtual environment..."
  python3 -m venv .venv
fi
echo "=> Installing requirements..."
./.venv/bin/pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  ./.venv/bin/pip install -r requirements.txt
else
  # Install standard stack if requirements missing
  ./.venv/bin/pip install pytest pandas rich
fi

# 4. Install Skills Cache
echo "=> Installing skills cache..."
bash scripts/install_hongstr_skills.sh --force

# 5. Environment Variables setup
ENV_FILE=".env.worker"
if [ ! -f "$ENV_FILE" ]; then
  echo "=> Generating worker environment template ($ENV_FILE)..."
  
  # Default prompting
  read -p "Worker Role [research]: " role
  role=${role:-research}
  
  read -p "Main Host (Tailscale IP/Hostname): " main_host
  read -p "Main SSH User: " ssh_user
  read -p "Main Dest Path [/Users/hong/Projects/HONGSTR/data/backtests]: " main_dest
  main_dest=${main_dest:-/Users/hong/Projects/HONGSTR/data/backtests}

  cat <<EOF > "$ENV_FILE"
# Worker specific configuration
HONGSTR_WORKER_ROLE="$role"
HONGSTR_MAIN_HOST="$main_host"
HONGSTR_MAIN_SSH_USER="$ssh_user"
HONGSTR_MAIN_DEST="$main_dest"
EOF
  echo "Saved configuration to $ENV_FILE"
else
  echo "=> $ENV_FILE already exists. Skipping prompts."
fi

echo "== Bootstrap Complete =="
echo "Next step: review $ENV_FILE and run: bash scripts/worker_pack_smoke.sh"
