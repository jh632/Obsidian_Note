# Claude Code 能力清单：Plugin / Skill 分类与触发方式

> 更新日期：2026-06-16

---

## 一、整体概念

| 大类 | 作用 | 特点 |
|------|------|------|
| **🔧 系统插件** | 扩展基础设施能力 | 添加新工具/命令，持久生效 |
| **📋 流程技能** | 提供工作方法论 | 通过 Skill 工具加载，指导行为 |
| **🎯 领域技能** | 针对特定输出/任务 | 用于文档处理、代码审查等具体工作 |

## 二、触发方式图标

| 图标 | 含义 |
|:----:|------|
| 🔄 | **常驻自动** — 后台持续运行/一直生效 |
| ⚡ | **上下文自触发** — 检测到场景自动加载使用 |
| 👆 | **手动触发** — 必须用户提出或我主动调用 |

---

## 🔧 系统插件

> 自动生效或通过 `/command` 触发，扩展基础设施能力

| 名称 | 触发 | 说明 |
|------|:----:|------|
| **hookify** | 🔄 + 👆 | **规则常驻拦截**；管理规则需手动：`/hookify list` 查看，对话定义规则 |
| **claude-hud** | 🔄 | 终端状态面板，启用即自动显示；配置：`~/.claude/plugins/claude-hud/config.json` |
| **commit-commands** | 👆 | `/commit` — 交互式提交；`/push` — 推送；`/pr` — 创建 PR |
| **planning-with-files** | 👆 | `/plan start "..."` 创建规划；`/plan show` 查看；`/plan resume` 恢复 |
| **claude-md-management** | 👆 + ⚡ | `/claude-md sync` 写入记忆；`/claude-md audit` **自动**审计过时内容；`/claude-md update` 手动更新 |
| **kimi-webbridge** | 👆 | 控制真实浏览器操作网页（需说"打开浏览器/网页"等） |
| **skill-creator** | 👆 | `/skill-create` — 交互式创建新技能 |
| **update-config** | 👆 | 修改 `settings.json` 配置 Claude Code 行为 |
| **keybindings-help** | 👆 | 自定义快捷键绑定（改 `~/.claude/keybindings.json`） |
| **fewer-permission-prompts** | 👆 | 扫描记录自动降低权限提示频率 |
| **init** | 👆 | 初始化 CLAUDE.md：`/init` |

---

## 📋 流程技能

> 通过 Skill 工具加载，指导工作方法论。绝大多数是上下文自触发，不需要你记得名字

| 名称 | 触发 | 说明 |
|------|:----:|------|
| **using-superpowers** | ⚡ | **每次对话开始自动加载**，告知如何用技能 |
| **brainstorming** | ⚡ | 开始创意/设计前自动触发，先探索需求再动手 |
| **test-driven-development** | ⚡ | 写新功能/修 bug 时自动启用，先写测试再实现 |
| **systematic-debugging** | ⚡ | 遇到 bug/测试失败，自动系统排查 |
| **verification-before-completion** | ⚡ | 即将说"完成了"之前自动验证 |
| **writing-plans** | ⚡ | 接到多步骤任务（5+ 工具调用）自动规划 |
| **requesting-code-review** | ⚡ | 合并前自动审查工作是否达标 |
| **receiving-code-review** | ⚡ | 收到审查意见后自动处理 |
| **finishing-a-development-branch** | ⚡ | 开发完成收尾时自动引导 |
| **dispatching-parallel-agents** | ⚡ | 遇到 2+ 独立任务自动并行派发 |
| **subagent-driven-development** | ⚡ | 执行实现计划时自动派发子代理 |
| **using-git-worktrees** | ⚡ | 需要工作隔离时自动创建工作树 |
| **surgical-code-edit** | 🔄 | **常驻** — 改代码时自动遵循最小修改原则 |
| **esp-idf-device-driver-style** | 🔄 | **常驻** — 嵌入式项目中自动遵循驱动规范 |
| **deep-research** | ⚡ | 涉及查芯片寄存器/硬数据时自动启用联网多源验证 |
| **grill-me** | 👆 | 说"推敲我的方案/来 grill 我"触发 |
| **grill-with-docs** | 👆 | 说"推敲方案并更新文档"触发 |

---

## 🎯 领域技能

> 针对特定输出或任务的指令集，均为手动触发

| 名称                                 | 触发  | 说明                                |
| ---------------------------------- | :-: | --------------------------------- |
| **code-review**                    | 👆  | 审查当前 diff：`/code-review` 或说"审查代码" |
| **simplify** (原 `code-simplifier`) | 👆  | 简化代码：`/simplify` 或说"简化这段代码"       |
| **verify**                         | 👆  | 运行应用验证改动效果                        |
| **run**                            | 👆  | 启动项目                              |
| **loop**                           | 👆  | 循环执行：`/loop 5m <命令>`              |
| **security-review**                | 👆  | PR 安全审查                           |
| **obsidian-note**                  | 👆  | 说"帮我记笔记" — 整理到 Obsidian vault     |
| **pdf**                            | 👆  | PDF 处理（提取/合并/拆分/OCR 等）            |
| **pptx**                           | 👆  | PPT 制作与编辑                         |
| **docx / word-doc-creator**        | 👆  | Word 文档/论文生成                      |
| **xlsx**                           | 👆  | Excel 电子表格（公式/格式化/图表）             |
| **claude-api**                     |  ⚡  | 提到 Claude/Anthropic 相关话题时自动加载参考   |

---




**Tips：**
- 🔄 常驻型的只需要确保启用，不用管它
- ⚡ 自触发的你也不需要记名字，场景到了我自动会用
- 👆 手动型的记住关键命令即可，大部分有 `/command` 快捷方式
- 所有技能可通过 `Skill` 工具加载，所有命令支持 `--help` 查看参数
