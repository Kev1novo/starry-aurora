.PHONY: dev backend frontend docker-up docker-down test lint

# 启动开发环境
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

backend:
	cd backend && uvicorn app.asgi:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose -f docker-compose.dev.yml down

docker-build:
	docker-compose -f docker-compose.prod.yml build

test:
	cd backend && pytest -v

lint:
	cd backend && black . && isort . && flake8 .
	cd frontend && npm run lint

migrate:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"