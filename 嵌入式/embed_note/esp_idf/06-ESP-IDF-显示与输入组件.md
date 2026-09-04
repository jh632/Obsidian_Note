---
tags: [esp-idf, lvgl, esp-lcd, button, gui, 显示, 输入]
date: 2026-09-01
aliases: [LVGL适配, idf button组件, LVGL-ESP-IDF-porting, esp_lvgl_adapter, esp_lvgl_port, IDF Button]
---

# ESP-IDF 显示与输入组件（LVGL 适配 / Button）

> 2026-09-01 由原《lvgl适配》《idf button组件》整理合并（原 lvgl 笔记存在内容重复段落，已去重）。分为两大部分：**① LVGL 适配分层 ② IDF Button 组件**。

---

## 目录

1. [LVGL 适配分层](#1-lvgl-适配分层)
2. [IDF Button 组件](#2-idf-button-组件)

---

# 1. LVGL 适配分层

## 1.1 概述

ESP-IDF 中 LVGL 的适配分为三层：**LVGL 核心库**（图形渲染引擎）→ **Adapter/Port 层**（桥接适配）→ **esp_lcd 驱动框架**（硬件驱动）。三层之间通过**回调函数**和**句柄指针交换**实现双向通信。

Adapter 层有两个官方组件，按推出时间排列：
- **[`esp_lvgl_adapter`]**（较新，推荐）— 统一适配层，内置撕裂避免、FS/Decoder/FreeType 模块，要求 IDF ≥ 5.5
- **[`esp_lvgl_port`]**（较早）— 位于 esp-bsp 仓库，较简单，广泛用于早期项目

此外还有**自制移植模式**，直接手写回调桥接。

## 1.2 三层架构总览

```
┌────────────────────────────────────────────────────────────┐
│  层级1: LVGL 核心库 (lvgl/lvgl)                             │
│  职责: 图形渲染、UI 对象管理、动画、输入事件分发               │
│  核心文件: src/hal/lv_hal_disp.h, src/hal/lv_hal_indev.h   │
└──────────────────────┬─────────────────────────────────────┘
                       │ flush_cb / read_cb 回调
                       ▼
┌────────────────────────────────────────────────────────────┐
│  层级2: Adapter / Port 层                                   │
│                                                           │
│  ┌─ 形态A: esp_lvgl_adapter (v0.6.0+, 推荐新项目) ──────┐  │
│  │  来源: components.espressif.com 组件注册中心             │  │
│  │  要求: ESP-IDF ≥ 5.5                                   │  │
│  │  命名前缀: esp_lv_adapter_*                             │  │
│  │  核心文件:                                              │  │
│  │    include/esp_lv_adapter.h                             │  │
│  │    include/esp_lv_adapter_display.h                     │  │
│  │    include/esp_lv_adapter_touch.h                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ 形态B: esp_lvgl_port (较早, 来自 esp-bsp) ───────────┐  │
│  │  来源: github.com/espressif/esp-bsp                     │  │
│  │  命名前缀: lvgl_port_*                                  │  │
│  │  核心文件:                                              │  │
│  │    include/esp_lvgl_port.h                              │  │
│  │    include/esp_lvgl_port_disp.h                         │  │
│  │    src/lvgl8/esp_lvgl_port_disp.c                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                           │
│  职责: 桥接 LVGL ↔ esp_lcd, 任务调度, 互斥保护, 旋转同步    │
└──────────────────────┬─────────────────────────────────────┘
                       │ esp_lcd API 调用
                       ▼
┌────────────────────────────────────────────────────────────┐
│  层级3: ESP-IDF esp_lcd 驱动框架                             │
│  职责: SPI/I80/RGB/MIPI-DSI 总线时序, LCD 控制器驱动,       │
│        触摸屏驱动, DMA 传输                                  │
│  核心文件:                                                 │
│    esp_lcd_panel_io.h   (面板 IO 接口)                      │
│    esp_lcd_panel_ops.h  (面板操作接口)                       │
│    esp_lcd_panel_vendor.h  (厂商驱动: ST7789/NT35510/...)    │
│    esp_lcd_touch.h  (触摸接口)                               │
└──────────────────────┬─────────────────────────────────────┘
                       │ SPI / I80 / RGB 总线
                       ▼
                  ┌──────────────┐
                  │  LCD 硬件     │
                  │  (ST7789等)   │
                  └──────────────┘
```

## 1.3 层级1: LVGL 核心库 — API

### 显示驱动接口

```c
// 初始化 LVGL 核心
lv_init();

// === LVGL v8 API ===
// 绘制缓冲区初始化
lv_disp_draw_buf_t disp_buf;
lv_disp_draw_buf_init(&disp_buf, buf1, buf2, buffer_size);

// 显示驱动注册
lv_disp_drv_t disp_drv;
lv_disp_drv_init(&disp_drv);
disp_drv.hor_res    = 240;           // 水平分辨率
disp_drv.ver_res    = 320;           // 垂直分辨率
disp_drv.flush_cb   = my_flush_cb;   // 刷新回调（由 Port 层实现）
disp_drv.draw_buf   = &disp_buf;
disp_drv.user_data  = panel_handle;  // 桥接：持有 esp_lcd 面板句柄
lv_disp_drv_register(&disp_drv);

// === LVGL v9 API ===
lv_display_t *disp = lv_display_create(240, 320);
lv_display_set_buffers(disp, buf1, buf2, draw_buffer_sz, LV_DISPLAY_RENDER_MODE_PARTIAL);
lv_display_set_flush_cb(disp, my_flush_cb);
lv_display_set_user_data(disp, panel_handle);
lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
```

| LVGL v8 | LVGL v9 | 说明 |
|---------|---------|------|
| `lv_disp_drv_t` | `lv_display_t*` | 显示驱动句柄 |
| `lv_disp_drv_init()` | `lv_display_create()` | 初始化/创建显示设备 |
| `lv_disp_drv_register()` | — | v8 注册驱动 |
| `lv_disp_draw_buf_init()` | `lv_display_set_buffers()` | 设置绘制缓冲区 |
| `lv_disp_flush_ready()` | `lv_display_flush_ready()` | 通知刷新完成 |
| `lv_disp_set_rotation()` | `lv_disp_set_rotation()` | 设置旋转 |

### 输入设备接口

```c
// LVGL v8
lv_indev_drv_t indev_drv;
lv_indev_drv_init(&indev_drv);
indev_drv.type    = LV_INDEV_TYPE_POINTER;  // 或 KEYPAD / ENCODER
indev_drv.read_cb = my_input_read_cb;        // 读输入回调
lv_indev_drv_register(&indev_drv);

// LVGL v9
lv_indev_t *indev = lv_indev_create();
lv_indev_set_type(indev, LV_INDEV_TYPE_POINTER);
lv_indev_set_read_cb(indev, my_input_read_cb);
lv_indev_set_display(indev, disp);
```

### 任务与心跳

```c
// 心跳时钟（必须 2-5ms 周期调用）
lv_tick_inc(tick_period_ms);

// 任务循环（周期调用）
lv_timer_handler();        // 处理动画、渲染、刷新
```

## 1.4 层级2: Adapter / Port 层 — API

### 形态A: `esp_lvgl_adapter`（推荐，IDF ≥ 5.5）

来源: [components.espressif.com/components/espressif/esp_lvgl_adapter](https://components.espressif.com/components/espressif/esp_lvgl_adapter/versions/0.6.0/readme?language=zh)

统一适配层，一个组件覆盖所有显示接口类型（MIPI DSI / RGB / QSPI / SPI / I2C / I80 / MONO），内置撕裂避免策略和可选 FS/Decoder/FreeType 模块。

#### 初始化与生命周期

```c
#include "esp_lv_adapter.h"

// 初始化配置
esp_lv_adapter_config_t adapter_cfg = ESP_LV_ADAPTER_DEFAULT_CONFIG();
esp_lv_adapter_init(&adapter_cfg);   // 初始化 LVGL + 适配层

esp_lv_adapter_start();            // 启动 LVGL 任务
esp_lv_adapter_deinit();           // 全量反初始化
```

#### 显示设备注册

按接口类型选择对应的默认配置宏，一套 API 统一接入：

```c
#include "esp_lv_adapter_display.h"

// ── SPI/I2C/I80/QSPI 显示（无 PSRAM） ──
esp_lv_adapter_display_config_t disp_cfg =
    ESP_LV_ADAPTER_DISPLAY_SPI_WITHOUT_PSRAM_DEFAULT_CONFIG(
        panel_handle,    // esp_lcd 面板句柄
        io_handle,       // esp_lcd IO 句柄
        240,             // 水平分辨率
        320,             // 垂直分辨率
        ESP_LV_ADAPTER_ROTATE_0
    );
lv_display_t *disp = esp_lv_adapter_register_display(&disp_cfg);

// ── SPI/I2C/I80/QSPI 显示（有 PSRAM） ──
esp_lv_adapter_display_config_t disp_cfg =
    ESP_LV_ADAPTER_DISPLAY_SPI_WITH_PSRAM_DEFAULT_CONFIG(
        panel_handle, io_handle, 240, 320, ESP_LV_ADAPTER_ROTATE_0
    );

// ── RGB 显示 ──
esp_lv_adapter_display_config_t disp_cfg =
    ESP_LV_ADAPTER_DISPLAY_RGB_DEFAULT_CONFIG(
        panel_handle, io_handle, 800, 480, ESP_LV_ADAPTER_ROTATE_0
    );

// ── MIPI DSI 显示 ──
esp_lv_adapter_display_config_t disp_cfg =
    ESP_LV_ADAPTER_DISPLAY_MIPI_DEFAULT_CONFIG(
        panel_handle, io_handle, 800, 480, ESP_LV_ADAPTER_ROTATE_0
    );

// ── MONO（单色屏，支持 0°/90°/180°/270° 全旋转） ──
esp_lv_adapter_display_config_t disp_cfg =
    ESP_LV_ADAPTER_DISPLAY_PROFILE_MONO_DEFAULT_CONFIG(
        panel_handle, io_handle, 128, 64, ESP_LV_ADAPTER_ROTATE_0
    );

// 注册 / 注销
lv_display_t *disp = esp_lv_adapter_register_display(&disp_cfg);
esp_lv_adapter_unregister_display(disp);
```

#### 撕裂避免（Tear-Avoidance）

仅 RGB 和 MIPI DSI 支持。SPI/I2C/I80/QSPI 仅为 `NONE` 或 `TE_SYNC`。

```c
// 计算所需帧缓冲区数
uint8_t num_fbs = esp_lv_adapter_get_required_frame_buffer_count(
    ESP_LV_ADAPTER_TEAR_AVOID_MODE_DEFAULT_RGB,
    ESP_LV_ADAPTER_ROTATE_0
);
// 结果: 90°/270°旋转或三缓冲 → 3 FB; 双缓冲 → 2; 单缓冲 → 1
```

| 撕裂避免模式 | 用途场景 | FB 数 | 内存 | 支持接口 |
|-------------|---------|-------|------|---------|
| `TRIPLE_PARTIAL` | 90°/270°旋转、高刷流畅 UI | 3 | 高 | RGB/DSI |
| `TRIPLE_FULL`    | 全屏/大面积刷新 | 3 | 高 | RGB/DSI |
| `DOUBLE_FULL`    | 大面积，内存吃紧 | 2 | 中 | RGB/DSI |
| `DOUBLE_DIRECT`  | 小区域/控件局部更新 | 2 | 中 | RGB/DSI |
| `TE_SYNC`        | 带 TE 信号的外设接口屏 | 1 | 低 | SPI/I80/... |
| `NONE`           | 静态 UI，极低内存 | 1 | 低 | 全部 |

**关键限制**：
- RGB/DSI 在 `NONE` 模式**不支持任何非零旋转**
- OTHER 接口（SPI/I80/...）**不处理 90°/270° 旋转**，需在 LCD 初始化时配好朝向
- MONO 通过 LVGL 像素级处理**完整支持 0°/90°/180°/270° 软件旋转**

#### 触摸输入

```c
esp_lv_adapter_touch_config_t touch_cfg =
    ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(disp, touch_handle);
lv_indev_t *touch = esp_lv_adapter_register_touch(&touch_cfg);

// 多指触碰（LVGL9）
touch_cfg.multi_touch.mode = ESP_LV_ADAPTER_TOUCH_MODE_MULTI_CONTROL;
touch_cfg.multi_touch.pointers = 2;
```

#### 线程安全

```c
if (esp_lv_adapter_lock(-1) == ESP_OK) {  // -1 = 无限等待
    // 所有 LVGL 操作放在这里
    lv_btn_create(lv_scr_act());
    lv_label_set_text(label, "Hello");
    esp_lv_adapter_unlock();
}
```

#### 可选模块（Kconfig 控制）

| Kconfig 选项 | 功能 | API |
|-------------|------|-----|
| `ESP_LV_ADAPTER_ENABLE_FS` | 文件系统桥接 | `esp_lv_adapter_fs_mount()`，路径前缀 `"A:image.png"` |
| `ESP_LV_ADAPTER_ENABLE_DECODER` | 图片解码 (JPG/PNG/QOI) | 集成 `esp_lv_decoder`，路径前缀 `"I:"` |
| `ESP_LV_ADAPTER_ENABLE_FREETYPE` | FreeType 矢量字体 | `esp_lv_adapter_ft_font_init()/get()` |
| `ESP_LV_ADAPTER_ENABLE_FPS_STATS` | FPS 统计 | `esp_lv_adapter_fps_stats_enable(disp, true)` |
| `ESP_LV_ADAPTER_ENABLE_KNOB` | 旋钮输入 | — |
| `ESP_LV_ADAPTER_ENABLE_BUTTON` | 按键导航 | — |

#### 电源管理

适配层不直接控制 LCD 电源。提供自动休眠机制：

```c
// PAUSE 模式: 适配层暂停 LVGL，用户回调处理面板休眠/唤醒
//   触摸/按键/旋钮会自动唤醒
//   自定义唤醒源: esp_lv_adapter_request_wake()
//                 esp_lv_adapter_request_wake_from_isr()

// USER 模式: on_enter_sleep() 回调自行完成完整休眠流程

// 手动休眠恢复:
void sleep_prepare(void);   // 删除 LCD 硬件 → light_sleep
void sleep_recover(disp, panel, panel_io);  // 重新初始化 LCD
```

#### 默认参数总结

| 参数 | SPI no PSRAM | SPI w/ PSRAM | RGB | MIPI DSI | MONO |
|------|-------------|-------------|-----|---------|------|
| `buffer_height` | 10 行 | 全屏高 | 50 | 50 | — |
| 撕裂避免 | NONE | NONE | 默认 | 默认 | NONE |
| 旋转支持 | 仅在 LCD 初始化配 | 同上 | 全支持 | 全支持 | 全支持 |

#### 完整初始化示例

```c
void app_main(void)
{
    // ── 层级3: 初始化 SPI 总线 + LCD 硬件 ──
    spi_bus_initialize(LCD_HOST, &buscfg, SPI_DMA_CH_AUTO);
    esp_lcd_new_panel_io_spi(LCD_HOST, &io_config, &io_handle);
    esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle);
    esp_lcd_panel_reset(panel_handle);
    esp_lcd_panel_init(panel_handle);
    esp_lcd_panel_disp_on_off(panel_handle, true);

    // ── 层级2: esp_lvgl_adapter 初始化 ──
    esp_lv_adapter_config_t adapter_cfg = ESP_LV_ADAPTER_DEFAULT_CONFIG();
    esp_lv_adapter_init(&adapter_cfg);

    // 注册显示
    esp_lv_adapter_display_config_t disp_cfg =
        ESP_LV_ADAPTER_DISPLAY_SPI_WITHOUT_PSRAM_DEFAULT_CONFIG(
            panel_handle, io_handle, 240, 320, ESP_LV_ADAPTER_ROTATE_0);
    lv_display_t *disp = esp_lv_adapter_register_display(&disp_cfg);

    // 注册触摸
    esp_lv_adapter_touch_config_t touch_cfg =
        ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(disp, touch_handle);
    esp_lv_adapter_register_touch(&touch_cfg);

    // 启动 LVGL 任务
    esp_lv_adapter_start();

    // ── 应用层 UI ──
    esp_lv_adapter_lock(-1);
    example_lvgl_demo_ui(disp);
    esp_lv_adapter_unlock();
}
```

### 形态B: `esp_lvgl_port`（较早，来自 esp-bsp）

来源: [github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port](https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port)

较早的移植组件，仍在广泛使用，功能较 `esp_lvgl_adapter` 简单。

#### 初始化和反初始化

```c
#include "esp_lvgl_port.h"

const lvgl_port_cfg_t lvgl_cfg = ESP_LVGL_PORT_INIT_CONFIG();
// 默认值: priority=4, stack=7168, affinity=-1,
//         max_sleep=500ms, timer_period=5ms

esp_lvgl_port_init(&lvgl_cfg);    // 创建 LVGL 任务 + 心跳定时器
esp_lvgl_port_deinit(void);       // 反初始化
```

#### 显示设备添加

```c
#include "esp_lvgl_port_disp.h"

// SPI/I2C/I8080 显示接入
lv_display_t *lvgl_port_add_disp(const lvgl_port_display_cfg_t *disp_cfg);

// 配置结构体
typedef struct {
    esp_lcd_panel_io_handle_t    io_handle;       // esp_lcd IO 句柄（必需）
    esp_lcd_panel_handle_t       panel_handle;    // esp_lcd 面板句柄（必需）
    esp_lcd_panel_handle_t       control_handle;  // 分离控制句柄（可选，用于旋转）
    uint32_t                     buffer_size;     // 缓冲区大小（像素数）
    bool                         double_buffer;   // 是否双缓冲
    uint32_t                     trans_size;      // DMA 中转缓冲区大小（PSRAM场景）
    uint32_t                     hres;            // 水平分辨率
    uint32_t                     vres;            // 垂直分辨率
    bool                         monochrome;      // 是否单色
    lvgl_port_rotation_cfg_t     rotation;        // 默认旋转
    struct {
        bool buff_dma;       // LVGL 缓冲区使用 DMA 内存
        bool buff_spiram;    // LVGL 缓冲区使用 PSRAM
        bool sw_rotate;      // 使用软件旋转
        bool full_refresh;   // 全屏刷新
        bool direct_mode;    // 全尺寸直接模式
        bool swap_bytes;     // RGB565 字节交换（LVGL9+）
    } flags;
} lvgl_port_display_cfg_t;

// RGB 显示（带撕裂避免）
lv_display_t *lvgl_port_add_disp_rgb(const lvgl_port_display_rgb_cfg_t *disp_cfg);

// MIPI-DSI 显示
lv_display_t *lvgl_port_add_disp_dsi(const lvgl_port_display_dsi_cfg_t *disp_cfg);

// 移除显示
esp_err_t lvgl_port_remove_disp(lv_display_t *disp);
```

#### 输入设备添加

```c
lv_indev_t *lvgl_port_add_touch(const lvgl_port_touch_cfg_t *touch_cfg);
lv_indev_t *lvgl_port_add_navigation_buttons(const lvgl_port_nav_btns_cfg_t *btn_cfg);
lv_indev_t *lvgl_port_add_encoder(const lvgl_port_encoder_cfg_t *enc_cfg);
lv_indev_t *lvgl_port_add_usb_hid_mouse_input(const lvgl_port_usb_hid_mouse_cfg_t *mouse_cfg);
lv_indev_t *lvgl_port_add_usb_hid_keyboard_input(const lvgl_port_usb_hid_kb_cfg_t *kb_cfg);
```

#### 锁与同步

```c
bool lvgl_port_lock(uint32_t timeout_ms);   // timeout=0 无限等待
void lvgl_port_unlock(void);
esp_err_t lvgl_port_flush_ready(lv_display_t *disp);     // 手动触发刷新
esp_err_t lvgl_port_task_wake(lvgl_port_event_type_t event, void *param);
esp_err_t lvgl_port_stop(void);    // 休眠前停止定时器
esp_err_t lvgl_port_resume(void);  // 唤醒后恢复定时器
```

#### 内部回调桥接实现（核心）

```c
// 显示上下文（私有结构体，封装在 src/lvgl8/esp_lvgl_port_disp.c）
typedef struct {
    esp_lcd_panel_io_handle_t   io_handle;      // esp_lcd IO 句柄
    esp_lcd_panel_handle_t      panel_handle;   // esp_lcd 面板句柄
    esp_lcd_panel_handle_t      control_handle; // 控制句柄（旋转用）
    lv_disp_drv_t               disp_drv;       // LVGL 显示驱动
    SemaphoreHandle_t           trans_sem;      // 传输同步信号量
    uint8_t                    *trans_buf;      // DMA 中转缓冲区
} lvgl_port_display_ctx_t;

// flush_cb: LVGL → esp_lcd 的桥接
static void lvgl_port_flush_callback(lv_disp_drv_t *drv,
                                     const lv_area_t *area,
                                     lv_color_t *color_map)
{
    lvgl_port_display_ctx_t *disp_ctx = drv->user_data;
    if (disp_ctx->trans_buf == NULL) {
        // 直接传输：color_map 已经是 DMA 内存
        esp_lcd_panel_draw_bitmap(disp_ctx->panel_handle,
                                  area->x1, area->y1,
                                  area->x2 + 1, area->y2 + 1,
                                  color_map);
    } else {
        // 分块传输：从 PSRAM → SRAM DMA 缓冲区逐块发送
        for (/* each chunk */) {
            memcpy(disp_ctx->trans_buf, src, trans_size);
            esp_lcd_panel_draw_bitmap(..., disp_ctx->trans_buf);
            xSemaphoreTake(disp_ctx->trans_sem, portMAX_DELAY);
        }
    }
}

// on_color_trans_done: esp_lcd → LVGL 的反向通知
static bool lvgl_port_flush_io_ready_callback(
    esp_lcd_panel_io_handle_t panel_io,
    esp_lcd_panel_io_event_data_t *edata,
    void *user_ctx)
{
    lv_disp_drv_t *disp_drv = (lv_disp_drv_t *)user_ctx;
    lv_disp_flush_ready(disp_drv);  // 通知 LVGL 缓冲区可用

    lvgl_port_display_ctx_t *disp_ctx = disp_drv->user_data;
    if (disp_ctx->trans_sem) {
        xSemaphoreGiveFromISR(disp_ctx->trans_sem, NULL);  // 释放传输信号量
    }
    return false;
}

// 旋转同步: LVGL 旋转 → esp_lcd 硬件配置
static void lvgl_port_update_callback(lv_disp_drv_t *drv)
{
    lvgl_port_display_ctx_t *disp_ctx = drv->user_data;
    esp_lcd_panel_handle_t panel = disp_ctx->control_handle
                                   ? disp_ctx->control_handle
                                   : disp_ctx->panel_handle;
    switch (drv->rotated) {
        case LV_DISP_ROT_90:
            esp_lcd_panel_swap_xy(panel, true);
            esp_lcd_panel_mirror(panel, false, true);
            break;
        case LV_DISP_ROT_180:
            esp_lcd_panel_mirror(panel, true, true);
            break;
        case LV_DISP_ROT_270:
            esp_lcd_panel_swap_xy(panel, true);
            esp_lcd_panel_mirror(panel, true, false);
            break;
        default:
            esp_lcd_panel_swap_xy(panel, false);
            esp_lcd_panel_mirror(panel, false, false);
            break;
    }
}
```

### 形态C: 自制移植模式

当不使用任何官方组件时，直接在应用代码中手写桥接。

```c
// 1. 分配 LVGL 绘制缓冲区（DMA 内存）
lv_color_t *buf1 = heap_caps_malloc(LCD_H_RES * 20 * sizeof(lv_color_t),
                                     MALLOC_CAP_DMA);
lv_color_t *buf2 = heap_caps_malloc(LCD_H_RES * 20 * sizeof(lv_color_t),
                                     MALLOC_CAP_DMA);
lv_disp_draw_buf_init(&disp_buf, buf1, buf2, LCD_H_RES * 20);

// 2. 注册 LVGL 显示驱动
lv_disp_drv_init(&disp_drv);
disp_drv.flush_cb  = lvgl_flush_cb;          // 手写 flush 回调
disp_drv.draw_buf  = &disp_buf;
disp_drv.user_data = panel_handle;            // 桥接：持有 esp_lcd 句柄
lv_disp_drv_register(&disp_drv);

// 3. 手写 flush_cb：LVGL → esp_lcd
static void lvgl_flush_cb(lv_disp_drv_t *drv, const lv_area_t *area,
                          lv_color_t *color_map)
{
    esp_lcd_panel_handle_t panel = drv->user_data;
    esp_lcd_panel_draw_bitmap(panel,
                              area->x1, area->y1,
                              area->x2 + 1, area->y2 + 1,
                              color_map);
}

// 4. 在 SPI IO 配置中注册传输完成回调：esp_lcd → LVGL
esp_lcd_panel_io_spi_config_t io_config = {
    .on_color_trans_done = notify_lvgl_flush_ready,
    .user_ctx = &disp_drv,   // 持有 LVGL 驱动的引用
};

static bool notify_lvgl_flush_ready(esp_lcd_panel_io_handle_t io,
                                     esp_lcd_panel_io_event_data_t *edata,
                                     void *user_ctx)
{
    lv_disp_drv_t *disp_driver = (lv_disp_drv_t *)user_ctx;
    lv_disp_flush_ready(disp_driver);
    return false;
}

// 5. 创建 LVGL 任务 + 心跳
void lvgl_task(void *arg) {
    while (1) {
        lvgl_lock(portMAX_DELAY);
        lv_timer_handler();
        lvgl_unlock();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
```

## 1.5 层级3: ESP-IDF esp_lcd 驱动框架 — API

### 总线层（SPI）

```c
#include "esp_lcd_panel_io.h"

// 初始化 SPI 总线
spi_bus_config_t buscfg = {
    .sclk_io_num    = GPIO_NUM_18,
    .mosi_io_num    = GPIO_NUM_19,
    .miso_io_num    = GPIO_NUM_21,
    .max_transfer_sz = LCD_H_RES * 80 * sizeof(uint16_t),
};
spi_bus_initialize(LCD_HOST, &buscfg, SPI_DMA_CH_AUTO);

// 创建 SPI 面板 IO
esp_lcd_panel_io_spi_config_t io_config = {
    .dc_gpio_num   = GPIO_NUM_5,
    .cs_gpio_num   = GPIO_NUM_4,
    .pclk_hz       = 20 * 1000 * 1000,      // 20MHz
    .lcd_cmd_bits  = 8,
    .lcd_param_bits = 8,
    .spi_mode      = 0,
    .trans_queue_depth = 10,
    .on_color_trans_done = my_flush_notify_cb,  // 注册传输完成回调
    .user_ctx      = &disp_drv,                   // 传入 LVGL 驱动句柄
};
esp_lcd_panel_io_handle_t io_handle;
esp_lcd_new_panel_io_spi(LCD_HOST, &io_config, &io_handle);

// 控制命令传输
esp_lcd_panel_io_tx_param(io_handle, cmd, param_buf, param_len);
esp_lcd_panel_io_tx_color(io_handle, cmd, color_data, color_len);  // 异步颜色数据
```

### 总线层（I80 并行）

```c
#include "esp_lcd_panel_io.h"

esp_lcd_i80_bus_handle_t i80_bus;
esp_lcd_i80_bus_config_t bus_config = {
    .dc_gpio_num = GPIO_NUM_7,
    .wr_gpio_num = GPIO_NUM_8,
    .data_gpio_nums = {GPIO_NUM_1, GPIO_NUM_2, ...},
    .bus_width = 8,
    .max_transfer_bytes = LCD_H_RES * 100 * sizeof(uint16_t),
    .dma_burst_size = 64,
};
esp_lcd_new_i80_bus(&bus_config, &i80_bus);

esp_lcd_panel_io_i80_config_t io_config = {
    .cs_gpio_num     = GPIO_NUM_6,
    .pclk_hz         = EXAMPLE_LCD_PIXEL_CLOCK_HZ,
    .trans_queue_depth = 10,
    .lcd_cmd_bits    = 8,
    .lcd_param_bits  = 8,
    .dc_levels = { .dc_idle_level = 0, .dc_cmd_level = 0,
                   .dc_dummy_level = 0, .dc_data_level = 1 },
};
esp_lcd_panel_io_handle_t io_handle;
esp_lcd_new_panel_io_i80(i80_bus, &io_config, &io_handle);
```

### 面板操作层

```c
#include "esp_lcd_panel_ops.h"

// 生命周期
esp_lcd_panel_reset(panel_handle);
esp_lcd_panel_init(panel_handle);
esp_lcd_panel_disp_on_off(panel_handle, true);
esp_lcd_panel_disp_sleep(panel_handle, false);

// 核心刷新函数（由 Adapter/Port 层的 flush_cb 调用）
// 坐标参数为右开区间 [x1, x2), [y1, y2)
esp_lcd_panel_draw_bitmap(panel_handle, x1, y1, x2, y2, color_map);

// 硬件旋转（由 update_callback 调用）
esp_lcd_panel_swap_xy(panel_handle, true/false);
esp_lcd_panel_mirror(panel_handle, mirror_x, mirror_y);

// 配置
esp_lcd_panel_set_gap(panel_handle, x_gap, y_gap);
esp_lcd_panel_invert_color(panel_handle, true/false);
esp_lcd_panel_set_brightness(panel_handle, brightness);
```

### 厂商面板驱动

```c
#include "esp_lcd_panel_vendor.h"

esp_lcd_panel_handle_t panel_handle;
esp_lcd_panel_dev_config_t panel_config = {
    .reset_gpio_num  = GPIO_NUM_3,
    .rgb_ele_order   = LCD_RGB_ELEMENT_ORDER_RGB,
    .bits_per_pixel  = 16,
};

esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle);  // ST7789
esp_lcd_new_panel_nt35510(io_handle, &panel_config, &panel_handle); // NT35510
// ILI9341 复用 ST7789 驱动 + 自定义伽马表
esp_lcd_panel_io_tx_param(io_handle, 0xE0, gamma_pos, 15);
esp_lcd_panel_io_tx_param(io_handle, 0xE1, gamma_neg, 15);
```

### 触摸驱动

```c
#include "esp_lcd_touch.h"

esp_lcd_touch_handle_t tp;
esp_lcd_touch_config_t tp_cfg = {
    .x_max = 240, .y_max = 320,
    .rst_gpio_num = GPIO_NUM_NC,
    .int_gpio_num = GPIO_NUM_NC,
};
esp_lcd_touch_new_spi_stmpe610(tp_io_handle, &tp_cfg, &tp);
// 或 esp_lcd_touch_new_spi_xpt2046(...)

// 在 read_cb 中调用
esp_lcd_touch_read_data(tp);
uint16_t touch_x, touch_y;
uint8_t touch_point_cnt;
esp_lcd_touch_get_coordinates(tp, &touch_x, &touch_y, &touch_point_cnt);
```

## 1.6 各层之间传递的数据

### 正向路径：LVGL 渲染 → LCD 显示

```
LVGL 核心                    Adapter/Port 层               esp_lcd 层
────────                    ──────────────               ──────────
lv_timer_handler()
  → flush_cb(drv, area, color_map)
                            adapter_flush_callback()
                              ├─ drv->user_data → disp_ctx
                              ├─ disp_ctx->panel_handle
                              └─ esp_lcd_panel_draw_bitmap(
                                   panel_handle,
                                   area->x1,      → x1
                                   area->y1,      → y1
                                   area->x2 + 1,  → x2 (右开)
                                   area->y2 + 1,  → y2 (右开)
                                   color_map)     → RGB565 像素
```

| 传递内容 | 来源 API | 去向 API | 数据类型 |
|---------|----------|---------|---------|
| 面板句柄 | 初始化时用户传入 | `esp_lcd_panel_draw_bitmap` | `esp_lcd_panel_handle_t` |
| 刷新矩形 | LVGL `lv_area_t` | 坐标转换（+1 转右开） | `{x1,y1,x2+1,y2+1}` |
| 像素数据 | `lv_color_t*` buffer | 原样传递 | 内存地址指针 |

### 反向路径：DMA 完成 → LVGL 就绪

```
esp_lcd 层                    Adapter/Port 层               LVGL 核心
─────────                    ──────────────               ──────────
SPI DMA 传输完成中断
  → on_color_trans_done(user_ctx)
                            flush_io_ready_callback()
                              ├─ user_ctx → disp_drv
                              ├─ lv_disp_flush_ready(disp_drv)
                              └─ xSemaphoreGiveFromISR(trans_sem)
                                                            lv_disp_flush_ready()
                                                              → 缓冲区可重用
                                                              → 触发下一帧
```

| 传递内容 | 来源 API | 去向 API | 数据类型 |
|---------|----------|---------|---------|
| LVGL 驱动句柄 | `io_config.user_ctx = &disp_drv` | `lv_disp_flush_ready()` | `lv_disp_drv_t*` |
| 传输信号量 | 初始化时创建 | `xSemaphoreGiveFromISR` | `SemaphoreHandle_t` |

### 双向指针交换（核心桥接模式）

```
初始化时建立两个方向的指针持有关系:

┌──── LVGL 侧 ──────────────────────────────────────────────┐
│  lv_disp_drv_t.user_data = panel_handle                   │
│  → 当 LVGL 调用 flush_cb 时, Adapter 层可以从 drv 取出     │
│    panel_handle, 调用 esp_lcd_panel_draw_bitmap()          │
└───────────────────────────────────────────────────────────┘

┌──── esp_lcd 侧 ───────────────────────────────────────────┐
│  io_config.user_ctx = &disp_drv                           │
│  → 当 SPI DMA 传输完成时, on_color_trans_done 回调可以     │
│    取出 disp_drv, 调用 lv_disp_flush_ready() 通知 LVGL    │
└───────────────────────────────────────────────────────────┘

两个方向:
  LVGL → flush_cb → Adapter → drv->user_data → panel_handle → esp_lcd API
  esp_lcd 传输完 → on_color_trans_done → user_ctx → disp_drv → lv_disp_flush_ready
```

## 1.7 组件对比一览

| 对比维度 | `esp_lvgl_adapter` | `esp_lvgl_port` | 自制移植 |
|---------|-------------------|----------------|---------|
| 推出时间 | 较新（v0.6.0） | 较早 | — |
| 来源 | 组件注册中心 | esp-bsp 仓库 | 用户代码 |
| 最低 IDF | ≥ 5.5 | 无严格限制 | 任意 |
| 命名前缀 | `esp_lv_adapter_*` | `lvgl_port_*` | 自定义 |
| 接口类型 | 统一宏 + 默认配置 | 分 `add_disp/add_disp_rgb/add_disp_dsi` | 手动写 |
| 撕裂避免 | 内置（RGB/DSI 专用） | 无内置 | 无 |
| FS/Decoder/FreeType | 内置 Kconfig 可选模块 | 无 | 无 |
| 旋转处理 | 按接口类型区分策略 | drv_update_cb | 手写 |
| 电源管理 | PAUSE/USER 自动模式 | stop/resume 手动 | 手写 |
| 三缓冲支持 | 内置（`get_required_fb_count`） | 无 | 手写 |
| 代码复杂度 | 低（配置宏化） | 中 | 高 |

## 1.8 调用时序总结

```
app_main()
├── spi_bus_initialize(LCD_HOST, ...)              ─ 层级3: SPI 总线
├── esp_lcd_new_panel_io_spi(...)                  ─ 层级3: 创建 IO
├── esp_lcd_new_panel_st7789(...)                  ─ 层级3: 创建面板
├── esp_lcd_panel_reset/init/disp_on(...)           ─ 层级3: 初始化 LCD
│
├── esp_lv_adapter_init(&cfg)                      ─ 层级2: 初始化适配层
├── esp_lv_adapter_register_display(&disp_cfg)     ─ 层级2: 注册显示
│   ├── 内部 lv_display_create()                  ─ 层级1: 创建 LVGL 显示对象
│   ├── 内部 lv_display_set_flush_cb(adapter_cb)  ─ 层级1: 注册 flush 回调
│   ├── 内部 lv_display_set_user_data(panel)       ─ 层级1: 桥接句柄
│   └── 内部 esp_lcd_panel_io_register_callbacks(  ─ 层级3: 注册完成回调
│         .on_color_trans_done = adapter_cb)
│
├── esp_lv_adapter_register_touch(...)             ─ 层级2: 注册触摸
├── esp_lv_adapter_start()                          ─ 层级2: 启动 LVGL 任务
│
└── esp_lv_adapter_lock/unlock
    └── ui_init() (用户 UI)                         ─ 应用层

LVGL 任务循环:
├── esp_lv_adapter_lock(-1)                         ─ 层级2: 获取锁
├── lv_timer_handler()                              ─ 层级1: LVGL 渲染
│   └── → flush_cb → esp_lcd_panel_draw_bitmap()
├── esp_lv_adapter_unlock()                         ─ 层级2: 释放锁
└── vTaskDelay()
```

---

# 2. IDF Button 组件

## 2.1 概述

`button` 组件来自 `esp-iot-solution`，提供统一的按键检测框架，支持 **GPIO 按键**、**ADC 按键**和**矩阵键盘**三种硬件类型。内置消抖、长按/短按/连击等事件检测，可通过回调或轮询获取事件。

## 2.2 硬件类型

| 类型 | 优点 | 缺点 |
|------|------|------|
| GPIO 按键 | 独立 IO，稳定性高 | 占用引脚多 |
| ADC 按键 | 多键共享一个 ADC 通道，省 IO | 不支持同时按键，氧化后不稳定 |
| 矩阵键盘 | 大量按键只需 row+col 个 IO | 需要扫描，有鬼键问题 |

> [!warning] GPIO 注意
> input-only GPIO（如 ESP32-S3 的 GPIO44-47）**没有内部上下拉**，需要外部接电阻。

## 2.3 事件类型

共 11 种事件（`button_event_t`）：

| 事件 | 触发条件 |
|------|----------|
| `BUTTON_PRESS_DOWN` | 按下瞬间 |
| `BUTTON_PRESS_UP` | 松开瞬间 |
| `BUTTON_PRESS_REPEAT` | 按下期间检测到 ≥2 次按压 |
| `BUTTON_PRESS_REPEAT_DONE` | 连击周期结束 |
| `BUTTON_SINGLE_CLICK` | 一次完整的按下-松开 |
| `BUTTON_DOUBLE_CLICK` | 两次连击 |
| `BUTTON_MULTIPLE_CLICK` | N 次连击（通过参数指定次数） |
| `BUTTON_LONG_PRESS_START` | 长按达到阈值时刻 |
| `BUTTON_LONG_PRESS_HOLD` | 长按期间持续触发 |
| `BUTTON_LONG_PRESS_UP` | 长按后松开 |
| `BUTTON_PRESS_END` | 检测周期结束 |

## 2.4 使用模式

### 回调模式（推荐）

为每个事件注册回调，事件触发时自动调用。**回调中不能有 `vTaskDelay` 等阻塞操作**。

```c
iot_button_register_cb(btn, BUTTON_SINGLE_CLICK, NULL, on_click, NULL);
```

### 轮询模式

周期调用 `iot_button_get_event()`，简单但可能漏事件。

```c
button_event_t event = iot_button_get_event(btn);
if (event != BUTTON_NONE_PRESS) {
    ESP_LOGI(TAG, "事件: %s", iot_button_get_event_str(event));
}
```

## 2.5 快速上手

### 创建按键

**GPIO 按键：**

```c
#include "iot_button.h"

const button_config_t btn_cfg = {0};
const button_gpio_config_t gpio_cfg = {
    .gpio_num     = 0,       // GPIO 编号
    .active_level = 0,       // 低电平有效（按下接地）
};

button_handle_t btn = NULL;
iot_button_new_gpio_device(&btn_cfg, &gpio_cfg, &btn);
```

**ADC 按键：**

```c
const button_adc_config_t adc_cfg = {
    .unit_id      = ADC_UNIT_1,
    .adc_channel  = 0,
    .button_index = 0,   // 同一 ADC 通道上的第几个按键
    .min          = 100, // ADC 最小值（对应按下）
    .max          = 400, // ADC 最大值
};

button_handle_t adc_btn = NULL;
iot_button_new_adc_device(&btn_cfg, &adc_cfg, &adc_btn);
```

**矩阵键盘：**

```c
const button_matrix_config_t matrix_cfg = {
    .row_gpios    = (int32_t[]){4, 5, 6, 7},
    .col_gpios    = (int32_t[]){3, 8, 16, 15},
    .row_gpio_num = 4,
    .col_gpio_num = 4,
};

button_handle_t matrix_btn = NULL;
iot_button_new_matrix_device(&btn_cfg, &matrix_cfg, btns, &matrix_btn);
```

### 注册事件回调

```c
static void on_single_click(void *arg, void *usr_data)
{
    ESP_LOGI(TAG, "单击!");
}

static void on_double_click(void *arg, void *usr_data)
{
    ESP_LOGI(TAG, "双击!");
}

static void on_long_press(void *arg, void *usr_data)
{
    ESP_LOGI(TAG, "长按! 持续时间: %"PRIu32" ms",
             iot_button_get_pressed_time(arg));
}

void button_init(void)
{
    // 基本回调：event_args 传 NULL 使用默认阈值
    iot_button_register_cb(btn, BUTTON_SINGLE_CLICK, NULL, on_single_click, NULL);
    iot_button_register_cb(btn, BUTTON_DOUBLE_CLICK, NULL, on_double_click, NULL);

    // 自定义长按阈值：通过 button_event_args_t 设置
    button_event_args_t args = { .long_press.press_time = 2000 };
    iot_button_register_cb(btn, BUTTON_LONG_PRESS_START, &args, on_long_press, NULL);
}
```

> [!tip] 万能回调模板
> 来自 [gpio_button_test.c](https://github.com/espressif/esp-iot-solution/blob/5f9cb98ae4d0e8153c4b4d1accf471214e5b6fe8/components/button/test_apps/main/gpio_button_test.c)，一个回调处理所有事件：
> ```c
> static void button_event_cb(void *arg, void *data)
> {
>     button_event_t event = iot_button_get_event(arg);
>     ESP_LOGI(TAG, "%s", iot_button_get_event_str(event));
>     if (event == BUTTON_PRESS_REPEAT || event == BUTTON_PRESS_REPEAT_DONE) {
>         ESP_LOGI(TAG, "\tREPEAT[%d]", iot_button_get_repeat(arg));
>     }
>     if (event == BUTTON_PRESS_UP || event == BUTTON_LONG_PRESS_HOLD ||
>         event == BUTTON_LONG_PRESS_UP) {
>         ESP_LOGI(TAG, "\tPressed Time[%"PRIu32"]", iot_button_get_pressed_time(arg));
>     }
>     if (event == BUTTON_MULTIPLE_CLICK) {
>         ESP_LOGI(TAG, "\tMULTIPLE[%d]", (int)data);
>     }
> }
> ```

## 2.6 参数配置

### `button_event_args_t` 联合体

用于为特定事件传递参数，是一个 union：

```c
typedef union {
    struct {
        uint16_t press_time;   // 长按阈值 ms（LONG_PRESS_START / LONG_PRESS_UP）
    } long_press;
    struct {
        uint16_t clicks;       // 连击次数（MULTIPLE_CLICK）
    } multiple_clicks;
} button_event_args_t;
```

### 长按阈值

**方式 1：全局默认值** — `iot_button_set_param()` 修改默认长按时间：

```c
// value 为 void* 类型，传入数值需强转
iot_button_set_param(btn, BUTTON_LONG_PRESS_TIME_MS, (void *)1500);
```

**方式 2：单回调独立配置** — 通过 `button_event_args_t` 为每个回调设置独立阈值：

```c
// 2 秒触发回调 1
button_event_args_t args1 = { .long_press.press_time = 2000 };
iot_button_register_cb(btn, BUTTON_LONG_PRESS_START, &args1, on_press_2s, NULL);

// 5 秒触发回调 2
button_event_args_t args2 = { .long_press.press_time = 5000 };
iot_button_register_cb(btn, BUTTON_LONG_PRESS_START, &args2, on_press_5s, NULL);
```

> [!tip] 容差
> 实际触发时间有约 `CONFIG_BUTTON_PERIOD_TIME_MS × 4` 的容差。例如扫描周期 10ms，容差约 40ms。

### 连击次数

通过 `button_event_args_t.multiple_clicks.clicks` 指定：

```c
// 双击
button_event_args_t dbl = { .multiple_clicks.clicks = 2 };
iot_button_register_cb(btn, BUTTON_MULTIPLE_CLICK, &dbl, on_double, (void *)2);

// 三击
button_event_args_t tri = { .multiple_clicks.clicks = 3 };
iot_button_register_cb(btn, BUTTON_MULTIPLE_CLICK, &tri, on_triple, (void *)3);
```

> [!warning] MULTIPLE_CLICK 必须提供 event_args
> `event_args` 参数**不能为 NULL**，否则行为未定义。

### 可修改的参数汇总

通过 `iot_button_set_param(btn, param, value)` 修改：

| `button_param_t` | 说明 |
|-------------------|------|
| `BUTTON_LONG_PRESS_TIME_MS` | 长按阈值（ms） |
| `BUTTON_SHORT_PRESS_TIME_MS` | 短按有效窗口（ms） |

### 查询按键状态

```c
iot_button_get_key_level(btn);              // 1=按下, 0=松开
iot_button_get_repeat(btn);                 // 连击次数（双击→2, 三击→3）
iot_button_get_pressed_time(btn);           // 按下持续时间 ms
iot_button_get_long_press_hold_cnt(btn);    // HOLD 回调触发次数
```

### 启停控制

```c
iot_button_stop();      // 停止按键检测定时器
iot_button_resume();    // 恢复按键检测定时器
iot_button_delete(btn); // 删除按键实例
```

## 2.7 低功耗模式

配合 Light Sleep 使用，所有按键必须是 **GPIO 类型** 且 `enable_power_save = true`。

### 配置

```c
const button_gpio_config_t gpio_cfg = {
    .gpio_num          = 0,
    .active_level      = 0,
    .enable_power_save = true,    // 关键
};
iot_button_new_gpio_device(&btn_cfg, &gpio_cfg, &btn);
```

### 进入 Light Sleep

**方式 1：自动** — 组件自动禁用 `esp_timer`，系统进入 Light Sleep。

**方式 2：手动** — 注册省电回调，在回调中进入：

```c
void btn_enter_power_save(void *usr_data)
{
    ESP_LOGI(TAG, "可以进入低功耗");
    // esp_light_sleep_start();
}

button_power_save_config_t config = {
    .enter_power_save_cb = btn_enter_power_save,
};
iot_button_register_power_save_cb(&config);
```

### GPIO 唤醒源

| GPIO 类型 | `POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP` | 唤醒源 |
|-----------|----------------------------------------|--------|
| 普通数字 GPIO | 未开启 | GPIO 电平触发 |
| 普通数字 GPIO | 已开启 | 无 |
| RTC/LP GPIO | 未开启 | GPIO 电平触发 / EXT1 |
| RTC/LP GPIO | 已开启 | EXT1 |

> [!note] ESP32-C5/C6
> LP GPIO 同时支持 GPIO 电平唤醒和 EXT1 唤醒，且需额外调用 `gpio_hold_en()`。

## 2.8 配置宏

在 `menuconfig` / `sdkconfig` 中可调整：

| 宏 | 作用 |
|----|------|
| `BUTTON_PERIOD_TIME_MS` | 扫描周期 |
| `BUTTON_DEBOUNCE_TICKS` | 消抖计数 |
| `BUTTON_SHORT_PRESS_TIME_MS` | 短按有效窗口 |
| `BUTTON_LONG_PRESS_TIME_MS` | 长按阈值 |
| `BUTTON_LONG_PRESS_HOLD_SERIAL_TIME_MS` | HOLD 回调间隔 |
| `ADC_BUTTON_MAX_CHANNEL` | ADC 按键最大通道数 |
| `ADC_BUTTON_MAX_BUTTON_PER_CHANNEL` | 每通道最大按键数 |
| `ADC_BUTTON_SAMPLE_TIMES` | ADC 每次扫描采样次数 |

## 2.9 API 速查

| 函数 | 说明 |
|------|------|
| `iot_button_new_gpio_device()` | 创建 GPIO 按键 |
| `iot_button_new_adc_device()` | 创建 ADC 按键 |
| `iot_button_new_matrix_device()` | 创建矩阵键盘按键 |
| `iot_button_delete()` | 删除按键 |
| `iot_button_register_cb()` | 注册事件回调 |
| `iot_button_unregister_cb()` | 注销事件回调 |
| `iot_button_get_event()` | 轮询获取当前事件 |
| `iot_button_get_event_str()` | 事件枚举转字符串 |
| `iot_button_print_event()` | 打印当前事件日志 |
| `iot_button_get_key_level()` | 读取原始按键电平 |
| `iot_button_get_repeat()` | 获取连击次数 |
| `iot_button_get_pressed_time()` | 获取按下持续时间 |
| `iot_button_get_long_press_hold_cnt()` | 获取 HOLD 回调计数 |
| `iot_button_set_param()` | 运行时修改参数 |
| `iot_button_stop()` | 停止检测 |
| `iot_button_resume()` | 恢复检测 |
| `iot_button_register_power_save_cb()` | 注册省电回调 |
| `iot_button_count_cb()` | 统计已注册回调总数 |
| `iot_button_count_event_cb()` | 统计某事件的回调数 |

---

## 参考

**LVGL：**
- [esp_lvgl_adapter 组件注册页 (v0.6.0)](https://components.espressif.com/components/espressif/esp_lvgl_adapter/versions/0.6.0/readme?language=zh)
- [ESP-IDF LCD 驱动框架文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html)
- [esp_lvgl_port 组件 (ESP-BSP 仓库)](https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port)
- [SPI LCD + Touch + LVGL 示例](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/lcd/spi_lcd_touch)
- [LVGL 官方文档](https://docs.lvgl.io/)

**Button：**
- [官方文档](https://docs.espressif.com/projects/esp-iot-solution/zh_CN/latest/input_device/button.html)
- [源码仓库](https://github.com/espressif/esp-iot-solution/tree/master/components/button)
- [iot_button.h 完整头文件](https://github.com/espressif/esp-iot-solution/blob/5f9cb98ae4d0e8153c4b4d1accf471214e5b6fe8/components/button/include/iot_button.h)

## 相关笔记

- [[02-ESP-IDF-核心外设速查]] — GPIO、低功耗（RTC GPIO 唤醒）
- [[lvgl_note/LVGL-显示原理]]、[[lvgl_note/lvgl_config]] — LVGL 基础笔记
- [[架构/嵌入式设计模式-事件总线]] — 按键事件分发可参考
