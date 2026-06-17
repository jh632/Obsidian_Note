---
date: 2026-06-16
tags: [esp32, gpio, esp-idf]
aliases: [ESP32-GPIO-cheatsheet, ESP32-GPIO-参考]
---

# ESP32 GPIO 速查表

## 概述

ESP32 GPIO 模块提供最多 34 个可编程 GPIO 引脚（GPIO0-GPIO39），支持数字输入/输出、多种边沿/电平中断触发、内部上拉/下拉电阻。部分引脚具有 RTC 域功能，可在深度睡眠中保持状态或唤醒芯片。ADC1/ADC2 与部分 GPIO 复用，使用时需注意 Wi-Fi 对 ADC2 的限制。

## 快速参考

### GPIO 主要功能

| 功能 | 说明 | 相关 API |
|---|---|---|
| 数字输入 | 读取引脚电平，高电平=1，低电平=0 | `gpio_get_level()` |
| 数字输出 | 设置引脚电平，推挽输出 | `gpio_set_level()` |
| 中断触发 | 支持上升沿/下降沿/任意边沿/电平触发 | `gpio_set_intr_type()` + `gpio_isr_handler_add()` |
| 内部上拉 | 使能内部上拉电阻（~45kΩ） | `GPIO_PULLUP_ENABLE` |
| 内部下拉 | 使能内部下拉电阻（~45kΩ） | `GPIO_PULLDOWN_ENABLE` |
| 开漏输出 | 开漏模式，需外部上拉电阻 | `GPIO_MODE_OUTPUT_OD` |

**注意事项：**
- GPIO34-39 为 **仅输入** 引脚：无输出能力，无内部上拉/下拉电阻
- 输入/输出方向通过 `gpio_config()` 或 `gpio_set_direction()` 设置

### 中断类型

| 中断类型宏 | 触发条件 |
|---|---|
| `GPIO_INTR_DISABLE` | 禁用中断 |
| `GPIO_INTR_POSEDGE` | 上升沿触发 |
| `GPIO_INTR_NEGEDGE` | 下降沿触发 |
| `GPIO_INTR_ANYEDGE` | 任意边沿触发 |
| `GPIO_INTR_LOW_LEVEL` | 低电平触发 |
| `GPIO_INTR_HIGH_LEVEL` | 高电平触发 |

### RTC GPIO 对应关系

RTC GPIO 属于 RTC 电源域，在深度睡眠期间保持电平状态，可用于从深度睡眠中唤醒芯片。

| RTC GPIO | 对应 GPIO | 额外功能 | 备注 |
|---|---|---|---|
| RTC_GPIO0 | GPIO36 | ADC1_CH0 | 仅输入 |
| RTC_GPIO1 | GPIO37 | ADC1_CH1 | 仅输入 |
| RTC_GPIO2 | GPIO38 | ADC1_CH2 | 仅输入 |
| RTC_GPIO3 | GPIO39 | ADC1_CH3 | 仅输入 |
| RTC_GPIO4 | GPIO34 | ADC1_CH6 | 仅输入 |
| RTC_GPIO5 | GPIO35 | ADC1_CH7 | 仅输入 |
| RTC_GPIO6 | GPIO25 | DAC_1 | |
| RTC_GPIO7 | GPIO26 | DAC_2 | |
| RTC_GPIO8 | GPIO27 | ADC2_CH7 | |
| RTC_GPIO9 | GPIO32 | ADC1_CH4 | |
| RTC_GPIO10 | GPIO33 | ADC1_CH5 | |
| RTC_GPIO11 | GPIO4 | ADC2_CH0 | |
| RTC_GPIO12 | GPIO0 | ADC2_CH1 | |
| RTC_GPIO13 | GPIO2 | ADC2_CH2 | |
| RTC_GPIO14 | GPIO15 | ADC2_CH3 | |
| RTC_GPIO15 | GPIO13 | ADC2_CH4 | |
| RTC_GPIO16 | GPIO12 | ADC2_CH5 | |
| RTC_GPIO17 | GPIO14 | ADC2_CH6 | |

### ADC1 / ADC2 通道与 GPIO 限制

**ADC1**（8 通道，独立使用，不受 Wi-Fi 影响）：

| ADC1 通道 | GPIO |
|---|---|
| ADC1_CH0 | GPIO36 |
| ADC1_CH1 | GPIO37 |
| ADC1_CH2 | GPIO38 |
| ADC1_CH3 | GPIO39 |
| ADC1_CH4 | GPIO32 |
| ADC1_CH5 | GPIO33 |
| ADC1_CH6 | GPIO34 |
| ADC1_CH7 | GPIO35 |

**ADC2**（10 通道，Wi-Fi 开启时不可用）：

| ADC2 通道 | GPIO |
|---|---|
| ADC2_CH0 | GPIO4 |
| ADC2_CH1 | GPIO0 |
| ADC2_CH2 | GPIO2 |
| ADC2_CH3 | GPIO15 |
| ADC2_CH4 | GPIO13 |
| ADC2_CH5 | GPIO12 |
| ADC2_CH6 | GPIO14 |
| ADC2_CH7 | GPIO27 |
| ADC2_CH8 | GPIO25 |
| ADC2_CH9 | GPIO26 |

> **关键限制：** 当 Wi-Fi 功能启用时，ADC2 的**所有通道不可使用**。若同时需要 ADC 和 Wi-Fi，必须选择 ADC1 的通道。

### 最大输出电流

| 参数 | 典型值 | 说明 |
|---|---|---|
| 单个 GPIO 最大驱动电流 | 40 mA | 建议不超过 20 mA 以留余量 |
| 全部 GPIO 总电流 | 受 VDD 供电能力限制 | 高驱动场景需注意散热 |
| VDD 电压 | 3.3 V | CMOS 电平，与供电电压一致 |

### 常用宏

| 宏 | 含义 |
|---|---|
| `GPIO_MODE_INPUT` | 数字输入 |
| `GPIO_MODE_OUTPUT` | 数字输出 |
| `GPIO_MODE_OUTPUT_OD` | 开漏输出 |
| `GPIO_MODE_INPUT_OUTPUT` | 输入 + 输出 |
| `GPIO_MODE_INPUT_OUTPUT_OD` | 输入 + 开漏输出 |
| `GPIO_PULLUP_ENABLE` | 使能内部上拉 |
| `GPIO_PULLUP_DISABLE` | 禁用内部上拉 |
| `GPIO_PULLDOWN_ENABLE` | 使能内部下拉 |
| `GPIO_PULLDOWN_DISABLE` | 禁用内部下拉 |

### 常用 API 函数

```c
#include "driver/gpio.h"

// 1. 通用配置方式
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_2),  // 选择引脚（位掩码，支持多引脚）
    .mode = GPIO_MODE_OUTPUT,               // 输出模式
    .pull_up_en = GPIO_PULLUP_DISABLE,      // 不上拉
    .pull_down_en = GPIO_PULLDOWN_DISABLE,  // 不下拉
    .intr_type = GPIO_INTR_DISABLE,         // 禁用中断
};
gpio_config(&io_conf);

// 2. 设置输出电平
gpio_set_level(GPIO_NUM_2, 1);   // 高电平
gpio_set_level(GPIO_NUM_2, 0);   // 低电平

// 3. 读取输入电平
int level = gpio_get_level(GPIO_NUM_4);

// 4. 设置中断类型
gpio_set_intr_type(GPIO_NUM_4, GPIO_INTR_POSEDGE);

// 5. 安装 ISR 服务并注册中断处理函数
gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT);
gpio_isr_handler_add(GPIO_NUM_4, my_isr_handler, (void *)arg);

// 6. 简化设置（省略 config 结构体）
gpio_set_direction(GPIO_NUM_2, GPIO_MODE_OUTPUT);
gpio_set_pull_mode(GPIO_NUM_2, GPIO_PULLUP_ONLY);
```

#### 典型配置：输入 + 下降沿中断

```c
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_4),
    .mode = GPIO_MODE_INPUT,
    .pull_up_en = GPIO_PULLUP_ENABLE,
    .intr_type = GPIO_INTR_NEGEDGE,
};
gpio_config(&io_conf);
gpio_install_isr_service(0);
gpio_isr_handler_add(GPIO_NUM_4, button_isr_cb, NULL);
```

#### 典型配置：推挽输出

```c
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_2),
    .mode = GPIO_MODE_OUTPUT,
    .pull_up_en = GPIO_PULLUP_DISABLE,
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE,
};
gpio_config(&io_conf);
gpio_set_level(GPIO_NUM_2, 1);  // LED 亮 / 输出高
```

## 参考

- ESP32 技术参考手册 — GPIO 与 RTC_GPIO 章节
- ESP-IDF 编程指南: GPIO & RTC GPIO — https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/gpio.html
- ESP32 数据手册 — 引脚定义表（Pin Definitions）

## 相关笔记

- [[睡眠模式]] — RTC GPIO 用于深度睡眠唤醒和保持
- [[nvs api]] — ESP-IDF 框架下的其他常用 API 参考
- [[常用idf命令]] — ESP-IDF 开发常用命令

## 待补充笔记

以下相关主题目前尚无独立笔记，后续可考虑创建：
- **ADC 驱动配置** — ADC1/ADC2 的详细配置、衰减系数与电压换算
- **GPIO 矩阵** — ESP32 GPIO 交换矩阵的信号任意映射功能
- **中断系统** — ESP32 中断控制器与 ISR 服务整体架构
