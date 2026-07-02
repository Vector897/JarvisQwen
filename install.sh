#!/usr/bin/env bash
# AAOS 一键安装（Ubuntu/Debian VM，如 Oracle Cloud Free A1）
# 用法：curl -fsSL https://raw.githubusercontent.com/Vector897/AAOS/main/install.sh | bash
set -euo pipefail

echo "==> AAOS 一键安装"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> 安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

if [ ! -d AAOS ]; then
  echo "==> 克隆仓库..."
  git clone https://github.com/Vector897/AAOS.git
fi
cd AAOS

echo "==> 构建并启动（首次约 3-5 分钟）..."
sudo docker compose up -d --build

echo ""
echo "=============================================="
echo " AAOS 已启动！"
echo "   控制台:  http://$(hostname -I | awk '{print $1}'):3000"
echo "   初始密码: 稍后查看 ./data/admin_password.txt"
echo "   （容器首次启动后生成，运行: sudo cat data/admin_password.txt）"
echo ""
echo " 下一步：浏览器打开控制台 → 登录 → 设置页粘贴 API Key → 订阅页添加研究关键词"
echo "=============================================="
