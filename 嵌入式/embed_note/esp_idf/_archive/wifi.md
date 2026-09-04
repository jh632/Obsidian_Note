---
date: 2026-06-01
tags: [wifi, esp32, esp-idf, networking]
aliases: [ESP32 WiFi, WiFi API]
---

# ESP-IDF WiFi

## 概述

ESP-IDF WiFi 驱动基于 `esp_netif` + `esp_event` + `esp_wifi` 三层架构，提供 Station (STA)、SoftAP、STA+AP 三种工作模式。所有 WiFi 操作均为事件驱动 —— 不在回调中等待结果，而是注册事件处理函数响应状态变化。

## 核心概念

- **三层关系**：`esp_wifi` (驱动层) → `esp_event` (事件分发) → `esp_netif` (TCP/IP 接口层)
- **事件驱动模型**：WiFi 连接/断开/IP 获取等均为异步事件，通过 `esp_event_handler_register` 注册回调
- **NVS 依赖**：WiFi 默认将配置存入 NVS，必须先 `nvs_flash_init()`
- **STA 重连由用户负责**：`esp_wifi_connect()` 只尝试连接一次，断开后需在事件回调中自行重连

## 初始化流程（STA 模式）

```c
// 1. 底层初始化（一般系统启动时做一次）
nvs_flash_init();                          // WiFi 配置默认存 NVS
esp_netif_init();                          // TCP/IP 协议栈
esp_event_loop_create_default();           // 默认事件循环
esp_netif_create_default_wifi_sta();       // 创建 STA 网络接口

// 2. WiFi 初始化
wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
esp_wifi_init(&cfg);

// 3. 注册事件回调（必须在 esp_wifi_start 之前）
esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &ip_event_handler, NULL);

// 4. 配置并启动
esp_wifi_set_mode(WIFI_MODE_STA);

wifi_config_t wifi_cfg = {
    .sta = {
        .ssid = "your_ssid",
        .password = "your_password",
    },
};
esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg);
esp_wifi_start();   // 启动后不要立即 connect，等 WIFI_EVENT_STA_START
```

### 事件回调示例

```c
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data)
{
    if (event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_id == WIFI_EVENT_STA_DISCONNECTED) {
        // 重连逻辑：加退避延迟，避免频繁闪连
        esp_wifi_connect();
    }
}

static void ip_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data)
{
    if (event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        // event->ip_info.ip 等可用，连接真正就绪
    }
}
```

### 完整启动时序

```
nvs_flash_init → esp_netif_init → esp_event_loop_create_default
→ esp_netif_create_default_wifi_sta
→ esp_wifi_init → esp_event_handler_register × N
→ esp_wifi_set_mode → esp_wifi_set_config → esp_wifi_start
→ [WIFI_EVENT_STA_START] → esp_wifi_connect
→ [WIFI_EVENT_STA_CONNECTED] → (等待 DHCP)
→ [IP_EVENT_STA_GOT_IP] → 网络就绪
```

## API 速查表

### 生命周期

| API | 说明 | 备注 |
|---|---|---|
| `esp_wifi_init(&cfg)` | 分配 WiFi 驱动资源 | 用 `WIFI_INIT_CONFIG_DEFAULT()` 初始化 cfg |
| `esp_wifi_deinit()` | 释放所有资源，停止 WiFi 任务 | 与 init 配对 |
| `esp_wifi_start()` | 按当前 mode 创建控制块并启动 | STA/AP/APSTA |
| `esp_wifi_stop()` | 停止 WiFi，释放控制块 | 与 start 配对 |
| `esp_wifi_connect()` | STA 发起一次连接 | **只尝试一次**，不在内部重连 |
| `esp_wifi_disconnect()` | STA 断开当前连接 | — |
| `esp_wifi_restore()` | 将 NVS 中 WiFi 配置恢复为出厂值 | — |

### 设置与配置

| API | 说明 |
|---|---|
| `esp_wifi_set_mode(mode)` | 设置工作模式：`WIFI_MODE_STA` / `WIFI_MODE_AP` / `WIFI_MODE_APSTA` |
| `esp_wifi_set_config(ifx, &cfg)` | 设置指定接口配置（SSID/密码等），**同时写入 NVS** |
| `esp_wifi_get_config(ifx, &cfg)` | 读取当前接口配置 |
| `esp_wifi_set_storage(storage)` | `WIFI_STORAGE_FLASH` (默认) 或 `WIFI_STORAGE_RAM` |
| `esp_wifi_set_ps(type)` | 省电模式：`WIFI_PS_NONE` / `WIFI_PS_MIN_MODEM` (默认) / `WIFI_PS_MAX_MODEM` |
| `esp_wifi_set_protocol(ifx, bitmap)` | 设置 802.11 协议：`WIFI_PROTOCOL_11B\|G\|N` 等 |
| `esp_wifi_set_bandwidth(ifx, bw)` | 带宽：`WIFI_BW_HT20` / `WIFI_BW_HT40` |
| `esp_wifi_set_mac(ifx, mac)` | 设置 MAC 地址（接口需未启动） |
| `esp_wifi_set_channel(primary, second)` | 设置主/辅信道 |
| `esp_wifi_set_event_mask(mask)` | 屏蔽事件位（默认屏蔽 `AP_PROBEREQRECVED`） |

### 扫描

| API | 说明 |
|---|---|
| `esp_wifi_scan_start(&cfg, block)` | 启动扫描，`block=true` 阻塞直到完成 |
| `esp_wifi_scan_stop()` | 停止正在进行的扫描 |
| `esp_wifi_scan_get_ap_num(&num)` | 获取扫描到的 AP 数量 |
| `esp_wifi_scan_get_ap_records(&num, list)` | 获取扫描结果列表 |
| `esp_wifi_scan_get_ap_record(ap, &record)` | 按索引获取单条扫描记录 |

### 信号/RSSI

| API | 说明 |
|---|---|
| `esp_wifi_get_rssi(&rssi)` | 获取当前连接的 RSSI |
| `esp_wifi_set_rssi_threshold(&rssi_cfg)` | 设置 RSSI 低于阈值时触发 `WIFI_EVENT_STA_BSS_RSSI_LOW` |

## 关键结构体

### `wifi_init_config_t`

初始化参数，**必须**用 `WIFI_INIT_CONFIG_DEFAULT()` 赋值后再覆盖特定字段：

```c
wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
// 常用覆盖项：
cfg.static_rx_buf_num = 10;   // 静态 RX buffer 数量
cfg.static_tx_buf_num = 4;    // 静态 TX buffer 数量
cfg.nvs_enable = 1;           // 是否用 NVS 存配置
cfg.wifi_task_core_id = 0;    // WiFi 任务跑在哪个核
```

### `wifi_config_t`（union）

```c
// STA 配置
wifi_config_t cfg = {
    .sta = {
        .ssid = "AP_SSID",              // 必填
        .password = "password",          // 必填（开放网络置空）
        .channel = 0,                    // 0 = 全信道扫描
        .bssid_set = 0,                  // 是否指定 BSSID
        .scan_method = WIFI_ALL_CHANNEL_SCAN,
        .sort_method = WIFI_CONNECT_AP_BY_SIGNAL,
        .threshold.authmode = WIFI_AUTH_WPA2_PSK,  // 最低认证要求
        .failure_retry_cnt = 3,          // MbedTLS 握手失败重试次数
    },
};
// 然后用 esp_wifi_set_config(WIFI_IF_STA, &cfg) 生效
```

### `wifi_ap_config_t`（AP 模式）

| 字段 | 说明 |
|---|---|
| `ssid` / `password` | AP 凭证 |
| `ssid_len` | 0 = 以 `\0` 结尾；非 0 可含任意字节 |
| `channel` | 信道号 |
| `authmode` | `WIFI_AUTH_OPEN` / `WIFI_AUTH_WPA_PSK` / `WIFI_AUTH_WPA2_PSK` / `WIFI_AUTH_WPA3_PSK` 等 |
| `max_connection` | 最大 STA 接入数（默认 4） |
| `ssid_hidden` | 隐藏 SSID |
| `beacon_interval` | Beacon 间隔 ms（默认 100） |

## WiFi 事件

### WIFI_EVENT（esp_wifi 层）

| 事件 ID | 触发时机 |
|---|---|
| `WIFI_EVENT_STA_START` | `esp_wifi_start()` 完成后 |
| `WIFI_EVENT_STA_STOP` | `esp_wifi_stop()` 完成后 |
| `WIFI_EVENT_STA_CONNECTED` | STA 完成链路认证（802.11 层），但尚未获取 IP |
| `WIFI_EVENT_STA_DISCONNECTED` | STA 断开，`event_data` 含 `reason_code` |
| `WIFI_EVENT_SCAN_DONE` | 扫描完成 |
| `WIFI_EVENT_AP_START` | AP 模式启动完成 |
| `WIFI_EVENT_AP_STOP` | AP 模式停止 |
| `WIFI_EVENT_AP_STACONNECTED` | 有 STA 接入本 AP |
| `WIFI_EVENT_AP_STADISCONNECTED` | 有 STA 离开本 AP |
| `WIFI_EVENT_STA_BSS_RSSI_LOW` | RSSI 低于设定阈值 |

### IP_EVENT（esp_netif 层）

| 事件 ID | 触发时机 |
|---|---|
| `IP_EVENT_STA_GOT_IP` | DHCP 获取到 IP，连接真正可用 |
| `IP_EVENT_STA_LOST_IP` | IP 丢失 |
| `IP_EVENT_AP_STAIPASSIGNED` | AP 模式给接入设备分配了 IP |

### 事件注册模式

```c
// 监听该 event_base 下所有事件
esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, handler, NULL);

// 只监听特定事件
esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, handler, NULL);

// handler 签名
void handler(void *arg, esp_event_base_t base, int32_t id, void *data);
```

## 常见错误码

| 错误码 | 含义 |
|---|---|
| `ESP_ERR_WIFI_NOT_INIT` | `esp_wifi_init()` 未调用 |
| `ESP_ERR_WIFI_NOT_STARTED` | `esp_wifi_start()` 未调用 |
| `ESP_ERR_WIFI_MODE` | 当前 mode 不支持该操作 |
| `ESP_ERR_WIFI_STATE` | 内部状态冲突（如扫描时发起连接） |
| `ESP_ERR_WIFI_CONN` | STA/AP 控制块错误 |
| `ESP_ERR_WIFI_SSID` | SSID 无效 |
| `ESP_ERR_WIFI_PASSWORD` | 密码无效 |
| `ESP_ERR_WIFI_TIMEOUT` | 操作超时 |
| `ESP_ERR_WIFI_NOT_CONNECT` | 当前未连接 |
| `ESP_ERR_WIFI_NVS` | NVS 读写错误 |
| `ESP_ERR_WIFI_MAC` | MAC 地址无效 |

## 参考

- [ESP-IDF WiFi API Reference (v6.0.x)](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_wifi.html)
- [ESP-IDF Wi-Fi Driver Guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/wifi-driver/index.html)

## 相关笔记

- [[nvs api]] — WiFi 配置默认存 NVS
- [[esp32 bootloader]] — 启动流程中 netif 初始化
