---
name: commit
description: 当用户输入 /commit 时，执行 git commit 操作。自动暂存所有更改并提交，使用中文 commit message。
---

# Git Commit

当用户输入 `/commit` 时，执行以下操作：

## 步骤

1. 检查当前 git 状态 (`git status`)
2. 暂存所有更改 (`git add .`)
3. 生成中文 commit message 并提交

## Commit Message 格式

遵循项目 AGENTS.md 中的格式：

```
## YYYY-MM-DD

## [feat/chore/fix] 简要描述
```

根据实际更改内容自动判断：
- **feat**: 新功能、新需求
- **chore**: 改进、优化、文档更新
- **fix**: bug 修复

## 示例

```bash
git add .
git commit -m "## 2026-07-08

## [chore] 更新嵌入式项目文档"
```

## 注意事项

- 如果没有更改，提示用户"没有可提交的更改"
- 如果有未跟踪的新文件，会自动包含在提交中
- commit message 使用中文描述
