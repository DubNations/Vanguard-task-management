#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 更新脚本
# 用法: bash deploy/scripts/update.sh
# ============================================================
set -e

cd "$(dirname "$0")/../.."

echo "=== 系统更新 $(date) ==="

# 1. 备份
echo "[1/4] 备份当前数据 ..."
bash deploy/scripts/backup.sh

# 2. 拉取最新代码
echo "[2/4] 拉取最新代码 ..."
git pull origin main 2>/dev/null || echo "  (非 Git 仓库或拉取失败，跳过)"

# 3. 重建并启动
echo "[3/4] 重建镜像并重启 ..."
cd deploy
docker compose build --no-cache
docker compose up -d

# 4. 数据库迁移
echo "[4/4] 执行迁移 ..."
until docker compose exec -T db pg_isready -U seedteam 2>/dev/null; do
    sleep 2
done
docker compose exec -T app python manage.py migrate --noinput
docker compose exec -T app python manage.py collectstatic --noinput 2>/dev/null || true

cd ..
echo ""
echo "=== 更新完成 $(date) ==="
docker compose -f deploy/docker-compose.yml ps
