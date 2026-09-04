---
tags: [esp-idf, esp32, idf.py, esptool, 构建, 固件打包, 分区表]
date: 2026-09-01
aliases: [常用idf命令, esptool, merge-bin, ESP-IDF构建工具, idf.py]
---

# ESP-IDF 项目结构与构建工具

> 2026-09-01 由原《常用idf命令》《固件打包》整理合并，并补充 ESP-IDF 标准工程结构与常用构建流程。

---

## 目录

1. [工程目录结构](#1-工程目录结构)
2. [idf.py 常用命令](#2-idfpy-常用命令)
3. [esptool.py 常用命令](#3-esptoolpy-常用命令)
4. [固件打包（merge-bin）](#4-固件打包merge-bin)
5. [常见烧录流程](#5-常见烧录流程)

---

## 1. 工程目录结构

一个标准的 ESP-IDF 工程通常包含：

```
my_project/
├── CMakeLists.txt          # 工程级构建配置
├── main/                   # 主应用源码目录
│   ├── CMakeLists.txt      # 主组件构建配置（源文件/依赖）
│   └── main.c              # 入口函数 app_main()
├── components/             # 自定义组件（可选）
├── sdkconfig               # 生成的项目配置（Kconfig 结果）
├── sdkconfig.defaults      # 默认配置覆盖文件
├── partition_table.csv     # 自定义分区表（可选）
└── README.md
```

| 文件/目录 | 作用 |
|---|---|
| `CMakeLists.txt` | 定义构建规则，查找 ESP-IDF 组件 |
| `main/CMakeLists.txt` | 声明 main 组件的源文件、依赖组件（`REQUIRES`） |
| `sdkconfig` | 构建时由 Kconfig 生成的配置，**不要手动改** |
| `sdkconfig.defaults` | 项目自定义默认配置，改动后需 `idf.py save-defconfig` 固化 |
| `partition_table.csv` | 自定义分区表（Type/SubType/Offset/Size） |

---

## 2. idf.py 常用命令

`idf.py` 是 ESP-IDF 的命令行入口，本质是对 CMake + Ninja + esptool 的封装。

### 2.1 构建与烧录

| 命令 | 作用 |
|---|---|
| `idf.py build` | 编译工程（增量构建） |
| `idf.py flash` | 编译并烧录到设备（默认 0x0 起始，自动识别分区） |
| `idf.py flash monitor` | 烧录后打开串口监视器 |
| `idf.py monitor` | 监视设备串口输出（可组合：`idf.py -p COM24 monitor`） |
| `idf.py menuconfig` | 图形化配置（Kconfig） |
| `idf.py clean` | 清理构建产物（保留配置） |
| `idf.py fullclean` | 完全清理（含 sdkconfig 重新生成） |
| `idf.py set-target esp32s3` | 切换目标芯片（如 esp32 / esp32s3 / esp32c3） |

### 2.2 配置管理

```bash
idf.py save-defconfig   # 保存 sdkconfig 的更改到 sdkconfig.defaults
```

> `save-defconfig` 会把当前 `sdkconfig` 中的配置项精简后写入 `sdkconfig.defaults`，是固化项目配置的标准方式。

### 2.3 分区表与固件工具

| 命令 | 作用 |
|---|---|
| `idf.py partition-table` | 打印当前分区表布局 |
| `idf.py merge-bin` | 合并 bootloader + partition-table + app 为单个 bin |
| `idf.py size` / `size-components` | 查看固件体积构成（内存/代码段） |
| `idf.py erase-flash` | 擦除整个 flash（等价 esptool erase_flash） |

---

## 3. esptool.py 常用命令

`esptool.py` 是底层烧录/芯片工具，`idf.py` 内部也在用它。直接调用时需指定串口（`-p`）与芯片型号（`--chip`）。

| 命令 | 作用 |
|---|---|
| `esptool.py -p COM24 --chip esp32s3 chip_id` | 探查芯片信息：MAC 地址、型号、晶振、chip id |
| `esptool.py -p COM24 flash_id` | 探查 flash 信息：flash 厂家和大小 |
| `esptool.py -p COM24 erase_flash` | 擦除整个 flash |
| `esptool.py -p COM24 erase_region 0x10000 0x200000` | 擦除指定区域 |
| `esptool.py -p COM24 write_flash 0x0 merged-binary.bin` | 烧录指定 bin 到指定地址 |
| `esptool.py -p COM24 read_flash` | 读取 flash 内容（备份用） |

### erase_region 参数说明

| 参数 | 含义 |
|---|---|
| `0x10000` | 起始地址 |
| `0x200000` | 长度 |

---

## 4. 固件打包（merge-bin）

`idf.py merge-bin` 将**二级 bootloader + 分区表 + app** 合并为单个二进制文件 `merged-binary.bin`，方便整包烧录（如产线烧录、U 盘拷贝升级）。

```bash
idf.py merge-bin
```

合并后文件名：**`merged-binary.bin`**

> ⚠️ **注意事项**：执行 merge-bin 时需要**关闭 `--flash_size detect`**（即在合并时指定明确的 flash 大小，而非靠探测），否则产线/拷贝场景下可能因 flash 大小探测失败导致烧录异常。

---

## 5. 常见烧录流程

```
① 配置：  idf.py set-target esp32s3 && idf.py menuconfig
② 构建：  idf.py build
③ 开发烧录：idf.py -p COM24 flash monitor
④ 整包烧录：idf.py merge-bin
           esptool.py -p COM24 write_flash 0x0 build/merged-binary.bin
⑤ 排障：
           esptool.py -p COM24 chip_id      # 芯片是否正常
           esptool.py -p COM24 flash_id     # flash 是否正常
           esptool.py -p COM24 erase_flash  # 设备异常/加密冲突时清空
```

---

## 参考

- ESP-IDF 编程指南 — 构建系统：https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-guides/build-system.html
- esptool 文档：https://docs.espressif.com/projects/esptool/en/latest/esp32/

## 相关笔记

- [[02-ESP-IDF-核心外设速查]] — NVS 初始化等系统服务
- [[03-ESP-IDF-启动流程与OTA]] — 烧录地址与分区表、bootloader 的关系
- [[04-ESP-IDF-WiFi与网络]] — WiFi 需先 `nvs_flash_init()`
