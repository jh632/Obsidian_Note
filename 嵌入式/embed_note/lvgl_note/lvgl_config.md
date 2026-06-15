---
date: 2026-06-15
tags: [lvgl, gui, configuration, memory, porting]
aliases: [LVGL configuration, LVGL porting, LVGL memory]
---

# LVGL 配置与内存管理

## 概述

LVGL 的上手配置主要包括：颜色深度、内存管理方式和显示缓冲区大小与绑定。理解不同内存类型的角色与差异，是正确配置和排查内存问题的前提。

## 初始化流程

```text
硬件初始化
  ↓
LVGL 核心初始化 (lv_init)
  ↓
显示设备 display 初始化 (flush_cb + draw_buf)
  ↓
输入设备 input 初始化 (read_cb)
  ↓
定时器 / tick / task handler 启动
```

## 颜色深度

| `LV_COLOR_DEPTH` | 含义       | 常见场景                   |
| ---------------- | -------- | ---------------------- |
| `1`              | 单色       | 墨水屏、黑白屏                |
| `8`              | 256 色    | 少见                     |
| `16`             | RGB565   | MCU 小屏幕最常见             |
| `24`             | RGB888   | Linux framebuffer、PC   |
| `32`             | ARGB8888 | 带 alpha 的 GUI、PC、Linux |

**`LV_COLOR_16_SWAP`**：RGB565 模式下字节序交换（0/1），取决于 LCD 控制器的字节序要求。

## 内存类型

LVGL 运行中涉及多种内存区域，它们的用途和配置方式各不相同：

| 类型                  | 作用                       | 常见配置                                           |
| ------------------- | ------------------------ | ---------------------------------------------- |
| LVGL heap           | 控件、样式、动画、事件等动态对象分配       | `LV_MEM_SIZE` / `CONFIG_LV_MEM_SIZE_KILOBYTES` |
| Display draw buffer | 屏幕刷新绘图缓冲区                | `buffer_size` / `draw_buf` 参数                  |
| FreeRTOS task stack | LVGL task / UI task 的栈空间 | `uxTaskGetStackHighWaterMark()` 监控余量           |
| 图片/字体资源             | bin、C array、字体 bitmap 等  | 编译进 flash / RAM / PSRAM                        |
| DMA buffer          | SPI/LCD 刷屏 DMA 使用的缓冲区    | `buff_dma = true` 标记（部分平台需要 DMA-capable 内存）    |

### LVGL Heap vs Draw Buffer

这两个最容易混淆。它们的根本区别在于存什么、谁在用：

| 维度 | LVGL Heap | Draw Buffer |
|------|-----------|-------------|
| **存什么** | 控件对象、样式、动画、事件等结构化数据 | 像素颜色值（RGB565/ARGB8888） |
| **谁在用** | `lv_btn_create()` 等 API 分配对象时 | LVGL 渲染引擎绘制像素时 |
| **数据结构** | 链表管理的堆（malloc/free） | 平坦的像素数组 |
| **大小** | 通常 16~128 KB | 分辨率 × 缓冲行数 × 字节/像素 |
| **分配方式** | 运行时动态分配/释放 | 启动时静态分配，永久固定 |
| **配置入口** | `LV_MEM_SIZE` / `LV_MEM_CUSTOM` | `lv_disp_draw_buf_init()` |

**类比：**

```text
LVGL Heap  = 图层面板 —— 存每个图层的属性（位置、大小、透明度）
Draw Buffer = 画布    —— 最终合成好的像素矩阵
```

LVGL 的工作就是**遍历 Heap 中的对象树，渲染成 Buffer 中的像素**——两者是生产者和消费者的关系。

### 各内存要点

- **LVGL heap** — 小对象多、分配频繁，放内部 SRAM 性能最好；PSRAM 延迟高可能拖慢 UI
- **Draw buffer** — 大块连续，对延迟不敏感，放 PSRAM 是常见做法
- **DMA buffer** — 必须在 DMA 可访问的内存区域（如 ESP32 只有内部 RAM 支持 DMA）
- **Task stack** — 通过 `uxTaskGetStackHighWaterMark()` 在运行后确认余量，避免栈溢出

## 内存池配置

### 内置内存池

```c
#define LV_MEM_CUSTOM 0
#define LV_MEM_SIZE (64U * 1024U)  // LVGL 内部管理一段静态内存
```

### 外部 malloc

```c
#define LV_MEM_CUSTOM 1
#define LV_MEM_CUSTOM_ALLOC   malloc
#define LV_MEM_CUSTOM_FREE    free
#define LV_MEM_CUSTOM_REALLOC realloc
```

有 RTOS 时推荐 `LV_MEM_CUSTOM 1`，让 LVGL 使用系统的堆管理，避免额外占用一块静态内存。

## 显示缓冲区

分配一块像素缓冲区给 LVGL 绘制：

```c
static lv_color_t buf1[MY_DISP_HOR_RES * 40];  // 40 行缓冲

static lv_disp_draw_buf_t draw_buf;
lv_disp_draw_buf_init(&draw_buf, buf1, NULL, MY_DISP_HOR_RES * 40);
```

绑定到 display driver：

```c
static lv_disp_drv_t disp_drv;
lv_disp_drv_init(&disp_drv);

disp_drv.hor_res  = MY_DISP_HOR_RES;
disp_drv.ver_res  = MY_DISP_VER_RES;
disp_drv.flush_cb = my_disp_flush;
disp_drv.draw_buf = &draw_buf;

lv_disp_drv_register(&disp_drv);
```

缓冲行数（`40`）决定了单次刷新的高度，越大则每帧 DMA 传输次数越少，但占用 RAM 更多。

## 完整配置示例

### 头文件与配置宏

```c
/**
 * @file lvgl_port.c
 * @brief LVGL 初始化配置示例（ESP-IDF + SPI LCD）
 */

#include "lvgl.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_dev.h"

/* ——— 颜色深度 ——— */
/** LVGL 颜色深度：16bit RGB565 */
#define LV_COLOR_DEPTH 16
/** RGB565 字节序交换：视 LCD 控制器而定 */
#define LV_COLOR_16_SWAP 1

/* ——— 显示参数 ——— */
#define LCD_HOR_RES     240
#define LCD_VER_RES     320

/* ——— 像素缓冲区（Draw Buffer） ——— */
/**
 * 一次刷新 40 行，占用 240 × 40 × 2 = 19.2 KB
 * 
 * buf1 和 buf2 两片缓冲区构成双缓冲：
 *   - DMA 发送 buf1 的同时，LVGL 绘制 buf2
 *   - 发送完成后再交换角色
 *   从而实现 CPU 绘图与 DMA 传输并行执行，提升帧率
 */
#define FLUSH_LINE 40
static  lv_color_t buf1[LCD_HOR_RES * FLUSH_LINE];
static  lv_color_t buf2[LCD_HOR_RES * FLUSH_LINE];  /* 双缓冲第二块 */

static lv_disp_draw_buf_t draw_buf;
static lv_disp_drv_t      disp_drv;
static lv_disp_t         *disp;
```

### 初始化函数

```c
/**
 * @brief 初始化 LVGL 显示系统
 * 
 * 调用顺序固定：lv_init → draw_buf 初始化 → disp_drv 注册
 * 必须在 FreeRTOS task 启动、SPI LCD 硬件初始化完成后调用
 * 
 * @return lv_disp_t* 注册成功的显示设备句柄，用于后续操作
 */
lv_disp_t *lvgl_port_init(void)
{
 
    lv_init();

    lv_disp_draw_buf_init(&draw_buf, buf1, buf2, LCD_HOR_RES * FLUSH_LINE);

    lv_disp_drv_init(&disp_drv);

    /* 设置显示驱动参数 */
    disp_drv.hor_res  = LCD_HOR_RES;   /**< 水平分辨率（像素） */
    disp_drv.ver_res  = LCD_VER_RES;   /**< 垂直分辨率（像素） */
    disp_drv.flush_cb = flush_cb;      /**< 刷新回调：LVGL 将渲染完毕的像素数据由此送出 */
    disp_drv.draw_buf = &draw_buf;     /**< 绑定已初始化的 Draw Buffer */

    disp = lv_disp_drv_register(&disp_drv);

    return disp;
}
```

### LVGL 原生 API 说明

```c
/**
 * @brief 初始化 LVGL 核心库
 * 
 * 必须在所有其他 LVGL API 之前调用。
 * 内部完成：全局状态初始化、默认样式注册、内存池初始化等。
 * 
 * @param  无
 * @return 无
 */
void lv_init(void);

/**
 * @brief 初始化显示缓冲区（Draw Buffer）
 * 
 * @param draw_buf  缓冲区控制块指针
 * @param buf1      第一缓冲区（LVGL 渲染用）
 * @param buf2      第二缓冲区（DMA 发送用），传 NULL 则为单缓冲
 * @param size      缓冲区大小（以像素数为单位）
 * 
 * buf2 不为 NULL 时启用双缓冲：
 *   LVGL 渲染 buf1 的同时 DMA 发送 buf2，交替使用
 * 
 * @return 无
 */
void lv_disp_draw_buf_init(lv_disp_draw_buf_t *draw_buf,
                           lv_color_t *buf1,
                           lv_color_t *buf2,
                           uint32_t size);

/**
 * @brief 初始化显示设备驱动结构体
 * 
 * 将 disp_drv 各字段置为默认值，避免未初始化的字段导致异常。
 * 调用后仍需手动设置分辨率、flush_cb、draw_buf 等字段。
 * 
 * @param drv  显示驱动结构体指针
 * @return 无
 */
void lv_disp_drv_init(lv_disp_drv_t *drv);

/**
 * @brief 注册显示设备到 LVGL 系统
 * 
 * 将配置好的 disp_drv 注册到 LVGL，使系统可用该设备进行渲染输出。
 * LVGL 内部据此创建并绑定显示设备对象。
 * 
 * @param drv  已配置完成的显示驱动结构体指针
 * @return lv_disp_t* 注册成功的显示设备句柄，失败返回 NULL
 */
lv_disp_t *lv_disp_drv_register(lv_disp_drv_t *drv);
```

## 参考

- LVGL Porting 文档: https://docs.lvgl.io/master/porting/display.html
- ESP-IDF LVGL 内存配置: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/lcd.html

## 相关笔记

- [[LVGL-显示原理]] — 显示流水线整体原理
