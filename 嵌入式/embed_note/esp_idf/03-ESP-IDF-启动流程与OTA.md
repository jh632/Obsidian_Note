---
tags: [esp-idf, esp32, bootloader, ota, 分区表, 启动流程]
date: 2026-09-01
aliases: [esp32 bootloader, ota升级方案, OTA, ESP-IDF启动流程, 启动流程]
---

# ESP-IDF 启动流程与 OTA

> 2026-09-01 由原《esp32 bootloader》《ota升级方案》整理合并。完整的启动流程分析见 [[ota/ESP32启动流程与Bootloader]]，本篇聚焦 bootloader 自定义与 OTA 实战。

---

## 目录

1. [启动流程速览](#1-启动流程速览)
2. [自定义 Bootloader 的两种方式](#2-自定义-bootloader-的两种方式)
3. [OTA 分区方案](#3-ota-分区方案)
4. [OTA 升级 API](#4-ota-升级-api)
5. [升级流程与回滚](#5-升级流程与回滚)

---

## 1. 启动流程速览

ESP32 采用**三级启动架构**：

```
上电/复位
  → ① ROM Bootloader（芯片固化，不可修改）
      → 检查 strapping 引脚（GPIO0 拉低 = 下载模式）
      → 从 flash 0x1000 加载二级引导
  → ② 二级 Bootloader（ESP-IDF 编译，可配置）
      → 读取分区表（默认 flash 0x8000）
      → 根据 otadata 选择 factory / ota_0 / ota_1
      → 校验镜像 → 跳转 app 入口
  → ③ 应用：call_start_cpu0 → start_cpu0 → FreeRTOS → app_main
```

| Flash 偏移 | 内容 |
|---|---|
| 0x1000 | 二级 Bootloader（经典 ESP32；新芯片 C3/S3 默认 0x0） |
| 0x8000 | 分区表（`CONFIG_PARTITION_TABLE_OFFSET` 可配置） |
| 0x9000 | nvs |
| 0x10000 | factory app（app 分区必须 64KB 对齐） |

> 完整细节（strapping 引脚、镜像格式、与 Cortex-M 对比）见 [[ota/ESP32启动流程与Bootloader]]。

---

## 2. 自定义 Bootloader 的两种方式

ESP-IDF 提供两种自定义二级引导的方式，按复杂程度选择：

| 特性 | 方式一：钩子（Hooks） | 方式二：完全覆盖（Override） |
|---|---|---|
| **核心思路** | 在标准启动流程前后插入自定义钩子函数 | 提供完全自定义的 `bootloader_start.c` 替换默认实现 |
| **适用场景** | 轻量扩展：硬件初始化/自检、自定义启动 Logo、启动日志 | 深度定制：多镜像选择、新安全检查、专有固件更新机制 |
| **实现难度** | 较低，实现几个接口函数即可 | 较高，需完全理解启动加载程序职责 |
| **官方示例** | `custom_bootloader/bootloader_hooks` | `custom_bootloader/bootloader_override` |

### 2.1 方式一：Bootloader Hooks

新建 `bootloader/main/hook.c`：

```c
#include "esp_log.h"

/* 用于告诉链接器包含本文件及其所有符号 */
void bootloader_hooks_include(void) {
}

/* 系统初始化之前调用：此时 BSS、SPI flash、内存保护均未初始化，
 * 大量函数不能在此调用！ */
void bootloader_before_init(void) {
    ESP_LOGI("HOOK", "This hook is called BEFORE bootloader initialization");
}

/* 系统初始化之后调用 */
void bootloader_after_init(void) {
    ESP_LOGI("HOOK", "This hook is called AFTER bootloader initialization");
}
```

### 2.2 方式二：完全 Override

用自定义 `bootloader_start.c` 覆盖默认实现，核心入口是 `call_start_cpu0`（不返回）：

```c
void __attribute__((noreturn)) call_start_cpu0(void)
{
    // 1. 硬件初始化
    if (bootloader_init() != ESP_OK) {
        bootloader_reset();
    }

#ifdef CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP
    // 深睡唤醒走捷径：直接加载睡眠前运行的 app
    bootloader_utility_load_boot_image_from_deep_sleep();
#endif

    // 2. 选择启动分区
    bootloader_state_t bs = {0};
    int boot_index = select_partition_number(&bs);
    if (boot_index == INVALID_INDEX) {
        bootloader_reset();
    }

    // 2.1 打印自定义信息
    esp_rom_printf("[%s] %s\n", TAG, CONFIG_EXAMPLE_BOOTLOADER_WELCOME_MESSAGE);

    // 3. 加载 app 镜像并启动
    bootloader_utility_load_boot_image(&bs, boot_index);
}

// 选择启动分区
static int select_partition_number(bootloader_state_t *bs)
{
    if (!bootloader_utility_load_partition_table(bs)) {
        ESP_LOGE(TAG, "load partition table error!");
        return INVALID_INDEX;
    }
    return bootloader_utility_get_selected_boot_partition(bs);
}
```

---

## 3. OTA 分区方案

### 3.1 常见 OTA 分区表

```csv
# Name,     Type, SubType, Offset,   Size
nvs,        data, nvs,     0x9000,   0x6000
otadata,    data, ota,     0xf000,   0x2000
phy_init,   data, phy,     0x11000,  0x1000
factory,    app,  factory, 0x20000,  1M
ota_0,      app,  ota_0,   ,         2M
ota_1,      app,  ota_1,   ,         2M
```

| 分区 | 作用 |
|---|---|
| `factory` | 出厂固件（可选，可取消） |
| `ota_0` / `ota_1` | OTA 固件槽位 0 / 1 |
| `otadata` | 记录当前应该启动哪个固件槽位 |
| `nvs` | 保存 Wi-Fi、配置、设备参数等 |
| `phy_init` | RF 校准相关数据 |

> factory 可取消，程序直接运行在 ota_0 或 ota_1。

### 3.2 otadata 的作用

`otadata` 不是存放固件的地方，只存放**启动选择信息**——相当于一个"启动指针"：

```
otadata = 当前应该启动 ota_0（或 ota_1）

启动时：
bootloader 读取 otadata
  → 知道应该启动 ota_0 还是 ota_1
  → 加载对应 app
```

OTA 成功后应用调用：

```c
esp_ota_set_boot_partition(update_partition);
esp_restart();
```

这一步本质上就是**修改 otadata 告诉 bootloader 下次启动新固件**。

> 官方分区表文档：`data/ota` 分区用于存储当前选中的 OTA app slot 信息，通常大小应为 0x2000 字节。

### 3.3 OTA 分区大小估算

分区大小需 ≥ 固件实际大小，构建日志会给出参考：

```
Total image size: 1777048 bytes (.bin may be padded larger)
```

估算时建议留出余量（考虑 `.bin` 填充、未来功能增长）。

---

## 4. OTA 升级 API

### 4.1 分区查询与引导控制

| 函数 | 功能 |
|---|---|
| `esp_ota_get_next_update_partition(NULL)` | 获取应写入的**非活动 OTA 分区**（ota_1 或 ota_0），是 `esp_ota_begin` 的参数 |
| `esp_ota_get_running_partition()` | 获取**当前正在运行**的分区 |
| `esp_ota_get_boot_partition()` | 获取**下次启动**时 bootloader 会引导的分区 |
| `esp_ota_set_boot_partition(partition)` | **设置下次启动的分区**，数据验证成功后调用，重启进入新固件 |

### 4.2 固件写入流程（升级链路核心，三函数按序调用）

| 函数 | 功能 |
|---|---|
| `esp_ota_begin(partition, image_size, &handle)` | 初始化 OTA 写入会话。传目标分区和固件总大小（可传 `OTA_SIZE_UNKNOWN`），获得写入句柄 |
| `esp_ota_write(handle, data, data_len)` | 向分区写入一块数据，可循环调用。**必须在 `esp_ota_begin` 后调用** |
| `esp_ota_end(handle)` | 结束写入会话，进行**校验和验证**（镜像完整性）。**验证通过后分区才被标记为可用** |

```c
// 典型写入循环
esp_ota_handle_t ota_handle;
esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &ota_handle);

while ((len = read_firmware_chunk(buf, sizeof(buf))) > 0) {
    esp_ota_write(ota_handle, buf, len);
}

esp_ota_end(ota_handle);          // 校验镜像完整性
esp_ota_set_boot_partition(update_partition);  // 切换启动槽
esp_restart();
```

---

## 5. 升级流程与回滚

### 5.1 回滚与安全确认 API

| 函数 | 功能 |
|---|---|
| `esp_ota_mark_app_valid_cancel_rollback()` | **必须在新固件中调用**。新固件启动并完成核心功能自检后调用，将分区状态从 `PENDING_VERIFY` 改为 `VALID`，阻止自动回滚 |
| `esp_ota_mark_app_invalid_rollback_and_reboot()` | **立即主动触发回滚并重启**。新固件自检发现严重错误时调用，放弃当前固件返回旧版本 |

### 5.2 安全 OTA 状态机

```
新固件启动
  → 分区处于 PENDING_VERIFY（待验证）
  → 应用做核心功能自检
       ├─ 自检通过 → esp_ota_mark_app_valid_cancel_rollback() → VALID
       └─ 自检失败 → esp_ota_mark_app_invalid_rollback_and_reboot() → 回滚旧版
```

> 如果不调用 `mark_app_valid`，下次启动会触发自动回滚到旧固件——这是"防变砖"机制。实际产品 OTA 状态机设计见 [[架构/嵌入式设计模式-状态机]]、[[workspace/公司项目/ota升级状态机]]。

---

## 参考

- ESP-IDF 编程指南 — 自定义 Bootloader：https://docs.espressif.com/projects/esp-idf/en/v5.3.1/esp32s3/api-guides/bootloader.html
- ESP-IDF 编程指南 — OTA：https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/apps/ota.html
- ESP-IDF 分区表文档
- 官方示例：`examples/custom_bootloader/bootloader_hooks`、`examples/custom_bootloader/bootloader_override`

## 相关笔记

- [[01-ESP-IDF-项目结构与构建工具]] — 烧录地址与 merge-bin
- [[ota/ESP32启动流程与Bootloader]] — 完整启动流程分析
- [[ota/ota为什么需要双分区]]、[[ota/ota如何保障真正的安全]]
- [[架构/嵌入式设计模式-状态机]] — OTA 状态机设计
