#!/usr/bin/env bash
# JarvisQwen one-click install (Ubuntu/Debian VM, e.g. Alibaba Cloud ECS)
# Usage: curl -fsSL https://raw.githubusercontent.com/Vector897/JarvisQwen/main/install.sh | bash
set -euo pipefail

echo "==> JarvisQwen installer"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

if [ ! -d JarvisQwen ]; then
  echo "==> Cloning repository..."
  git clone https://github.com/Vector897/JarvisQwen.git
fi
cd JarvisQwen

echo "==> Building and starting (first run takes 3-5 min)..."
sudo docker compose up -d --build

echo ""
echo "=============================================="
echo " JarvisQwen is up!"
echo "   Console:  http://$(hostname -I | awk '{print $1}'):3000"
echo "   Password: generated on first boot, run: sudo cat data/admin_password.txt"
echo ""
echo " Next: open the console -> log in -> paste your Qwen Cloud API key in Settings"
echo "       -> add research keywords in Subscriptions"
echo "=============================================="
