#!/bin/bash
# 启动开发环境
set -e

echo "=== 启动基础设施 (MySQL, Redis, Qdrant, ES) ==="
docker-compose -f docker-compose.dev.yml up -d

echo "=== 等待服务就绪 ==="
sleep 5

echo "=== 初始化数据库迁移 ==="
cd backend
alembic upgrade head
cd ..

echo "=== 启动后端 ==="
cd backend && uvicorn app.asgi:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "=== 安装前端依赖 (如需) ==="
cd frontend && npm install
cd ..

echo "=== 启动前端 ==="
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== 智数归因平台 开发环境已启动 ==="
echo "后端 API: http://localhost:8000"
echo "前端页面: http://localhost:5173"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose -f docker-compose.dev.yml down" EXIT

wait