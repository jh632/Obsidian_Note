---
date: 2026-06-29
tags: [esp-idf, lvgl, esp-lcd, gui, display-driver]
aliases: [LVGL-ESP-IDF-porting, LVGL移植, esp_lvgl_adapter]
---

# LVGL 在 ESP-IDF 中的适配分层

## 概述

ESP-IDF 中 LVGL 的适配分为三层：**LVGL 核心库**（图形渲染引擎）→ **Adapter/Port 层**（桥接适配）→ **esp_lcd 驱动框架**（硬件驱动）。三层之间通过**回调函数**和**句柄指针交换**实现双向通信。

Adapter 层有两个官方组件，按推出时间排列：
- **[`esp_lvgl_adapter`]**（较新，推荐）— 统一适配层，内置撕裂避免、FS/Decoder/FreeType 模块，要求 IDF ≥ 5.5
- **[`esp_lvgl_port`]**（较早）— 位于 esp-bsp 仓库，较简单，广泛用于早期项目

此外还有**自制移植模式**，直接手写回调桥接。

---

## 三层架构总览

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

---

## 层级1: LVGL 核心库 — API

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

---

## 层级2: Adapter / Port 层 — API

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

// 注册
lv_display_t *disp = esp_lv_adapter_register_display(&disp_cfg);

// 注销
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

#### 旋钮/编码器与按键

Kconfig 使能后：
```c
// Kconfig: ESP_LV_ADAPTER_ENABLE_KNOB / ESP_LV_ADAPTER_ENABLE_BUTTON
// API 见 esp_lv_adapter_input.h
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

---

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

#### 内部回调桥接实现

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

---

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

---

## 层级3: ESP-IDF esp_lcd 驱动框架 — API

### 总线层

#### SPI 总线

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

#### I80 并行总线

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
esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle);
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

---

## 各层之间传递的数据

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

---

## 组件对比一览

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

---

## 调用时序总结

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

## 参考

- [esp_lvgl_adapter 组件注册页 (v0.6.0)](https://components.espressif.com/components/espressif/esp_lvgl_adapter/versions/0.6.0/readme?language=zh)
- [ESP-IDF LCD 驱动框架文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html)
- [esp_lvgl_port 组件 (ESP-BSP 仓库)](https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port)
- [esp_lvgl_port.h API 头文件](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/include/esp_lvgl_port.h)
- [SPI LCD + Touch + LVGL 示例](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/lcd/spi_lcd_touch)
- [I80 并行 LCD + LVGL 示例](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/lcd/i80_controller)
- [LVGL 官方文档](https://docs.lvgl.io/)

## 相关笔记

- [[idf button组件]]
- [[ESP32-GPIO-速查表]]

---

## 三层架构总览

```
┌────────────────────────────────────────────────────────────┐
│  层级1: LVGL 核心库 (lvgl/lvgl)                             │
│  职责: 图形渲染、UI 对象管理、动画、输入事件分发               │
│  核心文件: src/hal/lv_hal_disp.h, src/hal/lv_hal_indev.h   │
└──────────────────────┬─────────────────────────────────────┘
                       │ flush_cb / read_cb 回调
                       ▼
┌────────────────────────────────────────────────────────────┐
│  层级2: Port / Adapter 层 (esp_lvgl_port)                   │
│  职责: 桥接 LVGL ↔ esp_lcd, 任务调度, 互斥保护, 旋转同步     │
│  核心文件:                                                 │
│    include/esp_lvgl_port.h  (主 API)                        │
│    include/esp_lvgl_port_disp.h  (显示适配 API)              │
│    include/esp_lvgl_port_touch.h  (触摸适配 API)             │
│    src/lvgl8/esp_lvgl_port_disp.c  (显示桥接实现)             │
│    src/lvgl8/esp_lvgl_port_touch.c  (触摸桥接实现)            │
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

---

## 层级1: LVGL 核心库 — API

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

---

## 层级2: Port / Adapter 层 — API

这一层有两种形态：**官方 `esp_lvgl_port` 组件** 和 **自制移植（手写回调）**。

### 形态A: 官方 `esp_lvgl_port` 组件

来源: `https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port`

#### 初始化和反初始化

```c
#include "esp_lvgl_port.h"

// 配置 LVGL 任务参数
const lvgl_port_cfg_t lvgl_cfg = ESP_LVGL_PORT_INIT_CONFIG();
// 默认值: priority=4, stack=7168, affinity=-1,
//         max_sleep=500ms, timer_period=5ms

// 初始化：创建 LVGL 任务 + 心跳定时器
esp_err_t lvgl_port_init(const lvgl_port_cfg_t *cfg);

// 反初始化：停止任务和定时器
esp_err_t lvgl_port_deinit(void);
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
    esp_lcd_panel_handle_t       control_handle;  // 分离控制句柄（可选）
    uint32_t                     buffer_size;     // 缓冲区大小（像素数）
    bool                         double_buffer;   // 是否双缓冲
    uint32_t                     trans_size;      // DMA 中转缓冲区大小（可选，PSRAM 场景）
    uint32_t                     hres;            // 水平分辨率
    uint32_t                     vres;            // 垂直分辨率
    bool                         monochrome;      // 是否单色
    lvgl_port_rotation_cfg_t     rotation;        // 默认旋转配置
    struct {
        bool buff_dma;       // LVGL 缓冲区使用 DMA 内存
        bool buff_spiram;    // LVGL 缓冲区使用 PSRAM
        bool sw_rotate;      // 使用软件旋转
        bool full_refresh;   // 全屏刷新
        bool direct_mode;    // 全尺寸缓冲区直接模式
        bool swap_bytes;     // RGB565 字节交换（LVGL9+）
    } flags;
} lvgl_port_display_cfg_t;

// RGB 显示接入（带撕裂避免）
lv_display_t *lvgl_port_add_disp_rgb(const lvgl_port_display_rgb_cfg_t *disp_cfg);

// MIPI-DSI 显示接入
lv_display_t *lvgl_port_add_disp_dsi(const lvgl_port_display_dsi_cfg_t *disp_cfg);

// 移除显示
esp_err_t lvgl_port_remove_disp(lv_display_t *disp);
```

#### 输入设备添加

```c
// 触摸屏接入（依赖 esp_lcd_touch 组件）
lv_indev_t *lvgl_port_add_touch(const lvgl_port_touch_cfg_t *touch_cfg);

// 导航按键接入（prev/next/enter，依赖 button 组件）
lv_indev_t *lvgl_port_add_navigation_buttons(const lvgl_port_nav_btns_cfg_t *btn_cfg);

// 旋转编码器接入（依赖 knob 组件）
lv_indev_t *lvgl_port_add_encoder(const lvgl_port_encoder_cfg_t *enc_cfg);

// USB HID 鼠标接入
lv_indev_t *lvgl_port_add_usb_hid_mouse_input(const lvgl_port_usb_hid_mouse_cfg_t *mouse_cfg);

// USB HID 键盘接入
lv_indev_t *lvgl_port_add_usb_hid_keyboard_input(const lvgl_port_usb_hid_kb_cfg_t *kb_cfg);
```

#### 锁与同步

```c
// 所有 LVGL API 调用必须包裹在锁中
bool lvgl_port_lock(uint32_t timeout_ms);   // timeout=0 表示无限等待
void lvgl_port_unlock(void);

// 手动触发刷新（唤醒 LVGL 任务）
esp_err_t lvgl_port_flush_ready(lv_display_t *disp);

// 唤醒 LVGL 任务（外部事件通知）
esp_err_t lvgl_port_task_wake(lvgl_port_event_type_t event, void *param);

// 电源管理
esp_err_t lvgl_port_stop(void);    // 停止定时器（休眠前）
esp_err_t lvgl_port_resume(void);  // 恢复定时器（唤醒后）
```

#### 官方 Port 层的内部回调实现

这是关键桥接代码，封装在 `src/lvgl8/esp_lvgl_port_disp.c` 中：

```c
// 内部显示上下文
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
        // 直接传输：color_map 是 DMA 内存
        esp_lcd_panel_draw_bitmap(disp_ctx->panel_handle,
                                  area->x1, area->y1,
                                  area->x2 + 1, area->y2 + 1,
                                  color_map);
    } else {
        // 分块传输：从 PSRAM 拷贝到 SRAM DMA 缓冲区逐块发送
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
        default: // LV_DISP_ROT_0
            esp_lcd_panel_swap_xy(panel, false);
            esp_lcd_panel_mirror(panel, false, false);
            break;
    }
}
```

### 形态B: 自制移植模式

当不使用官方 `esp_lvgl_port` 组件时，直接在应用代码中手写桥接。常见于早期 ESP-IDF 版本或小型项目。

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

// 5. 创建 LVGL 任务
void lvgl_task(void *arg) {
    while (1) {
        lvgl_lock(portMAX_DELAY);
        lv_timer_handler();
        lvgl_unlock();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
```

---

## 层级3: ESP-IDF esp_lcd 驱动框架 — API

### 总线层

#### SPI 总线

```c
#include "esp_lcd_panel_io.h"

// 初始化 SPI 总线
spi_bus_config_t buscfg = {
    .sclk_io_num   = GPIO_NUM_18,
    .mosi_io_num   = GPIO_NUM_19,
    .miso_io_num   = GPIO_NUM_21,
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
    .on_color_trans_done = my_flush_notify_cb,  // ← 注册传输完成回调
    .user_ctx      = &disp_drv,                   // ← 传入 LVGL 驱动句柄
};
esp_lcd_panel_io_handle_t io_handle;
esp_lcd_new_panel_io_spi(LCD_HOST, &io_config, &io_handle);

// 控制命令传输
esp_lcd_panel_io_tx_param(io_handle, cmd, param_buf, param_len);
esp_lcd_panel_io_tx_color(io_handle, cmd, color_data, color_len);  // 颜色数据（异步）
```

#### I80 并行总线

```c
#include "esp_lcd_panel_io.h"

// 初始化 I80 总线
esp_lcd_i80_bus_handle_t i80_bus;
esp_lcd_i80_bus_config_t bus_config = {
    .dc_gpio_num = GPIO_NUM_7,
    .wr_gpio_num = GPIO_NUM_8,
    .data_gpio_nums = {GPIO_NUM_1, GPIO_NUM_2, ...},  // 8 或 16 个数据引脚
    .bus_width = 8,
    .max_transfer_bytes = LCD_H_RES * 100 * sizeof(uint16_t),
    .dma_burst_size = 64,
};
esp_lcd_new_i80_bus(&bus_config, &i80_bus);

// 创建 I80 面板 IO
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
esp_lcd_panel_reset(panel_handle);          // 硬件复位
esp_lcd_panel_init(panel_handle);           // LCD 初始化序列
esp_lcd_panel_disp_on_off(panel_handle, true);  // 开启显示
esp_lcd_panel_disp_sleep(panel_handle, false);  // 退出休眠

// 核心刷新函数（由 Port 层的 flush_cb 调用）
// 注意：坐标参数为右开区间 [x1, x2), [y1, y2)
esp_lcd_panel_draw_bitmap(panel_handle,
                          x1, y1, x2, y2,  // 刷新矩形
                          color_map);       // RGB565 像素数据

// 硬件旋转（由 Port 层的 update_callback 调用）
esp_lcd_panel_swap_xy(panel_handle, true/false);   // X/Y 交换
esp_lcd_panel_mirror(panel_handle, mirror_x, mirror_y);  // 镜像翻转

// 配置
esp_lcd_panel_set_gap(panel_handle, x_gap, y_gap);        // 边框偏移
esp_lcd_panel_invert_color(panel_handle, true/false);     // 颜色取反
esp_lcd_panel_set_brightness(panel_handle, brightness);    // 亮度（若支持）
```

### 厂商面板驱动

```c
#include "esp_lcd_panel_vendor.h"

esp_lcd_panel_handle_t panel_handle;
esp_lcd_panel_dev_config_t panel_config = {
    .reset_gpio_num  = GPIO_NUM_3,
    .rgb_ele_order   = LCD_RGB_ELEMENT_ORDER_RGB,  // 或 BGR
    .bits_per_pixel  = 16,
};

// ST7789（常见 SPI 小屏）
esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle);

// NT35510
esp_lcd_new_panel_nt35510(io_handle, &panel_config, &panel_handle);

// ILI9341（复用 ST7789 驱动）
esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle);
// 然后通过 tx_param 发自定义伽马表
esp_lcd_panel_io_tx_param(io_handle, 0xE0, gamma_pos, 15);
esp_lcd_panel_io_tx_param(io_handle, 0xE1, gamma_neg, 15);
```

### 触摸驱动

```c
#include "esp_lcd_touch.h"

// 初始化触摸控制器
esp_lcd_touch_handle_t tp;
esp_lcd_touch_config_t tp_cfg = {
    .x_max = 240, .y_max = 320,
    .rst_gpio_num = GPIO_NUM_NC,
    .int_gpio_num = GPIO_NUM_NC,
};
esp_lcd_touch_new_spi_stmpe610(tp_io_handle, &tp_cfg, &tp);
// 或 esp_lcd_touch_new_spi_xpt2046(...)

// 读取触摸数据（在 read_cb 中调用）
esp_lcd_touch_read_data(tp);
uint16_t touch_x, touch_y;
uint8_t touch_point_cnt;
esp_lcd_touch_get_coordinates(tp, &touch_x, &touch_y, &touch_point_cnt);
```

---

## 各层之间传递的数据

### 正向路径：LVGL 渲染 → LCD 显示

```
LVGL 核心                    Port 层                       esp_lcd 层
────────                    ──────                       ──────────
lv_timer_handler()
  → flush_cb(drv, area, color_map)
                            lvgl_port_flush_callback()
                              ├─ 从 drv->user_data 取出 disp_ctx
                              ├─ 从 disp_ctx->panel_handle 取出面板句柄
                              └─ esp_lcd_panel_draw_bitmap(
                                   panel_handle,
                                   area->x1,      → x1
                                   area->y1,      → y1
                                   area->x2 + 1,  → x2 (右开)
                                   area->y2 + 1,  → y2 (右开)
                                   color_map)     → RGB565 像素数据
```

| 传递内容 | 来源 API | 去向 API | 数据类型 |
|---------|----------|---------|---------|
| 面板句柄 | 初始化时用户传入 | `esp_lcd_panel_draw_bitmap` | `esp_lcd_panel_handle_t` |
| 刷新矩形 | LVGL `lv_area_t` | 坐标转换后传给 esp_lcd | `{x1,y1,x2+1,y2+1}` |
| 像素数据 | `lv_color_t*` buffer | 原样传递 | 内存地址指针 |

### 反向路径：DMA 完成 → LVGL 就绪

```
esp_lcd 层                    Port 层                       LVGL 核心
─────────                    ──────                       ──────────
SPI DMA 传输完成中断
  → 调用 on_color_trans_done(user_ctx)
                            lvgl_port_flush_io_ready_callback()
                              ├─ user_ctx → disp_drv
                              ├─ lv_disp_flush_ready(disp_drv)
                              └─ xSemaphoreGiveFromISR(trans_sem)
                                                            lv_disp_flush_ready()
                                                              → 标记缓冲区可重用
                                                              → 触发下一帧渲染
```

| 传递内容 | 来源 API | 去向 API | 数据类型 |
|---------|----------|---------|---------|
| LVGL 驱动句柄 | `io_config.user_ctx = &disp_drv` | `lv_disp_flush_ready()` | `lv_disp_drv_t*` |
| 传输信号量 | 初始化时创建 | `xSemaphoreGiveFromISR` | `SemaphoreHandle_t` |

### 双向指针交换（核心桥接模式）

```
初始化时：
  esp_lcd_panel_io_spi_config_t.io_handle ─── 创建 ───→ panel_handle
  lv_disp_drv_t.user_data = panel_handle  ←── (Port 层持有 esp_lcd 句柄)

  esp_lcd 侧持有 LVGL 引用：
    io_config.on_color_trans_done = port_notify_cb
    io_config.user_ctx = &disp_drv       ←── (esp_lcd 回调能回调 LVGL)

两个方向：
  LVGL → flush_cb → port 层 → drv->user_data 取出 panel_handle → esp_lcd API
  esp_lcd 传输完 → on_color_trans_done → user_ctx 取出 disp_drv → lv_disp_flush_ready
```

---

## 调用时序总结

```
app_main()
├── spi_bus_initialize(LCD_HOST, ...)        ─ 层级3: SPI 总线
├── esp_lcd_new_panel_io_spi(...)            ─ 层级3: 创建 IO 接口
├── esp_lcd_new_panel_st7789(...)            ─ 层级3: 创建面板驱动
├── esp_lcd_panel_reset/init(...)            ─ 层级3: 初始化 LCD
│
├── lvgl_port_init(&cfg)                     ─ 层级2: 创建 LVGL 任务 + 定时器
├── lvgl_port_add_disp(&disp_cfg)            ─ 层级2: 内部注册 LVGL flush_cb
│   ├── lv_display_create()                  ─ 层级1: 创建 LVGL 显示对象
│   ├── lv_display_set_flush_cb(port_cb)     ─ 层级1: 注册 flush 回调
│   ├── lv_display_set_user_data(panel)      ─ 层级1: 桥接 esp_lcd 句柄
│   └── esp_lcd_panel_io_register_callbacks( ─ 层级3: 注册传输完成回调
│         .on_color_trans_done = port_cb)
│
├── lvgl_port_add_touch(...)                 ─ 层级2: 注册 LVGL 输入设备
│
└── lvgl_port_lock/unlock
    └── ui_init() (SquareLine Studio UI)     ─ 应用层

LVGL 任务循环:
├── lvgl_port_lock(0)                        ─ 层级2: 获取互斥锁
├── lv_timer_handler()                       ─ 层级1: LVGL 渲染
│   └── → flush_cb → esp_lcd_panel_draw_bitmap()
├── lvgl_port_unlock()                       ─ 层级2: 释放互斥锁
└── vTaskDelay()
```

---

## 参考

- [ESP-IDF LCD 驱动框架文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html)
- [esp_lvgl_port 组件 (ESP-BSP 仓库)](https://github.com/espressif/esp-bsp/tree/master/components/esp_lvgl_port)
- [esp_lvgl_port 组件注册页面](https://components.espressif.com/components/espressif/esp_lvgl_port)
- [esp_lvgl_port.h API 头文件](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/include/esp_lvgl_port.h)
- [esp_lvgl_port_disp.h](https://github.com/espressif/esp-bsp/blob/master/components/esp_lvgl_port/include/esp_lvgl_port_disp.h)
- [SPI LCD + Touch + LVGL 示例](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/lcd/spi_lcd_touch)
- [I80 并行 LCD + LVGL 示例](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/lcd/i80_controller)
- [LVGL 官方文档](https://docs.lvgl.io/)

## 相关笔记

- [[idf button组件]]
- [[ESP32-GPIO-速查表]]
