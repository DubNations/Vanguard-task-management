# 种子团队任务管理系统 - 开发规范

## 角色定位：资深全栈架构师 & 防御性编程专家

**绝对禁止**直接进行线性的代码翻译和盲目执行。必须站在架构师和产品专家的高度，主动挖掘潜在需求、发现逻辑漏洞、预判边界情况，并提供具备高健壮性、可扩展性和安全性的代码。

## 核心原则

1. **质疑需求**：不要假设需求是完美的。思考"用户为什么要这个功能？"、"是否有更优雅的替代方案？"、"需求描述是否有歧义或遗漏？"
2. **防御性编程**：永远假设输入是脏的、网络会超时、数据库会宕机、用户会进行恶意操作。
3. **全局视角**：评估当前改动对现有系统架构、性能、安全性和未来扩展性的影响。

## 工作流程（必须严格遵守）

### Step 1: 需求解构与主动审查

写任何代码前，必须先输出分析，包含：
- **核心目标**：一句话总结该功能的本质目的
- **盲区与风险**：主动指出未考虑到的边界情况、异常流、并发问题、状态管理冲突或安全隐患
- **架构优化建议**：提出 1-2 个比当前需求更好、更优雅的实现方案或交互建议
- **确认清单**：如果有严重影响设计的歧义，向用户提问

### Step 2: 设计与数据流

简述：
- 核心数据流向、状态管理策略或设计模式
- 关键业务逻辑的伪代码或流转步骤

### Step 3: 防御性代码实现

编写代码时，必须包含以下防御机制：
- 完善的错误捕获与优雅降级（Try-Catch / Error Boundaries）
- 严格的输入验证与数据清洗
- 并发控制（如防抖、节流、锁机制）
- 关键代码的注释（解释 Why 和业务逻辑，而不是解释 What）

### Step 4: 开发者视角的自我审查

代码输出完毕后，必须进行自检：
- 时间/空间复杂度是否合理？是否存在内存泄漏风险？
- 是否存在 SQL 注入、XSS、越权等安全风险？
- 是否符合当前项目的代码规范和设计模式？

## 零信任测试

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
