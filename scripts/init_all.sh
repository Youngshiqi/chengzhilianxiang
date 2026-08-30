#!/bin/bash
# ============================================================
# 城市公共设施智能报修与派单系统 - 一键初始化脚本
# 作用：按顺序执行：基础设施启动 → 数据库初始化 → 模拟数据填充 → ES索引同步
# 运行：bash scripts/init_all.sh
# ============================================================

set -e

echo "========================================="
echo "城市公共设施智能报修与派单系统 - 初始化"
echo "========================================="

echo ""
echo "[Step 1/4] 启动基础设施（Docker Compose）..."
docker-compose up -d
echo "等待服务就绪..."
sleep 15

echo ""
echo "[Step 2/4] 初始化MySQL/MongoDB/ES..."
cd backend && python scripts/init_db.py

echo ""
echo "[Step 3/4] 填充模拟数据..."
python seed_data.py

echo ""
echo "[Step 4/4] 同步数据至ES..."
python scripts/sync_es.py

echo ""
echo "========================================="
echo "初始化全部完成！"
echo "后端API: http://localhost:8000/docs"
echo "RabbitMQ管理: http://localhost:15672"
echo "MinIO控制台: http://localhost:9001"
echo "========================================="
