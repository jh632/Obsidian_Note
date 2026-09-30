---
date: 2026-09-25
tags: [embed_note, 程序构建与内存优化, CMake]
---

# Zephyr 的 CMake 语法

> Zephyr 的整个构建系统建立在 CMake 上，用 west 命令行封装调用。应用侧写法与通用 CMake 差异明显：没有 add_executable，代码全部挂到构建系统预定义的 target 上。通用语法见 [[03-CMake基础语法]]，项目结构见 [[02-Zephyr-项目结构与构建配置]]。

## 1. 构建入口

```bash
west build -b nrf52840dk/nrf52840   # 指定 board + 应用目录，生成 build/
west build                          # 增量构建
west build -t menuconfig            # 终端调 Kconfig
```

`west build` 内部就是带 `-DBOARD=...` 的 cmake 加 ninja。CMake 配置阶段会先完成 devicetree 与 Kconfig 的处理，生成中间产物，然后才编译。

## 2. 应用 CMakeLists.txt 模板

```cmake
cmake_minimum_required(VERSION 3.28.0)   # 跟随所用 Zephyr 版本的要求

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
# 也允许只写 find_package(Zephyr)；上面写法强制使用 ZEPHYR_BASE 环境变量指定的那份 Zephyr

project(my_app)                          # 必须在 find_package 之后

target_sources(app PRIVATE src/main.c)   # app target 由 find_package(Zephyr) 创建
target_include_directories(app PRIVATE include)
```

要点：

- `app` 是 Zephyr 预先创建的库 target，应用代码都挂到它上面；没有 add_executable，最终可执行体 `zephyr.elf` 由 Zephyr-Kernel 工程统一生成
- 顺序约束：`set(BOARD ...)`、`BOARD_ROOT`、`SOC_ROOT` 等变量必须写在 find_package 之前
- `project()` 必须在 find_package(Zephyr) 之后，避免干扰 Zephyr 内部的 project(Zephyr-Kernel)

board 也可以直接写进 CMakeLists.txt：

```cmake
set(BOARD nrf52840dk/nrf52840)
set(BOARD_ROOT ${CMAKE_CURRENT_SOURCE_DIR})   # 自定义板卡搜索根，先于 find_package
find_package(Zephyr)
project(my_app)
```

进入构建的所有源码都属于某个库 target，应用代码挂 `app`，内核与驱动各挂自己的库。

## 3. zephyr_library_* 系列扩展函数

应用简单时挂 app 就够了；代码分层或编写模块时用扩展函数建自己的库：

```cmake
zephyr_library()                                   # 以目录名建库，ZEPHYR_CURRENT_LIBRARY 指向它
zephyr_library_named(my_lib)                       # 指定库名
zephyr_library_sources(src/foo.c src/bar.c)
zephyr_library_include_directories(include)
zephyr_library_compile_definitions(PRIVATE_API)
```

zephyr_library 系列创建的库会自动加入最终链接。应用里同样可以用标准 CMake 命令直接操作 app target。

## 4. Kconfig 片段与 devicetree overlay 的选择

| 变量 | 作用 |
| --- | --- |
| CONF_FILE | 指定 Kconfig 片段（空格或分号分隔多个） |
| EXTRA_CONF_FILE | 在默认片段之上追加，不改 CONF_FILE |
| DTC_OVERLAY_FILE | 指定 devicetree overlay（分号分隔） |
| EXTRA_DTC_OVERLAY_FILE | 追加 overlay |
| APPLICATION_CONFIG_DIR | 配置文件所在目录，默认应用源码目录 |
| FILE_SUFFIX | 给默认文件名追加后缀，缺文件时回退无后缀版本 |

默认查找：应用目录下的 `prj.conf`（Kconfig 片段）与 `app.overlay`（devicetree overlay），不用设置任何变量。

FILE_SUFFIX 示例：`west build -DFILE_SUFFIX=mouse` 时优先找 `prj_mouse.conf` 与 `boards/<board>_mouse.overlay`，文件不存在则回退 `prj.conf`、`<board>.overlay`。

## 5. 常用变量

| 变量 | 说明 |
| --- | --- |
| ZEPHYR_BASE | Zephyr 源码根目录；find_package 会缓存它，也可用环境变量强制指定 |
| BOARD | 目标板卡，如 nrf52840dk/nrf52840 |
| BOARD_ROOT | 自定义板卡的搜索根目录 |
| SOC_ROOT / DTS_ROOT / KCONFIG_ROOT | 自定义 SoC / devicetree 绑定 / Kconfig 的搜索根 |
| SHIELD | 扩展板 |

## 6. 配置阶段的中间产物

build/zephyr/ 下的关键文件：

- `.config`：Kconfig 汇总后的最终配置
- `zephyr.dts`：board 与 overlay 合并后的完整设备树
- `include/generated/devicetree_generated.h`、`include/generated/autoconf.h`：给 C 代码用的宏头文件
- `zephyr.elf` / `.hex` / `.bin`、`.map`

## 7. 模块（module）里的 CMake

west 管理的外部仓库通过 `zephyr/module.yml` 挂进构建：

```yaml
build:
  cmake: .      # 指向模块的 CMakeLists.txt
  kconfig: Kconfig
```

模块的 CMakeLists.txt 在 find_package(Zephyr) 引导构建系统时被加载，里面可用 zephyr_library() 等。

## 8. sysbuild

多镜像场景（MCUboot + 应用、双核）用 sysbuild 把多个 Zephyr 应用组合成一张固件：

```bash
west build -b nrf52840dk/nrf52840 --sysbuild
```

应用目录放 `sysbuild/CMakeLists.txt` 声明镜像组合，每个镜像有独立的 build 子目录。对照 MCUboot 学习线：ESP-IDF 靠 bootloader 处理多镜像，Zephyr 靠 sysbuild。

## 相关笔记

- [[01-ESP-IDF-CMake语法]]
- [[03-CMake基础语法]]
