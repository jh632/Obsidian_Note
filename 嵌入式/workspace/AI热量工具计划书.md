# AI 热量记录工具 - 开发计划书

## 1. 项目概述

一款跨平台热量记录 App，通过 AI 对话的方式记录每日饮食与热量摄入。用户可自定义 AI API（OpenAI 兼容格式），以自然语言描述饮食内容，AI 自动解析食物名称、热量、营养素等结构化数据。

**核心价值**：告别手动查表录入，用说话的方式完成热量记录。

**目标平台**：Android / iOS / Windows / macOS / Web

---

## 2. 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 框架 | Flutter 3.x + Dart | 一套代码全平台运行 |
| 状态管理 | Riverpod 2.x | 编译期安全，可测试性好 |
| 路由 | go_router | 声明式路由，深链接支持 |
| 本地数据库 | Drift (SQLite) | 类型安全 ORM，支持复杂查询 |
| 图表 | fl_chart | 轻量 Flutter 原生图表库 |
| AI 接口 | dart_openai / 自定义 HTTP | OpenAI 兼容 API 格式 |
| 拍照 | image_picker | 预留接口，后续迭代 |
| 本地缓存 | shared_preferences | 轻量 KV 存储（设置项） |
| 国际化 | flutter_localizations | 预留，初期中文优先 |

---

## 3. 功能模块

### 3.1 AI 对话记录（核心）

- 用户输入自然语言描述饮食（如"午餐吃了一份宫保鸡丁和一碗米饭"）
- AI 解析为结构化数据：食物名称、预估重量、热量(kcal)、蛋白质(g)、碳水(g)、脂肪(g)
- 支持多轮对话修正（如"米饭是大碗的"、"再加一杯拿铁"）
-  支持ai主动反问,询问更多实物细节
-  支持存储记忆,高频食物优先存储
- 解析结果确认后入库

### 3.2 自定义 AI API

- 支持配置项：API Base URL、API Key、模型名称
- 兼容 OpenAI Chat Completions 格式（覆盖 OpenAI / DeepSeek / 通义千问 / 本地 Ollama 等）
- API Key 本地加密存储，不上传云端
- 内置连通性测试按钮

### 3.3 每日记录与统计

- 按日展示饮食记录列表，支持删除/编辑
- 每日热量/蛋白质/碳水/脂肪摄入汇总
- 日历视图快速切换日期
- 周报/月报趋势图

### 3.4 目标管理

- 设置每日热量/营养素目标
- 进度条显示当日完成度
- 超标预警

### 3.5 拍照识别（预留）

- 架构预留 image_picker 接口
- 图片转 base64 发送给多模态模型
- V2 迭代实现

### 3.6 数据管理

- 本地 SQLite 存储，无需注册登录
- 数据导出（JSON/CSV）
- 数据导入恢复

---

## 4. 数据模型

```
┌─────────────────────────────────────────────┐
│  MealRecord                                 │
├─────────────────────────────────────────────┤
│  id          : int (PK, auto)               │
│  date        : DateTime (日期)               │
│  meal_type   : String (早/午/晚/加餐)        │
│  description : String (用户原始输入)          │
│  foods       : List<FoodItem> (嵌套)         │
│  total_kcal  : double                       │
│  created_at  : DateTime                     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  FoodItem                                   │
├─────────────────────────────────────────────┤
│  name        : String (食物名称)             │
│  amount      : String (份量描述)             │
│  weight_g    : double (预估克数)             │
│  kcal        : double                       │
│  protein_g   : double                       │
│  carb_g      : double                       │
│  fat_g       : double                       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  DailyGoal                                  │
├─────────────────────────────────────────────┤
│  id          : int (PK)                     │
│  target_kcal : double                       │
│  target_protein_g : double                  │
│  target_carb_g    : double                  │
│  target_fat_g     : double                  │
│  is_active    : bool                        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  ApiConfig                                  │
├─────────────────────────────────────────────┤
│  id          : int (PK)                     │
│  name        : String (配置名称)             │
│  base_url    : String                       │
│  api_key     : String (加密存储)             │
│  model       : String                       │
│  is_active   : bool                         │
└─────────────────────────────────────────────┘
```

---

## 5. 页面规划

```
App
├── /home              首页 - 今日概览 + 快速记录入口
├── /chat              AI 对话页 - 输入饮食描述
├── /records           历史记录 - 日历 + 记录列表
│   └── /records/:id   记录详情/编辑
├── /stats             统计页 - 周报/月报图表
├── /goals             目标设置
└── /settings          设置
    ├── /settings/api  API 配置
    └── /settings/data 数据导入导出
```

---

## 6. AI 提示词设计（待定）

> 提示词将决定解析准确度，后续专项设计。初步结构：

- System Prompt：角色定义 + 输出格式约束（JSON Schema）
- User Message：用户饮食描述
- 输出格式：严格 JSON，包含 foods 数组 + 置信度

---

## 7. Agent 分工与协调

### 7.1 Agent 列表

本项目由 3 个子 Agent 协同开发，你需要向名字前的子 agent 委派任务（通过名字投喂任务）：

| Agent | 名称 | 职责 | 负责层次 |
|-------|------|------|---------|
| Agent A | **arch** | 架构与基础设施 | 项目骨架、数据库、路由、模型、配置 |
| Agent B | **core** | 核心业务逻辑 | AI服务、Provider状态、数据仓库、计算 |
| Agent C | **ui** | 用户界面 | 所有页面、组件、图表、响应式适配 |

### 7.2 依赖关系（重要）

```
     ┌──────────────────────┐
     │        arch           │  ← 最先执行，搭建地基
     │  (项目骨架 + 数据库)    │
     └──────┬───────────────┘
            │ 产出：模型、DB、路由、主题
            ▼
     ┌──────────────────────┐
     │        core           │  ← 依赖 arch 的模型和DB
     │  (业务逻辑 + Provider) │
     └──────┬───────────────┘
            │ 产出：Provider、Service、Repository
            ▼
     ┌──────────────────────┐
     │         ui            │  ← 依赖 core 的 Provider
     │  (页面 + 组件)         │
     └──────────────────────┘
```

- **arch** 无前置依赖，可立即启动
- **core** 依赖 arch 产出（模型类、数据库接口）
- **ui** 依赖 core 产出（Provider 接口）
- **同一 Phase 内按此顺序执行**，不同 Phase 间不可跳级

### 7.3 协作流程

1. 你委派任务给 agent → agent 执行并提交代码
2. agent 完成后向你汇报 → 你通知我审核
3. 我审核代码质量、一致性、跨 agent 兼容性
4. 审核通过 → 下一批任务继续

### 7.4 AGENTS.md 传递

每个 agent 启动前，确保 project 下的 `AGENTS.md` 已被其读取，保证编码风格统一。

---

## 8. 任务清单

> 任务编号格式：`Phase-AGENT-序号`，`[ ]` 表示未开始，`[x]` 表示已完成。
> 建议用法：复制某一 Phase 中某个 Agent 的全部任务，发给对应 agent 执行。

### Phase 1 — MVP 最小可用（目标：能用 AI 记录一顿饭）

#### arch（架构师）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P1-ARCH-01 | Flutter 项目创建 | `flutter create` 全平台 | — |
| P1-ARCH-02 | 目录骨架搭建 | `lib/` 下所有子目录 | P1-ARCH-01 |
| P1-ARCH-03 | pubspec.yaml 依赖声明 | `pubspec.yaml` | P1-ARCH-01 |
| P1-ARCH-04 | analysis_options.yaml | `analysis_options.yaml` | P1-ARCH-01 |
| P1-ARCH-05 | .gitignore 配置 | `.gitignore` | P1-ARCH-01 |
| P1-ARCH-06 | 主题配置 | `lib/config/theme.dart` | P1-ARCH-02 |
| P1-ARCH-07 | GoRouter 路由骨架 | `lib/config/routes.dart` | P1-ARCH-02 |
| P1-ARCH-08 | 数据模型基类定义 | `lib/models/food_item.dart` `lib/models/daily_goal.dart` `lib/models/api_config.dart` | P1-ARCH-02 |
| P1-ARCH-09 | MealRecord 模型定义 | `lib/models/meal_record.dart` | P1-ARCH-02 |
| P1-ARCH-10 | Drift 数据库表定义 | `lib/database/tables/` | P1-ARCH-08 P1-ARCH-09 |
| P1-ARCH-11 | AppDatabase 入口 + DAO | `lib/database/app_database.dart` | P1-ARCH-10 |
| P1-ARCH-12 | DatabaseProvider 初始化 | `lib/providers/database_provider.dart` | P1-ARCH-11 |
| P1-ARCH-13 | 仓库初始化脚本 + README | `README.md` | — |

#### core（引擎）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P1-CORE-01 | ApiConfigRepository（增删改查） | `lib/repositories/api_config_repo.dart` | arch 全部 |
| P1-CORE-02 | API Key 安全存储 | `lib/services/secure_storage_service.dart` | P1-CORE-01 |
| P1-CORE-03 | OpenAI 兼容 HTTP 客户端 | `lib/services/ai_http_client.dart` | P1-CORE-02 |
| P1-CORE-04 | AiService 封装（发请求+接收响应） | `lib/services/ai_service.dart` | P1-CORE-03 |
| P1-CORE-05 | System Prompt 构建器 | `lib/services/prompt_builder.dart` | P1-CORE-04 |
| P1-CORE-06 | AI 返回 JSON 解析器 | `lib/services/ai_response_parser.dart` | P1-CORE-04 |
| P1-CORE-07 | NutritionCalculator 工具 | `lib/services/nutrition_calculator.dart` | arch |
| P1-CORE-08 | MealRecordRepository（CRUD） | `lib/repositories/meal_record_repo.dart` | arch |
| P1-CORE-09 | ApiConfigProvider（状态管理） | `lib/providers/api_config_provider.dart` | P1-CORE-01 |
| P1-CORE-10 | ChatProvider（单轮对话状态） | `lib/providers/chat_provider.dart` | P1-CORE-04 P1-CORE-06 P1-CORE-08 |
| P1-CORE-11 | MealProvider（今日记录状态） | `lib/providers/meal_provider.dart` | P1-CORE-07 P1-CORE-08 |

#### ui（界面）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P1-UI-01 | App 入口 + MaterialApp 组装 | `lib/main.dart` `lib/app.dart` | arch core |
| P1-UI-02 | 首页 - 今日概览页面 | `lib/pages/home/home_page.dart` | P1-UI-01 |
| P1-UI-03 | NutritionBar 组件 | `lib/widgets/nutrition_bar.dart` | P1-UI-01 |
| P1-UI-04 | FoodCard 组件 | `lib/widgets/food_card.dart` | P1-UI-01 |
| P1-UI-05 | AI 对话页 - 消息列表 | `lib/pages/chat/chat_page.dart` | P1-UI-01 |
| P1-UI-06 | 对话消息气泡组件 | `lib/widgets/chat_bubble.dart` | P1-UI-05 |
| P1-UI-07 | 食物确认卡片（解析结果+确认） | `lib/widgets/food_confirm_card.dart` | P1-UI-05 |
| P1-UI-08 | API 配置列表页 | `lib/pages/settings/api_config_list_page.dart` | P1-UI-01 |
| P1-UI-09 | API 配置表单（添加/编辑） | `lib/pages/settings/api_config_form_page.dart` | P1-UI-08 |
| P1-UI-10 | 设置入口页 | `lib/pages/settings/settings_page.dart` | P1-UI-01 |
| P1-UI-11 | 响应式布局基础框架 | `lib/widgets/responsive_scaffold.dart` | P1-UI-01 |

---

### Phase 2 — 完善（目标：可回溯历史 + 数据统计）

#### arch（架构师）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P2-ARCH-01 | 数据库索引优化（按日期查询） | `lib/database/app_database.dart`（修改） | Phase 1 |

#### core（引擎）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P2-CORE-01 | MealProvider 扩展（按日期查询+删除） | `lib/providers/meal_provider.dart`（修改） | Phase 1 |
| P2-CORE-02 | DailyGoalRepository | `lib/repositories/daily_goal_repo.dart` | Phase 1 |
| P2-CORE-03 | GoalProvider | `lib/providers/goal_provider.dart` | P2-CORE-02 |
| P2-CORE-04 | StatsProvider（周报/月报聚合） | `lib/providers/stats_provider.dart` | P2-CORE-01 |
| P2-CORE-05 | 提示词调优 | `lib/services/prompt_builder.dart`（修改） | Phase 1 |

#### ui（界面）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P2-UI-01 | 历史记录页 - 日历+列表 | `lib/pages/records/records_page.dart` | Phase 1 |
| P2-UI-02 | 日历选择器组件 | `lib/widgets/date_picker.dart` | P2-UI-01 |
| P2-UI-03 | 记录详情/编辑页 | `lib/pages/records/record_detail_page.dart` | P2-UI-01 |
| P2-UI-04 | 统计页 - 趋势图表 | `lib/pages/stats/stats_page.dart` | P2-CORE-04 |
| P2-UI-05 | 目标设置页 | `lib/pages/goals/goals_page.dart` | P2-CORE-03 |
| P2-UI-06 | 进度条组件 | `lib/widgets/progress_bar.dart` | P2-UI-01 |

---

### Phase 3 — 增强（目标：多轮对话 + 导出 + 拍照预留）

#### arch（架构师）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P3-ARCH-01 | 文件选择器平台配置 | `pubspec.yaml`（新增依赖）各平台权限配置 | Phase 2 |

#### core（引擎）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P3-CORE-01 | 多轮对话上下文维护 | `lib/providers/chat_provider.dart`（修改） | Phase 2 |
| P3-CORE-02 | 数据导出服务（JSON/CSV） | `lib/services/export_service.dart` | P3-ARCH-01 |
| P3-CORE-03 | 数据导入服务 | `lib/services/import_service.dart` | P3-ARCH-01 |
| P3-CORE-04 | ImagePicker 服务封装 | `lib/services/image_service.dart` | Phase 2 |

#### ui（界面）

| 编号 | 任务 | 产出文件 | 前置 |
|------|------|---------|------|
| P3-UI-01 | 深色模式切换 | `lib/config/theme.dart`（修改） | Phase 2 |
| P3-UI-02 | 桌面端宽屏布局适配 | 各页面响应式调整 | Phase 2 |
| P3-UI-03 | 数据导入/导出页面入口 | `lib/pages/settings/data_manage_page.dart` | P3-CORE-02 P3-CORE-03 |
| P3-UI-04 | 拍照记录入口（UI 预留） | `lib/pages/chat/`（新增相机按钮） | P3-CORE-04 |

---

## 9. 项目结构（拟）

```
lib/
├── main.dart
├── app.dart
├── config/
│   ├── theme.dart
│   └── routes.dart
├── models/
│   ├── meal_record.dart
│   ├── food_item.dart
│   ├── daily_goal.dart
│   └── api_config.dart
├── database/
│   ├── app_database.dart
│   └── tables/
├── providers/
│   ├── database_provider.dart
│   ├── api_config_provider.dart
│   ├── meal_provider.dart
│   └── chat_provider.dart
├── services/
│   ├── ai_service.dart
│   └── nutrition_calculator.dart
├── pages/
│   ├── home/
│   ├── chat/
│   ├── records/
│   ├── stats/
│   ├── goals/
│   └── settings/
└── widgets/
    ├── food_card.dart
    ├── nutrition_bar.dart
    └── date_picker.dart
```

---

## 10. 系统架构分层

```
┌──────────────────────────────────────────────────┐
│  Presentation Layer (UI)                         │
│  pages/ + widgets/ + providers/ (Riverpod)       │
│  负责：页面渲染、用户交互、状态绑定               │
├──────────────────────────────────────────────────┤
│  Domain Layer (业务逻辑)                          │
│  models/ + services/                             │
│  负责：数据模型、业务规则、营养计算               │
├──────────────────────────────────────────────────┤
│  Data Layer (数据访问)                            │
│  database/ + api_client/                         │
│  负责：SQLite CRUD、AI API 调用、数据持久化        │
└──────────────────────────────────────────────────┘
```

### 层间依赖规则

- **Presentation → Domain ← Data**：Domain 是核心，不依赖任何具体实现
- Presentation 通过 Riverpod Provider 调用 Domain 层 Repository 接口
- Data 层实现 Repository 接口，注入到 Provider
- 每层只依赖下一层的接口，不依赖具体实现

### 数据流

```
用户输入 → UI (TextFormField)
    → Provider (状态管理)
        → AiService (调用 AI API)
            → 解析 AI 返回的 JSON
                → Repository (保存到 SQLite)
                    → Provider 通知 UI 刷新
```

---

## 11. Git 规范

### 11.1 分支策略

```
main          ──── 稳定发布分支，直接合并到该分支触发构建
  └── dev     ──── 开发主线，功能分支从此切出
       ├── feat/xxx    功能分支
       ├── fix/xxx     Bug 修复分支
       └── docs/xxx    文档更新分支
```

- **main**：保护分支，仅通过 merge request 合入
- **dev**：日常开发分支，阶段性合入 main
- **feat/*** ：新功能开发，合入 dev
- **fix/***  ：bug 修复，合入 dev 后 cherry-pick 到 main
- 单人项目初期可以简化：main + feat/ 分支，直接在 feat 分支开发，完成后合并

### 11.2 Commit 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>  (可选)
```

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响逻辑） |
| refactor | 重构（非新功能、非修复） |
| chore | 构建/工具/依赖变更 |
| test | 测试相关 |

**示例**：
```
feat(chat): 实现 AI 对话页面的多轮对话功能
fix(database): 修复日期字段时区转换错误
chore: 升级 Flutter SDK 到 3.10
```

### 11.3 提交前检查

- [ ] 代码通过 `flutter analyze`（无 error）
- [ ] 相关测试通过 `flutter test`
- [ ] 未包含 API Key 或敏感信息
- [ ] `.gitignore` 已配置

### 11.4 .gitignore 要点

```gitignore
# Flutter
.dart_tool/
build/
*.iml
*.bak
*.orig
# 暂存区特别说明
.env
.env.*
# Idea IDEs
.idea/
# macOS
.DS_Store
# 加密秘钥文件——绝对不要提交
lib/config/secrets.dart
# 测试覆盖率
coverage/
**/fastlane/report.xml
**/fastlane/Preview.html
**/fastlane/test_output
# other
*.lock
*.log
*.tgz
*.ipr
*.iws
*.swp
*.swo
``` 

---

## 12. GitHub 托管

### 12.1 仓库信息

| 项目 | 内容 |
|------|------|
| 平台 | GitHub |
| 账户 | jh632 |
| Git 本地 | jasper（公司账户，仅本地 commit 签名用） |
| 仓库名 | health-tracker（待确认） |
| 可见性 | 初期 Private，稳定后按需改 Public |
| 默认分支 | main |

### 12.2 仓库初始化步骤

```bash
# 1. 在 GitHub 网页端创建仓库 health-tracker（Private）

# 2. 本地初始化
cd D:\project\health_app
git init
git remote add origin https://github.com/jh632/health-tracker.git

# 3. 创建初始文件后首次提交
git add .
git commit -m "chore: 初始化项目结构"
git push -u origin main
```

### 12.3 仓库目录结构

```
health-tracker/
├── lib/                     # Dart 源码
├── test/                    # 单元/Widget 测试
├── assets/                  # 图片/字体等静态资源
├── web/                     # Web 平台配置
├── android/                 # Android 原生配置
├── ios/                     # iOS 原生配置
├── windows/                 # Windows 原生配置
├── macos/                   # macOS 原生配置
├── pubspec.yaml             # 依赖配置
├── analysis_options.yaml    # Lint 规则
├── .gitignore
├── AGENTS.md                # AI 编码规范
└── README.md                # 项目说明
```

### 12.4 CI/CD（后续可选）

- GitHub Actions：push 到 main 时自动运行 `flutter analyze` + `flutter test`
- 暂不配置自动构建分发（MVP 阶段手动构建）

---

## 13. 注意事项

- **隐私**：所有数据本地存储，API Key 加密，不设云端后端
- **离线**：AI 功能需网络，但历史记录/统计完全离线可用
- **最小权限**：仅请求网络权限（拍照阶段再加相机权限）
- **API 成本**：提醒用户关注 API 调用量，对话尽量精简 token
- 
