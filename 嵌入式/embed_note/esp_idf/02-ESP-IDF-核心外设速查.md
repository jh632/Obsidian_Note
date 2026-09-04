---
tags: [esp-idf, esp32, gpio, nvs, 存储, 低功耗, 睡眠]
date: 2026-09-01
aliases: [ESP32-GPIO-速查表, nvs api, 睡眠模式, ESP-IDF外设速查, GPIO参考]
---

# ESP-IDF 核心外设速查（GPIO / NVS / 低功耗）

> 2026-09-01 由原《ESP32-GPIO-速查表》《nvs api》《睡眠模式》整理合并。睡眠模式部分原笔记为空，此处整合 [[低功耗/esp32低功耗支持]] 的核心内容并给出指引。

---

## 目录

1. [GPIO 速查表](#1-gpio-速查表)
2. [NVS 非易失存储 API](#2-nvs-非易失存储-api)
3. [睡眠模式与低功耗](#3-睡眠模式与低功耗)

---

## 1. GPIO 速查表

### 1.1 概述

ESP32 GPIO 模块提供最多 34 个可编程 GPIO 引脚（GPIO0-GPIO39），支持数字输入/输出、多种边沿/电平中断触发、内部上拉/下拉电阻。部分引脚具有 RTC 域功能，可在深度睡眠中保持状态或唤醒芯片。ADC1/ADC2 与部分 GPIO 复用，使用时需注意 Wi-Fi 对 ADC2 的限制。

### 1.2 GPIO 主要功能

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

### 1.3 中断类型

| 中断类型宏 | 触发条件 |
|---|---|
| `GPIO_INTR_DISABLE` | 禁用中断 |
| `GPIO_INTR_POSEDGE` | 上升沿触发 |
| `GPIO_INTR_NEGEDGE` | 下降沿触发 |
| `GPIO_INTR_ANYEDGE` | 任意边沿触发 |
| `GPIO_INTR_LOW_LEVEL` | 低电平触发 |
| `GPIO_INTR_HIGH_LEVEL` | 高电平触发 |

### 1.4 RTC GPIO 对应关系

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

### 1.5 ADC1 / ADC2 通道与 GPIO 限制

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

### 1.6 最大输出电流

| 参数 | 典型值 | 说明 |
|---|---|---|
| 单个 GPIO 最大驱动电流 | 40 mA | 建议不超过 20 mA 以留余量 |
| 全部 GPIO 总电流 | 受 VDD 供电能力限制 | 高驱动场景需注意散热 |
| VDD 电压 | 3.3 V | CMOS 电平，与供电电压一致 |

### 1.7 常用宏

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

### 1.8 常用 API 函数

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

---

## 2. NVS 非易失存储 API

NVS（Non-Volatile Storage）是 ESP-IDF 的 key-value 持久化存储，Wi-Fi 配置、设备参数、校准数据都默认存这里。**使用前必须先 `nvs_flash_init()`**。

### 2.1 生命周期 API

| API | 作用 | 备注 |
|---|---|---|
| `nvs_flash_init()` | 初始化默认 `nvs` 分区 | 一般全局只做一次 |
| `nvs_flash_erase()` | 擦除默认 `nvs` 分区 | 常配合 `nvs_flash_init()` 使用 |
| `nvs_open()` | 打开默认 `nvs` 分区中的命名空间 | 返回 `nvs_handle_t` |
| `nvs_open_from_partition()` | 打开指定 NVS 分区中的命名空间 | 项目有多个 NVS 分区时用 |
| `nvs_close()` | 关闭已打开的 handle | open 成功后通常都要 close |

### 2.2 写入 API（写后需 `nvs_commit()`）

| API | 数据类型 | 常见用途 |
|---|---|---|
| `nvs_set_u8()` / `nvs_get_u8()` | `uint8_t` | 标志位、状态位 |
| `nvs_set_u16()` / `nvs_get_u16()` | `uint16_t` | 较小范围数值 |
| `nvs_set_u32()` / `nvs_get_u32()` | `uint32_t` | 计数、长度、CRC、版本号（很常用） |
| `nvs_set_u64()` / `nvs_get_u64()` | `uint64_t` | 时间戳、长整型计数 |
| `nvs_set_i8()` ~ `nvs_set_i64()` | 有符号整数 | 有符号配置值 |
| `nvs_set_str()` / `nvs_get_str()` | 字符串 | 设备名、服务器地址、版本字符串 |
| `nvs_set_blob()` / `nvs_get_blob()` | 二进制块 | 结构体、校准参数、原始 buffer |

> 读取 `str`/`blob` 时**常先查长度再正式读取**，否则会返回 `ESP_ERR_NVS_INVALID_LENGTH`。

### 2.3 删除与其他

| API | 作用 |
|---|---|
| `nvs_erase_key()` | 删除一个 key（删后需 commit） |
| `nvs_erase_all()` | 删除当前命名空间全部 key |
| `nvs_commit()` | 提交写入到 flash（**不调用可能掉电丢失**） |
| `nvs_get_stats()` | 获取 NVS 分区使用情况 |
| `nvs_get_used_entry_count()` | 当前命名空间已用条目数 |
| `nvs_find_key()` | 查询 key 是否存在及类型 |

### 2.4 常见返回值

| 返回值 | 含义 | 常见场景 | 处理建议 |
|---|---|---|---|
| `ESP_OK` | 成功 | 读写/打开/提交正常 | — |
| `ESP_ERR_NVS_NOT_FOUND` | key 或 namespace 不存在 | 第一次启动、配置未写入 | 按"使用默认值"处理 |
| `ESP_ERR_NVS_INVALID_LENGTH` | 缓冲区长度不够 | `nvs_get_str()` / `nvs_get_blob()` | 先查长度再读 |
| `ESP_ERR_NVS_NO_FREE_PAGES` | 分区无可用页 | 分区满、分区表变化 | 常擦除后重新初始化 |
| `ESP_ERR_NVS_NEW_VERSION_FOUND` | 数据版本不兼容 | 升级后旧数据格式不兼容 | 常擦除后重新初始化 |
| `ESP_ERR_INVALID_ARG` | 参数非法 | 空指针、长度非法 | 检查参数 |

### 2.5 标准使用流程

```c
// 1. 启动时初始化
esp_err_t err = nvs_flash_init();
if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());   // 分区异常 → 擦除重建
    err = nvs_flash_init();
}
ESP_ERROR_CHECK(err);

// 2. 打开命名空间
nvs_handle_t handle;
ESP_ERROR_CHECK(nvs_open("storage", NVS_READWRITE, &handle));

// 3. 写入（提交前不落盘）
ESP_ERROR_CHECK(nvs_set_u32(handle, "boot_count", boot_count + 1));
ESP_ERROR_CHECK(nvs_commit(handle));

// 4. 读取（带默认值兜底）
uint32_t boot_count = 0;
esp_err_t r = nvs_get_u32(handle, "boot_count", &boot_count);
if (r != ESP_OK) boot_count = 0;

// 5. 关闭
nvs_close(handle);
```

---

## 3. 睡眠模式与低功耗

> 完整细节见 [[低功耗/esp32低功耗支持]]。本节为速查。

ESP32 的功耗管理从浅到深分三级：**DFS（动态调频）→ Light-sleep → Deep-sleep**。`CONFIG_PM_ENABLE` 必须为 on。

### 3.1 三种模式对比

| 模式 | 机制 | 唤醒后 | 典型用途 |
|---|---|---|---|
| **DFS** | 动态调整 CPU/APB 频率（持锁高频、空闲低频） | 无影响 | 配合其他模式，降低运行功耗 |
| **Light-sleep** | 关闭不必要的电源域 + 时钟门控，CPU 停止 | 保留上下文，秒级恢复 | 间歇性采集、等待事件 |
| **Deep-sleep** | 仅保留 RTC/LP 域，其余全部关闭 | **丢失上下文**，重新跑 bootloader | 长周期上报、待机 |

### 3.2 Auto Light-sleep

基于 FreeRTOS Tickless IDLE：所有任务阻塞、释放电源锁后，系统自动进入 light sleep，到下一个定时事件唤醒。配置 `esp_pm_config_t.light_sleep_enable = true` 即可启用。

### 3.3 关键配置

```c
// DFS 与自动 Light-sleep（esp_pm_configure）
esp_pm_config_t pm_config = {
    .max_freq_mhz       = CONFIG_EXAMPLE_MAX_CPU_FREQ_MHZ,
    .min_freq_mhz       = CONFIG_EXAMPLE_MIN_CPU_FREQ_MHZ,
    .light_sleep_enable = true,   // 使能后空闲自动进 light sleep
};
ESP_ERROR_CHECK(esp_pm_configure(&pm_config));
```

| 配置项 | 说明 |
|---|---|
| `CONFIG_PM_ENABLE` | 电源管理总开关，必须 on |
| `max_freq_mhz` / `min_freq_mhz` | DFS 频率上下限 |
| `light_sleep_enable` | 空闲自动进 Light-sleep |

### 3.4 Deep-sleep 与唤醒源

- Deep-sleep 唤醒后会**丢失 CPU 运行上下文**，需重新运行引导加载程序
- 必须配置唤醒源，否则只能外部复位唤醒
- RTC GPIO 可作唤醒源 / 保持电平，见本文 [1.4 RTC GPIO 对应关系](#14-rtc-gpio-对应关系)
- 与按键低功耗配合：IDF Button 组件的 `enable_power_save` + Light Sleep，见 [[06-ESP-IDF-显示与输入组件]]

---

## 参考

- ESP32 技术参考手册 — GPIO 与 RTC_GPIO 章节
- ESP-IDF 编程指南: GPIO & RTC GPIO — https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/gpio.html
- ESP-IDF 编程指南: NVS — https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/nvs_flash.html
- ESP-IDF 编程指南: 睡眠模式 — https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/sleep_modes.html
- ESP32 数据手册 — 引脚定义表（Pin Definitions）

## 相关笔记

- [[01-ESP-IDF-项目结构与构建工具]] — idf.py / esptool 命令
- [[04-ESP-IDF-WiFi与网络]] — WiFi 配置默认存 NVS
- [[低功耗/esp32低功耗支持]] — 低功耗完整笔记
- [[06-ESP-IDF-显示与输入组件]] — IDF Button 低功耗配合
