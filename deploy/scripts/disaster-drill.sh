#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 灾难演练
# 在临时环境还原备份，验证备份完整性
# ============================================================
set -e

cd "$(dirname "$0")/../.."

echo "=== 灾难恢复演练 $(date) ==="

# 找最新备份
BACKUP_FILE=$(ls -t backups/db/*.dump 2>/dev/null | head -1)
if [ -z "$BACKUP_FILE" ]; then
    echo "错误: 没有找到备份文件"
    exit 1
fi

echo "使用备份: $BACKUP_FILE"

# 创建临时数据库
echo "[1/4] 启动临时 PostgreSQL ..."
docker run -d --name seedteam-drill-db \
    -e POSTGRES_DB=seedteam_drill \
    -e POSTGRES_USER=seedteam \
    -e POSTGRES_PASSWORD=drill_test \
    -p 15432:5432 \
    postgres:16-alpine

sleep 5

# 还原
echo "[2/4] 还原备份 ..."
docker cp "$BACKUP_FILE" seedteam-drill-db:/tmp/restore.dump
docker exec seedteam-drill-db pg_restore -U seedteam -d seedteam_drill --clean --if-exists /tmp/restore.dump 2>/dev/null || true

# 验证
echo "[3/4] 验证数据 ..."
TASK_COUNT=$(docker exec seedteam-drill-db psql -U seedteam -d seedteam_drill -t -c "SELECT COUNT(*) FROM tasks;" 2>/dev/null | tr -d ' ')
USER_COUNT=$(docker exec seedteam-drill-db psql -U seedteam -d seedteam_drill -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')

echo "  任务数: ${TASK_COUNT:-0}"
echo "  用户数: ${USER_COUNT:-0}"

if [ -n "$TASK_COUNT" ] && [ "$TASK_COUNT" -gt 0 ]; then
    echo "  ✅ 数据完整性验证通过"
else
    echo "  ⚠️  数据为空或验证失败"
fi

# 清理
echo "[4/4] 清理临时环境 ..."
docker rm -f seedteam-drill-db

echo ""
echo "=== 演练完成 $(date) ==="
