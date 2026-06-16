#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 备份脚本
# 用法: bash deploy/scripts/backup.sh
# ============================================================
set -e

cd "$(dirname "$0")/../.."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/app_storage" "$BACKUP_DIR/wal_archive"

echo "=== 备份开始 $(date) ==="

# 1. PostgreSQL 全量备份
echo "[1/3] 数据库备份 ..."
cd deploy
docker compose exec -T db pg_dump -U seedteam -Fc seedteam > "$BACKUP_DIR/db/seedteam_${TIMESTAMP}.dump"
echo "  数据库备份: db/seedteam_${TIMESTAMP}.dump ($(du -h "$BACKUP_DIR/db/seedteam_${TIMESTAMP}.dump" | cut -f1))"

# 2. 附件文件备份
echo "[2/3] 附件备份 ..."
if [ -d "../backend/storage" ]; then
    tar czf "$BACKUP_DIR/app_storage/storage_${TIMESTAMP}.tar.gz" -C ../backend storage/ 2>/dev/null || true
    echo "  附件备份: app_storage/storage_${TIMESTAMP}.tar.gz"
fi

# 3. 清理旧备份（保留最近30天）
echo "[3/3] 清理旧备份 ..."
find "$BACKUP_DIR/db" -name "*.dump" -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR/app_storage" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null || true

cd ..
echo ""
echo "=== 备份完成 $(date) ==="
echo "备份位置: $BACKUP_DIR"
du -sh "$BACKUP_DIR/db" "$BACKUP_DIR/app_storage" 2>/dev/null
