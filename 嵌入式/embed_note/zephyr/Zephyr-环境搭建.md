---
date: 2026-06-01
tags: [zephyr, rtos, toolchain, environment-setup, windows]
aliases: [Zephyr-Setup]
---

# Zephyr 环境搭建

## 概述
Zephyr RTOS 开发环境在 **Windows 11 + Git Bash** 下的搭建记录。使用 `west` 管理代码，复用已有 ARM GCC 工具链进行编译。

## 目录结构

```
/d/zephyr/                   # 工作区根目录
├── zephyr/                  # Zephyr 内核源码（ZEPHYR_BASE）
├── modules/                 # 第三方模块（TF-M, segger, zcbor 等）
├── bootloader/              # MCUboot 等引导加载程序
├── tools/                   # 工具
├── build/                   # 编译输出
└── .west/                   # west 元数据
```

## 安装步骤

### 前置条件
| 工具 | 版本 | 来源 |
|---|---|---|
| Python | 3.12.10 | 已有 |
| CMake | 4.3.2 | 已有 |
| Ninja | 1.13.2 | 已有 |
| ARM GCC | 10.3-2021.10 | 已有 |

### 1. 安装 west
```bash
pip install west
```

### 2. 初始化工作区
```bash
west init -m https://github.com/zephyrproject-rtos/zephyr --mr v4.1.0 /d/zephyr
cd /d/zephyr && west update
```

### 3. 安装 Python 依赖
```bash
pip install -r zephyr/scripts/requirements.txt
```

### 4. 配置环境变量（`~/.bashrc.d/zephyr`）
```bash
export ZEPHYR_TOOLCHAIN_VARIANT=gnuarmemb
export GNUARMEMB_TOOLCHAIN_PATH="/c/Program Files (x86)/GNU Arm Embedded Toolchain/10 2021.10"
```
可用快捷命令进入工作区：
```bash
zephyr_setup
```

## 常用命令

```bash
# 编译 hello_world（qemu_cortex_m3）
west build -p auto -b qemu_cortex_m3 zephyr/samples/hello_world

# 编译其他板子（如 nRF52840）
west build -p auto -b nrf52840dk/nrf52840 path/to/app

# 清理并重建
west build -p always -b <board> <app>

# 查看可用板型
west boards

# 运行 menuconfig
west build -t menuconfig

# 查看 flash/ram 占用
west build -t ram_report
west build -t rom_report
```

## 注意点（踩坑记录）

### ⚠️ 中文用户名导致 DTS 编码错误
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbd in position 14
```
- **原因**: 用户名含中文（`蒋瀚`），MSYS2 的 C 预处理器将中文路径以 GBK/UTF-8 混合编码写入 `.dts.pre` 文件，Python 读取时无法解析。
- **解决**: Zephyr 工作区**必须放在无中文的路径**（如 `/d/zephyr`），不能放在 `~/zephyr` 下。
- 环境变量配置在 `.bashrc.d/zephyr` 中，路径都是 `/d/zephyr/...`。

### 已知约束
- Zephyr SDK 在 Windows 上支持有限，ARM GCC 工具链可用于 ARM 目标（STM32、nRF、LPC 等）。
- ESP32 / RISC-V 目标需要对应工具链。
- 在 Git Bash 下编译，不要用 PowerShell（编码和路径问题）。

## 参考
- [Zephyr 官方文档 - Getting Started](https://docs.zephyrproject.org/latest/develop/getting_started/index.html)
- [Zephyr v4.1.0 Release](https://github.com/zephyrproject-rtos/zephyr/releases/tag/v4.1.0)
- [West 命令参考](https://docs.zephyrproject.org/latest/develop/west/index.html)

## 相关笔记
- [[TI RTOS和Free RTOS]]
- [[工具链/Claude-Code.md]]
- [[工具链/clang-format-Linux内核风格.md]]
