---
date: 2026-05-25
tags: [clang-format, linux-kernel, 代码格式化]
aliases: [Linux-kernel-clang-format-style]
---

# Linux 内核 clang-format 配置特点

## 概述

Linux 内核自带 `.clang-format`（位于 `Documentation/dev-tools/clang-format.rst`），是为内核 C 代码定制的一套格式化规则。整体遵循内核编码风格文档（`Documentation/process/coding-style.rst`），核心约束是 **Tab=8、80 列、函数大括号另起一行、其余 K&R**。

## 核心特点

### 硬 Tab，8 字符缩进

```yaml
IndentWidth: 8
TabWidth: 8
UseTab: Always
```

Linux 内核最显著的风格标识。全部使用 Tab 字符，一个 Tab 占用 8 列宽度。嵌入式项目通常用 4 空格，这是移植到 ESP32 项目时最大的不适配点。

### 80 列硬限制

```yaml
ColumnLimit: 80
```

内核强制要求，没有例外。

### 大括号：K&R + 函数大括号换行

```yaml
BreakBeforeBraces: Custom
BraceWrapping:
  AfterFunction: true          # 函数定义大括号另起一行
  AfterControlStatement: false # if/for/while 大括号同行
```

- 控制语句（`if`/`for`/`while`）的左大括号与关键字同行
- **函数定义的左大括号必须独占一行**，这是 Linux 内核与纯 K&R 的唯一区别

### `char *p` 指针风格

```yaml
DerivePointerAlignment: false
PointerAlignment: Right
```

星号紧靠变量名：`char *ptr`，而非 `char* ptr` 或 `char * ptr`。

### 禁止短语句同行

```yaml
AllowShortIfStatementsOnASingleLine: false
AllowShortLoopsOnASingleLine: false
AllowShortFunctionsOnASingleLine: None
AllowShortCaseLabelsOnASingleLine: false
AllowShortBlocksOnASingleLine: false
```

所有语句都必须换行，不允许 `if (x) return;` 之类的缩写。

### SpaceBeforeParens 特例

```yaml
SpaceBeforeParens: ControlStatementsExceptForEachMacros
```

`if (`、`for (`、`while (` 前面加空格，但 `for_each_*` 宏不加 —— 因为它们是函数式宏，被识别为函数而非控制语句。

### 不排序 include

```yaml
SortIncludes: false
IncludeBlocks: Preserve
```

内核有严格的 include 层级规则（`linux/` → `asm/` → `linux/`），clang-format 无权重排。

### 巨量 ForEachMacros 列表

```yaml
ForEachMacros:
  - 'list_for_each'
  - 'list_for_each_entry'
  - 'for_each_cpu'
  # ... ~680 个
```

告诉 clang-format 这些都是 `for_each_*` 宏，不要按普通函数调用格式化（保持 `;` 前换行风格一致）。

### Penality 惩罚值调优

```yaml
PenaltyBreakAssignment: 10
PenaltyBreakBeforeFirstCallParameter: 30
PenaltyBreakComment: 10
PenaltyBreakString: 10
PenaltyExcessCharacter: 100
PenaltyReturnTypeOnItsOwnLine: 60
```

控制换行决策的权重：

- `PenaltyExcessCharacter: 100` — 超出 80 列的惩罚最高，优先在其他位置换行
- `PenaltyReturnTypeOnItsOwnLine: 60` — 返回值类型独占一行的惩罚次高，尽量避免
- `PenaltyBreakBeforeFirstCallParameter: 30` — 第一个参数前换行惩罚中等

### 其他细节

```yaml
AlignOperands: true              # 操作数对齐
AlignAfterOpenBracket: Align     # 括号内对齐
MaxEmptyLinesToKeep: 1           # 最多保留 1 个空行
ReflowComments: false            # 不重排注释
Standard: Cpp03                  # 用 C++03 模式（对 C 代码兼容最好）
ConstructorInitializerIndentWidth: 8
ContinuationIndentWidth: 8       # 续行缩进也是 8（对齐 Tab）
```

## 移植到嵌入式项目的注意点

1. **Tab=8 太宽**：嵌入式项目通常用 4 空格或 Tab=4，直接改成 `IndentWidth: 4, TabWidth: 4`
2. **80 列过窄**：现代项目常用 100 或 120
3. **ForEachMacros 列表**：内核的宏列表对 ESP-IDF 无用，应删掉或替换为项目自己的 `for_each_*` 宏
4. **Include 规则**：如果不需要保留 include 顺序，可开启 `SortIncludes`
5. **指针风格**：`PointerAlignment: Right` 保留与否取决于团队习惯

## 参考

- Linux 内核源码 `Documentation/dev-tools/clang-format.rst`
- [ClangFormat 文档](https://clang.llvm.org/docs/ClangFormat.html)
- [ClangFormat Style Options](https://clang.llvm.org/docs/ClangFormatStyleOptions.html)

## 相关笔记

- 暂无
