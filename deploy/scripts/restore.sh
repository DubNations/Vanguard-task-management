#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 还原脚本
# 用法: bash deploy/scripts/restore.sh [backup_file]
# ============================================================
set -e

cd "$(dirname "$0")/../.."

if [ -z "$1" ]; then
    echo "用法: bash deploy/scripts/restore.sh <备份文件路径>"
    echo ""
    echo "可用备份:"
    ls -lh backups/db/*.dump 2>/dev/null || echo "  (无备份文件)"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "=== 数据库还原 ==="
echo "备份文件: $BACKUP_FILE"
echo ""
read -p "⚠️  这将覆盖当前数据库！确认还原？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

cd deploy

# 复制备份文件到容器
CONTAINER_ID=$(docker compose ps -q db)
docker cp "$BACKUP_FILE" "$CONTAINER_ID:/tmp/restore.dump"

# 还原
echo "正在还原 ..."
docker compose exec -T db pg_restore -U seedteam -d seedteam --clean --if-exists /tmp/restore.dump

echo ""
echo "=== 还原完成 ==="
echo "正在重启应用 ..."
docker compose restart app

echo "应用已重启，请检查服务状态: docker compose ps"
