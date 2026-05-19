# USB OTA 升级状态机

  

## 概述

  

PSA 固件通过 **USB 大容量存储 (MSC)** 实现离线 OTA 升级。核心思路：设备模拟 U 盘，用户将 `ota.bin` 拖入，长按键触发升级。

  

整个流程由一个 **三态状态机** 驱动，模式写入 NVS 后重启切换。

  

---

  

## 架构分层

  

```

┌──────────────────────────────────────────┐

│  comm_ota_usb     U 盘管理层              │

│  udisk 分区读写 · MSC 挂载/卸载 · 文件校验 │

├──────────────────────────────────────────┤

│  ota_service      OTA 烧录层              │

│  esp_ota_begin/write/end · 分区切换 · CRC │

├──────────────────────────────────────────┤

│  ESP-IDF OTA API  Flash 分区操作          │

└──────────────────────────────────────────┘

```

  

---

  

## 三种模式

  

| 模式 | NVS 值 | 启动行为 | TinyUSB 角色 | CDC |

|------|--------|----------|-------------|-----|

| `NORMAL` | 0 | 不做任何事 | 由 `comm_usb` 初始化 CDC | ✓ |

| `MSC` | 1 | 初始化 udisk 并暴露给 USB | MSC 大容量存储 | ✗ |

| `APPLY` | 2 | 挂载 FS → 校验 ota.bin → 导入 → 重启 | MSC（APP 侧） | ✗ |

  

---

  

## 状态转移图

  

```

         ┌─────────────────────────────────┐

         │                                 │

         ▼                                 │

     ┌────────┐  长按松手   ┌───────┐      │

     │ NORMAL │ ──────────→ │  MSC  │      │

     └────────┘             └───┬───┘      │

                               │           │

                 ┌─────────────┼───────────┘

                 │             │

           无 ota.bin    有 ota.bin

                 │             │

                 ▼             ▼

             ┌────────┐   ┌───────┐   启动自动执行

             │ NORMAL │   │ APPLY │ ──────────────┐

             └────────┘   └───┬───┘               │

                              │                   │

                    ┌─────────┴─────────┐         │

                    │                   │         │

                导入成功             导入失败      │

                    │                   │         │

                    ▼                   ▼         │

                ┌────────┐         ┌───────┐      │

                │ NORMAL │         │  MSC  │ ─────┘

                └────────┘         └───────┘  (回 MSC 重试)

```

  

---

  

## 启动流程

  

### main.c 调用链

  

```

app_main()

  │

  ├─ usb_disk_update_boot_prepare(&usb_mode)   // 获取模式 + 执行分流

  │     │

  │     ├─ NORMAL → 直接返回 ESP_OK

  │     ├─ MSC    → init_storage + switch_to_usb → 返回（不阻塞）

  │     └─ APPLY  → run_apply → esp_restart（不返回）

  │

  ├─ comm_init(usb_mode)

  │     │

  │     ├─ NORMAL → 初始化 TinyUSB CDC

  │     └─ MSC/APPLY → 跳过 CDC，只初始化 BLE

  │

  ├─ drivers_init / UI_Start / ...              // 主应用正常运行

  │

  └─ usb_mode_switch_task（后台轮询按键事件）

```

  

### init_for_boot 分流细节

  

```

init_for_boot(handle)

  │

  ├─ NORMAL ──────────────────────────────────────→ return ESP_OK

  │

  ├─ MSC ──→ init_storage()

  │            ① 查找 "udisk" FAT 分区

  │            ② 挂载 Wear-Leveling (wl_mount)

  │            ③ 安装 TinyUSB MSC 驱动

  │            ④ 注册 SPI Flash 存储设备（base_path="/udisk"）

  │        → switch_storage_to_usb()

  │            ① 安装 TinyUSB 设备驱动

  │            ② 切换挂载点 MOUNT_USB（暴露给电脑）

  │        → return ESP_OK    ★ 不阻塞，主应用继续运行

  │

  └─ APPLY ──→ init_storage()（挂载在 APP 侧，不暴露 USB）

            → process_file()

                ① 获取 OTA 目标分区 (esp_ota_get_next_update_partition)

                ② 加载 NVS marker（防重复刷入）

                ③ 检查 /udisk/ota.bin 是否存在

                ④ 计算 CRC32 并校验文件大小

                ⑤ 若 CRC 与 marker 一致 → 跳过（已刷过），删除，重启

                ⑥ import_file → ota_service 逐包写入 Flash

                ⑦ 删除 ota.bin / 更新 marker

                ⑧ 写 NORMAL 到 NVS → esp_restart

            → 失败 → 写 MSC 到 NVS → esp_restart

```

  

---

  

## 按键切换规则

  

按键任务 `usb_mode_switch_task` 轮询标志 `ota_mode_trigger`（由 `driver_key` 长按松手设置）：

  

```

ota_mode_trigger == true:

  │

  ├─ 当前 NORMAL → set_mode(MSC) → esp_restart

  │

  ├─ 当前 MSC ──→ check_ota_file()  // 先切回 APP 侧，再 stat ota.bin

  │     ├─ 存在 ota.bin → set_mode(APPLY) → esp_restart

  │     └─ 无 ota.bin   → set_mode(NORMAL) → esp_restart

  │

  └─ 当前 APPLY → 忽略

```

  

> **注意**：MSC 模式下存储被暴露给 USB Host。`check_ota_file` 会先调用 `switch_storage_to_app()` 将挂载点切回 APP 侧，再检查文件。

  

---

  

## APPLY 模式详细流程

  

```

run_apply(handle)

  │

  ├─ init_storage()  失败 → 写 MSC → 重启

  │

  ├─ process_file()

  │     │

  │     ├─ 无 ota.bin        → 写 MSC → 重启（让用户重新拖入文件）

  │     │

  │     ├─ 处理失败（CRC/IO） → 写 MSC → 重启

  │     │

  │     ├─ 文件已应用（marker匹配）→ 删除 ota.bin → 写 NORMAL → 重启

  │     │

  │     └─ 导入成功 → 删除 ota.bin → 写 NORMAL → 重启

  │

  └─ 安全网：无论过程如何，函数不会返回（最终必定重启）

```

  

### 文件导入子流程 (import_file)

  

```

import_file(path, image_size, image_crc32)

  │

  ├─ ota->init()                         // 重置 OTA 服务状态

  ├─ ota->begin({size, crc32})           // esp_ota_begin，打开目标分区

  ├─ while (未读完):

  │     fread 4KB → ota->write(seq, buf, len)

  │        └─ ota_service_write:

  │             seq 连续性校验

  │             长度不溢出校验

  │             esp_ota_write 写入 Flash

  │             累加 CRC32

  └─ ota->end()

       ├─ 校验 written_size == image_size

       ├─ 校验 final_crc32 == expected_crc32

       ├─ esp_ota_end 关闭写入

       └─ esp_ota_set_boot_partition  标记新分区

```

  

### CRC 双重校验

  

| 位置 | 校验内容 | 目的 |

|---|---|---|

| `calc_file_crc` (comm_ota_usb) | 全文件 CRC32 | 完整性预检 |

| `ota_service_end` (ota_service) | 写入数据的 CRC32 vs 期望值 | Flash 写入正确性 |

  

算法一致：多项式 `0xEDB88320`，初始值 `0xFFFFFFFF`，最终异或取反。

  

---

  

## NVS 存储

  

命名空间：`usb_disk_update`

  

| Key | 类型 | 说明 |

|---|---|---|

| `mode` | u8 | 0=NORMAL, 1=MSC, 2=APPLY |

| `valid` | u8 | marker 有效标志 |

| `size` | u32 | 已刷入固件字节数 |

| `crc32` | u32 | 已刷入固件 CRC32 |

  

**marker 用途**：导入成功后若 `ota.bin` 删除失败，下次启动通过 marker 识别已应用的固件，直接跳过。

  

---

  

## 分区布局

  

```

# partitions.csv

Name     Type  SubType  Offset     Size

nvs      data  nvs      0x9000     0x8000      NVS 存储

fwinfo   data  nvs      0x11000    0x2000      固件信息

otadata  data  ota      0x13000    0x2000      OTA 数据

phy_init data  phy      0x15000    0x1000      PHY 初始化

ota_0    app   ota_0    0x20000    0x2a0000    固件 A (~2.6 MB)

ota_1    app   ota_1    0x2c0000   0x2a0000    固件 B (~2.6 MB)

udisk    data  fat      0x560000   0x2a0000    USB 磁盘空间 (~2.6 MB)

```

  

`udisk` 在 MSC 模式下作为电脑上的 U 盘出现，`ota_0`/`ota_1` 是 ESP-IDF 标准 OTA 双备份区。

  

---

  

## result.txt

  

每次关键操作写入 `/udisk/result.txt`，用户插入电脑即可查看：

  

| 内容 | 含义 |

|---|---|

| `ota file not found` | U 盘内无 ota.bin |

| `ota file stat failed` | 无法读取文件 |

| `ota file too large: size=X limit=Y` | 超过分区容量 |

| `ota init/begin/write/end failed: ...` | OTA 写入阶段错误 |

| `skip applied file: size=X crc=0x...` | 文件已刷过 |

| `ota import done rebooting` | 升级成功 |

| `apply storage init failed` | APPLY 模式存储初始化失败 |

| `apply: ota.bin not found` | APPLY 模式文件缺失 |

  

---

  

## 关键设计决策

  

1. **MSC 模式不阻塞**：设备同时作为 U 盘和运行主应用（UI、传感器、BLE），不再使用死循环 hold。

  

2. **模式切换通过重启**：避免运行时动态切换 TinyUSB 角色，简化驱动管理。

  

3. **APPLY 隔离**：升级逻辑集中在独立的 APPLY 模式，启动即执行，不与正常业务逻辑耦合。

  

4. **CDC/MSC 互斥**：TinyUSB 同一时刻只运行一种角色，避免复合设备复杂性。

  

5. **marker 防重刷**：NVS 记录已刷固件的 size+crc32，防止因文件删除失败导致的重复刷写。