---
date: 2026-06-15
tags: [lvgl, gui, display, framebuffer]
aliases: [LVGL display pipeline, LVGL rendering]
---

# LVGL 显示原理

## 概述

LVGL 是一个**软件渲染引擎（Software Renderer）**，它根据控件树计算最终画面并将像素写入缓冲区，不关心底层显示硬件如何传输数据。理解从控件到屏幕的整个流水线，是正确配置和优化显示性能的基础。

## 核心概念

- **LVGL 不负责 SPI/RGB/DMA** — 它只负责"画什么"，不负责"怎么显示"
- **Draw Buffer** — LVGL 渲染输出的像素数组，是连接 LVGL 和显示驱动的桥梁
- **flush_cb** — LVGL 回调，将渲染好的 Buffer 交给底层驱动发送到屏幕
- **双缓冲** — 解决 DMA 发送期间不能修改 Buffer 的问题，形成 CPU 与 DMA 的流水线并行

## 细节

### 本质：软件渲染引擎

```c
lv_btn_create(parent);
```

最终被渲染为像素数据写入 Buffer：

```text
矩形背景 → 边框 → 阴影 → 文字 → 像素数据
```

```c
buf[0] = color;
buf[1] = color;
// ...
```

### 完整显示流程

```text
lv_timer_handler()
    ↓
计算脏区域（哪些控件需要重绘）
    ↓
渲染控件到 Draw Buffer
    ↓
flush_cb()  →  将 Buffer 交给显示驱动
    ↓
LCD Driver (SPI/RGB/I80)
    ↓
LCD
```

核心思想：**控件 → 像素 → 缓冲区 → 屏幕**

### Draw Buffer

```c
static lv_color_t buf1[400 * 30];  // 宽400, 高30行, RGB565
```

内存布局就是一个像素数组：

```text
+------------------+
| Pixel0 (RGB565)  |
| Pixel1 (RGB565)  |
| Pixel2 (RGB565)  |
| ...              |
+------------------+
```

### flush_cb

LVGL 渲染完成后调用的回调，将像素数据传递给底层驱动：

```c
void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    lcd_draw_bitmap(area->x1, area->y1, area->x2, area->y2, px_map);
    lv_display_flush_ready(disp);  // 通知 LVGL 发送完成
}
```

`px_map` 就是 LVGL 渲染好的像素数据。

### SPI LCD 流程

```text
LVGL → Draw Buffer → flush_cb → SPI DMA → LCD GRAM → 显示
```

本质就是：

```c
spi_write(px_map, len);
```

### RGB LCD 流程（如 ESP32-S3 RGB 接口）

```text
LVGL → Frame Buffer → RGB Controller → LCD
```

CPU 不需要主动发送数据，LCD 控制器自动从 Frame Buffer 读取像素，类似**显卡读取显存**。

### 双缓冲详解

**单缓冲问题：**

```text
LVGL绘图 → Buffer → DMA发送 → 等待完成 → 继续绘图
```

DMA 发送期间 LVGL 不能修改 Buffer，否则产生花屏/撕裂。

**双缓冲流水线：**

```text
DMA 发送 BufferA  ←──┐
                      │  并行执行
LVGL 绘制 BufferB  ──┘

发送完成 → 交换角色：
DMA 发送 BufferB
LVGL 绘制 BufferA
```

**效果：**

| 模式 | 时间 |
|------|------|
| 单缓冲 | 绘图 5ms + 发送 10ms = **15ms** |
| 双缓冲 | max(绘图 5ms, 发送 10ms) = **10ms** |

双缓冲既提高刷新率，又防止撕裂。

### 源码阅读主线

```text
lv_timer_handler()
    → lv_refr_timer()
    → lv_display_refr_timer()
    → lv_refr_area()
    → lv_draw_xxx()
    → flush_cb()
```

这条链路就是：**发现需要刷新 → 渲染控件 → 生成像素 → 发送到屏幕**。

## 参考

- LVGL 官方文档: https://docs.lvgl.io/master/
- LVGL Porting 指南: https://docs.lvgl.io/master/porting/display.html

## 相关笔记

- [[lvgl_config]] — 配置、内存类型与显示缓冲区设置
