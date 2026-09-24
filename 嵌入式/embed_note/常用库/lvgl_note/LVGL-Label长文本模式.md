---
date: 2026-09-14
tags: [embed_note, 常用库, lvgl_note]
aliases: [lv_label_long_mode_t, LVGL Label 长文本模式, LVGL long mode]
---

# LVGL 8 Label 长文本模式（lv_label_long_mode_t）

## 概述

当 Label 的文本尺寸超过控件尺寸时，由 `long_mode` 决定裁剪、换行、滚动还是省略。

**前提：只有显式设置了宽度/高度，`long_mode` 才会生效。** Label 的宽高默认是 `LV_SIZE_CONTENT`，此时控件会自动撑到文本大小，不存在"文本超出"，任何 `long_mode` 都看不出效果。同理，如果只有文本比控件**高**（垂直方向超出），策略同样按下面的规则作用。

LVGL 8 共有 **5 种**模式，默认是 `LV_LABEL_LONG_WRAP`。

## 五种模式

| 模式 | 行为 |
| ---- | ---- |
| `LV_LABEL_LONG_WRAP` | 保持对象宽度，超长行自动换行，并扩展对象高度（默认） |
| `LV_LABEL_LONG_DOT` | 保持尺寸，文本过长时把右下角最后 3 个字符替换为 `...` |
| `LV_LABEL_LONG_SCROLL` | 保持尺寸，文本来回滚动（back and forth） |
| `LV_LABEL_LONG_SCROLL_CIRCULAR` | 保持尺寸，文本连续循环滚动，首尾衔接 |
| `LV_LABEL_LONG_CLIP` | 保持尺寸，超出部分直接裁剪，不换行、不滚动、无省略号 |

`SCROLL` 与 `SCROLL_CIRCULAR` 的滚动方向规则相同：文本更宽则水平滚动，文本更高则垂直滚动；**只滚一个方向，水平优先**。

## 效果对比

Label 宽度 120 px，文本 `SN4-PSW-20260914-ABCDEFG`：

```text
LV_LABEL_LONG_WRAP              文字折行，高度自动增长
  SN4-PSW-2026
  0914-ABCDEFG

LV_LABEL_LONG_DOT               末 3 字符变省略号
  SN4-PSW-20…

LV_LABEL_LONG_SCROLL            来回滚动，能看到完整内容
  ← PSW-20260914- →

LV_LABEL_LONG_SCROLL_CIRCULAR   循环滚动，首尾衔接
  …ABCDEFG-SN4-PSW…

LV_LABEL_LONG_CLIP              硬裁剪，看不到的部分就是没有
  SN4-PSW-2026
```

## 代码

```c
lv_obj_t * label = lv_label_create(lv_scr_act());
lv_label_set_text(label, "SN4-PSW-20260914-ABCDEFG");

/* 先设 long_mode，再设尺寸 */
lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
lv_obj_set_width(label, 120);                   /* 滚动的三种模式必须给出确定宽度，不能是 LV_SIZE_CONTENT */
lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
```

## 注意事项

- **先设 `long_mode`，再设尺寸。** 头文件注释明确要求：`WRAP` / `DOT` / `SCROLL` / `SCROLL_CIRCULAR` 四种模式下尺寸应在 `lv_label_set_long_mode()` **之后**设置。
- **`WRAP` 的高度行为分两种情况**：高度是 `LV_SIZE_CONTENT` 时自动扩展以容纳所有行；显式设了高度且不够时，超出的行被裁剪。不会自动保证页面布局正确，仍需检查下方控件是否重叠。
- **`DOT` 会原地改写文本缓冲区**（为插入/移除 `...` 直接改 buffer），且只替换最后 3 个字符。
  - 配 `lv_label_set_text()` / `lv_label_set_text_fmt()` 时无感知（内部另分配了 buffer）；
  - 配 `lv_label_set_text_static()` 时，传入的 buffer 必须可写 —— 常量字符串在 ROM 中，用于 `DOT` 模式会出错。
- **滚动速度在 LVGL 8 中不可直接配置**：v7 的 `lv_label_set_anim_speed()` 已移除。官方文档说明，`SCROLL` / `SCROLL_CIRCULAR` 的动画可通过 `lv_style_set_anim()` 定制，但目前仅 `SCROLL_CIRCULAR` 的启动/重复延迟可调。
- `LV_LABEL_LONG_SCROLL` 只滚一个方向，文本同时超宽又超高时不会双向滚动，水平优先。
- 超长文本（> 40k 字符）开启 `LV_LABEL_LONG_TXT_HINT 1`，以约 12 字节额外数据加速绘制。

## 选型建议

| 需求 | 推荐模式 |
| ---- | -------- |
| 内容必须完整显示，允许两行 | `LV_LABEL_LONG_WRAP` |
| 必须一行，不要求完整显示 | `LV_LABEL_LONG_DOT` |
| 必须完整显示，但只有一行空间 | `LV_LABEL_LONG_SCROLL` |
| 希望持续循环展示 | `LV_LABEL_LONG_SCROLL_CIRCULAR` |
| 明确不希望出现任何提示（裁剪即可） | `LV_LABEL_LONG_CLIP` |

设备型号之类的信息位于设置页，下方还有其他选项，选 `WRAP` 时除了给 Label 留出高度，还要确认布局能容纳两行文本。

## 附：与 LVGL 7 的对应关系

LVGL 8 移除了 `EXPAND` 和 `CROP` 的命名，并统一了拼写错误：

| LVGL 7 | LVGL 8 |
| ------ | ------ |
| `LV_LABEL_LONG_EXPAND` | 移除，语义由默认的 `LV_SIZE_CONTENT` 承担 |
| `LV_LABEL_LONG_BREAK` | `LV_LABEL_LONG_WRAP` |
| `LV_LABEL_LONG_DOT` | `LV_LABEL_LONG_DOT` |
| `LV_LABEL_LONG_SROLL`（v7 源码即拼错） | `LV_LABEL_LONG_SCROLL` |
| `LV_LABEL_LONG_SROLL_CIRC` | `LV_LABEL_LONG_SCROLL_CIRCULAR` |
| `LV_LABEL_LONG_CROP` | `LV_LABEL_LONG_CLIP` |

在 LVGL 8 中写 `LV_LABEL_LONG_EXPAND` 会直接编译报错，展开对象以适应文本这件事改用"不设宽高"或 `LV_SIZE_CONTENT` 表达。

## 参考

- LVGL 8.3 Label 文档: https://docs.lvgl.io/8.3/widgets/core/label.html
- 枚举与 API 定义: https://github.com/lvgl/lvgl/blob/release/v8.3/src/widgets/lv_label.h
- LVGL 7.11 定义（迁移对照）: https://github.com/lvgl/lvgl/blob/v7.11.0/src/lv_widgets/lv_label.h

## 相关笔记

- [[lvgl_config]] — Label 依赖的显示缓冲与内存配置
- [[LVGL-显示原理]] — 显示流水线整体原理
