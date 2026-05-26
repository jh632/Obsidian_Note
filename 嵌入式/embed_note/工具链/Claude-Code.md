---
date: 2026-05-25
tags: [claude-code, cli, ai-tool, dev-tools]
aliases: [Claude Code CLI]
---

# Claude Code

## 概述

Anthropic 官方 CLI 工具，在终端中运行。作为 AI 编程助手，可以读写文件、执行 bash 命令、使用 git、搜索代码库等。基于 Claude Opus/Sonnet/Haiku 模型。

## 核心命令

### 会话控制

| 命令 | 说明 |
|---|---|
| `/clear` | 清空当前对话上下文，重新开始 |
| `/compact` | 压缩上下文，保留关键信息 |
| `/context` | 查看当前上下文使用情况 |
| `/cost` | 查看当前会话 token 消耗 |
| `/doctor` | 诊断环境问题 |
| `/help` | 帮助信息 |

### 模式切换

| 命令 | 说明 |
|---|---|
| `/plan` | 进入计划模式 — 先设计方案，用户审批后再写代码 |
| `/fast` | 切换到快速模式（更快的输出速度） |
| `/think` | 启用/切换思考模式（Opus 深度推理） |
| `/loop` | 按间隔重复执行某个 prompt（如 `/loop 5m /test`） |
| `/plugin` | 安装插件 |

### 项目配置

| 命令 | 说明 |
|---|---|
| `/init` | 在当前项目初始化 CLAUDE.md |
| `/config` | 修改配置（主题、模型等） |
| `/memory` | 打开记忆文件管理 |
| `/settings` | 查看/编辑 settings.json |
| `/hooks` | 管理 hooks 配置 |
| `/statusline` | 配置状态栏 |
| `/terminal-setup` | 终端集成设置（Shift+Enter 换行绑定） |

### Git / PR

| 命令 | 说明 |
|---|---|
| `/pr-comments` | 查看当前分支的 PR 评论 |
| `/review` | 代码审查 PR |
| `/security-review` | 安全审查当前分支变更 |

### 其他

| 命令 | 说明 |
|---|---|
| `/export` | 导出对话记录 |
| `/upgrade` | 升级 Claude Code |
| `/install-github-app` | 安装 GitHub App 集成 |
| `/bashes` | 查看后台运行的 bash 任务 |
| `/tasks` | 查看后台任务 |
| `/todos` | 查看/管理 todo 列表 |
| `/add-dir` | 添加额外工作目录 |
| `/mcp` | 管理 MCP 服务器 |
| `/ide` | IDE 集成相关 |
| `/permissions` | 管理权限设置 |
| `/output-style` | 设置输出风格 |
| `/resume` | 恢复之前的会话 |

## CLAUDE.md

项目根目录和用户家目录下的 `.md` 文件，作为 persistent instruction 自动注入到每轮对话中。

**加载优先级：**
1. 用户全局 `~/.claude/CLAUDE.md` — 个人偏好和规范
2. 项目根目录 `CLAUDE.md` — 项目级指令
3. 子目录 `CLAUDE.md`（递归向上） — 模块级指令
4. 子目录内仅对当前目录及子目录生效

```markdown
# 示例 CLAUDE.md
## 编码规范
- 使用 4 空格缩进
- 函数名用 snake_case
```

## 记忆系统 (Memory)

持久化文件记忆，存储在 `~/.claude/projects/<project-name>/memory/`：

| 类型 | 用途 |
|---|---|
| `user` | 用户角色、偏好、知识背景 |
| `feedback` | 用户给出的行为反馈和指导 |
| `project` | 项目目标、约束、进度信息 |
| `reference` | 外部系统指针（Linear、Slack、Grafana 等）|

记忆会自动在相关对话中加载使用。每个记忆存储为独立 `.md` 文件，`MEMORY.md` 为索引。

## Skills（技能/插件）

可安装的专业化能力模块，处理特定类型任务：

- 通过 `/plugin` 安装
- 用户可以用 `/技能名` 或自然语言触发
- 常见内置技能：`code-review`、`commit`、`pr-comments` 等
- 自定义技能用 `skill-creator` 插件创建

## Hooks（钩子）

在特定事件触发时自动执行的脚本/命令，配置在 `settings.json` 中：

常见事件：
- `PostToolUse` — 工具调用后
- `PreToolUse` — 工具调用前
- `Notification` — 通知时
- `Stop` — 对话停止时
- `UserPromptSubmit` — 用户提交 prompt 时

## Settings

三个级别的配置文件：

| 文件 | 作用域 |
|---|---|
| `~/.claude/settings.json` | 用户全局 |
| `.claude/settings.json` | 项目级（可提交 git） |
| `.claude/settings.local.json` | 项目本地（不提交 git） |

关键配置项：
- `permissions` — 工具权限白名单/黑名单
- `hooks` — 事件钩子
- `mcpServers` — MCP 服务器配置
- `model` — 默认模型
- `enableAllProjectMcpServers` — 项目级 MCP
- `env` — 环境变量

## 权限系统

每个工具调用分 4 个权限级别：

| 级别 | 行为 |
|---|---|
| `allow` | 始终允许，不询问 |
| `default` | 首次询问，之后可用 `always allow` |
| `deny` | 始终拒绝 |
| `ask` | 每次都询问 |

在 `settings.json` 中可配置白名单/黑名单规则。

## Worktree（工作树）

通过 `/worktree` 或 `EnterWorktree` 创建隔离的 git worktree：
- 在 `.claude/worktrees/` 下创建
- 适合并行处理多个任务
- 退出时可选保留或删除

## MCP (Model Context Protocol)

扩展 Claude Code 能力的协议，可连接外部工具和数据源。配置在 `settings.json` 的 `mcpServers` 下。

## 实用技巧

### 快捷输入
- 在 prompt 中输入 `! 命令` — 直接在会话中执行 shell 命令
- `Esc` 两次清理输入框
- `Shift+Enter` 换行（需 `/terminal-setup` 配置）

### IDE 集成
- VS Code 扩展可用
- JetBrains 插件可用
- `/ide` 命令管理 IDE 连接

### 性能
- 模型选择：Opus（最强推理）、Sonnet（平衡）、Haiku（最快）
- `/fast` 模式使用 Opus 但输出更快
- `/compact` 在上下文过长时压缩

### 项目结构约定
- `.claude/` 目录存放项目级 Claude Code 配置
- `.claude/settings.json` 可以提交到 git 供团队共享
- `.claude/settings.local.json` 放个人密钥等敏感配置

## 参考

- [Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code)
- [GitHub Issues](https://github.com/anthropics/claude-code/issues)


