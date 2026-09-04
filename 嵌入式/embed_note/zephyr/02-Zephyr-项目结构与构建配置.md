---
tags: [zephyr, 项目结构, cmake, kconfig, prj.conf, 构建]
date: 2026-09-01
aliases: [Zephyr项目结构, 项目结构, prj.conf, CMakeLists]
---

# Zephyr 项目结构与构建配置

> 2026-09-01 由原《zephyr项目目录结构》整理重组，拆成四块：**① 应用目录结构 ② 源码目录结构 ③ CMakeLists.txt ④ prj.conf（Kconfig）**。

---

## 1. 应用项目目录结构

一个标准的 Zephyr 应用项目通常包含以下目录和文件：

```
my_zephyr_app/
├── CMakeLists.txt          # CMake 构建配置文件
├── prj.conf                # 项目配置文件
├── src/                    # 源代码目录
│   ├── main.c              # 主程序入口
│   └── ...                 # 其他源文件
├── boards/                 # 板级配置目录（可选）
│   └── nrf52840dk_nrf52840.overlay  # 设备树 Overlay
├── include/                # 头文件目录（可选）
│   └── ...
├── lib/                    # 自定义库目录（可选）
│   └── ...
└── README.md               # 项目说明文档
```

| 目录/文件 | 作用 |
|---|---|
| `CMakeLists.txt` | 定义项目构建规则，指定源文件、包含路径等 |
| `prj.conf` | 配置 Zephyr 内核和子系统的功能选项 |
| `src/` | 存放应用程序的源代码文件 |
| `boards/` | 存放板级特定的配置文件（设备树 Overlay、板级 Kconfig） |
| `include/` | 存放应用程序的头文件 |
| `lib/` | 存放自定义的库代码 |

---

## 2. Zephyr 源码目录结构

```
zephyr/
├── arch/                   # 架构相关代码（ARM、x86、RISC-V 等）
├── boards/                 # 板级支持包（BSP）
├── cmake/                  # CMake 构建脚本
├── doc/                    # 官方文档
├── drivers/                # 设备驱动程序
│   ├── gpio/
│   ├── i2c/
│   ├── spi/
│   └── ...
├── dts/                    # 设备树源文件和绑定
│   ├── bindings/           # 设备树绑定定义
│   └── ...
├── include/                # 公共头文件
│   ├── zephyr/
│   └── ...
├── kernel/                 # 内核核心代码
├── lib/                    # 通用库
├── modules/                # 外部模块
├── samples/                # 示例程序
├── scripts/                # 构建和工具脚本
├── subsys/                 # 子系统（日志、Shell、文件系统等）
│   ├── logging/
│   ├── shell/
│   ├── fs/
│   └── ...
├── tests/                  # 测试用例
└── CMakeLists.txt          # 顶层 CMake 文件
```

> 平时开发最常逛的：`drivers/`（驱动源码）、`dts/bindings/`（设备树绑定）、`include/zephyr/`（API 头文件）、`samples/`（示例）——驱动查找方法见 [[03-Zephyr-设备树与驱动开发]]。

---

## 3. CMakeLists.txt

CMakeLists.txt 是 Zephyr 项目的构建配置文件，使用 CMake 语法定义项目的构建规则。

### 3.1 最小示例

```cmake
# 指定最低 CMake 版本
cmake_minimum_required(VERSION 3.20.0)

# 查找 Zephyr 包（必须在 project() 之前）
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

# 定义项目名称
project(my_app)

# 添加源文件
target_sources(app PRIVATE src/main.c)
```

### 3.2 完整示例

```cmake
# 指定最低 CMake 版本
cmake_minimum_required(VERSION 3.20.0)

# 查找 Zephyr 包（必须在 project() 之前）
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

# 定义项目名称和版本
project(my_sensor_app VERSION 1.0.0)

# 添加应用程序源文件
target_sources(app PRIVATE
    src/main.c
    src/sensor.c
    src/display.c
)

# 添加包含目录
target_include_directories(app PRIVATE
    include
)

# 添加编译选项
target_compile_options(app PRIVATE
    -Wall                    # 启用所有警告
    -Wextra                  # 启用额外警告
)

# 添加编译定义
target_compile_definitions(app PRIVATE
    APP_VERSION_MAJOR=${PROJECT_VERSION_MAJOR}
    APP_VERSION_MINOR=${PROJECT_VERSION_MINOR}
)

# 条件编译：如果启用了调试模式
if(CONFIG_DEBUG)
    target_compile_definitions(app PRIVATE DEBUG_MODE=1)
endif()

# 链接自定义库（如果有）
# target_link_libraries(app PRIVATE my_custom_lib)
```

### 3.3 CMake 常用命令速查

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `cmake_minimum_required()` | 指定最低 CMake 版本 | `cmake_minimum_required(VERSION 3.20.0)` |
| `find_package()` | 查找 Zephyr 包 | `find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})` |
| `project()` | 定义项目名称和版本 | `project(my_app VERSION 1.0.0)` |
| `target_sources()` | 添加源文件到目标 | `target_sources(app PRIVATE src/main.c)` |
| `target_include_directories()` | 添加头文件搜索路径 | `target_include_directories(app PRIVATE include)` |
| `target_compile_options()` | 添加编译选项 | `target_compile_options(app PRIVATE -Wall)` |
| `target_compile_definitions()` | 添加编译宏定义 | `target_compile_definitions(app PRIVATE DEBUG=1)` |
| `target_link_libraries()` | 链接库 | `target_link_libraries(app PRIVATE my_lib)` |

---

## 4. prj.conf（Kconfig）

prj.conf 是 Zephyr 项目的配置文件，使用 Kconfig 语法定义系统功能和参数。

### 4.1 基本配置示例

一个简单的 prj.conf 文件：

```ini
# 串口配置
CONFIG_SERIAL=y
CONFIG_UART_CONSOLE=y

# 日志系统
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3

# GPIO 驱动
CONFIG_GPIO=y

# 线程栈大小
CONFIG_MAIN_STACK_SIZE=2048
```

### 4.2 完整示例

```ini
# ============================================================================
# 基础系统配置
# ============================================================================

# 串口和控制台
CONFIG_SERIAL=y
CONFIG_UART_CONSOLE=y
CONFIG_CONSOLE=y

# 系统时钟
CONFIG_SYS_CLOCK_TICKS_PER_SEC=1000

# 主线程栈大小（字节）
CONFIG_MAIN_STACK_SIZE=2048

# 空闲线程栈大小
CONFIG_IDLE_STACK_SIZE=512

# ============================================================================
# 日志系统配置
# ============================================================================

# 启用日志系统
CONFIG_LOG=y

# 日志级别：0=OFF, 1=ERR, 2=WRN, 3=INF, 4=DBG
CONFIG_LOG_DEFAULT_LEVEL=3

# 日志后端：串口输出
CONFIG_LOG_BACKEND_UART=y

# 日志时间戳
CONFIG_LOG_TIMESTAMP=y

# 日志颜色输出
CONFIG_LOG_BACKEND_SHOW_COLOR=y

# ============================================================================
# 驱动配置
# ============================================================================

# GPIO 驱动
CONFIG_GPIO=y

# I2C 驱动
CONFIG_I2C=y

# SPI 驱动
CONFIG_SPI=y

# PWM 驱动
CONFIG_PWM=y

# ============================================================================
# 子系统配置
# ============================================================================

# Shell 控制台
CONFIG_SHELL=y
CONFIG_SHELL_BACKEND_SERIAL=y

# 文件系统
CONFIG_FILE_SYSTEM=y
CONFIG_FILE_SYSTEM_LITTLEFS=y

# ============================================================================
# 调试配置
# ============================================================================

# 断言检查
CONFIG_ASSERT=y

# 栈溢出检查
CONFIG_STACK_SENTINEL=y

# 线程监控
CONFIG_THREAD_MONITOR=y

# 线程名称
CONFIG_THREAD_NAME=y

# ============================================================================
# 优化配置
# ============================================================================

# 编译优化级别：0=无优化, 1=O1, 2=O2, 3=O3, s=Os（体积优化）
CONFIG_COMPILER_OPTIMIZATIONS="2"

# 代码体积优化（如果需要）
# CONFIG_SIZE_OPTIMIZATIONS=y
```

> 提示：Kconfig 配置名**不要靠记忆猜**（如 `CONFIG_TMP11X` 而非 `CONFIG_TMP117`），要以驱动源码里的 Kconfig 文件为准——见 [[03-Zephyr-设备树与驱动开发]]。
