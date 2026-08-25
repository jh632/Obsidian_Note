# NimBLE - 蓝牙低功耗协议栈

## 简介

Apache NimBLE 是一个完全开源的蓝牙低功耗（BLE）协议栈，完全符合蓝牙 5.0 核心规范，支持蓝牙 Mesh。它是 Apache Mynewt 项目的一部分，专为资源受限的嵌入式系统设计。

## 核心特点

- **蓝牙 5.0 合规**：支持所有蓝牙 5.0 特性
- **内存高效**：优化 RAM 和 ROM 使用
- **模块化设计**：可灵活配置和扩展
- **跨平台**：支持多种操作系统和硬件平台
- **开源**：Apache 2.0 许可证

## 架构组件

### 物理层（Physical Layer）
- 自适应跳频高斯频移键控（GFSK）无线电
- 使用 40 个 RF 通道（0-39），2 MHz 间隔

### 链路层（Link Layer）
五种状态之一在任意时刻激活：
1. Standby（待机）
2. Advertising（广播）
3. Scanning（扫描）
4. Initiating（发起）
5. Connection（连接）

### 逻辑链路控制和适配协议（L2CAP）
- 提供逻辑通道，多路复用
- 分段和重组、流控制、错误控制
- 支持 L2CAP 连接导向通道（CoC）

### 安全管理（SM）
- 使用安全管理协议（SMP）
- 配对和密钥分发
- 支持传统配对和安全连接（LE SC）

### 属性协议（ATT）
- 允许设备暴露数据属性
- 支持服务端和客户端模型

### 通用属性配置文件（GATT）
- 使用 ATT 协议交换属性
- 封装为特征（Characteristics）或服务（Services）

### 通用访问配置文件（GAP）
- 定义所有蓝牙设备的基础配置
- 管理设备发现、连接、配对

### 主机控制器接口（HCI）
- 主机和控制器之间的接口
- 支持软件 API 和硬件接口（SPI、UART、USB）

## 蓝牙 5.0 特性支持

### 已支持特性
- **2M PHY**：需要硬件支持
- **编码 PHY（LE 长距离）**：需要硬件支持
- **LE 广播扩展**：支持链式广播（最大 1650 字节）
- **LE 周期性广播**：支持链式广播
- **LE 信道选择算法 #2**
- **高占空比非连接广播**

### 蓝牙 5.1 特性
- 到达角度（AoA）：需要硬件支持
- 离开角度（AoD）：需要硬件支持
- GATT 缓存
- 周期性广播同步传输

### 蓝牙 5.2 特性
- LE 同步通道
- 增强属性协议（Enhanced ATT）
- LE 功率控制

## 蓝牙 Mesh 支持

### 已支持特性
- 广播和 GATT 承载
- PB-GATT 和 PB-ADV 配网
- 基础模型（服务器角色）
- 中继支持
- GATT 代理
- 低功耗节点
- Friend 节点

## 初始化流程

### 1. 初始化蓝牙控制器
```c
// ESP-IDF 示例
esp_err_t ret = nvs_flash_init();
if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
}
ESP_ERROR_CHECK(ret);

ret = nimble_port_init();
if (ret != ESP_OK) {
    ESP_LOGE(tag, "Failed to init nimble %d ", ret);
    return;
}
```

### 2. 配置主机
```c
// 初始化 NimBLE 主机配置
ble_hs_cfg.reset_cb = bleprph_on_reset;
ble_hs_cfg.sync_cb = bleprph_on_sync;
ble_hs_cfg.gatts_register_cb = gatt_svr_register_cb;
ble_hs_cfg.store_status_cb = ble_store_util_status_rr;

// 配置安全管理
ble_hs_cfg.sm_io_cap = CONFIG_EXAMPLE_IO_TYPE;
#ifdef CONFIG_EXAMPLE_BONDING
ble_hs_cfg.sm_bonding = 1;
ble_hs_cfg.sm_our_key_dist |= BLE_SM_PAIR_KEY_DIST_ENC;
ble_hs_cfg.sm_their_key_dist |= BLE_SM_PAIR_KEY_DIST_ENC;
#endif

#ifdef CONFIG_EXAMPLE_MITM
ble_hs_cfg.sm_mitm = 1;
#endif

#ifdef CONFIG_EXAMPLE_USE_SC
ble_hs_cfg.sm_sc = 1;
#endif
```

### 3. 初始化 GATT 服务器
```c
int gatt_svr_init(void)
{
    int rc = 0;

#if CONFIG_BT_NIMBLE_GAP_SERVICE
    ble_svc_gap_init();
#endif
#if MYNEWT_VAL(BLE_GATTS)
    ble_svc_gatt_init();
#endif

    rc = ble_gatts_count_cfg(new_ble_svc_gatt_defs);
    if (rc != 0) {
        return rc;
    }

    rc = ble_gatts_add_svcs(new_ble_svc_gatt_defs);
    if (rc != 0) {
        return rc;
    }

    return 0;
}
```

### 4. 设置设备名称
```c
rc = ble_svc_gap_device_name_set("nimble-bleprph");
assert(rc == 0);
```

### 5. 启动 NimBLE 任务
```c
nimble_port_freertos_init(bleprph_host_task);
```

## GAP（通用访问配置文件）

### 设备发现
- **广播**：设备发送可发现广播包
- **扫描**：其他设备监听广播
- **发起**：建立连接前的最后一步

### 连接建立
```c
// 启动广播
struct ble_gap_adv_params adv_params;
memset(&adv_params, 0, sizeof(adv_params));
adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;
rc = ble_gap_adv_start(own_addr_type, NULL, BLE_HS_FOREVER,
                       &adv_params, bleprph_gap_event, NULL);
```

### GAP 事件回调
```c
static int
bleprph_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            // 处理连接事件
            break;
        case BLE_GAP_EVENT_DISCONNECT:
            // 处理断开事件
            break;
        case BLE_GAP_EVENT_ADV_COMPLETE:
            // 处理广播完成事件
            break;
        // ... 其他事件
    }
    return 0;
}
```

## GATT（通用属性配置文件）

### 服务定义
```c
static const struct ble_gatt_svc_def new_ble_svc_gatt_defs[] = {
    {
        /*** Service: SPP */
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(BLE_SVC_SPP_UUID16),
        .characteristics = (struct ble_gatt_chr_def[])
        { {
            /* 支持 SPP 服务 */
            .uuid = BLE_UUID16_DECLARE(BLE_SVC_SPP_CHR_UUID16),
            .access_cb = ble_svc_gatt_handler,
            .val_handle = &ble_spp_svc_gatt_read_val_handle,
            .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_NOTIFY,
        }, {
            0, /* 没有更多特征 */
        } },
    },
    {
        0, /* 没有更多服务 */
    },
};
```

### 特征标志
- `BLE_GATT_CHR_F_READ`：可读
- `BLE_GATT_CHR_F_WRITE`：可写
- `BLE_GATT_CHR_F_NOTIFY`：支持通知
- `BLE_GATT_CHR_F_INDICATE`：支持指示

### GATT 事件处理
```c
static int
ble_svc_gatt_handler(uint16_t conn_handle, uint16_t attr_handle,
                     struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    switch (ctxt->op) {
        case BLE_GATT_ACCESS_OP_READ_CHR:
            // 处理读取请求
            break;
        case BLE_GATT_ACCESS_OP_WRITE_CHR:
            // 处理写入请求
            break;
        case BLE_GATT_ACCESS_OP_READ_DSC:
            // 处理描述符读取
            break;
        case BLE_GATT_ACCESS_OP_WRITE_DSC:
            // 处理描述符写入
            break;
    }
    return 0;
}
```

## SMP（安全管理协议）

### 安全特性
- **传统配对**：Legacy Pairing
- **安全连接**：LE Secure Connections
- **MITM 保护**：中间人攻击防护
- **绑定**：密钥存储和恢复

### IO 能力配置
```c
// 配置 IO 能力
ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_DISP_ONLY;  // 仅显示
ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_INPUT_ONLY;  // 仅输入
ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_IO;          // 输入输出
ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_NONE;        // 无 IO
```

### 静态密码配置
```c
// 设置静态密码（仅用于演示）
ble_sm_configure_static_passkey(456789, true);
```

## 线程模型

### FreeRTOS 集成
```c
// 创建 NimBLE 主机任务
nimble_port_freertos_init(bleprph_host_task);

// 主机任务函数
void bleprph_host_task(void *pvParameters)
{
    // NimBLE 主循环
    while (1) {
        ble_npl_eventq_run(&g_eventq_dflt);
    }
}
```

### 事件队列
- 使用事件队列处理异步操作
- 支持多任务并发

## 存储管理

### 安全材料存储
```c
// 配置存储回调
ble_store_config_init();

// 存储操作回调
ble_hs_cfg.store_status_cb = ble_store_util_status_rr;
```

### 支持的存储操作
- 密钥存储
- 绑定信息存储
- 白名单存储

## 配置选项

### menuconfig 选项
- `CONFIG_BT_NIMBLE_ENABLED`：启用 NimBLE
- `CONFIG_BT_NIMBLE_MAX_CONNECTIONS`：最大连接数
- `CONFIG_BT_NIMBLE_GAP_SERVICE`：启用 GAP 服务
- `CONFIG_BT_NIMBLE_GATT_ENABLED`：启用 GATT

### 编译时配置
- 禁用未使用的功能以节省内存
- 调整缓冲区大小
- 配置最大属性数

## 示例项目

### bleprph（BLE 外设）
基本外设设备示例：
- 自动启动广播
- 连接终止后恢复广播
- 支持最大一个连接

### btshell（BLE 命令行）
简单 shell 应用：
- 提供主机侧 BLE 栈的基本接口
- 支持命令行操作

### blemesh（蓝牙 Mesh）
蓝牙 Mesh 节点示例：
- 使用 on/off 模型
- 演示 Mesh 网络功能

## 调试和日志

### 日志配置
```c
// 启用详细日志
MODLOG_DFLT(INFO, "message");
MODLOG_DFLT(ERROR, "error message");
MODLOG_DFLT(DEBUG, "debug message");
```

### 常见问题排查
1. **初始化失败**：检查 NVS 初始化和蓝牙控制器配置
2. **连接失败**：验证广播参数和 GAP 配置
3. **配对失败**：检查 SMP 配置和 IO 能力
4. **内存不足**：调整缓冲区大小和最大连接数

## 参考资源

- 官方文档：https://mynewt.apache.org/latest/network/
- GitHub 仓库：https://github.com/apache/mynewt-nimble
- ESP-IDF NimBLE 示例：https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/nimble
- 蓝牙 5.0 规范：https://www.bluetooth.com/specifications/specs/core-specification-5-0/