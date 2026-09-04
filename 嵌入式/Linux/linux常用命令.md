---
date: 2026-08-12
tags: [linux, 工具链]
aliases: [linux-commands]
---

# Linux 常用命令

> 按使用场景组织的 Linux 常用命令速查，嵌入式开发 + WSL 日常使用。
> 大纲先行，后续学习中逐条补充命令示例。

## 文件与目录

- [x] `ls` — 列出目录内容（`-l` `-a` `-h` `-t` `-S` 组合） ✅ 2026-08-12
	- `ls -l` — 长格式（权限、大小、时间）
	- `ls -a` — 显示隐藏文件
	- `ls -lh` — 人类可读大小（KB/MB）
	- `ls -lt` — 按修改时间排序（最新在前）
	- `ls -lS` — 按大小排序（最大在前）
- [x] `cd` / `pwd` — 切换 / 查看当前目录 ✅ 2026-08-12
	- `cd ~` — 回到家目录
	- `cd -` — 回到上一次目录
	- `pwd` — 打印当前绝对路径
- [x] `mkdir` / `touch` — 创建目录 / 文件 ✅ 2026-08-12
	- `mkdir -p a/b/c` — 递归创建多级目录
	- `touch file.txt` — 创建空文件或更新时间戳
- [x] `cp` / `mv` / `rm` — 复制 / 移动 / 删除 ✅ 2026-08-31
	- `cp -r dir1 dir2` — 递归复制目录
	- `cp -i src dst` — 覆盖前确认
	- `mv old new` — 重命名或移动
	- `rm -i file` — 删除前确认
	- `rm -rf dir` — 强制递归删除（慎用）
- [ ] `find` — 按名称、类型、大小查找文件
	- `find . -name "*.c"` — 按名称查找（支持通配符）
	- `find . -type f` — 只找文件（`-d` 只找目录）
	- `find . -size +1M` — 大于 1MB 的文件
	- `find . -mtime -7` — 7 天内修改过的文件
	- `find . -exec grep -l "TODO" {} \;` — 找到后执行命令
- [x] `fdfind`（fd） — find 的现代替代，速度快、语法友好 🔧 需手动安装 `sudo apt install fd-find` ✅ 2026-08-31
	- `fdfind "\.c$"` — 按正则查找（默认递归、忽略 .gitignore）
	- `fdfind -e c` — 按扩展名查找
	- `fdfind -t f` — 只找文件（`d` 只找目录）
	- `fdfind -S +1M` — 按大小排序
	- `fdfind -H pattern` — 包含隐藏文件
- [x] `ln` — 软链接 / 硬链接 ✅ 2026-08-13
	- `ln -s target link_name` — 创建软链接（跨文件系统）
	- `ln target link_name` — 创建硬链接（同一文件系统）
- [ ] `du` / `df` — 目录大小 / 磁盘空间
- [ ] `file` / `tree` — 文件类型 / 目录树

## 文本处理

- [ ] `cat` / `less` / `head` / `tail` — 查看文件（`tail -f` 看日志）
- [x] `grep` — 文本搜索（`-r` `-n` `-i` `-v`） ✅ 2026-08-12
- [x] `rg`（ripgrep） — 更快的文本搜索，自动递归、忽略 .gitignore 🔧 需手动安装 `sudo apt install ripgrep` ✅ 2026-08-31
	- `rg "pattern" .` — 递归搜索当前目录
	- `rg -i "pattern" .` — 忽略大小写
	- `rg -t py "def init" .` — 只搜 Python 文件
	- `rg -g '!build/' "TODO" .` — 排除 build 目录
	- `rg -l "pattern" .` — 只打印匹配的文件名
	- `rg "pattern" file1 file2` — 指定文件
- [ ] `sed` — 流式替换
- [ ] `wc` / `sort` / `uniq` — 统计 / 排序 / 去重
- [ ] `diff` — 文件对比
- [ ] `awk` / `cut` — 字段提取（了解）

## 进程与系统

- [ ] `ps` / `top` — 查看进程与资源
- [ ] `kill` — 终止进程
- [ ] `free` — 内存占用
- [ ] `uname` / `lscpu` — 系统与 CPU 信息
- [ ] `crontab` — 定时任务

## 网络与远程

- [ ] `ping` / `ip` / `ifconfig` — 网络连通与接口信息
- [ ] `curl` / `wget` — HTTP 请求 / 下载
- [ ] `ssh` / `scp` — 远程登录 / 传输文件
- [ ] `netstat` / `ss` — 端口与连接
- [ ] `tcpdump` — 抓包（了解）

## 权限与用户

- [ ] `chmod` — 修改权限
- [ ] `chown` — 修改属主
- [ ] `sudo` / `su` — 提权
- [ ] `whoami` / `id` — 当前用户信息

## 压缩与归档

- [ ] `tar` — 打包压缩（`.tar.gz`）
- [ ] `zip` / `unzip` — 常见压缩格式
- [ ] `gzip` / `xz` — 单文件压缩（了解）

## 其他常用

- [ ] `man` / `--help` — 查文档
- [ ] `which` / `whereis` — 定位命令路径
- [ ] `history` — 命令历史
- [ ] 重定向与管道（`>` `>>` `|`）
