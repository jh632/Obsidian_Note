---
date: 2026-06-25
tags: [esp-idf, input-device, button, esp-iot-solution]
aliases: [idf-button, iot-button, 按钮组件]
---

# IDF Button 组件

## 概述

`button` 组件来自 `esp-iot-solution`，提供统一的按键检测框架，支持 **GPIO 按键**、**ADC 按键**和**矩阵键盘**三种硬件类型。内置消抖、长按/短按/连击等事件检测，可通过回调或轮询获取事件。

## 硬件类型

| 类型 | 优点 | 缺点 |
|------|------|------|
| GPIO 按键 | 独立 IO，稳定性高 | 占用引脚多 |
| ADC 按键 | 多键共享一个 ADC 通道，省 IO | 不支持同时按键，氧化后不稳定 |
| 矩阵键盘 | 大量按键只需 row+col 个 IO | 需要扫描，有鬼键问题 |

> [!warning] GPIO 注意
> input-only GPIO（如 ESP32-S3 的 GPIO44-47）**没有内部上下拉**，需要外部接电阻。

## 事件类型

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

## 使用模式

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

## 快速上手

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

## 参数配置

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

### 短按窗口

```c
iot_button_set_param(btn, BUTTON_SHORT_PRESS_TIME_MS, (void *)200);
```

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

## 低功耗模式

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

## 配置宏

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

## API 速查

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

## 参考

- [官方文档](https://docs.espressif.com/projects/esp-iot-solution/zh_CN/latest/input_device/button.html)
- [源码仓库](https://github.com/espressif/esp-iot-solution/tree/master/components/button)
- [gpio_button_test.c](https://github.com/espressif/esp-iot-solution/blob/5f9cb98ae4d0e8153c4b4d1accf471214e5b6fe8/components/button/test_apps/main/gpio_button_test.c) — GPIO 按键测试
- [auto_test.c](https://github.com/espressif/esp-iot-solution/blob/5f9cb98ae4d0e8153c4b4d1accf471214e5b6fe8/components/button/test_apps/main/auto_test.c) — 自动化测试，含长按时间配置
- [iot_button.h](https://github.com/espressif/esp-iot-solution/blob/5f9cb98ae4d0e8153c4b4d1accf471214e5b6fe8/components/button/include/iot_button.h) — 完整头文件

## 相关笔记

- [[embed_note/esp_idf/ESP32-GPIO-速查表]]
