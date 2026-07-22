---
date: 2026-07-17
tags: [nimble, esp32, ble, gatt, api]
aliases: [NimBLE API, NimBLE 基础]
---

# NimBLE API 基础

## 初始化流程总览

一个 NimBLE Peripheral 应用的完整初始化路径：

```
app_main()
├── nvs_flash_init()                    // 1. NVS 初始化（BLE 配对密钥存储在此）
├── nimble_port_init()                  // 2. Controller + Host 底层初始化
├── ble_hs_cfg 配置回调                  // 3. 注册 Host 事件回调
├── gatt_svr_init()                     // 4. 定义并注册 GATT 服务
├── ble_svc_gap_device_name_set()       // 5. 设置 GAP 设备名称
├── ble_store_config_init()             // 6. 安全材料存储配置
└── nimble_port_freertos_init()         // 7. 启动 NimBLE Host 任务
    └── sync_cb 触发
        └── ble_gap_adv_start()         // 8. 开始广播
```

## 头文件

```c
// NimBLE 核心
#include "nimble/nimble_port.h"         // nimble_port_init(), nimble_port_stop()
#include "nimble/nimble_port_freertos.h" // nimble_port_freertos_init()

// BLE Host
#include "host/ble_hs.h"                // ble_hs_cfg, ble_hs_id_infer_auto()
#include "host/ble_uuid.h"              // BLE_UUID128_INIT() 等 UUID 宏

// GAP/GATT 服务（自动注册 GAP/GATT 基础服务）
#include "services/gap/ble_svc_gap.h"   // ble_svc_gap_device_name_set()
#include "services/gatt/ble_svc_gatt.h" // ble_svc_gatt_init()
```

## 1. nimble_port_init()

```c
esp_err_t ret = nimble_port_init();
```

这个函数内部完成：
1. 创建 `esp_bt_controller_config_t`（使用 `BT_CONTROLLER_INIT_CONFIG_DEFAULT()` 默认配置）
2. `esp_bt_controller_init()` + `esp_bt_controller_enable()` — 初始化并使能 BT Controller
3. `esp_nimble_init()` — 初始化 NimBLE Host（HCI 事件队列、内存池、Host 层）
4. `ble_hs_init()` — 初始化 Host 层

> 这一步之后，Controller 和 Host 都已就绪，但还没有配置任何应用层逻辑。

## 2. ble_hs_cfg 回调配置

`ble_hs_cfg` 是全局 Host 配置结构体，必须在 `nimble_port_freertos_init()` 之前设置：

```c
ble_hs_cfg.reset_cb = on_reset;          // Host 复位回调（Controller 出错时触发）
ble_hs_cfg.sync_cb = on_sync;            // Host 与 Controller 同步完成（可以开始操作了）
ble_hs_cfg.gatts_register_cb = on_register; // GATT 服务/特征注册完成回调
ble_hs_cfg.store_status_cb = ble_store_util_status_rr; // 安全材料存储状态
```

### 回调触发时机

```
nimble_port_freertos_init()
    │
    ├── 创建 Host 任务
    │
    ├── reset_cb ──→ Host 复位时调用（BLE Controller 重启等）
    │
    ├── gatts_register_cb ──→ 每注册一个 service/characteristic/descriptor 调用一次
    │
    └── sync_cb ──→ Host 与 Controller 同步完成
                    在这里做：获取 MAC 地址、启动广播
```

### on_reset 回调

```c
static void on_reset(int reason)
{
    ESP_LOGE(TAG, "BLE Host reset, reason=%d", reason);
    // reason: BLE_HS_EUNKNOWN, BLE_HS_EOS 等
}
```

### on_sync 回调（关键）

```c
static void on_sync(void)
{
    int rc;

    // 1. 获取并打印本机 MAC 地址
    uint8_t addr_val[6] = {0};
    int addr_type;
    rc = ble_hs_id_infer_auto(0, &addr_type);
    assert(rc == 0);
    rc = ble_hs_id_copy_addr(addr_type, addr_val, NULL);
    ESP_LOGI(TAG, "Device Address: %02x:%02x:%02x:%02x:%02x:%02x",
             addr_val[5], addr_val[4], addr_val[3],
             addr_val[2], addr_val[1], addr_val[0]);

    // 2. 开始广播
    bleprph_advertise();
}
```

> `sync_cb` 是真正"BLE 系统就绪"的标志。在此之前不能调用 GAP 相关 API。

## 3. GATT 服务定义

### 服务表结构

NimBLE 用一个结构体数组定义整个 GATT 数据库：

```c
// 自定义 128-bit UUID（用在线工具生成：https://www.uuidgenerator.net/）
static const ble_uuid128_t my_svc_uuid =
    BLE_UUID128_INIT(0x2d, 0x71, 0xa2, 0x59, 0xb4, 0x58, 0xc8, 0x12,
                     0x99, 0x99, 0x43, 0x95, 0x12, 0x2f, 0x46, 0x59);

static const ble_uuid16_t my_chr_uuid =
    BLE_UUID16_INIT(0x2A37);  // SIG 定义的 16-bit UUID

// 特征值句柄（NimBLE 分配后通过此指针写入）
static uint16_t my_chr_val_handle;

// 服务表
static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        // ---- 服务 1 ----
        .type = BLE_GATT_SVC_TYPE_PRIMARY,   // 主服务
        .uuid = &my_svc_uuid.u,              // 服务 UUID
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = &my_chr_uuid.u,       // 特征 UUID
                .access_cb = my_chr_access,    // 读写回调
                .flags = BLE_GATT_CHR_F_READ |
                         BLE_GATT_CHR_F_WRITE |
                         BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &my_chr_val_handle, // 存储分配的 handle
            },
            {0}, // 结尾标记
        },
    },
    {0}, // 所有服务结束
};
```

### ble_gatt_svc_def 关键字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | `BLE_GATT_SVC_TYPE_PRIMARY` | 主服务（几乎总是用这个） |
| `uuid` | `ble_uuid_t *` | 服务 UUID，16-bit 或 128-bit |
| `characteristics` | `ble_gatt_chr_def[]` | 特征数组，以 `{0}` 结尾 |

### ble_gatt_chr_def 关键字段

| 字段 | 说明 |
|---|---|
| `uuid` | 特征 UUID |
| `access_cb` | **读写回调函数**，所有操作都经过这里 |
| `flags` | 权限标志（组合使用） |
| `val_handle` | 指针，NimBLE 注册后写入实际 handle 值 |
| `descriptors` | 描述符数组（如 CCCD），可选 |

### flags 权限标志

```c
// 读写权限
BLE_GATT_CHR_F_READ                    // 允许读
BLE_GATT_CHR_F_WRITE_NO_ENC            // 允许无加密写
BLE_GATT_CHR_F_WRITE_ENC               // 允许加密后写
BLE_GATT_CHR_F_READ_ENC                // 允许加密后读

// 通知/指示
BLE_GATT_CHR_F_NOTIFY                  // 允许通知（无需确认）
BLE_GATT_CHR_F_INDICATE                // 允许指示（需要确认）

// 其他
BLE_GATT_CHR_F_WRITE                   // 允许写（含响应）
BLE_GATT_CHR_F_WRITE_NO_RSP            // 允许无响应写
```

### CCCD 描述符（通知开关）

当 flags 包含 `NOTIFY` 或 `INDICATE` 时，NimBLE 会**自动添加 CCCD 描述符**（UUID `0x2902`），无需手动定义。客户端通过写 CCCD 来开启/关闭通知或指示。

## 4. 特征值读写回调

这是最核心的回调——所有对特征的读/写操作都经过这里：

```c
static int
my_chr_access(uint16_t conn_handle, uint16_t attr_handle,
              struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    switch (ctxt->op) {

    case BLE_GATT_ACCESS_OP_READ_CHR:
        // 客户端读取特征值
        // 把数据追加到 ctxt->om 即可
        return os_mbuf_append(ctxt->om, &my_value, sizeof(my_value));

    case BLE_GATT_ACCESS_OP_WRITE_CHR:
        // 客户端写入特征值
        // 从 ctxt->om 读取数据
        return gatt_svr_write(ctxt->om,
                              sizeof(my_value),   // 最小长度
                              sizeof(my_value),   // 最大长度
                              &my_value,           // 目标变量
                              NULL);

    case BLE_GATT_ACCESS_OP_READ_DSC:
        // 描述符读取
        return os_mbuf_append(ctxt->om, &my_dsc_val, sizeof(my_dsc_val));

    default:
        return BLE_ATT_ERR_UNLIKELY;
    }
}
```

### write 辅助函数

NimBLE 不提供通用 write 辅助，通常自己写一个：

```c
static int
gatt_svr_write(struct os_mbuf *om, uint16_t min_len, uint16_t max_len,
               void *dst, uint16_t *len)
{
    uint16_t om_len = OS_MBUF_PKTLEN(om);
    if (om_len < min_len || om_len > max_len) {
        return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
    }
    return ble_hs_mbuf_to_flat(om, dst, max_len, len);
}
```

### 关键参数说明

| 参数 | 说明 |
|---|---|
| `conn_handle` | 连接句柄，用于后续 notify/indicate 时标识目标 |
| `attr_handle` | 被访问属性的句柄，用于区分同一服务内的不同特征 |
| `ctxt->op` | 操作类型：READ_CHR / WRITE_CHR / READ_DSC / WRITE_DSC |
| `ctxt->om` | `os_mbuf` 指针，读时追加数据，写时从中读取数据 |
| `ctxt->chr` | 当前特征的定义指针（包含 uuid 等） |

## 5. GATT 服务注册

在 `app_main` 中调用，将服务表注册到 NimBLE Host：

```c
int gatt_svr_init(void)
{
    int rc;

    // 1. 初始化 GAP 和 GATT 基础服务
    ble_svc_gap_init();     // GAP Service (0x1800)
    ble_svc_gatt_init();    // GATT Service (0x1801)

    // 2. 计算需要的 handle 数量
    rc = ble_gatts_count_cfg(gatt_svr_svcs);
    if (rc != 0) return rc;

    // 3. 注册所有服务
    rc = ble_gatts_add_svcs(gatt_svr_svcs);
    if (rc != 0) return rc;

    return 0;
}
```

调用顺序**不能变**：`ble_svc_gap_init()` → `ble_svc_gatt_init()` → `ble_gatts_count_cfg()` → `ble_gatts_add_svcs()`

## 6. 广播配置

### 广播参数

```c
static void bleprph_advertise(void)
{
    struct ble_gap_adv_params adv_params;
    struct ble_hs_adv_fields fields;

    // --- 广播数据字段 ---
    memset(&fields, 0, sizeof(fields));

    // Flags（必填）
    fields.flags = BLE_HS_ADV_F_DISC_GEN |
                   BLE_HS_ADV_F_BREDR_NOTSUP;
    // DISC_GEN    = 通用可发现（General Discoverable）
    // BREDR_NOTSUP = 不支持经典蓝牙（Only LE）

    // 设备名称（放在广播数据中，方便扫描时看到）
    fields.name = (uint8_t *)"ESP32-BLE";
    fields.name_len = strlen("ESP32-BLE");
    fields.name_is_complete = 1;

    // 服务 UUID（可选，告诉扫描者你提供什么服务）
    fields.uuids16 = (struct ble_hs_adv_uuid_array[]){
        { .uuid = (ble_uuid_t *)&my_svc_uuid },
    };
    fields.num_uuids16 = 1;
    fields.uuids16_is_complete = 1;

    ble_gap_adv_set_fields(&fields);

    // --- 广播间隔等参数 ---
    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;   // 非定向可连接
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;   // 通用可发现
    adv_params.itvl_min  = 0x20;  // 最小广播间隔 (32 * 0.625ms = 20ms)
    adv_params.itvl_max  = 0x40;  // 最大广播间隔 (64 * 0.625ms = 40ms)

    // --- 启动广播 ---
    int rc = ble_gap_adv_start(
        BLE_HS_OWN_ADDR_PUBLIC,    // 地址类型
        NULL,                       // 不限定扫描者
        BLE_HS_FOREVER,             // 永久广播
        &adv_params,                // 广播参数
        bleprph_gap_event,          // GAP 事件回调
        NULL                        // 用户参数
    );
    if (rc != 0) {
        ESP_LOGE(TAG, "error enabling advertisement; rc=%d", rc);
    }
}
```

### conn_mode 与 disc_mode

| conn_mode | 含义 |
|---|---|
| `BLE_GAP_CONN_MODE_NON` | 不可连接 |
| `BLE_GAP_CONN_MODE_DIR` | 定向可连接（只回应特定设备） |
| `BLE_GAP_CONN_MODE_UND` | 非定向可连接（任意设备可连） |

| disc_mode | 含义 |
|---|---|
| `BLE_GAP_DISC_MODE_NON` | 不可发现 |
| `BLE_GAP_DISC_MODE_LTD` | 有限可发现 |
| `BLE_GAP_DISC_MODE_GEN` | 通用可发现（最常用） |

## 7. GAP 事件回调

处理连接、断开、订阅等所有 GAP 层事件：

```c
static int
bleprph_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {

    case BLE_GAP_EVENT_CONNECT:
        // 连接建立
        if (event->connect.status == 0) {
            ESP_LOGI(TAG, "Connection established, handle=%d", event->connect.conn_handle);
        } else {
            // 连接失败，重新广播
            ESP_LOGE(TAG, "Connection failed, status=%d", event->connect.status);
            bleprph_advertise();
        }
        return 0;

    case BLE_GAP_EVENT_DISCONNECT:
        // 连接断开，重新广播
        ESP_LOGI(TAG, "Disconnected, reason=%d", event->disconnect.reason);
        bleprph_advertise();
        return 0;

    case BLE_GAP_EVENT_SUBSCRIBE:
        // 客户端订阅通知/指示
        ESP_LOGI(TAG, "subscribe event: conn_handle=%d attr_handle=%d "
                 "notify=%d indicate=%d",
                 event->subscribe.conn_handle,
                 event->subscribe.attr_handle,
                 event->subscribe.cur_notify,
                 event->subscribe.cur_indicate);
        return 0;

    case BLE_GAP_EVENT_MTU:
        // MTU 协商完成
        ESP_LOGI(TAG, "MTU updated: %d", event->mtu.value);
        return 0;

    default:
        return 0;
    }
}
```

### 常见 GAP 事件

| 事件 | 说明 |
|---|---|
| `BLE_GAP_EVENT_CONNECT` | 连接建立或失败 |
| `BLE_GAP_EVENT_DISCONNECT` | 连接断开 |
| `BLE_GAP_EVENT_SUBSCRIBE` | 客户端订阅/取消订阅 |
| `BLE_GAP_EVENT_MTU` | MTU 协商完成 |
| `BLE_GAP_EVENT_ADV_COMPLETE` | 广播完成（超时） |
| `BLE_GAP_EVENT_PAIRING_REQUEST` | 收到配对请求 |
| `BLE_GAP_EVENT_ENC_CHANGE` | 加密状态变化 |

## 8. 发送通知/指示

当特征值变化时，主动推送给已连接的客户端：

```c
// 发送通知（无需客户端确认）
int rc = ble_gatts_notify(conn_handle, val_handle);

// 发送指示（需要客户端确认）
int rc = ble_gatts_indicate(conn_handle, val_handle);

// 先更新值再发送
static void update_and_notify(uint16_t conn_handle)
{
    // 更新值（修改全局变量或缓存）
    my_sensor_value = read_sensor();

    // 触发通知给所有已订阅的客户端
    ble_gatts_chr_updated(val_handle);
    // 或指定连接：
    // ble_gatts_notify(conn_handle, val_handle);
}
```

> **notify vs indicate**：notify 不等确认，快但可能丢包；indicate 等 ACK，可靠但慢。传感器数据一般用 notify。

## 9. 启动 NimBLE Host 任务

```c
// 在 app_main 最后调用
nimble_port_freertos_init(bleprph_host_task);

// Host 任务函数
void bleprph_host_task(void *param)
{
    ESP_LOGI(TAG, "BLE Host Task Started");
    // nimble_port_run() 会阻塞，直到 nimble_port_stop() 被调用
    nimble_port_run();
    nimble_port_freertos_deinit();
}
```

`nimble_port_freertos_init()` 内部调用 `esp_nimble_enable()`，创建一个 FreeRTOS 任务运行 NimBLE Host。Host 在这个独立任务中处理所有异步事件（HCI 命令、ATT 请求等）。

## 最小完整模板

```c
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *tag = "BLE_APP";

/* ---- GATT 定义 ---- */
static const ble_uuid16_t svc_uuid = BLE_UUID16_INIT(0x180F); // Battery Service
static const ble_uuid16_t chr_uuid = BLE_UUID16_INIT(0x2A19); // Battery Level
static uint16_t chr_val_handle;

static int chr_access(uint16_t conn, uint16_t attr,
                      struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        uint8_t level = 85;
        return os_mbuf_append(ctxt->om, &level, sizeof(level));
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static const struct ble_gatt_svc_def svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = &chr_uuid.u,
                .access_cb = chr_access,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &chr_val_handle,
            },
            {0},
        },
    },
    {0},
};

/* ---- GAP 事件 ---- */
static int gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status != 0) {
            // 连接失败，重新广播
            ble_gap_adv_start(BLE_HS_OWN_ADDR_PUBLIC, NULL,
                              BLE_HS_FOREVER, &(struct ble_gap_adv_params){
                                  .conn_mode = BLE_GAP_CONN_MODE_UND,
                                  .disc_mode = BLE_GAP_DISC_MODE_GEN,
                              }, gap_event, NULL);
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        // 断开后重新广播
        ble_gap_adv_start(BLE_HS_OWN_ADDR_PUBLIC, NULL,
                          BLE_HS_FOREVER, &(struct ble_gap_adv_params){
                              .conn_mode = BLE_GAP_CONN_MODE_UND,
                              .disc_mode = BLE_GAP_DISC_MODE_GEN,
                          }, gap_event, NULL);
        break;
    }
    return 0;
}

/* ---- Host 回调 ---- */
static void on_reset(int reason) { ESP_LOGE(tag, "reset, reason=%d", reason); }

static void on_sync(void)
{
    uint8_t addr[6];
    ble_hs_id_copy_addr(BLE_HS_OWN_ADDR_PUBLIC, addr, NULL);
    ESP_LOGI(TAG, "MAC: %02x:%02x:%02x:%02x:%02x:%02x",
             addr[5], addr[4], addr[3], addr[2], addr[1], addr[0]);

    // 开始广播
    ble_gap_adv_start(BLE_HS_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                      &(struct ble_gap_adv_params){
                          .conn_mode = BLE_GAP_CONN_MODE_UND,
                          .disc_mode = BLE_GAP_DISC_MODE_GEN,
                      }, gap_event, NULL);
}

static void host_task(void *param)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

/* ---- 入口 ---- */
void app_main(void)
{
    // NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // NimBLE 初始化
    ESP_ERROR_CHECK(nimble_port_init());

    // Host 配置
    ble_hs_cfg.reset_cb = on_reset;
    ble_hs_cfg.sync_cb = on_sync;
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ESP_ERROR_CHECK(ble_gatts_count_cfg(svcs));
    ESP_ERROR_CHECK(ble_gatts_add_svcs(svcs));
    ESP_ERROR_CHECK(ble_svc_gap_device_name_set("ESP32-BLE"));

    // 启动
    nimble_port_freertos_init(host_task);
}
```

## 常见 API 速查

| API | 用途 |
|---|---|
| `nimble_port_init()` | 初始化 Controller + Host |
| `nimble_port_freertos_init(task_fn)` | 启动 Host 任务 |
| `ble_svc_gap_init()` | 注册 GAP 基础服务 |
| `ble_svc_gatt_init()` | 注册 GATT 基础服务 |
| `ble_svc_gap_device_name_set(name)` | 设置设备名称 |
| `ble_gatts_count_cfg(svcs)` | 计算服务表所需 handle 数 |
| `ble_gatts_add_svcs(svcs)` | 注册服务表 |
| `ble_gap_adv_start(...)` | 启动广播 |
| `ble_gap_adv_stop()` | 停止广播 |
| `ble_gatts_notify(conn, handle)` | 发送通知 |
| `ble_gatts_indicate(conn, handle)` | 发送指示 |
| `ble_gatts_chr_updated(handle)` | 值变化后触发通知/指示 |
| `ble_hs_id_infer_auto()` | 推断本机地址类型 |
| `ble_hs_id_copy_addr()` | 获取本机 MAC 地址 |
| `ble_hs_mbuf_to_flat()` | os_mbuf → 普通内存 |
| `os_mbuf_append(om, data, len)` | 追加数据到 os_mbuf |

## 小结

| 要点 | 内容 |
|---|---|
| 初始化顺序 | NVS → nimble_port_init → 配置回调 → GATT 注册 → 启动任务 |
| `sync_cb` 是起点 | Host 就绪后才能做 GAP 操作（获取 MAC、开始广播） |
| 服务表用结构体数组 | `ble_gatt_svc_def[]`，以 `{0}` 结尾 |
| 读写都走 `access_cb` | 通过 `ctxt->op` 区分读/写 |
| CCCD 自动添加 | flags 含 NOTIFY/INDICATE 时自动加 |
| 断开后要重新广播 | 在 `BLE_GAP_EVENT_DISCONNECT` 中调用 `ble_gap_adv_start()` |
