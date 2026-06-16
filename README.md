# 尖兵部队 — 任务管理系统

面向 20-100 人小团队的任务工作单 Web 化管理系统。支持任务全生命周期管理、积分激励、数据看板和多格式导入导出。

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | Django 5.0 LTS + Django REST Framework 3.15 |
| 数据库 | PostgreSQL 16（生产）/ SQLite（本地开发） |
| 前端 | Vue 3.4 + Vite 5 + TypeScript + Element Plus |
| 状态管理 | Pinia |
| 认证 | JWT（Simple JWT） |
| 部署 | Docker Compose + Nginx |

## 核心功能

- **任务管理** — CRUD + 状态机（待领取 → 进行中 → 待审核 → 已完成）
- **揭榜挂帅** — 无主任务可由成员主动领取
- **看板视图** — 按状态分列展示，支持拖拽
- **三级权限** — 超级管理员 / 组长(含ADMIN) / 成员，数据按角色隔离
- **积分系统** — 规则配置、积分发放/扣除、周/月/总排行榜
- **导入导出** — 支持 xlsx / csv / wps 导入，Excel / CSV 导出
- **仪表盘** — 多维度统计看板，待办事项、趋势图表
- **审计日志** — 全操作记录，筛选追溯
- **通知系统** — 站内通知 + 邮件告警（任务分配、状态变更、逾期提醒）
- **备份恢复** — 3-2-1 策略 + 一键还原

## 快速启动

### 方式一：Windows 本地开发（推荐）

**前置条件：** Python 3.11+、Node.js 18+

```powershell
# 克隆项目
git clone https://github.com/DubNations/Vanguard-task-management.git
cd Vanguard-task-management

# 一键启动（自动创建虚拟环境、安装依赖、初始化数据库）
.\start.ps1

# 前端（另开终端）
.\start-fe.ps1
```

启动后访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- 默认管理员：`admin@seedteam.local` / `seedteam2026`

### 方式二：Docker 部署

```bash
git clone https://github.com/DubNations/Vanguard-task-management.git
cd Vanguard-task-management

# 配置环境变量
cp deploy/.env.prod.example deploy/.env.prod
# 编辑 deploy/.env.prod，修改密码、域名等

# 启动
cd deploy && docker compose up -d

# 首次初始化
bash scripts/init.sh
```

### 方式三：手动开发环境

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate  # Windows

pip install -r requirements/local.txt
python manage.py migrate
python manage.py seed_data    # 加载演示数据
python manage.py runserver

# 前端
cd frontend
npm install
npm run dev
```

## 项目结构

```
├── backend/                    # Django 后端
│   ├── apps/
│   │   ├── accounts/           # 用户 & 团队管理
│   │   ├── admin_api/          # 管理员接口（审计日志、系统状态）
│   │   ├── audit/              # 审计日志模型
│   │   ├── dashboard/          # 仪表盘数据服务
│   │   ├── exports/            # 导出任务（Excel/CSV/PDF）
│   │   ├── files/              # 文件上传/下载/删除
│   │   ├── imports/            # 文件导入（xlsx/csv/wps）
│   │   ├── notifications/      # 通知（站内 + 邮件）
│   │   ├── points/             # 积分系统（规则/流水/余额）
│   │   └── tasks/              # 任务核心（CRUD/状态机/看板/评论）
│   ├── common/                 # 通用模块（权限/分页/异常/中间件）
│   ├── seedteam/               # Django 配置（settings/urls）
│   ├── tests/                  # 测试套件（334 个测试）
│   └── manage.py
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # Axios 实例 & API 模块
│   │   ├── components/         # 通用组件（StatusTag/PriorityTag）
│   │   ├── composables/        # 组合式函数
│   │   ├── layouts/            # 布局（MainLayout）
│   │   ├── router/             # Vue Router
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── styles/             # 全局样式
│   │   └── views/              # 页面视图
│   └── vite.config.ts
├── deploy/                     # 部署配置
│   ├── nginx/                  # Nginx 反向代理
│   ├── scripts/                # 运维脚本
│   ├── docker-compose.yml      # 生产环境
│   └── docker-compose.dev.yml  # 开发环境
├── start.ps1                   # Windows 一键启动
└── start-fe.ps1                # 前端独立启动
```

## API 概览

所有接口前缀 `/api/v1/`，JWT Bearer 认证。

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /auth/login/` | 登录获取 JWT |
| 任务 | `GET/POST /tasks/` | 任务列表（筛选/搜索/排序/分页） |
| | `GET/PUT /tasks/{id}/` | 任务详情 |
| | `POST /tasks/{id}/transition/` | 状态转换 |
| | `POST /tasks/{id}/claim/` | 揭榜挂帅 |
| | `GET/POST /tasks/{id}/comments/` | 评论 |
| 看板 | `GET /tasks/kanban/` | 看板数据 |
| 积分 | `GET /points/balance/` | 积分余额 |
| | `GET /points/leaderboard/` | 排行榜 |
| | `GET/POST /points/rules/` | 积分规则配置 |
| 导入 | `POST /imports/upload/` | 上传解析预览 |
| | `POST /imports/{id}/confirm/` | 确认导入 |
| 导出 | `POST /exports/create/` | 创建导出任务 |
| | `GET /exports/{id}/download/` | 下载导出文件 |
| 文件 | `POST /files/upload/{task_id}/` | 上传附件 |
| | `GET /files/download/{id}/` | 下载附件 |
| 管理 | `GET /admin/audit/` | 审计日志 |
| 仪表盘 | `GET /dashboard/*` | 统计数据 |

## 开发

### 运行测试

```bash
# 后端（334 个测试）
cd backend
DJANGO_ENV=local python -m pytest tests/ -v

# 前端类型检查
cd frontend
npx vue-tsc --noEmit
```

### 权限体系

| 角色 | 说明 | 数据范围 |
|------|------|----------|
| 超级管理员 | `is_superuser` | 全部数据 |
| 组长/ADMIN | `role=LEADER` 或 `role=ADMIN` | 全部数据 |
| 成员 | `role=MEMBER` | 仅自己负责/创建的任务 |

### 积分规则

| 动作 | 默认积分 | 说明 |
|------|----------|------|
| TASK_ASSIGNED | 5 | 被分配任务时 |
| TASK_COMPLETED | 20 | 完成任务时 |
| TASK_CREATED | 2 | 创建任务时 |

支持三种计积分模式：FIXED（固定值）、PRIORITY_BASED（按优先级加权）、CUSTOM（任务自定义积分）。

## License

[MIT](LICENSE)
