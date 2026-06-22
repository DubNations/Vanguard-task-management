# 种子团队任务管理系统 - 开发规范

## 核心原则：零信任测试

每次做任何功能，必须遵守：

### 1. 构造前：想清楚再动手
- 功能涉及哪些模型字段？字段流向：Parser → Executor → Model → Serializer → API → Frontend
- 每个环节的字段名是否一致？是否存在转换/映射/重命名？
- 数据在哪个环节会被丢失、覆盖、嵌套？

### 2. 构造中：每一步验证
- 改了 model → 跑 makemigrations --check
- 改了 serializer → 验证 API 返回的 JSON 结构
- 改了前端 → 跑 vue-tsc --noEmit
- 改了导入流程 → 用实际文件测试完整链路（上传 → 预览 → 确认 → 数据库）

### 3. 构造后：全链路自测
- 后端：python manage.py check + makemigrations --check
- 前端：npx vue-tsc --noEmit
- 功能：用真实数据走一遍完整流程
- 回归：确认改一个地方没有破坏另一个地方

## 已知坑点（血泪教训）

### Bug #1: 模板字段被塞进 custom_fields（2026-06-22）
- **现象**：WPS 表单导入后，任务来源/完成标准/派发人/产出全部丢失
- **原因**：`import_parser.py` 的 `_parse_form_layout()` 用 `record.pop(key)` 把字段从 record 中移除，放入 `custom_fields` dict；executor 期望字段在 record 顶层
- **修复**：parser 只把 `attachments` 放入 custom_fields，其余字段保留在 record 顶层
- **教训**：数据流经多个环节时，每个环节的输入/输出字段名必须一致。改了 parser 的输出结构，必须同步改 executor 的消费逻辑

### Bug #2: Token 刷新死循环（2026-06-22）
- **现象**：登录后页面空白，无限 401 → refresh → 401
- **原因**：axios 拦截器对所有 401 都尝试刷新 token，包括 refresh 接口本身
- **教训**：拦截器必须排除关键路径（login、refresh、logout）

### Bug #3: Loading 遮罩挡住了侧边栏（2026-06-22）
- **现象**：页面加载中时，侧边栏无法点击
- **原因**：`el-loading` 的 overlay 有 `pointer-events: auto`
- **教训**：全局 loading 样式要考虑 z-index 和事件穿透

## 字段流向速查

### WPS 表单导入
```
WPS文件 → 解析器 → record dict → executor → Task model
                                         ↓
                                    TaskParticipant
```

关键字段：
| WPS 模板 | Parser 字段 | Model 字段 | API 字段 |
|-----------|-------------|------------|----------|
| 任务名称 | title | title | title |
| 任务来源 | task_source | task_source | task_source |
| 事项内容 | content → description | description | description |
| 牵头人 | lead_name | assignee | assignee |
| 参与人 | participant_names | TaskParticipant | participants |
| 开始时间 | start_date → started_at | started_at | started_at |
| 结束时间 | end_date → deadline | deadline | deadline |
| 任务赋分 | reward_info → reward_points | reward_points | reward_points |
| 完成标准 | completion_criteria | completion_criteria | completion_criteria |
| 附件 | attachments | custom_fields.attachments | custom_fields |
| 派发人 | dispatcher_name | dispatcher_name | dispatcher_name |
| 核心输出成果 | output | output | output |

## 测试命令

```bash
# 后端检查
$env:DJANGO_ENV="local"; $env:DJANGO_SECRET_KEY="dev"; $env:JWT_SIGNING_KEY="dev"
python manage.py check
python manage.py makemigrations --check

# 前端检查
cd frontend && npx vue-tsc --noEmit

# 完整导入测试（用实际文件）
# 1. 启动后端 python manage.py runserver
# 2. 前端页面上传 .wps 文件
# 3. 检查预览数据是否包含所有字段
# 4. 确认导入后检查数据库 tasks 表的字段值
```
