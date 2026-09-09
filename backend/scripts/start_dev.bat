@echo off
REM 启动开发环境 (Windows)

echo === 启动基础设施 (MySQL, Redis, Qdrant, ES) ===
docker-compose -f docker-compose.dev.yml up -d

echo === 等待服务就绪 ===
timeout /t 5 /nobreak

echo === 初始化数据库迁移 ===
cd backend
alembic upgrade head
cd ..

echo === 安装前端依赖 ===
cd frontend
if not exist "node_modules" npm install
cd ..

echo === 启动后端 ===
start "starry-backend" cmd /c "cd backend && uvicorn app.asgi:app --reload --host 0.0.0.0 --port 8000"

echo === 启动前端 ===
start "starry-frontend" cmd /c "cd frontend && npm run dev"

echo.
echo === 智数归因平台 开发环境已启动 ===
echo 后端 API: http://localhost:8000
echo 前端页面: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 按任意键关闭所有窗口...
pause