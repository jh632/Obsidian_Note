---
tags: [mcuboot, bootloader, ota, 状态机, 掉电恢复, 签名]
date: 2026-09-04
aliases: [MCUboot, mcuboot设计, swap状态机, 镜像trailer]
---

# MCUboot 如何实现 OTA

> MCUboot 是 Zephyr / Mynewt / RIOT/ESPIDF 等生态的默认开源安全 bootloader。它的本质问题只有一句话：**设备在任意时刻掉电的情况下，如何安全地把 Flash 里的新旧固件切换，并且支持失败回滚。**

> 阅读顺序建议：整体模型 → 镜像格式 → Flash 双槽 → Trailer 状态 → Swap 状态机 → 掉电恢复 → 对照 ESP-IDF OTA。

---

## 目录

1. [全局模型](#1-全局模型)
2. [架构拆分：bootutil 与 boot application](#2-架构拆分bootutil-与-boot-application)
3. [镜像格式](#3-镜像格式)
4. [五种升级方式](#4-五种升级方式)
5. [核心状态机：Swap Type](#5-核心状态机swap-type)
6. [Trailer：状态机的持久化载体](#6-trailer状态机的持久化载体)
7. [判定表：从两个 Trailer 反推 Swap Type](#7-判定表从两个-trailer-反推-swap-type)
8. [搬运过程与掉电恢复](#8-搬运过程与掉电恢复)
9. [安全设计](#9-安全设计)
10. [对照 ESP-IDF OTA](#10-对照-esp-idf-ota)

---

## 1. 全局模型

设备 Flash 布局：

```text
Flash
│
├── Bootloader（MCUboot 本身）
│
├── Primary Slot   ← 当前正在运行的固件
│
├── Secondary Slot ← OTA 下载的新固件
│
└── Scratch        ← 搬运缓冲（某些 swap 算法需要）
```

升级前：

```text
Primary Slot                Secondary Slot
┌──────────────────┐        ┌──────────────────┐
│  Firmware V1     │        │  Firmware V2     │
│  正在运行        │        │  OTA 下载完成    │
└──────────────────┘        └──────────────────┘
```

重启后 MCUboot 面临"我要不要运行 V2？"，但它不是简单 `boot(new)`，因为还要回答：

- V2 是否下载完整？签名是否正确？
- V2 启动后崩溃怎么办（回滚）？
- Swap 中途掉电怎么办？Flash 擦一半掉电怎么办？
- 新固件没有确认怎么办？

整个设计围绕三个东西展开：

```text
Image       → 验证镜像是否合法
Trailer     → 记录升级状态（掉电后还能恢复）
Swap 算法   → 保证掉电也不会损坏升级过程
```

---

## 2. 架构拆分：bootutil 与 boot application

```text
                 MCUboot
                    │
      ┌─────────────┴─────────────┐
      │                           │
   bootutil                   boot application
   通用逻辑（平台无关）          平台相关
```

| 组件 | 职责 |
|---|---|
| **bootutil 库** | Image 验证、签名验证、Swap 决策、Trailer 解析、Rollback、升级状态判断 |
| **boot application** | 最后的平台操作：设置 MSP/VTOR、跳转 Reset_Handler（Cortex-M），或其他 MCU 各自的启动方式 |

拆分动机：**bootutil 可以做单元测试，完整 boot application 不容易测**。核心逻辑脱离硬件可测，这是移植到 ESP32/STM32/nRF/NXP 时只改 boot application 的前提。

---

## 3. 镜像格式

一个 MCUboot Image 不是裸 `.bin`：

```text
┌──────────────────┐
│  Image Header    │  描述镜像
├──────────────────┤
│                  │
│  Firmware Body   │  真正代码
│                  │
├──────────────────┤
│  Protected TLV   │  参与 hash 被认证
├──────────────────┤
│  Unprotected TLV │  Signature 等
└──────────────────┘
```

### 3.1 Image Header

```c
struct image_header {
    uint32_t ih_magic;            /* 固定 0x96f3b83d，判断是不是 MCUboot 镜像 */
    uint32_t ih_load_addr;        /* RAM load 时拷贝目标地址；XIP 时无意义 */
    uint16_t ih_hdr_size;         /* header 大小（含 padding） */
    uint16_t ih_protect_tlv_size; /* protected TLV 大小 */
    uint32_t ih_img_size;         /* firmware body 大小（不含 header/TLV） */
    uint32_t ih_flags;            /* IMAGE_F_ENCRYPTED / RAM_LOAD 等 */
    struct image_version ih_ver;  /* major.minor.revision+build_num */
    uint32_t _pad1;
};
```

关键设计：

- **ih_magic**：类似 PNG/ELF 的 magic，bootloader 读取后不对就判非法镜像。
- **ih_hdr_size 不写死 32**：通过 `image_body_addr = slot_addr + ih_hdr_size` 而不是 `+ 32` 计算，这是二进制协议的**向前兼容设计**——未来 header 扩到 48 字节，旧 bootloader 也能跳过。
- **ih_img_size 不含 TLV**：hash 范围由 `ih_hdr_size + ih_img_size + ih_protect_tlv_size` 决定。

### 3.2 TLV：为什么不用固定结构

TLV = Type-Length-Value，天然可扩展。不同产品放不同元数据：

- SHA256 / SHA384 / SHA512（完整性）
- RSA / ECDSA / Ed25519 签名
- KEYHASH（验签密钥的公钥哈希）
- SEC_CNT（安全计数器，防降级）
- DEPENDENCY（多镜像依赖）

### 3.3 Protected TLV 与 Unprotected TLV 的区别

```text
Header + Firmware + Protected TLV
            │
            ▼
         SHA256
            │
            ▼
        Digest
            │
            ▼
     Private Key Sign
            │
            ▼
       Signature
            │
            ▼
    Unprotected TLV
```

- **Protected TLV**：参与签名 hash，内容被认证，不能被改。
- **Unprotected TLV**：不参与 hash（Signature 本身放这里——不然 `Hash(Image + Signature)` 会形成循环依赖）。

---

## 4. 五种升级方式

| 方式 | 需要额外区域 | 特点 |
|---|---|---|
| **swap-using-scratch** | 独立 scratch 区 | 最经典、逻辑最直观；官方标注未来可能移除 |
| **swap-using-offset** | 次槽多一个 sector | 新算法，状态位更省（每 sector 2 个 flag），**官方目前推荐** |
| **swap-using-move** | 主槽多一个 sector | 老算法，仍支持但让位给 offset（每 sector 3 个 flag） |
| **direct-xip** | 无（两槽对等） | 不搬数据，直接执行对应槽；代价是无法做加密镜像 |
| **ram-load** | 无（两槽对等） | 复制到 RAM 执行，适合无 XIP 能力的场景 |

> swap 模式的共同点：**Primary 永远是固定的执行位置**，新固件先从 Secondary 搬到 Primary 才能跑；direct-xip/ram-load 例外。

---

## 5. 核心状态机：Swap Type

整个设计的灵魂。设计哲学是"**先试跑，确认没问题再转正**"，防止坏固件把设备变砖。

```text
BOOT_SWAP_TYPE_NONE   → 正常启动，不升级
BOOT_SWAP_TYPE_TEST   → 尝试新固件（试跑，等应用确认）
BOOT_SWAP_TYPE_PERM   → 永久升级（用户直接要求，不两步走）
BOOT_SWAP_TYPE_REVERT → 回滚旧固件
BOOT_SWAP_TYPE_FAIL   → 新镜像校验不过
BOOT_SWAP_TYPE_PANIC  → 过程中不可恢复错误，直接挂起不启动
```

### 5.1 Test Upgrade（试跑-确认-转正）

```text
初始：Primary = V1，Secondary = V2
  → 应用请求 TEST 升级（boot_request_upgrade(permanent=0)）
  → 重启 → MCUboot 判定 TEST → Swap
  → Primary = V2，Secondary = V1 → Boot V2  （V2 处于"未确认"状态）
  → V2 运行：硬件自检 → 核心业务正常 → boot_set_confirmed()（IMAGE_OK = 1）
  → 下次启动：V2 已被确认 → 保留，升级完成
```

### 5.2 V2 崩溃 → 自动回滚

```text
V2 启动 → Crash → Watchdog Reset
  → 重启 → MCUboot 发现：上次是 TEST，IMAGE_OK 仍然 false
  → REVERT → Swap 回去 → Primary = V1，Secondary = V2 → Boot V1
```

> 对应 ESP-IDF：`esp_ota_mark_app_valid_cancel_rollback()` 就是 IMAGE_OK，不调用就自动回滚，同一个思想。

### 5.3 与 ESP-IDF 回滚时机的对照

你之前问过"回滚标记清空放在 main() 一进来吗"——MCUboot 的答案很明确：**不该**。

```c
// 错误：一进 main 就确认，后面初始化崩了也没法回滚
void app_main(void) {
    confirm_firmware();      // ← 危险
    init_sensor(); init_wifi();
}
```

```c
// 正确顺序：初始化 → 核心服务跑起来 → 自检通过 → 最后确认
void app_main(void) {
    init_system();
    init_core_service();
    start_critical_tasks();
    verify_system_running();
    confirm_firmware();      // ← 最后一步
}
```

---

## 6. Trailer：状态机的持久化载体

状态机要跨掉电重启还记得自己在哪一步，靠每个槽**尾部**的 Trailer：

```text
Primary Slot
┌──────────────────────┐
│ Header               │
├──────────────────────┤
│ Firmware             │
├──────────────────────┤
│ Padding              │
├──────────────────────┤
│ Swap Status          │  搬运进度（最占地方）
│ 加密密钥区（仅加密镜像） │
│ Swap Size            │  这次搬运的总大小，中断恢复用
│ Swap Info            │  低 4 位 = swap type；高 4 位 = 多镜像时是哪个镜像
│ Copy Done            │  本槽搬运是否完成（0xFF=未完成 / 0x01=完成）
│ Image OK             │  本槽镜像是否被确认（0xFF=未确认 / 0x01=已确认）
│ Magic                │  16 字节 trailer 合法性标记
└──────────────────────┘
```

地址计算：`trailer_addr = slot_end - trailer_size`，从槽尾倒推，和镜像写入方向（从头往尾）自然隔离。

Swap Status 大小公式：

```text
Swap Status = BOOT_MAX_IMG_SECTORS（默认 128） × min-write-size × flag 数（3 或 2）
```

> 槽越大、sector 越多，trailer 占比越小；但小 sector 器件上这块开销不能忽略。

---

## 7. 判定表：从两个 Trailer 反推 Swap Type

同时读主槽/次槽的 `magic / image-ok / copy-done` 三个字段，**按固定优先级从上到下匹配**（所以文档用 State I/II/III 编号而不是并列条件）：

| 状态 | 条件（次槽 / 主槽字段） | 结论 |
|---|---|---|
| **State I** | 次槽 magic 有效 + image-ok 未设 + copy-done 已设 | **REVERT**（试跑过但没人确认，要复位） |
| **State II** | 次槽 magic 有效 + image-ok 未设（不管 copy-done） | **TEST** |
| **State III** | 次槽 magic 有效 + image-ok 已设（0x01） | **PERM** |
| **State IV** | 主槽 magic 有效 + image-ok 未设 + copy-done 已设 | **REVERT**（已搬到主槽但没确认） |
| **State V** | 以上都不满足 | **NONE / FAIL / PANIC**，尝试启动主槽 |

`boot_swap_type()` 返回的枚举值就是整个 bootloader 决策的入口：根据它决定"启动主槽 / 执行 swap / 执行 revert"。

---

## 8. 搬运过程与掉电恢复

### 8.1 为什么必须用三等份交换

假设 Primary = A B C，Secondary = X Y Z，直接"擦 A 写 X"掉电就变砖（旧系统损坏且新系统不完整）。所以用 Scratch 三步交换（**swap-using-scratch**，逐 sector 从低到高）：

```text
Step 1: Primary A → Scratch   （备份旧数据）
Step 2: Secondary X → Primary （搬新数据）
Step 3: Scratch A → Secondary （旧数据归位）

第一轮后：Primary = X ..., Secondary = A ..., 然后继续 B↔Y、C↔Z
```

### 8.2 中途掉电：Swap Status 怎么记录进度

Flash 只能擦除后整体写、不能覆写单字节，所以一个 sector 的状态**不能**用 1 条记录改值，而是用 3 条只会从 `0xFF` 递增写成 `0x01/0x02/0x03` 的记录，组合出 4 种状态：

```text
全部 0xFF      → sector 未开始
第 1 条已写    → Step 1 完成（旧数据已备份）
前 2 条已写    → Step 2 完成（新数据已进主槽）
3 条全写      → sector 交换完成
```

掉电重启后读这 3 个字节，就能精确知道该 sector 搬到哪一步，**接着往下做而不是从头再来**。

### 8.3 Reset Recovery（断电恢复定位）

1. 看 magic + copy-done 组合，定位 swap 状态记录在 主槽 / 次槽 / scratch 哪一个；
2. 从 `swap info` 低 4 位解出中断时是哪种 swap type；
3. 从 `swap status` 数组确定已完成到第几个 sector；
4. 从中断点直接继续跑完剩余搬运。

核心思想（可复用到任何掉电保护的嵌入式流程）：

> **不保存"当前执行到哪一行代码"，而是把 Flash 操作拆成多个可恢复的原子步骤，把每步完成状态持久化——Persistent State Machine。**

```text
不要：do_A(); do_B(); do_C(); 然后祈祷不断电。
要：  重启后 switch(state) { case INIT: do_A(); case A_DONE: do_B(); ... }
```

---

## 9. 安全设计

- **完整性**：SHA256 必须匹配；签名（RSA/ECDSA/Ed25519）可选，但只要有签名就必须与 KEYHASH 配对验证（防止换公钥假签名）。
- **防降级**：软件版本号比较（`MCUBOOT_DOWNGRADE_PREVENTION`），或更硬核的**安全计数器**方案——存在 protected TLV 里，单调递增，和版本号解耦，更可靠。
- **加密镜像**：镜像体用对称密钥加密（AES），密钥本身用公钥加密打包进镜像；direct-xip 无法做（Flash 上没法解密执行）。
- **硬件密钥**：`MCUBOOT_HW_KEY` / `MCUBOOT_BUILTIN_KEY`，公钥不放 bootloader 固件里，从硬件（如 OTP）读取。
- **Measured boot / data sharing**：给 runtime 传递启动度量信息，走约定好的共享内存区，与签名验证是两回事。

---

## 10. 对照 ESP-IDF OTA

| MCUboot | ESP-IDF OTA |
|---|---|
| Primary Slot | 当前 running 分区（factory / ota_0 / ota_1） |
| Secondary Slot | 非活动 OTA 分区（`esp_ota_get_next_update_partition`） |
| Image Header | ESP 镜像头 |
| Trailer | otadata 分区 |
| IMAGE_OK / `boot_set_confirmed()` | `esp_ota_mark_app_valid_cancel_rollback()`（PENDING_VERIFY → VALID） |
| TEST Swap | 新固件启动后不调用 mark_app_valid |
| REVERT | 自动回滚旧固件 |
| Swap 决策 | bootloader 读 otadata 选分区 |

**本质区别：搬数据 vs 切指针。**

- MCUboot（swap 模式）：应用链接到 Primary 固定地址，新固件必须**物理搬进** Primary 才能执行，所以需要 trailer + swap status 这套掉电可恢复的搬运状态机。
- ESP-IDF：每个 OTA 分区按自己的链接地址编译，bootloader 只改 otadata **指针**指向新分区，不搬数据——所以它的 otadata 只需要记录"启动哪个分区 + 是否有效"，比 MCUboot 的 trailer 简单得多，代价是相同固件在每个分区各占一份 flash，且换分区必须重新链接/生成。

两者解决的是同一个问题：**A/B 双槽 + 试跑确认 + 失败回滚**，只是 Flash 状态管理方案不同。

---

## 参考

- MCUboot 官方设计文档：https://docs.mcuboot.com/design
- 配套镜像签名/加密实操：https://docs.mcuboot.com/signed_images.html 、https://docs.mcuboot.com/encrypted_images.html
- 核心源码：`boot/bootutil/src/swap_*.c`（判定表与搬运步骤的落地）、`boot/bootutil/src/bootutil_misc.c`

## 相关笔记

- [[ota/ota为什么需要双分区]] — A/B 槽动机
- [[ota/ota如何保障真正的安全]] — 安全链路
- [[esp_idf/03-ESP-IDF-启动流程与OTA]] — ESP-IDF OTA API 与回滚流程
- [[架构/嵌入式设计模式-状态机]] — OTA 状态机设计
- [[zephyr/05-Zephyr-官方组件用法]] — Zephyr MCUboot 组件（待补充）