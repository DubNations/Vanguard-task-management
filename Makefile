.PHONY: backup restore logs update drill stats dev prod test lint

# 日常运维命令
backup:
	bash deploy/scripts/backup.sh

restore:
	bash deploy/scripts/restore.sh

logs:
	docker compose -f deploy/docker-compose.yml logs -f

update:
	bash deploy/scripts/update.sh

drill:
	bash deploy/scripts/disaster-drill.sh

stats:
	@echo "=== 系统状态 ==="
	docker compose -f deploy/docker-compose.yml ps
	@echo ""
	@echo "=== 磁盘使用 ==="
	du -sh backend/storage/ deploy/certbot/ 2>/dev/null || true

# 开发环境
dev:
	docker compose -f deploy/docker-compose.dev.yml up -d
	@echo "PostgreSQL ready on port 5432"

# 生产环境
prod:
	cd deploy && docker compose up -d

# 测试
test:
	cd backend && python manage.py test --verbosity=2

# 代码检查
lint:
	cd backend && python -m flake8 . --max-line-length=120 --exclude=migrations
	cd frontend && npm run lint
