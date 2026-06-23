# 尖兵部队任务管理系统 -- 全量阶段 Review 执行计划

## 一、审查概览

本计划覆盖后端 Django + DRF、前端 Vue 3 + TypeScript、部署 Docker + Nginx 全栈，按以下六个维度组织：

| 维度 | 范围 |
|------|------|
| D1 - 核心路径一致性 | AGENTS.md 设计哲学 vs 实际代码 |
| D2 - 字段流向零信任验证 | Parser -> Executor -> Model -> Serializer -> API -> Frontend |
| D3 - 功能完整性与质量 | 边界条件、并发安全、数据一致性 |
| D4 - 安全性审查 | 注入、越权、JWT、文件上传 |
| D5 - 可维护性与技术债务 | 代码重复、命名、依赖、测试覆盖 |
| D6 - 业界标准对标 | Django/Vue 最佳实践对比 |

---

## 二、D1 -- 核心路径一致性验证

**目标**: 对照 AGENTS.md 中三大原则和零信任测试流程，逐项核查代码实现。

### D1.1 质疑需求原则

| # | 检查项 | 需查看的文件 | 验证方法 | 预期产出 |
|---|--------|------------|----------|----------|
| D1.1.1 | 状态机 REJECTED 是否真正允许回退到 IN_PROGRESS | `backend/apps/tasks/models.py` 第31-38行 `STATUS_TRANSITIONS` | 代码审查: 确认 REJECTED -> IN_PROGRESS 转换路径是否有进度回退逻辑 | 确认 `task_service.py` 第188行 `progress = max(0, task.progress - 10)` 是否合理（被退回后进度只减10%是否足够） |
| D1.1.2 | 揭榜模式下 PENDING 任务对所有 MEMBER 可见是否造成信息泄露 | `backend/apps/tasks/views.py` 第43-57行, `backend/common/permissions.py` 第31-36行 | 代码审查: 检查 PENDING 任务是否包含敏感字段（custom_fields、内部描述）在列表接口中暴露 | 评估列表接口 TaskListSerializer 是否包含不应对 MEMBER 暴露的字段 |
| D1.1.3 | 导入时同名用户的模糊匹配是否会导致误匹配 | `backend/apps/imports/services/import_executor.py` 第54-59行 | 代码审查: `icontains` 匹配 "张" 会匹配所有包含 "张" 的用户 | 建议改为精确匹配优先，模糊匹配需二次确认 |

### D1.2 防御性编程原则

| # | 检查项 | 需查看的文件 | 验证方法 | 预期产出 |
|---|--------|------------|----------|----------|
| D1.2.1 | XSS 防御是否覆盖所有用户输入路径 | `backend/apps/tasks/serializers.py` 第173-182行, `backend/common/utils.py` | 代码审查: 对比所有用户可写字段列表 vs strip_html_tags 调用点 | 检查 `TaskCommentCreateSerializer.validate_content` 第264行是否覆盖评论内容 |
| D1.2.2 | 通知发送失败是否影响主流程 | `backend/apps/tasks/services/task_service.py` 第116-117行, 第248-249行 | 代码审查: 确认所有 Notification.objects.create 调用都有 try-except 包裹 | 产出: 通知发送失败但主流程继续的场景清单 |
| D1.2.3 | 积分发放失败是否导致事务回滚 | `backend/apps/tasks/services/task_service.py` 第237-249行, `backend/apps/points/services/point_service.py` 第62-84行 | 代码审查: `PointService.award` 用了 `@transaction.atomic`，但 `_batch_award_on_completed` 中每个参与者的发放单独 try-except | 识别: 单个积分发放失败不会回滚其他人的积分，但也不会回滚任务状态变更 -- 这是否符合预期 |

### D1.3 全局视角原则

| # | 检查项 | 需查看的文件 | 验证方法 | 预期产出 |
|---|--------|------------|----------|----------|
| D1.3.1 | `celery` 在 requirements 中声明但项目使用 `django-q2` 作为任务队列 | `backend/requirements/base.txt` 第10行 vs `backend/seedteam/settings/base.py` 第190-200行 | 代码审查: 确认 celery 是否被实际使用 | 技术债务: 冗余依赖应移除 |
| D1.3.2 | `python-docx`, `olefile`, `weasyprint` 等依赖在代码中的实际使用情况 | 全局代码搜索 `import docx`, `import olefile`, `import weasyprint` | 搜索代码库 | 识别未使用或低效使用的依赖 |

---

## 三、D2 -- 字段流向零信任验证（核心路径）

**目标**: 验证 AGENTS.md 中定义的字段流向速查表，确保每个环节字段名一致。

### D2.1 WPS 表单导入全链路

| 环节 | 需查看的文件 | 具体检查 |
|------|------------|----------|
| **Parser 输出** | `backend/apps/imports/services/import_parser.py` 第536-611行 `_parse_form_layout()` | 检查字段名: `title`, `task_source`, `lead_name`, `participant_names_text`, `start_date`/`end_date`->`deadline`, `reward_info`->`reward_points`, `completion_criteria`, `output`, `dispatcher_name`, `attachments`->`custom_fields.attachments` |
| **Executor 消费** | `backend/apps/imports/services/import_executor.py` 第26-152行 | 检查: executor 是否正确读取 parser 输出的所有字段名 |
| **Model 存储** | `backend/apps/tasks/models.py` 第42-93行 | 检查: model 字段名是否与 executor 写入的字段名一致 |
| **Serializer 输出** | `backend/apps/tasks/serializers.py` 第79-131行 `TaskDetailSerializer` | 检查: API 返回的 JSON key 是否与前端期望一致 |
| **前端消费** | 搜索前端代码中对接口返回数据的字段引用 | 检查: 前端 TypeScript 类型定义与 API 返回是否匹配 |

**已知问题复核** (Bug #1):
- 验证修复: `_parse_form_layout()` 第587-592行现在只把 `attachments` 放入 `custom_fields`
- 验证 executor 第40-44行展开嵌套 custom_fields 的逻辑是否正确处理附件路径

**关键风险点**:
1. `_parse_form_layout` 第572-577行: `start_date` 和 `end_date` 被 `pop` 后合并为 `deadline`，但 executor 第69行仍尝试读取 `start_date` -- 需验证此路径是否会导致 `started_at` 永远为空
2. `participant_names` 在 parser 第595-596行被重命名为 `participant_names_text`，executor 第134行是否正确处理两种名称

### D2.2 标准表格导入全链路

| 环节 | 检查项 |
|------|--------|
| Parser `_build_mapping()` | 验证 `DEFAULT_COLUMN_MAPPING` 中所有中文列名的英文字段名是否与 Model 字段一一对应 |
| Executor | 验证: `assignee_name`/`lead_name` 两种名称都正确处理; `status` 中文到英文映射完整 |
| 前端上传 | 验证: upload 组件发送的 FormData 格式是否被后端正确解析 |

### D2.3 认证 Token 流向

| 环节 | 需查看的文件 | 检查项 |
|------|------------|--------|
| Login | `backend/apps/accounts/views.py` 第18-50行 | 返回字段: `access`, `refresh`, `user` |
| Frontend Store | `frontend/src/stores/auth.ts` 第37-47行 | 解析: `data.access`, `data.refresh`, `data.user` |
| Interceptor | `frontend/src/api/index.ts` 第15-30行 | 请求头: `Authorization: Bearer ${accessToken}` |
| Refresh | `frontend/src/stores/auth.ts` 第49-58行 | Bug #2 复核: 确认 `doRefreshToken` 使用独立 axios 实例 |
| Logout | `frontend/src/stores/auth.ts` 第61-78行 | 验证: `resetRefreshLock` 在 logout 后正确调用 |

---

## 四、D3 -- 功能完整性与质量审查

### D3.1 并发安全

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D3.1.1 | 任务编号生成的并发安全 | `backend/apps/tasks/services/task_service.py` 第24-38行 | 代码审查: `select_for_update()` + 重试机制是否覆盖所有竞争条件 |
| D3.1.2 | 揭榜领取的并发控制 | `backend/apps/tasks/views.py` 第202-204行 | 代码审查: `select_for_update()` 在事务内，`current_claimers` 原子递增 |
| D3.1.3 | 积分余额更新的并发安全 | `backend/apps/points/services/point_service.py` 第28-30行, 第62-84行 | 代码审查: `select_for_update()` + `@transaction.atomic` 保证余额一致性 |
| D3.1.4 | 状态机转换无锁保护 | `backend/apps/tasks/services/task_service.py` 第168-226行 | **风险**: `transition_status` 没有使用 `select_for_update()`，并发状态转换可能导致竞态条件 |

### D3.2 数据一致性

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D3.2.1 | Task.completed_at 在 REJECTED 后是否被清除 | `task_service.py` 第184-185行 | 代码审查: COMPLETED 设 completed_at，但 REJECTED 不清除 |
| D3.2.2 | TaskParticipant.points 默认值为 0 是否合理 | `backend/apps/imports/services/import_executor.py` 第221行 | 代码审查: 导入时参与人积分默认 0，但 task.reward_points 可能非 0 |
| D3.2.3 | `update_task` 中 diff 计算使用 `str()` 比较 | `task_service.py` 第291行 | 代码审查: `str(old_val) == str(new_val)` 对 JSONField 和 datetime 可能产生误判 |
| D3.2.4 | 任务创建后直接设置 `started_at` 但 `source` 未同步设置 | `task_service.py` 第66-71行 vs 第84行 | 代码审查: ASSIGNED 模式直接设 started_at，但 `source` 默认为 'MANUAL' |

### D3.3 边界条件

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D3.3.1 | 进度回退逻辑 `max(0, progress - 10)` 是否过于简单 | `task_service.py` 第188行 | 评估: 被退回后只减 10% 是否符合业务预期 |
| D3.3.2 | 看板视图限制 200 条 + 每列 20 条 | `backend/apps/tasks/views.py` 第625, 631行 | 评估: 大量任务时是否丢失数据，是否需要分页 |
| D3.3.3 | 日期解析 "6月22日" 自动填充当年 | `import_executor.py` 第187-188行 | 评估: 跨年时（如12月导入1月的日期）是否合理 |
| D3.3.4 | `strip_html_tags` 使用正则可能不完全安全 | `backend/common/utils.py` 第12行 | 评估: `re.sub(r'<[^>]+>', '', value)` 对 `<img onerror=...>` 等变体是否有效 |

### D3.4 测试覆盖度

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D3.4.1 | 运行完整测试套件 | `backend/tests/` | `cd backend; DJANGO_ENV=local pytest tests/ -v --tb=short` |
| D3.4.2 | 检查测试是否覆盖所有 API 端点 | 对比 `urls.py` 定义的端点 vs `tests/test_api/` 中的测试文件 | 交叉比对 |
| D3.4.3 | 前端类型检查 | `frontend/` | `cd frontend; npx vue-tsc --noEmit` |
| D3.4.4 | Django 系统检查 | `backend/` | `cd backend; DJANGO_ENV=local python manage.py check` |
| D3.4.5 | Migration 一致性检查 | `backend/` | `cd backend; DJANGO_ENV=local python manage.py makemigrations --check` |

---

## 五、D4 -- 安全性审查

### D4.1 认证与授权

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D4.1.1 | JWT 密钥强制从环境变量读取 | `backend/seedteam/settings/base.py` 第158-164行 | 代码审查: 确认运行时若无密钥则抛 RuntimeError |
| D4.1.2 | `LoginView` 不检查 `throttle_classes` | `backend/apps/accounts/views.py` 第18-19行 | **风险**: DRF 全局配置了 `LoginRateThrottle`，但需确认 `LoginView` 继承的 `APIView` 是否应用全局节流 |
| D4.1.3 | 前端路由权限控制 (minRole) | `frontend/src/router/index.ts` 第120-133行 | 代码审查: `meetsRole` 函数是否正确处理 `is_superuser` 和角色层级 |
| D4.1.4 | `UserResetPasswordView` 密码最小长度 6 位 vs 全局策略 8 位 | `backend/apps/accounts/views.py` 第194行 vs `base.py` 第101行 | **不一致**: 管理员重置密码允许6位，但全局策略要求8位 |
| D4.1.5 | CORS 配置 | `backend/seedteam/settings/base.py` 第178-181行 | 代码审查: `CORS_ALLOW_CREDENTIALS = True` 配合白名单 origins 是否安全 |

### D4.2 数据隔离

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D4.2.1 | MEMBER 只能看自己的任务 + PENDING 任务 | `backend/apps/tasks/views.py` 第43-57行 | 代码审查: 验证 Q 表达式是否正确排除非关联的 IN_PROGRESS/IN_REVIEW/COMPLETED 任务 |
| D4.2.2 | PENDING 任务对 MEMBER 完全可读 | 多个 views 的数据隔离逻辑 | **设计决策**: PENDING 任务是"任务大厅"，对所有人可见 -- 但这是否意味着 PENDING 任务的 description、custom_fields 等敏感信息也被暴露？ |
| D4.2.3 | 评论的 `is_internal` 过滤 | `backend/apps/tasks/views.py` 第556行 | 代码审查: `qs = qs.filter(is_internal=False)` 仅对非组长过滤，确认逻辑正确 |

### D4.3 文件安全

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D4.3.1 | 文件上传大小限制 | `base.py` 第186-187行, Nginx `client_max_body_size 50M` | 代码审查: Django 和 Nginx 限制是否一致 |
| D4.3.2 | WPS 解析中的 `subprocess.run` 命令注入风险 | `import_parser.py` 第277-288行 | 代码审查: `wpscli` 路径通过 `_find_wpscli()` 获取，用户文件路径通过 `file_path` 传入，是否有注入风险 |
| D4.3.3 | 临时文件清理 | `import_parser.py` 第269行 `tempfile.mkdtemp()` + 第299行 `shutil.rmtree` | 代码审查: 确认所有临时目录在 finally 中清理 |
| D4.3.4 | ZIP 炸弹防护 | `import_parser.py` 第220-228行 `_is_zip_file()` | **风险**: 没有检查 ZIP 内的文件数量和总大小 |

### D4.4 生产安全配置

| # | 检查项 | 文件位置 | 验证方法 |
|---|--------|----------|----------|
| D4.4.1 | HTTPS 未默认启用 | `deploy/nginx/conf.d/app.conf` 第9-10行 | 代码审查: HTTP -> HTTPS 重定向被注释 |
| D4.4.2 | Session Cookie 安全 | `backend/seedteam/settings/prod.py` 第17-19行 | 代码审查: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True` |
| D4.4.3 | Nginx 限流配置 | `deploy/nginx/conf.d/app.conf` 第40行, 第53行 | 代码审查: API burst=20, Login burst=3 |

---

## 六、D5 -- 可维护性与技术债务

### D5.1 代码质量

| # | 检查项 | 文件位置 | 问题描述 |
|---|--------|----------|----------|
| D5.1.1 | 重复 import | `backend/apps/imports/services/import_executor.py` 第6-9行 | `TaskService` 和 `User` 各被 import 两次 |
| D5.1.2 | `get_can_claim` 逻辑重复 | `serializers.py` TaskListSerializer 第54-76行 vs TaskDetailSerializer 第114-131行 | 完全相同的逻辑重复了两遍，应提取为共用方法 |
| D5.1.3 | 数据隔离逻辑重复 | `views.py` 多个 ViewSet 的 `get_queryset` 方法 | MEMBER 的数据隔离 Q 表达式在 TaskListView、TaskHistoryListView、TaskCommentListView、KanbanView 中重复出现 |
| D5.1.4 | 冗余依赖 | `requirements/base.txt` 第10行 `celery[redis]` | 项目实际使用 django-q2，celery 未被引用 |

### D5.2 依赖版本

| 依赖 | 当前版本 | 最新稳定版 | 风险评估 |
|------|---------|-----------|---------|
| Django | 5.0.* | 5.0 LTS | 合理，5.0 LTS 受支持至 2027 |
| djangorestframework | 3.15.* | 3.15.x | 合理 |
| openpyxl | 3.1.* | 3.1.x | 合理 |
| Vue | ^3.4 | 3.5+ | 可考虑升级 |
| Element Plus | ^2.7 | 2.8+ | 可考虑升级 |

### D5.3 项目结构

| # | 检查项 | 验证方法 |
|---|--------|----------|
| D5.3.1 | 散落的 PowerShell 脚本文件 | 根目录有 `_b1.ps1`, `_t1.ps1` 等临时脚本，应清理或移入 `scripts/` 目录 |
| D5.3.2 | `.gitignore` 是否覆盖所有临时文件 | 检查 `db.sqlite3`, `.venv`, `node_modules`, `dist`, `logs/` 等 |

---

## 七、D6 -- 业界标准对标

### 7.1 Django/DRF 最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **API 版本化** | URL 路径 `/api/v1/` | 推荐方案 | 已遵循 |
| **序列化器** | 使用 `Serializer` + `ModelSerializer` 混合 | 推荐一致使用 | TaskCreateSerializer 用 Serializer 而非 ModelSerializer，增加了维护成本 |
| **View 层** | 使用 `generics.*` + `APIView` 混合 | 视复杂度而定 | 合理 |
| **权限控制** | 自定义 Permission 类 | 推荐方案 | 设计合理，`IsOwnerOrLeader` 覆盖了大部分场景 |
| **数据库索引** | Model 中定义了复合索引 | 推荐方案 | `tasks` 表有 5 个索引，覆盖主要查询路径 |
| **序列化器 N+1 问题** | `select_related` 在 View 层 | 推荐在 ViewSet.get_queryset 中统一 | 已在 View 层使用 |
| **统一错误响应** | `custom_exception_handler` | 推荐方案 | 已实现，格式统一 |

### 7.2 Vue 3 最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **状态管理** | Pinia | 推荐方案 | 已使用 |
| **TypeScript** | 有 tsconfig，部分类型定义 | 强类型全覆盖 | `types/` 目录存在，需检查覆盖度 |
| **自动导入** | `unplugin-auto-import` + `unplugin-vue-components` | 推荐方案 | 已配置 |
| **代码分割** | Vite `manualChunks` 分离 vendor 和 element-plus | 推荐方案 | 已实现 |
| **路由守卫** | `beforeEach` 中检查 auth + role | 推荐方案 | 已实现 |
| **前端测试** | `tests/unit/`, `tests/e2e/` 目录存在但文件未知 | 至少单元测试 | 需检查实际测试文件内容 |

### 7.3 部署最佳实践

| 维度 | 当前实现 | 业界推荐 | 差距评估 |
|------|---------|---------|---------|
| **容器化** | Docker Compose | 推荐方案 | 已实现 |
| **健康检查** | App + Nginx + PostgreSQL 均有 | 推荐方案 | 已实现 |
| **备份策略** | 3-2-1 策略脚本 (`backup.sh`, `restore.sh`) | 推荐方案 | 已实现 |
| **日志轮转** | Django RotatingFileHandler (10MB, 5份) | 推荐方案 | 合理 |
| **HTTPS** | Certbot 配置就绪但默认注释 | 生产必须启用 | 需确保部署时取消注释 |
| **Secrets 管理** | 环境变量 + `.env` 文件 | 推荐方案 | 已实现，JWT_SIGNING_KEY 有强制检查 |
| **CI/CD** | GitHub Actions (pytest + flake8 + vue-tsc + vite build) | 推荐方案 | 已实现，但缺少前端 lint 步骤 |

---

## 八、执行步骤与时间估算

### Phase 1: 静态代码审查 (2-3 小时)

1. **D2.1 字段流向验证** -- 用实际 WPS 文件走一遍导入链路，对照字段表逐项核实
2. **D4.1 认证安全** -- 重点检查 JWT 配置、Token 刷新死循环修复、权限类实现
3. **D3.1 并发安全** -- 检查 `select_for_update` 使用位置和遗漏

### Phase 2: 动态验证 (1-2 小时)

4. **D3.4 测试执行** -- 运行后端测试套件、前端类型检查、Django 系统检查
5. **D2.3 认证 Token 流向** -- 手动走一遍登录 -> 刷新 -> 登出流程

### Phase 3: 综合评估 (1 小时)

6. **D5 技术债务清单** -- 汇总代码重复、冗余依赖、临时文件
7. **D6 业界对标报告** -- 输出差距分析和改进建议
8. **风险评级** -- 按严重程度对所有发现分级

---

## 九、风险评级标准

| 级别 | 含义 | 处理要求 |
|------|------|---------|
| **P0 - 阻塞** | 安全漏洞、数据丢失风险 | 立即修复 |
| **P1 - 严重** | 功能缺陷、并发问题 | 本迭代内修复 |
| **P2 - 一般** | 代码质量、技术债务 | 下个迭代排期 |
| **P3 - 建议** | 优化建议、最佳实践偏差 | 记录待评估 |

---

## 十、初步发现摘要（基于已读代码的即时判断）

以下是我在阅读代码过程中已经识别出的潜在问题，详细验证需要在执行阶段完成：

1. **[P1] 状态转换无行级锁**: `task_service.py` 的 `transition_status` 没有使用 `select_for_update()`，而 `TaskClaimView` 使用了 -- 存在不一致性，可能导致并发状态转换竞态。

2. **[P1] 管理员重置密码最小长度与全局策略不一致**: `views.py` 第194行允许6位，但 `AUTH_PASSWORD_VALIDATORS` 要求8位。

3. **[P2] executor 重复 import**: `import_executor.py` 第6-9行 `TaskService` 和 `User` 各被导入两次。

4. **[P2] get_can_claim 逻辑完全重复**: `TaskListSerializer` 和 `TaskDetailSerializer` 中的 `get_can_claim` 方法实现完全相同。

5. **[P2] 冗余依赖 celery**: `requirements/base.txt` 声明了 `celery[redis]` 但项目使用 `django-q2`。

6. **[P2] HTTPS 未默认启用**: Nginx 配置中 HTTP->HTTPS 重定向被注释。

7. **[P3] 数据隔离逻辑在多个 View 中重复**: MEMBER 的 Q 过滤逻辑在至少4个 View 中重复。

8. **[P3] 散落的临时脚本**: 根目录有 `_b1.ps1`, `_t1.ps1` 等临时文件。

---

## 十一、验证命令清单

```powershell
# 后端系统检查
$env:DJANGO_ENV="local"; $env:DJANGO_SECRET_KEY="dev"; $env:JWT_SIGNING_KEY="dev"
cd c:\Li8mu\Project\种子团队任务书\backend
python manage.py check
python manage.py makemigrations --check

# 后端测试
pytest tests/ -v --tb=short

# 前端类型检查
cd c:\Li8mu\Project\种子团队任务书\frontend
npx vue-tsc --noEmit

# 依赖检查
pip list --format=columns
npm list --depth=0
```
