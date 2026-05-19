#!/bin/bash
# Hermes Agent 监控面板 - 启动脚本

echo "=========================================="
echo "🐴 Hermes Agent 监控面板"
echo "=========================================="
echo ""

# 获取本机 IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || echo "无法获取")

echo "📍 本地访问: http://localhost:8080"
echo "📍 局域网访问: http://${LOCAL_IP}:8080"
if [ "$PUBLIC_IP" != "无法获取" ]; then
    echo "📍 公网访问: http://${PUBLIC_IP}:8080 (需要开放端口)"
fi
echo ""
echo "🔐 默认密码: xiaoma2026"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="

python3 server.py
