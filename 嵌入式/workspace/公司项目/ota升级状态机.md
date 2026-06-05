# ESP32-S3 OTA 升级技术文档

  

## 版本历史

  

| 版本 | 日期 | 作者 | 说明 |

|------|------|------|------|

| v1.0 | 2026-05-20 | 固件组 | 初始版本 |

  

---

  

## 1. 概述

  

本项目的 OTA（Over-The-Air）升级采用 **USB 大容量存储设备 (MSC) + 本地文件导入** 方案。设备通过 TinyUSB 协议栈将内部 Flash 的一个 FAT 分区暴露为 USB 可移动磁盘，用户在 PC 上将编译好的固件文件 `ota.bin` 拖入该磁盘，设备识别到文件后自动完成固件校验、写入 OTA 分区、切换启动分区并重启。

  

### 1.1 方案选型理由

  

- **无需网络/WiFi**：设备不依赖网络连接，规避了 OTA 服务器运维、TLS 证书管理等复杂性

- **USB 即插即用**：利用设备已有的 USB 接口，PC 端无需安装任何驱动或工具软件

- **防重复应用机制**：通过 NVS 持久化已应用固件的 CRC32 与大小，避免同一固件被反复刷写

- **日志可追溯**：升级过程日志写入 U 盘上的 `log.txt`，便于问题定位

  

### 1.2 整体架构

  

```

┌──────────────────────────────────────────────────────────┐

│                      main.c (boot)                       │

│                  comm_init() → boot_prepare()             │

│       根据 NVS 中的 mode 决定本次启动进入哪个分支            │

└────────┬──────────┬──────────┬───────────────────────────┘

         │          │          │

    NORMAL         MSC       APPLY

    (正常模式)    (U盘模式)   (升级模式)

         │          │          │

    CDC + BLE   挂载 FAT    挂载 FAT 分区

    通信任务    暴露 MSC    校验 ota.bin

         │          │       CRC32 → ota_service

         │          │       写入 OTA 分区

         │          │       设置启动分区

         │          │       清理文件 → 重启

         │          │

         └──────────┴──────────┐

                               │

                    长按按键触发模式切换

                    request_mode_switch()

                               │

                     NORMAL → MSC → APPLY

```

  

---

  

## 2. 分区布局

  

### 2.1 分区表 (`partitions.csv`)

  

| Name | Type | SubType | Offset | Size | 说明 |

|------|------|---------|--------|------|------|

| nvs | data | nvs | 0x9000 | 0x8000 (32KB) | 系统 NVS |

| fwinfo | data | nvs | 0x11000 | 0x2000 (8KB) | 设备出厂信息（不随 OTA 改变） |

| otadata | data | ota | 0x13000 | 0x2000 (8KB) | OTA 数据分区（记录当前启动槽位） |

| phy_init | data | phy | 0x15000 | 0x1000 (4KB) | PHY 初始化数据 |

| ota_0 | app | ota_0 | 0x20000 | 0x2a0000 (2688KB) | OTA 应用槽位 0 |

| ota_1 | app | ota_1 | 0x2c0000 | 0x2a0000 (2688KB) | OTA 应用槽位 1 |

| udisk | data | fat | 0x560000 | 0x2a0000 (2688KB) | USB 磁盘分区（FAT，存放 ota.bin） |

  

### 2.2 Flash 空间分配示意

  

```

0x000000 ┌──────────────┐

         │  Bootloader  │

0x009000 ├──────────────┤

         │     NVS      │  32KB

0x011000 ├──────────────┤

         │   fwinfo     │  8KB   (出厂设备信息，只读不写)

0x013000 ├──────────────┤

         │   otadata    │  8KB   (ESP-IDF OTA 管理)

0x015000 ├──────────────┤

         │  phy_init    │  4KB

0x020000 ├──────────────┤

         │              │

         │    ota_0     │  2688KB (运行槽位 A)

         │              │

0x2C0000 ├──────────────┤

         │              │

         │    ota_1     │  2688KB (运行槽位 B)

         │              │

0x560000 ├──────────────┤

         │              │

         │    udisk     │  2688KB (USB 磁盘，FAT 文件系统)

         │              │

0x800000 └──────────────┘  (8MB Flash 结束)

```

  

---

  

## 3. 核心模块详解

  

### 3.1 ota_service — OTA 核心服务层

  

**文件**: `components/application/communication/ota_service.c` / `ota_service.h`

  

对 ESP-IDF 原生 `esp_ota_*` API 的薄封装，提供一组标准的 OTA 操作接口。

  

#### 3.1.1 状态机

  

```

                 init()

    IDLE ────────────────────→ (就绪)

      ↑                          │

      │                    begin(args)

      │                          │

      │                          ↓

      │                    RECEIVING ──→ write(seq, data, len)

      │                       │              (循环调用)

      │                       │

      │                    end() / abort()

      │                       │

      │                  ┌────┴────┐

      │                  ↓         ↓

      │              FINISHED   ERROR/IDLE

      │                  │         ↑

      └──────────────────┘─────────┘

              (abort 可随时从任何状态回到 IDLE)

```

  

#### 3.1.2 操作接口

  

```c

typedef struct {

    esp_err_t (*init)(void);                                    // 初始化，重置上下文

    esp_err_t (*begin)(const ota_service_begin_args_t *args);   // 开始 OTA（传参: 镜像大小 + CRC32）

    esp_err_t (*write)(uint16_t seq, const uint8_t *data, uint16_t len); // 按序号写数据块

    esp_err_t (*end)(void);                                     // 结束 OTA，校验 CRC 并切换启动分区

    esp_err_t (*abort)(void);                                   // 中止 OTA

    const ota_service_status_t *(*get_status)(void);            // 获取当前状态

} ota_service_ops_t;

```

  

#### 3.1.3 CRC32 校验流程

  

1. `begin()` 时记录期望的 `image_crc32`

2. `write()` 每次写入时增量更新本地 CRC32（初始值 `0xFFFFFFFF`）

3. `end()` 时对最终 CRC32 取反，与期望值比对

4. 校验失败调用 `esp_ota_abort()` 并重置上下文，防止刷入损坏固件

  

CRC32 算法采用标准 Ethernet/gzip 多项式 `0xEDB88320`，与 Python `binascii.crc32` 兼容。

  

#### 3.1.4 序号校验

  

`write()` 内部维护 `last_seq`，每次期望序号为 `last_seq + 1`（首包为 0）。序号不匹配时拒绝写入，防止数据乱序或丢包。

  

#### 3.1.5 错误处理

  

任何步骤失败均调用 `ota_service_set_error()` 将状态设置为 `OTA_SERVICE_ERROR`，后续所有操作都会被拒绝直到调用 `init()` 或 `abort()` 重置。

  

---

  

### 3.2 comm_ota_usb — USB 磁盘升级模块

  

**文件**: `components/application/communication/comm_ota_usb.c` / `comm_ota_usb.h`

  

本项目的核心升级通道，实现完整的 USB MSC 升级流程。

  

#### 3.2.1 三种运行模式

  

| 模式 | 枚举值 | 行为 |

|------|--------|------|

| NORMAL | 0 | 常规 CDC 串口 + BLE 通信，不暴露 USB 磁盘 |

| MSC | 1 | 挂载 FAT 分区，通过 TinyUSB MSC 暴露为 USB 可移动磁盘 |

| APPLY | 2 | 挂载 FAT 分区，查找并应用 `ota.bin`，完成后重启 |

  

#### 3.2.2 模式状态机

  

```

        ┌──────────┐    长按按键     ┌──────────┐

        │  NORMAL  │ ──────────────→ │   MSC    │

        │ (正常)   │                 │ (U盘模式) │

        └────┬─────┘                 └────┬─────┘

             ↑                            │

             │         长按按键            │

             │  ←──────────────────────   │

             │    (如果无 ota.bin)         │

             │                            │

             │              长按按键       │

             │  ←──────────────────────   │

             │     (如果有 ota.bin)        │

             │                            ↓

             │                       ┌──────────┐

             └───────────────────────│  APPLY   │

                   升级完成后自动      │ (应用升级)│

                                     └──────────┘

```

  

#### 3.2.3 NVS 持久化键

  

使用 NVS 命名空间 `usb_disk_update` 存储：

  


| Key | 类型 | 说明 |

|-----|------|------|

| `mode` | u8 | 当前运行模式 (0/1/2) |

| `valid` | u8 | 固件标记有效标志 |

| `size` | u32 | 已应用固件的文件大小 |

| `crc32` | u32 | 已应用固件的 CRC32 校验值 |

  

#### 3.2.4 升级流程（APPLY 模式）

  

```

boot_prepare()

    │

    ├── 从 NVS 读取 mode

    ├── mode == APPLY:

    │       │

    │       ├── usb_disk_update_init_storage()

    │       │   ├── 查找 "udisk" 分区

    │       │   ├── wl_mount() (wear-leveling 挂载)

    │       │   └── tinyusb_msc_new_storage_spiflash() (注册 MSC 存储)

    │       │

    │       ├── usb_disk_update_process_file()

    │       │   ├── 查找 OTA 分区

    │       │   ├── 从 NVS 加载已应用固件的 marker

    │       │   ├── 检查 ota.bin 是否存在

    │       │   │   └── 不存在且 marker 有效 → 清理 marker

    │       │   │

    │       │   ├── usb_disk_update_calc_file_crc()

    │       │   │   ├── 校验文件大小 ≤ OTA 分区大小

    │       │   │   └── 逐 4KB 块读取文件计算 CRC32

    │       │   │

    │       │   ├── 防重复: 比对 marker 中的 size/crc32

    │       │   │   └── 一致 → 删除文件 + 清理 marker → 返回

    │       │   │

    │       │   ├── usb_disk_update_import_file()

    │       │   │   ├── ota_service.init()

    │       │   │   ├── ota_service.begin(image_size, image_crc32)

    │       │   │   ├── loop: fread 4KB → ota_service.write(seq, buf, len)

    │       │   │   └── ota_service.end()

    │       │   │       ├── CRC32 最终校验

    │       │   │       ├── esp_ota_end()

    │       │   │       └── esp_ota_set_boot_partition() (切换启动分区)

    │       │   │

    │       │   ├── 删除 ota.bin

    │       │   └── 清理 marker (文件删除成功时) / 保存 marker (删除失败时)

    │       │

    │       ├── 写入 NVS mode = NORMAL (成功) / MSC (失败)

    │       └── esp_restart()

    │

    ├── mode == MSC:

    │       ├── 初始化存储

    │       ├── 清空 log.txt

    │       ├── 切换 MSC 挂载点到 USB

    │       └── 返回 (主应用继续运行，USB 磁盘暴露给 PC)

    │

    └── mode == NORMAL:

            └── 直接返回，正常初始化 CDC + BLE

```

  

#### 3.2.5 TinyUSB MSC 集成

  

- 使用 ESP-IDF `tinyusb_msc` 组件实现 USB MSC 设备

- MSC 挂载点在 `APP` 和 `USB` 之间动态切换：

  - `TINYUSB_MSC_STORAGE_MOUNT_APP`：挂载到本地文件系统，设备可读写

  - `TINYUSB_MSC_STORAGE_MOUNT_USB`：暴露给 USB 主机，PC 可读写

- 切换时自动安装/卸载 TinyUSB 驱动，避免与 CDC 驱动冲突

  

#### 3.2.6 日志系统

  

升级过程日志通过内存缓冲区缓存（4KB），关键节点写入 U 盘 `log.txt`：

  

```

[t_ms=12345] msc mode start

[t_ms=13500] ota file found: size=1048576 crc=0xA1B2C3D4

[t_ms=15800] ota import done

[t_ms=15900] apply mode done

```

  

日志格式: `[t_ms=启动毫秒数] 事件描述`，支持设备断电后的离线问题追溯。

  

---

  

### 3.3 按键触发机制

  

**文件**: `components/drivers/sensor/driver_key/driver_key.c`

  

- 使用 `multi_button` 库管理按键事件

- **长按松手**：触发 `ota_mode_trigger = true`

- `communication.c` 中的 `usb_mode_switch_task` 轮询此标志，调用 `request_mode_switch()` 执行切换

  

```c

// driver_key.c - 按键回调

void Pwron_press_up_handler(void *btn) {

    if (!s_ota_long_press_armed) return;

    s_ota_long_press_armed = false;

    ota_mode_trigger = true;

}

  

// communication.c - 模式切换任务

void usb_mode_switch_task(void *pvParameters) {

    while (1) {

        if (!ota_mode_trigger) { vTaskDelay(100ms); continue; }

        ota_mode_trigger = false;

        ops->request_mode_switch();  // 执行切换 → 写 NVS → 重启

    }

}

```

  

---

  

## 4. 编译与打包

  

### 4.1 工具链

  

| 脚本 | 路径 | 功能 |

|------|------|------|

| `combine_firmware_ota.py` | `script/` | 完整固件合并 + OTA 包生成 |

| `generate_fwinfo.py` | `script/` | 设备出厂信息生成（fwinfo 分区） |

  

### 4.2 OTA 固件包结构

  

执行 `python combine_firmware_ota.py --ota` 后在 `script/ota_package/` 生成：

  

```

ota_package/

├── ota_firmware.bin              # 应用程序固件 (即 build/项目名.bin 的副本)

├── manifest.json                 # 固件元数据

└── 项目名-v1.0.0-260520.zip      # 压缩包（供分发）

```

  

### 4.3 manifest.json 格式

  

```json

{

  "format_version": "1.0",

  "firmware": {

    "version": "1.0.0",

    "project_name": "esp32s3_template",

    "file_name": "esp32s3_template.bin",

    "file_size": 1048576,

    "sha256": "a1b2c3...",

    "md5": "d4e5f6..."

  },

  "build": {

    "date": "2026-05-20",

    "time": "14:30:00",

    "timestamp": 1747720200,

    "idf_version": "v5.3.4",

    "c_compiler": "xtensa-esp32s3-elf-gcc"

  },

  "target": {

    "chip": "esp32s3",

    "min_chip_rev": 0

  }

}

```

  

### 4.4 常用命令

  

```bash

# 仅生成 OTA 固件包

python combine_firmware_ota.py --ota

  

# 同时生成完整固件 + OTA 包 + 设备信息

python combine_firmware_ota.py --with-fwinfo --serial SN00001 --ota

  

# 生成设备信息（交互模式）

python generate_fwinfo.py

  

# 生成设备信息（命令行）

python generate_fwinfo.py --serial SN00001 --product MyDevice --hwver v2.0

  

# 批量生成设备信息（100 台）

python generate_fwinfo.py --serial SN00001 --batch 100

```

  

---

  

## 5. 操作流程

  

### 5.1 用户操作步骤

  

```

步骤 1: 设备正常运行时（NORMAL 模式），长按按键

        → 设备重启进入 MSC 模式

        → PC 上出现一个可移动磁盘

  

步骤 2: 将 ota_firmware.bin 重命名为 ota.bin，拖入该磁盘

        等待文件复制完成

  

步骤 3: 再次长按按键

        → 设备检查到 ota.bin 存在

        → 重启进入 APPLY 模式

        → 自动校验并刷入固件

        → 刷入完成后删除 ota.bin

        → 再次重启回到 NORMAL 模式，运行新固件

```

  

### 5.2 设备内部时序

  

```

   NORMAL                MSC                    APPLY                 NORMAL

     │                    │                       │                     │

     │  长按按键           │                       │                     │

     ├──────────────────→│                       │                     │

     │  重启              │                       │                     │

     │                    │  PC 复制 ota.bin       │                     │

     │                    │←──────────→│           │                     │

     │                    │  长按按键   │           │                     │

     │                    ├──────────→│           │                     │

     │                    │  重启      │           │                     │

     │                    │            │  校验 CRC  │                     │

     │                    │            │  写入 OTA  │                     │

     │                    │            │  切换启动槽 │                     │

     │                    │            ├──────────→│                     │

     │                    │            │  重启      │  运行新固件          │

```

  

### 5.3 异常恢复

  

| 异常场景 | 系统行为 |

|----------|----------|

| ota.bin 文件损坏（CRC32 不匹配） | `ota_service.end()` 检测到 CRC 不匹配 → `esp_ota_abort()` → 回到 MSC 模式 |

| 写入过程中断电 | 重启后 `ota_service` 上下文丢失 → 下次进入 MSC 模式，用户重新放入文件 |

| ota.bin 大于 OTA 分区 | `calc_file_crc()` 拒绝 → 日志记录 → 回到 MSC 模式 |

| 重复放入同一固件 | NVS marker 匹配 → 直接删除文件，不重复刷写 |

| 升级后 OTA 分区切换失败 | `esp_ota_set_boot_partition()` 返回错误 → 状态置为 ERROR |

| NVS 损坏 | `nvs_flash_init()` 自动尝试擦除重建 → 模式回退到 NORMAL |

  

---

  

## 6. 关键数据结构

  

### 6.1 ota_service_status_t

  

```c

typedef struct {

    ota_service_state_t state;    // 当前状态: IDLE/RECEIVING/FINISHED/ERROR

    uint32_t            image_size;   // 期望的固件总大小

    uint32_t            written_size; // 已写入字节数

    uint16_t            last_seq;     // 上次写入的序号

} ota_service_status_t;

```

  

### 6.2 usb_disk_update_marker_t (NVS 持久化)

  

```c

typedef struct {

    bool     valid;        // 标记是否有效

    uint32_t image_size;   // 固件文件大小

    uint32_t image_crc32;  // 固件 CRC32

} usb_disk_update_marker_t;

```

  

### 6.3 ota_service_begin_args_t

  

```c

typedef struct {

    uint32_t image_size;   // 固件镜像总大小

    uint32_t image_crc32;  // 固件镜像 CRC32（0 表示跳过校验）

} ota_service_begin_args_t;

```

  

---

  

## 7. 依赖项

  

### 7.1 ESP-IDF 组件

  

| 组件 | 用途 |

|------|------|

| `esp_ota_ops` | OTA 操作 API（begin/write/end/set_boot_partition） |

| `esp_partition` | 分区查找与读写 |

| `app_update` | OTA 数据分区管理 |

| `tinyusb` / `tinyusb_msc` | USB MSC 设备协议栈 |

| `wear_levelling` | Flash 磨损均衡（FAT 分区底层） |

| `esp_vfs_fat` | FAT 文件系统 VFS 挂载 |

| `nvs_flash` | 非易失存储（模式持久化 + marker 存储） |

  

### 7.2 Python 工具依赖

  

- Python 3.6+

- 标准库：`os`, `sys`, `json`, `struct`, `hashlib`, `argparse`, `zipfile`, `datetime`, `pathlib`, `binascii`

  

---

  

## 8. 固件信息管理

  

### 8.1 fwinfo 分区

  

- 独立分区（8KB），仅在工厂烧录时写入一次

- 存储设备硬件信息（产品名称、型号、序列号、硬件版本、出厂固件版本等）

- CRC32 校验保护

- OTA 升级**不会**修改此分区

  

### 8.2 版本信息读取

  

```c

// 当前运行固件版本（来自 esp_app_desc，OTA 后自动更新）

fwinfo_get_current_fw_version();

  

// 出厂固件版本（来自 fwinfo 分区，永不改变）

fwinfo_get_factory_fw_version();

```

  

---

  

## 9. 安全设计要点

  

| 机制 | 实现位置 | 说明 |

|------|----------|------|

| CRC32 全量校验 | `ota_service.c:end()` | 所有数据块写入完成后，对固件整体 CRC32 校验 |

| 包序号校验 | `ota_service.c:write()` | 防止数据块乱序或丢失 |

| 大小边界检查 | `comm_ota_usb.c:calc_file_crc()` | 拒绝超过 OTA 分区大小的固件 |

| 防重复应用 | `comm_ota_usb.c:process_file()` | NVS 持久化 marker 防止同一固件反复刷写 |

| 闪存磨损均衡 | `wl_mount()` | FAT 分区使用 wear-leveling，延长 Flash 寿命 |

| 启动槽隔离 | ESP-IDF OTA | 使用 ota_0/ota_1 双槽位 + otadata 管理，升级失败不影响当前运行固件 |

  

---

  

## 10. 测试验证清单

  

- [x] NORMAL 模式启动正常（CDC + BLE 通信正常） ✅ 2026-05-20

- [x] 长按按键能正确触发模式切换（NORMAL → MSC） ✅ 2026-05-20

- [x] MSC 模式下 PC 能识别可移动磁盘 ✅ 2026-05-20

- [x] 拖入 ota.bin 后文件系统能正确读写 ✅ 2026-05-20

- [x] MSC → APPLY 模式切换正常 ✅ 2026-05-20

- [x] APPLY 模式正确完成固件导入和 CRC32 校验 ✅ 2026-05-20

- [x] 升级后设备自动重启并运行新固件 ✅ 2026-05-20

- [ ] 版本号读取正确更新（`fwinfo_get_current_fw_version()`）

- [ ] 重复拖入同一固件文件不会重复刷写

- [ ] 放入无效/损坏的 ota.bin 不会刷入

- [ ] 放入超过分区大小的固件被正确拦截

- [ ] 升级过程中断电后恢复能力

- [ ] log.txt 日志正确记录升级过程