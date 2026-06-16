#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 一键初始化脚本
# 用法: bash deploy/scripts/init.sh
# ============================================================
set -e

cd "$(dirname "$0")/../.."
echo "=== 种子团队任务管理系统 — 初始化 ==="

# 1. 检查 .env.prod
if [ ! -f deploy/.env.prod ]; then
    echo "[1/6] 创建 .env.prod ..."
    cp deploy/.env.prod.example deploy/.env.prod
    echo "  ⚠️  请编辑 deploy/.env.prod 修改密码和密钥！"
else
    echo "[1/6] .env.prod 已存在，跳过"
fi

# 2. 构建镜像
echo "[2/6] 构建 Docker 镜像 ..."
cd deploy && docker compose build --no-cache

# 3. 启动服务
echo "[3/6] 启动服务 ..."
docker compose up -d

# 4. 等待数据库就绪
echo "[4/6] 等待 PostgreSQL 就绪 ..."
until docker compose exec -T db pg_isready -U seedteam 2>/dev/null; do
    sleep 2
done
echo "  PostgreSQL 就绪"

# 5. 数据库迁移
echo "[5/6] 执行数据库迁移 ..."
docker compose exec -T app python manage.py migrate --noinput

# 6. 创建种子数据
echo "[6/7] 初始化种子数据 ..."
docker compose exec -T app python manage.py seed_data

# 7. 注册定时任务
echo "[7/7] 注册定时任务 ..."
docker compose exec -T app python manage.py register_scheduled_tasks

# 收集静态文件
docker compose exec -T app python manage.py collectstatic --noinput 2>/dev/null || true

echo ""
echo "=== 初始化完成 ==="
echo "  访问地址: http://localhost"
echo "  管理员账号: admin@seedteam.local"
echo "  管理员密码: seedteam2026"
echo ""
echo "  ⚠️  生产环境请立即修改密码！"
echo "  📋 启动定时任务 Worker: docker compose exec -d app python manage.py qcluster"
