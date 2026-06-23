# 阶段 Review 基线文档

**审查时间**: 2026-06-23  
**审查范围**: 尖兵部队任务管理系统全栈代码  
**整体健康度评级**: ⚠️ **B+** (良好，有少量需要修复的问题)

---

## 🚨 阻断性问题预警

**无 P0 级阻断性问题**。以下 P1 问题需在本迭代内修复：

1. **状态转换缺少行级锁** — 并发状态变更可能导致数据不一致
2. **管理员重置密码绕过全局策略** — 安全漏洞

---

## 一、Review 概览

| 维度 | 范围 | 审查结果 |
|------|------|----------|
| D1 - 核心路径一致性 | AGENTS.md 设计哲学 vs 实际代码 | ✅ 基本遵循 |
| D2 - 字段流向零信任验证 | Parser → Executor → Model → Serializer → API → Frontend | ⚠️ 1处关键风险 |
| D3 - 功能完整性与质量 | 边界条件、并发安全、数据一致性 | ⚠️ 2处需修复 |
| D4 - 安全性审查 | 注入、越权、JWT、文件上传 | ⚠️ 2处需修复 |
| D5 - 可维护性与技术债务 | 代码重复、命名、依赖、测试覆盖 | ⚠️ 多处技术债务 |
| D6 - 业界标准对标 | Django/Vue/部署最佳实践 | ✅ 整体良好 |

---

## 二、核心路径合规清单

### 2.1 AGENTS.md 设计原则合规性

| 设计约束 | 验证结果 | 说明 |
|----------|----------|------|
| **质疑需求原则** | ✅ 通过 | 状态机设计合理，PENDING 任务大厅机制符合业务需求 |
| **防御性编程原则** | ⚠️ 偏离 | 通知发送缺少 try-except 保护（4处） |
| **全局视角原则** | ⚠️ 偏离 | 存在冗余依赖（celery），Django 版本需升级 |
| **零信任测试流程** | ✅ 通过 | 字段流向基本一致，仅 start_date 有丢失风险 |

### 2.2 字段流向合规性（WPS 表单导入）

| 环节 | 验证结果 | 说明 |
|------|----------|------|
| Parser → Executor | ⚠️ 偏离 | `start_date` 被 pop 后 executor 无法读取，导致 started_at 永远为 None |
| Executor → Model | ✅ 通过 | 字段名一致 |
| Model → Serializer | ✅ 通过 | API 返回字段与前端期望一致 |
| Serializer → Frontend | ✅ 通过 | Token 流向全链路验证通过 |

---

## 三、问题与风险台账

### 3.1 Critical Issues (MUST FIX)

#### C1. 状态转换缺少 select_for_update — 并发竞态

**位置**: [task_service.py#L168-L190](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/services/task_service.py)

**问题**: `transition_status` 方法未使用 `select_for_update()`，并发场景下可能导致：
- 两个审核人同时操作同一任务
- 后写覆盖前写，状态不可预期
- `_batch_award_on_completed` 可能被跳过（积分丢失）

**修复**:
```python
# views.py TaskTransitionView.post()
from django.db import transaction
with transaction.atomic():
    task = Task.objects.select_for_update().get(pk=pk)
    # ... 后续状态转换逻辑
```

**风险评级**: P1

---

#### C2. 管理员重置密码绕过全局策略

**位置**: [accounts/views.py#L193-L195](c:/Li8mu/Project/种子团队任务书/backend/apps/accounts/views.py)

**问题**: `UserResetPasswordView` 仅检查 `len < 6`，绕过 `AUTH_PASSWORD_VALIDATORS` 的 8 位要求和复杂度校验。

**修复**:
```python
from django.contrib.auth.password_validation import validate_password

try:
    validate_password(new_password)
except Exception as e:
    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

**风险评级**: P1

---

#### C3. 表单导入 start_date 丢失

**位置**: [import_parser.py#L572-L577](c:/Li8mu/Project/种子团队任务书/backend/apps/imports/services/import_parser.py) + [import_executor.py#L69](c:/Li8mu/Project/种子团队任务书/backend/apps/imports/services/import_executor.py)

**问题**: Parser 中 `start_date` 被 `pop` 后合并到 `deadline`，但 executor 仍尝试读取 `start_date`，导致表单导入的任务 `started_at` 永远为 None。

**修复**:
```python
# parser.py - 同时写入 started_at
start_str = record.pop('start_date', '')
if start_str:
    record['started_at'] = start_str
```

**风险评级**: P1

---

#### C4. 通知发送缺少异常保护（4处）

**位置**:
- [task_service.py#L203-L211](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/services/task_service.py)
- [views.py#L576-L589](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/views.py)
- [scheduled_tasks.py#L48-L54](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/scheduled_tasks.py)

**问题**: `Notification.objects.create` 未包裹 try-except，通知失败会导致：
- 状态已持久化但 API 返回 500
- 评论已保存但返回 500，重试会创建重复评论
- 定时任务中断，后续逾期任务不再处理

**修复**:
```python
try:
    Notification.objects.create(...)
except Exception:
    logger.warning('通知发送失败: task=%s', task.task_no, exc_info=True)
```

**风险评级**: P1

---

#### C5. PDF 导出 NameError

**位置**: [export_generator.py#L165-L168](c:/Li8mu/Project/种子团队任务书/backend/apps/exports/services/export_generator.py)

**问题**: `_export_pdf` 函数引用 `Task.Status.choices` 但未导入 `Task`，调用时必定抛出 `NameError`。

**修复**:
```python
def _export_pdf(qs, job):
    from apps.tasks.models import Task  # 添加导入
    ...
```

**风险评级**: P1

---

### 3.2 Warnings (SHOULD FIX)

#### W1. REJECTED 后未清除 completed_at

**位置**: [task_service.py#L187-L188](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/services/task_service.py)

**问题**: 任务被退回时未清除 `completed_at`，可能导致统计异常。

**修复**:
```python
if new_status == Task.Status.REJECTED:
    task.progress = max(0, task.progress - 10)
    task.completed_at = None  # 防御性清除
```

**风险评级**: P2

---

#### W2. update_task 使用 str() 比较不精确

**位置**: [task_service.py#L291](c:/Li8mu/Project/种子团队任务书/backend/apps/tasks/services/task_service.py)

**问题**: `str(old_val) == str(new_val)` 对 JSONField/datetime 可能误判。

**修复**: 对不同类型使用适当比较策略（JSONField 用 `json.dumps(sort_keys=True)`）。

**风险评级**: P2

---

#### W3. 看板视图 200 条硬截断

**位置**: [views.py#L625-L634](c:/Li8mu\Project/种子团队任务书/backend/apps/tasks/views.py)

**问题**: `[:200]` 截断后 count 基于截断数据，用户无法感知数据丢失。

**修复**: count 改用数据库查询：
```python
status_counts = dict(qs.values_list('status').annotate(c=Count('id')).values_list('status', 'c'))
```

**风险评级**: P2

---

#### W4. ZIP 炸弹防护缺失

**位置**: [import_parser.py#L220-L227](c:/Li8mu/Project/种子团队任务书/backend/apps/imports/services/import_parser.py)

**问题**: 未限制 ZIP 文件条目数量和解压后大小。

**修复**:
```python
MAX_ZIP_ENTRIES = 100
MAX_ZIP_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200MB
```

**风险评级**: P2

---

#### W5. 冗余依赖

**位置**: [requirements/base.txt](c:/Li8mu/Project/种子团队任务书/backend/requirements/base.txt)

**问题**: `celery[redis]`, `python-docx`, `olefile` 未被使用。

**修复**: 从 requirements 中移除。

**风险评级**: P3

---

#### W6. Django 版本需升级

**位置**: [requirements/base.txt](c:/Li8mu\Project/种子团队任务书/backend/requirements/base.txt)

**问题**: Django 5.0 将于 2025.12 EOL，建议升级至 5.2 LTS。

**风险评级**: P2

---

#### W7. 前端测试缺失

**位置**: `frontend/tests/`

**问题**: 测试目录为空，无单元测试和 E2E 测试。

**修复**: 安装 Vitest 并添加基础测试。

**风险评级**: P2

---

#### W8. HTTPS 未默认启用

**位置**: [deploy/nginx/conf.d/app.conf](c:/Li8mu\Project/种子团队任务书/deploy/nginx/conf.d/app.conf)

**问题**: HTTP→HTTPS 重定向被注释。

**风险评级**: P2

---

#### W9. 导入模糊匹配可能误关联

**位置**: [import_executor.py#L54-L59](c:/Li8mu\Project/种子团队任务书/backend/apps/imports/services/import_executor.py)

**问题**: `icontains` 匹配可能关联错误用户（如"张三"匹配到"张三丰"）。

**修复**: 记录模糊匹配结果供用户确认。

**风险评级**: P2

---

#### W10. 完成判定缺少并发防护

**位置**: [views.py#L431-L497](c:/Li8mu\Project/种子团队任务书/backend/apps/tasks/views.py)

**问题**: `TaskParticipantCompleteView` 未使用 `select_for_update()`，可能导致重复发放积分。

**风险评级**: P1

---

### 3.3 Suggestions (CONSIDER)

#### S1. 数据隔离逻辑重复（4处）

**位置**: views.py 多个 ViewSet 的 `get_queryset` 方法

**建议**: 提取为 mixin 或装饰器。

**风险评级**: P3

---

#### S2. get_can_claim 逻辑重复

**位置**: `TaskListSerializer` 和 `TaskDetailSerializer`

**建议**: 提取为公共函数。

**风险评级**: P3

---

#### S3. 日期解析跨年问题

**位置**: [import_executor.py#L184-L188](c:/Li8mu/Project/种子团队任务书/backend/apps/imports/services/import_executor.py)

**问题**: "6月22日" 使用当前年份，12月导入次年1月日期会错误。

**风险评级**: P3

---

#### S4. TypeScript 类型定义分散

**位置**: `frontend/src/`

**建议**: 将类型统一移至 `types/` 目录。

**风险评级**: P3

---

#### S5. CI 缺少前端测试和安全扫描

**位置**: `.github/workflows/ci.yml`

**建议**: 添加 `npm run lint` 和 `npm test` 步骤。

**风险评级**: P3

---

## 四、最优解对标分析

### 4.1 Django/DRF 最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **API 版本化** | `/api/v1/` | 推荐方案 | ✅ 已遵循 |
| **序列化器** | Serializer + ModelSerializer 混合 | 视复杂度而定 | ✅ 合理 |
| **权限控制** | 自定义 Permission 类 | 推荐方案 | ✅ 设计合理 |
| **数据库索引** | 5 个复合索引 | 覆盖主要查询 | ✅ 合理 |
| **统一错误响应** | custom_exception_handler | 推荐方案 | ✅ 已实现 |

### 4.2 Vue 3 最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **状态管理** | Pinia | 推荐方案 | ✅ 已使用 |
| **TypeScript** | 部分类型定义 | 强类型全覆盖 | ⚠️ 需完善 |
| **自动导入** | unplugin-auto-import | 推荐方案 | ✅ 已配置 |
| **代码分割** | manualChunks | 推荐方案 | ✅ 已实现 |
| **路由守卫** | beforeEach | 推荐方案 | ✅ 已实现 |
| **前端测试** | 无 | Vitest + E2E | ❌ 缺失 |

### 4.3 部署最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **容器化** | Docker Compose | 推荐方案 | ✅ 已实现 |
| **健康检查** | App + Nginx + PostgreSQL | 推荐方案 | ✅ 已实现 |
| **备份策略** | 3-2-1 策略脚本 | 推荐方案 | ✅ 已实现 |
| **HTTPS** | Certbot 配置就绪 | 生产必须启用 | ⚠️ 需启用 |
| **CI/CD** | GitHub Actions | 推荐方案 | ⚠️ 缺少前端测试 |

---

## 五、已验证基线清单

以下功能点已通过审查，下阶段可直接跳过：

### 5.1 后端核心功能

| 功能 | 验证状态 | 说明 |
|------|----------|------|
| 任务状态机 | ✅ | 状态转换逻辑正确，REJECTED→IN_PROGRESS 回退 10% 合理 |
| 任务编号生成 | ✅ | `select_for_update()` + 重试机制，并发安全 |
| 揭榜领取 | ✅ | `select_for_update()` + 事务保护，并发安全 |
| 积分余额更新 | ✅ | `select_for_update()` + `@transaction.atomic` |
| JWT 认证 | ✅ | 密钥强制检查，Token 刷新死循环已修复 |
| 数据隔离 | ✅ | MEMBER 只能看自己的任务 + PENDING 任务大厅 |
| 评论内部标记 | ✅ | `is_internal` 过滤逻辑正确 |
| 文件上传安全 | ✅ | Django/Nginx 限制一致（50MB），subprocess 无命令注入 |
| 临时文件清理 | ✅ | finally 块中 `shutil.rmtree` 清理 |
| 统一错误响应 | ✅ | `custom_exception_handler` 实现完善 |

### 5.2 前端核心功能

| 功能 | 验证状态 | 说明 |
|------|----------|------|
| Token 流向 | ✅ | Login→Store→Interceptor→Refresh→Logout 全链路正确 |
| 路由守卫 | ✅ | `meetsRole` 函数正确处理角色层级 |
| 代码分割 | ✅ | Vite manualChunks 分离 vendor 和 element-plus |
| 自动导入 | ✅ | unplugin-auto-import + unplugin-vue-components |

### 5.3 部署配置

| 功能 | 验证状态 | 说明 |
|------|----------|------|
| Docker Compose | ✅ | 配置完整，健康检查就绪 |
| 备份脚本 | ✅ | `backup.sh` 支持数据库 + 附件备份 |
| 日志轮转 | ✅ | RotatingFileHandler 10MB/5 份 |
| Session Cookie | ✅ | `SESSION_COOKIE_SECURE = True` |

### 5.4 测试验证

| 检查项 | 结果 |
|--------|------|
| Django check | ✅ 通过 (0 issues) |
| makemigrations --check | ✅ 通过 (No changes detected) |

---

## 六、下阶段 Review 指引

### 6.1 必须重点关注的审查点

| 优先级 | 审查点 | 预期成果物 | 验收标准 |
|--------|--------|------------|----------|
| **P0** | 并发状态转换修复 | `select_for_update()` 实现 | 并发测试通过 |
| **P0** | 密码策略统一 | `validate_password()` 调用 | 6位密码被拒绝 |
| **P1** | 通知异常保护 | try-except 包裹 | 通知失败不影响主流程 |
| **P1** | PDF 导出修复 | Task 导入添加 | PDF 导出功能正常 |
| **P1** | start_date 字段保留 | parser/executor 修改 | 表单导入 started_at 有值 |
| **P2** | 冗余依赖清理 | requirements 更新 | celery/python-docx 移除 |
| **P2** | Django 升级 | 5.2 LTS | 所有测试通过 |
| **P2** | 前端测试框架 | Vitest 配置 | 基础测试用例通过 |

### 6.2 预期成果物

1. **修复后的代码** — 所有 P1 问题已修复
2. **测试用例** — 并发状态转换、密码策略的测试覆盖
3. **依赖更新** — requirements.txt 清理冗余依赖
4. **前端测试** — Vitest 配置和基础测试用例

### 6.3 验收标准

- [ ] 所有 P1 问题已修复并通过测试
- [ ] Django check 通过
- [ ] makemigrations --check 通过
- [ ] vue-tsc --noEmit 通过
- [ ] 并发场景测试通过（模拟双人同时操作）
- [ ] 密码策略测试通过（6位密码被拒绝）

---

## 七、变更总结

### 本阶段已验证的核心变更

1. **Bug #1 修复确认** — 模板字段不再被塞进 custom_fields，仅 attachments 放入
2. **Bug #2 修复确认** — Token 刷新使用独立 axios 实例，避免死循环
3. **Bug #3 修复确认** — Loading 遮罩 z-index 问题已处理
4. **状态机设计** — 6 种状态 + 合法转换路径，设计合理
5. **积分系统** — 三种模式（FIXED/PRIORITY_BASED/CUSTOM）支持完整
6. **导入导出** — WPS 四层解析策略，覆盖 2003-2024 全版本

### 技术债务清单

| 类型 | 数量 | 优先级 |
|------|------|--------|
| 代码重复 | 3处 | P3 |
| 冗余依赖 | 3个 | P3 |
| 缺失测试 | 前端 | P2 |
| 版本升级 | Django | P2 |

---

**文档生成时间**: 2026-06-23  
**审查人**: AI Agent  
**下次 Review 建议时间**: 下个迭代结束时
