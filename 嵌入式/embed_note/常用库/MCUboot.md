# MCUboot - 安全 Bootloader

## 简介

MCUboot 是一个面向 32 位 MCU 的开源安全引导加载程序，定义了通用的 bootloader 基础设施和 flash 布局约定，提供带完整性/签名校验的可靠固件升级。它起源于 Apache Mynewt 项目，现为独立开放治理项目（mcu-tools）。

MCUboot 不依赖特定操作系统和硬件，通过移植层适配各平台，当前支持的 OS/SoC：

- Zephyr、Apache Mynewt、Apache NuttX、Mbed OS
- RIOT（仅作为启动目标）
- Espressif、Cypress/Infineon

## 核心特点

- **安全启动**：镜像哈希（SHA-256/384/512）+ 签名验证，拒绝无效或被篡改的镜像
- **可靠升级**：swap 过程逐扇区记录状态，掉电/复位后可从中断处恢复，不会损坏镜像
- **自动回滚**：test swap 机制，新镜像未确认则下次启动换回旧镜像，防变砖
- **镜像加密**：支持传输中的镜像加密（升级包解密后落盘）
- **多镜像**：每个镜像独立一对槽位，支持镜像间依赖管理
- **串口恢复**：boot_serial 提供 bootloader 内的串口升级（MCUmgr 协议）

## 架构设计

MCUboot 由两部分组成：

- **bootutil 库**（`boot/bootutil`）：bootloader 核心逻辑（镜像验证、swap 状态机、trailer 管理），与平台无关，可单元测试
- **boot 应用**（`boot/zephyr`、`boot/espressif`、`boot/mynewt` 等）：各平台移植层，只负责最后跳转到应用这一步

> 限制：镜像必须构建为从 flash 固定地址运行（不支持位置无关）。例外是 direct-xip 和 ram-load 模式。

## Flash 布局

```
+----------------------+
| MCUboot              |  FLASH_AREA_BOOTLOADER  (0)
+----------------------+
| Image 0 primary slot |  FLASH_AREA_IMAGE_PRIMARY   (1)
+----------------------+
| Image 0 secondary slot| FLASH_AREA_IMAGE_SECONDARY (2)
+----------------------+
| Scratch（可选）       |  FLASH_AREA_IMAGE_SCRATCH   (3)
+----------------------+
```

- 正常情况只从 **primary slot** 启动，secondary slot 用于暂存新固件
- 升级时把 secondary 的内容搬到 primary（swap/overwrite），例外是 direct-xip 和 ram-load 可以直接从任一槽运行

## 镜像格式

```
+----------------+------------------+---------------+-------------+
| Image header   | 镜像本体          | Protected TLV | TLV 区      |
| (32 字节)      |                  | (可选)        | (元数据)    |
+----------------+------------------+---------------+-------------+
```

**Image header**（32 字节，小端）：

- `ih_magic`：`0x96f3b83d`
- `ih_hdr_size`：头大小（也是镜像本体的起始偏移）
- `ih_img_size`：镜像大小（不含 header）
- `ih_flags`：`IMAGE_F_ENCRYPTED_AES128(0x04)`、`IMAGE_F_ENCRYPTED_AES256(0x08)`、`IMAGE_F_RAM_LOAD(0x20)` 等
- `ih_ver`：版本号 `major.minor.revision + build_num`

**TLV 区**（紧跟镜像尾部，magic `0x6907`，protected 为 `0x6908`）：type + len 记录序列，常用类型：

| TLV | 值 | 含义 |
|------|-----|------|
| SHA256 | 0x10 | 镜像哈希（含 header） |
| RSA2048_PSS | 0x20 | RSA-2048 签名 |
| ECDSA_SIG | 0x22 | ECDSA-P256 签名 |
| RSA3072_PSS | 0x23 | RSA-3072 签名 |
| ED25519 | 0x24 | Ed25519 签名 |
| ENC_EC256 | 0x32 | ECIES-P256 包裹的对称密钥 |
| DEPENDENCY | 0x40 | 镜像依赖（多镜像） |
| SEC_CNT | 0x50 | 安全计数器（防回滚） |

## 升级策略

| 策略 | 配置宏 | 特点 |
|------|--------|------|
| Swap using scratch | 默认（不启用其他策略宏） | 需要额外 scratch 区（≥ 最大扇区）；官方提示未来可能移除 |
| Overwrite-only | `MCUBOOT_OVERWRITE_ONLY` | 新镜像直接覆盖 primary，最简单；不存旧镜像，无法回滚 |
| Swap using move | `MCUBOOT_SWAP_USING_MOVE` | 不需要 scratch，primary 槽多留一个扇区做中转 |
| Swap using offset | `MCUBOOT_SWAP_USING_OFFSET` | **推荐**；secondary 槽多留一个扇区，比 move 少一次擦写 |
| Direct-XIP | `MCUBOOT_DIRECT_XIP` | 双槽等价，镜像按各自地址链接、就地运行，按版本号选最新 |
| RAM load | `MCUBOOT_RAM_LOAD` | 验证后拷贝到 RAM 运行，适合无内部 flash / 外部存储场景 |

> Zephyr 侧另有一层自己的 Kconfig 包装：应用侧为 `MCUBOOT_BOOTLOADER_MODE_*`，sysbuild 为 `MCUBOOT_MODE_*`，名称随版本变动，以当前版本 Kconfig 为准。

- swap 类策略：镜像必须链接到 primary slot 地址，升级 = 搬数据
- direct-xip / ram-load：镜像按各自槽位（或 RAM）地址链接，升级 = 切槽/加载，不支持传输加密（无搬移过程）

## 启动流程

1. 检查 swap status：上一次 swap 是否被复位打断？是 → 恢复完成 swap
2. 检查两侧 trailer：是否请求 swap？
   - 请求且 secondary 镜像验证通过 → 执行 swap，落盘完成标记
   - 验证失败 → 擦除无效镜像
3. 启动 primary slot 的镜像

Swap 类型（决定本次启动行为）：

| 类型 | 含义 |
|------|------|
| `BOOT_SWAP_TYPE_NONE` | 无升级，直接启动 primary |
| `BOOT_SWAP_TYPE_TEST` | 试运行新镜像，未确认则下次回滚 |
| `BOOT_SWAP_TYPE_PERM` | 永久切换到新镜像 |
| `BOOT_SWAP_TYPE_REVERT` | 上次 test 未确认，换回旧镜像 |
| `BOOT_SWAP_TYPE_FAIL` | 待运行镜像无效，挂机不启动 |

**回滚机制**：新镜像启动后必须自检通过并调用确认 API（把 trailer 的 image OK 写为 0x01）；否则下次复位 MCUboot 自动 revert。设备崩溃后只需一次复位即可回到旧镜像。

## 镜像 Trailer

每个槽位末尾存放的元数据，MCUboot 据此判断当前状态：

```
高地址端从后往前：
| MAGIC (16B) | image OK (1B) | copy done (1B) | swap info (1B)
| swap size (4B) | 加密 KEK x2 (16B each) | swap status |
```

- **MAGIC**：16 字节特征值，有效说明该槽有合法 trailer
- **copy done**：swap 是否完成（0x01 = 完成）
- **image OK**：新镜像是否被应用确认（0x01 = 确认），回滚依据
- **swap status**：每扇区记录 swap 进度（受 flash 最小写入粒度影响），掉电恢复的核心
- **swap info**：低 4 位为 swap 类型，高 4 位为多镜像时的镜像编号

注意：trailer 会占用槽位空间（swap status 可达上 KB），计算最大镜像尺寸时要扣除。

## 签名与加密

签名密钥支持：RSA-2048、RSA-3072、ECDSA P-256、Ed25519。

**imgtool** 是官方签名/密钥管理工具（Python）：

```bash
pip install imgtool

# 生成密钥
imgtool keygen -k root-ec-p256.pem -t ecdsa-p256

# 签名（以 Zephyr 应用为例）
imgtool sign --key root-ec-p256.pem \
    --header-size 0x200 --align 4 \
    --version 1.0.0 --slot-size 0x60000 --pad-header \
    zephyr.bin zephyr.signed.bin
```

**镜像加密**（`MCUBOOT_ENC_IMAGES`）：升级包用 AES-128/256 加密传输，对称密钥再被 KEK（RSA-OAEP / AES-KW / ECIES-P256 / ECIES-X25519）加密后放进 TLV，bootloader 在 swap 时边搬边解密落盘。

> 加密镜像落盘到 primary 后是**明文**，只防传输链路，不防 flash 读出。代码保密需配合芯片的 flash 加密（如 ESP32 Flash Encryption）。

## Zephyr 集成

1. `CONFIG_BOOTLOADER_MCUBOOT=y`，构建时自动启用镜像签名
2. devicetree 划分区：`boot_partition`、`slot0_partition`、`slot1_partition`（及可选 `scratch_partition`）
3. 上游 MCUboot 经 west module 引入，位于 `bootloader/mcuboot`
4. 应用侧 API（`<zephyr/dfu/mcuboot.h>`）：
   - `boot_request_upgrade(BOOT_UPGRADE_TEST)`：标记升级（test 或 permanent）
   - `boot_write_img_confirmed()`：新镜像自检通过后确认自己
5. 升级包写入 secondary slot 由 SMP/MCUmgr（如 nRF Connect Device Manager）或应用自身下载完成

## 在 ESP32 上使用

- MCUboot 的 Espressif 移植（`boot/espressif`）支持 ESP32 全系列（ESP32/S2/C3/S3/C2/C6/H2/C5/C61/P4）
- 典型用法是在 **Zephyr 或 NuttX** 里作为 bootloader（ESP-IDF 作为 HAL 源码也可独立构建 MCUboot）
- ESP-IDF 自身的 OTA 体系（双 ota 分区 + otadata 切指针，`esp_ota_*` API）**不使用 MCUboot**，两者是平行的方案
- 与 ESP-IDF OTA 的本质区别：ESP-IDF 只写 otadata 切换启动分区（零拷贝），MCUboot 靠 swap 把新镜像搬到 primary（或 direct-xip 切槽），换来统一的签名/回滚/多平台语义

## 常用配置项

| 配置 | 说明 |
|------|------|
| `BOOT_SIGNATURE_TYPE_RSA / _ECDSA_P256 / _ED25519` | 签名算法选择（bootloader Kconfig，Zephyr 构建的 MCUboot） |
| `MCUBOOT_ENC_IMAGES` | 启用镜像加密 |
| `MCUBOOT_VALIDATE_PRIMARY_SLOT` | 每次启动都验证 primary 镜像（默认只在 swap 后验证一次） |
| `MCUBOOT_OVERWRITE_ONLY` / `MCUBOOT_SWAP_USING_MOVE` / `MCUBOOT_SWAP_USING_OFFSET` / `MCUBOOT_DIRECT_XIP` / `MCUBOOT_RAM_LOAD` | 升级策略选择（互斥，只能启用一个） |
| `MCUBOOT_DIRECT_XIP_REVERT` | direct-xip 的回滚支持（镜像需 `--pad` 加 trailer） |
| `MCUBOOT_RAM_LOAD_REVERT` | ram-load 的回滚支持 |
| `MCUBOOT_DOWNGRADE_PREVENTION` | 防降级：新镜像版本不高于当前版本时拒绝升级 |
| `MCUBOOT_SERIAL` | 启用串口恢复（boot_serial） |
| `MCUBOOT_USE_TLV_ALLOW_LIST` | 启用非保护 TLV 白名单校验 |
| `BOOT_MAX_IMG_SECTORS` | 支持的最大扇区数，默认 128，小扇区大 flash 需调大 |

## 调试

- **镜像验证失败**：核对签名算法/密钥一致、`--header-size` 与链接脚本偏移一致、`--slot-size` 与分区一致
- **不触发 swap**：升级包未签名带 trailer、版本号不满足、trailer 状态未清（用 `imgtool` 签名时确认参数）
- **回滚循环**：新镜像忘了调 `boot_write_img_confirmed()`（Zephyr）/ 确认 API
- 官方 `sim/` 模拟器可对 swap 状态机做回归测试，调试掉电恢复逻辑时很有用

## 参考资源

- 官方文档：https://docs.mcuboot.com/
- 设计文档：https://docs.mcuboot.com/design.html
- GitHub 仓库：https://github.com/mcu-tools/mcuboot
- Espressif 移植说明：https://docs.mcuboot.com/readme-espressif.html
- imgtool：https://docs.mcuboot.com/imgtool.html

## 相关笔记

- [[ota为什么需要双分区]]
- [[ota如何保障真正的安全]]
- [[ESP32启动流程与Bootloader]]
- [[嵌入式系统启动流程与 Bootloader 核心笔记]]
