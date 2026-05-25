---
date: 2026-05-25
tags: [git, 工具链]
aliases: [git-commands]
---

# 常用 Git 命令

## 概述

日常开发中使用的 git 命令集合，包括 Claude Code 插件提供的快捷命令和原生 git 命令。

## Claude Code 快捷命令

### commit-commands 插件

| 命令 | 作用 |
|---|---|
| `/commit` | 自动分析改动 → stage 文件 → 生成 commit message → 提交 |
| `/commit-push-pr` | commit + push + 创建 PR（如果在 main 分支会自动创建新分支） |
| `/clean_gone` | 清理所有远程已删除但本地还残留的分支（包括关联的 worktree） |

典型工作流：
```
# 日常开发中反复提交
/commit

# 功能完成，推送并创建 PR
/commit-push-pr

# PR 合并后定期清理
/clean_gone
```

`/commit-push-pr` 要求安装并认证 GitHub CLI（`gh auth login`）。

### 其他相关命令

| 命令 | 作用 |
|---|---|
| `/review` | 审查当前 PR |
| `/security-review` | 安全审查当前分支的改动 |

---

## 仓库初始化

```bash
git remote add origin https://github.com/jh632/Obsidian_Note.git
git branch -M main
git push -u origin main
```

## 分支操作

```bash
# 查看分支
git branch -a                    # 所有分支（含远程）
git branch -v                    # 带最新 commit 信息
git branch -vv                   # 带追踪关系

# 创建/切换
git checkout -b feature/xxx      # 新建并切换
git checkout main                # 切换分支
git switch main                  # 新版切换命令

# 删除
git branch -d feat/xxx           # 安全删除（已合并）
git branch -D feat/xxx           # 强制删除

# 同步远程状态
git fetch --prune                # 更新远程追踪，清理已删除的远程分支
```

## 暂存与提交

```bash
git add <file>                   # 暂存指定文件
git add -p                       # 交互式暂存（逐块确认）
git commit -m "message"          # 提交
git commit --amend               # 修改上一次提交（不要 amend 已推送的）

git status                       # 查看工作区状态
git diff                         # 未暂存的改动
git diff --staged                # 已暂存的改动
git log --oneline -10            # 最近 10 条提交
```

## 同步与 PR

```bash
git push -u origin feat/xxx      # 首次推送并设置上游
git push                         # 后续推送
git pull --rebase                # 拉取并 rebase（推荐）
git fetch origin                 # 只拉取，不合并
```

## 撤销操作

```bash
git reset HEAD <file>            # 取消暂存
git checkout -- <file>           # 丢弃工作区改动（不可恢复）
git reset --soft HEAD~1          # 撤销 commit，改动回到暂存区
git stash                        # 暂存当前改动
git stash pop                    # 恢复暂存的改动
```

## 查看历史

```bash
git log --oneline --graph --all  # 图形化分支历史
git blame <file>                 # 查看每行代码的修改记录
git show <commit-hash>           # 查看某次提交的详情
```

## 相关笔记

- [[clang-format-Linux内核风格]]
