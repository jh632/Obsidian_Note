---
name: push
description: 当用户输入 /push 时，执行 git push 操作，将本地更改推送到远程仓库。
---

# Git Push

当用户输入 `/push` 时，执行以下操作：

## 步骤

1. 检查当前分支 (`git branch --show-current`)
2. 检查是否有未提交的更改
3. 推送到远程仓库

## 命令

```bash
# 推送到远程同名分支
git push

# 如果是新分支，设置上游分支
git push -u origin <branch-name>
```

## 注意事项

- 推送前检查是否有未提交的更改，如有则提示用户先 commit
- 显示推送结果
