#!/bin/bash
# ============================================================
# 种子团队任务管理系统 — 健康检查
# 用法: bash deploy/scripts/healthcheck.sh
# ============================================================

cd "$(dirname "$0")/../.."

echo "=== 系统健康检查 $(date) ==="
echo ""

# 1. Docker 容器状态
echo "--- 容器状态 ---"
cd deploy
docker compose ps
cd ..
echo ""

# 2. API 健康
echo "--- API 健康检查 ---"
API_URL="http://localhost/api/v1/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "  API: OK (HTTP $HTTP_CODE)"
else
    echo "  API: FAILED (HTTP $HTTP_CODE)"
fi
echo ""

# 3. 数据库
echo "--- 数据库状态 ---"
cd deploy
docker compose exec -T db pg_isready -U seedteam 2>/dev/null && echo "  PostgreSQL: OK" || echo "  PostgreSQL: FAILED"
cd ..
echo ""

# 4. 磁盘空间
echo "--- 磁盘使用 ---"
df -h . 2>/dev/null | tail -1 | awk '{printf "  磁盘: %s / %s (%s used)\n", $3, $2, $5}'
echo ""

# 5. 备份状态
echo "--- 最近备份 ---"
if ls backups/db/*.dump 2>/dev/null | head -1 > /dev/null; then
    LATEST=$(ls -t backups/db/*.dump | head -1)
    echo "  最近备份: $LATEST ($(stat -c %y "$LATEST" 2>/dev/null | cut -d' ' -f1))"
else
    echo "  ⚠️  无备份文件！"
fi

echo ""
echo "=== 检查完成 ==="
