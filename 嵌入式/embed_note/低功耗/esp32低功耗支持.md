---
date: 2026-06-15
tags:
  - esp32
  - 低功耗
aliases:
  - eps32
---

ESP32 支持多种低功耗模式，从系统功耗管理角度来看，主要有 DFS、Light-sleep 模式和 Deep-sleep 模式

# 低功耗模式介绍

## 1 DFS
Dynamic Frequency Scaling (DFS) 即动态频率切换

### 1.1 工作原理:

DFS 可以根据应用程序持有电源锁的情况，调整外围总线 (APB) 频率和 CPU 频率。持有**高性能锁**就使用高频，**空闲状态不持有电源锁**时则使用低频来降低功耗，以此来尽可能减少运行应用程序的功耗。

### 1.2 DFS运行机制:
```
      持有 CPU 和 APB MAX 锁
                 │
                 │        释放 CPU MAX 锁
        ▲        │       /
电流大小│        ▼      /
        │   ──────────┐             释放 APB MAX 锁
        │             │            /
        │             │           /
        │             └─────────┐
        │             ▲         │
        │             │         │
        │ 第 m 个 tick │         └───────────
        │                       ▲
        │                       │
        │           第 n 个 tick │
        └──────────────────────────────────────►
                                           时间
                理想 DFS 机制调频电流图
```

 **DFS 通常与其他低功耗模式共同开启**

## 2 Light-sleep模式
Light-sleep 模式是 ESP32 预设的一种低功耗模式
通过调用 [`esp_light_sleep_start()`](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/sleep_modes.html#_CPPv421esp_light_sleep_startv) 接口主动切换至 Light-sleep 模式

### 2.1 工作原理:
进入睡眠后，芯片将根据当前各外设的工作状态，关闭不必要的电源域和对睡眠期间不使用的模块进行时钟门控

### 2.2 auto light-sleep

Auto Light-sleep 模式是 ESP-IDF [电源管理](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/power_management.html) 组件基于 FreeRTOS 的 [[Tickless IDLE]]功能提供的一种低功耗模式。当应用程序释放所有电源锁，FreeRTOS 的所有任务都进入阻塞态或挂起态时，系统会自动获取下一个有就绪事件需要唤醒操作系统的时间点，当判定此时间点距当前超过设定时间（[CONFIG_FREERTOS_IDLE_TIME_BEFORE_SLEEP](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/kconfig-reference.html#config-freertos-idle-time-before-sleep)）后，`esp_pm` 组件会自动配置定时器唤醒源并进入 light sleep 以降低功耗。用户在配置 DFS 时置真 [`esp_pm_config_t`](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/power_management.html#_CPPv415esp_pm_config_t) 中的 `light_sleep_enable` 字段即可启用该模式

```
                              ┌────────┐
                              │        │
                              │  DFS   │
                              │        │
                              └───┬────┘
                                  │
                                  ▼
┌──────────┐     系统空闲     ┌──────────┐   超过设定时间  ┌─────────┐
│          │  ─────────────►  │          │  ────────────►  │         │
│          │                  │          │                 │   auto  │
│  active  │                  │   IDLE   │                 │  light  │
│          │                  │          │                 │   sleep │
│          │  ◄─────────────  │          │                 │         │
└──────────┘    系统非空闲    └──────────┘                 └────┬────┘
	  ▲                                                         │
	  │                         配置唤醒源唤醒                  │
	  └─────────────────────────────────────────────────────────┘

                Auto Light-sleep 模式工作流程图
```
## Deep-sleep 模式

Deep-sleep 模式是为了追求更好的功耗表现所设计，休眠时仅保留 **RTC/LP 相关内存及外设**，其余模块全部**关闭**

Deep-sleep 模式需配置唤醒源，ESP32 支持多种唤醒源，完整唤醒源列表详见 [睡眠模式](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/sleep_modes.html)。这些唤醒源也可以组合在一起，此时任何一个唤醒源都可以触发唤醒。若不配置唤醒源进入 Deep-sleep 模式，芯片将一直处在睡眠状态，直到外部复位。与 Light-sleep 模式不同，Deep-sleep 模式唤醒后会**丢失睡眠前的 CPU 运行上下文**，因此，唤醒后需要重新运行引导加载程序才可进入用户程序。

```
┌───────┐  调用 API  ┌───────┐
│       ├───────────►│ deep  │
│active │            │ sleep │
│       │            │       │
└───────┘            └───┬───┘
    ▲                    │
    └────────────────────┘
        配置的唤醒源唤醒
  Deep-sleep 模式工作流程图
```
# 纯系统下低功耗模式配置

**CONFIG_PM_ENABLE**:必须为on

## 公共配置
- 单双核工作模式 ([CONFIG_FREERTOS_UNICORE](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/kconfig-reference.html#config-freertos-unicore))
    对于多核心芯片，可以选择单核工作模式。
- RTOS Tick rate (Hz) ([CONFIG_FREERTOS_HZ](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/kconfig-reference.html#config-freertos-hz))
    该参数表示系统周期任务调度的频率。

## 1 DFS

* - `max_freq_mhz`：最大 CPU 频率 (MHz)。CPU 工作在最高性能时的频率，通常设置为芯片支持的最大值。
* - `min_freq_mhz`：最小 CPU 频率 (MHz)。系统空闲时 CPU 的工作频率，可设为晶振 (XTAL) 频率或其整数分频值。
* - `light_sleep_enable`：使能后，系统在空闲状态下自动进入 Light-sleep 模式（即 Auto Light-sleep）。
```c
/**
 * @brief DFS（动态频率缩放）与自动 Light-sleep 配置说明
 *
 * 本配置通过 esp_pm_config_t 结构体定义，并调用 esp_pm_configure() 使能电源管理。
 * @note 若启用 Auto Light-sleep（light_sleep_enable = true），必须同时配置唤醒源。
 * @note 启用 DFS 后，部分外设（如 UART、LEDC）可能受频率切换影响，可使用电源管理锁临时禁止 DFS。
 */
 esp_pm_config_t pm_config = {

 .max_freq_mhz = CONFIG_EXAMPLE_MAX_CPU_FREQ_MHZ,

 .min_freq_mhz = CONFIG_EXAMPLE_MIN_CPU_FREQ_MHZ,

 .light_sleep_enable = false

};

ESP_ERROR_CHECK(esp_pm_configure(&pm_config));
```

| 配置名称                                                                                                                                                               | 设置情况               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| 启用电源管理组件 ([CONFIG_PM_ENABLE](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/kconfig-reference.html#config-pm-enable))                | ON                 |
| RTOS Tick rate (Hz) ([CONFIG_FREERTOS_HZ](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/kconfig-reference.html#config-freertos-hz)) | 1000               |
| `max_freq_mhz`                                                                                                                                                     | ESP32 支持的最大 CPU 频率 |
| `min_freq_mhz`                                                                                                                                                     | {CONFIG_XTAL_FREQ} |
| `light_sleep_enable`                                                                                                                                               | false              |

## 2 Light-sleep

```c
esp_pm_config_t pm_config = {
  .max_freq_mhz = CONFIG_EXAMPLE_MAX_CPU_FREQ_MHZ,
  .min_freq_mhz = CONFIG_EXAMPLE_MIN_CPU_FREQ_MHZ,
  #if CONFIG_FREERTOS_USE_TICKLESS_IDLE
  .light_sleep_enable = true
  #endif
};
ESP_ERROR_CHECK(esp_pm_configure(&pm_config));
```