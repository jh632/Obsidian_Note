---
tags: [embed_note, NuttX]
date: 2026-10-10
aliases: [NuttX环境配置, NuttX编译, NuttX烧录, configure.sh]
---

# NuttX 环境配置和编译烧录流程

NuttX 的基本开发流程是：安装宿主机工具和目标工具链，获取 `nuttx` 与 `apps` 源码，选择 `board:config` 配置，编译固件，再使用板卡对应的工具完成烧录。

> [!important] 路径要求
> NuttX 官方文档明确说明源码路径不能包含空格。`nuttx` 与 `apps` 应位于同一个父目录中。

---

## 1. 选择开发环境

官方支持 Linux、macOS、Windows + WSL、Windows + Cygwin 等环境。Windows 用户可以在 WSL 中完成配置和编译；烧录 USB 设备时，需要通过 USBIP 将设备接入 WSL，或在 Windows 中直接调用烧录工具。

### 1.1 Ubuntu / Debian 安装基础依赖

```bash
sudo apt update
sudo apt install \
  bison flex gettext texinfo libncurses5-dev libncursesw5-dev xxd \
  git gperf automake libtool pkg-config build-essential genromfs \
  libgmp-dev libmpc-dev libmpfr-dev libisl-dev binutils-dev libelf-dev \
  libexpat1-dev gcc-multilib g++-multilib picocom u-boot-tools util-linux
```

安装基于 Python 的 Kconfig 配置前端：

```bash
python3 -m pip install kconfiglib
```

如果在原生 Windows 环境中运行 Kconfiglib，还需要：

```powershell
py -m pip install windows-curses
```

Ubuntu 20.04 及以上版本也可以安装 C 语言版本的配置前端：

```bash
sudo apt install kconfig-frontends
```

### 1.2 安装目标工具链

工具链由目标架构决定。以 ARM Cortex-M 板卡为例：

```bash
sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi
```

确认工具可用：

```bash
arm-none-eabi-gcc --version
make --version
python3 --version
```

ESP32 系列还需要对应的 Xtensa 或 RISC-V 工具链，并安装 `esptool`：

```bash
python3 -m pip install "esptool>=4.8.1"
```

> [!note]
> 工具链必须匹配目标芯片。具体安装方式以对应芯片平台文档为准，不能只安装 `gcc-arm-none-eabi` 后用于全部板卡。

---

## 2. 获取源码

NuttX 的内核与系统组件位于 `nuttx` 仓库，示例程序、NSH 命令和其他应用位于 `apps` 仓库。两个目录保持同级：

```bash
mkdir nuttxspace
cd nuttxspace
git clone https://github.com/apache/nuttx.git nuttx
git clone https://github.com/apache/nuttx-apps.git apps
```

目录关系：

```text
nuttxspace/
├── nuttx/    # 内核、架构、驱动、板级支持和构建系统
└── apps/     # NSH、示例、网络工具和其他应用
```

需要固定发布版本时，应从 NuttX 官方下载页获取版本一致的 `nuttx` 与 `apps` 发布包。

---

## 3. 查找并选择板卡配置

NuttX 使用 `board:config` 标识一套配置：

- `board`：板卡名称，例如 `stm32f4discovery`、`sim`。
- `config`：该板卡的配置名称，例如 `nsh`。
- `nsh`：启用 NuttShell，适合作为入门配置。

进入 `nuttx` 目录，列出全部配置：

```bash
cd nuttx
./tools/configure.sh -L
```

根据板卡名称筛选：

```bash
./tools/configure.sh -L stm32f4discovery
```

常用宿主机参数：

| 参数 | 宿主机环境 |
| --- | --- |
| `-l` | Linux，包括 WSL 中的 Linux |
| `-m` | macOS |
| `-c` | Windows + Cygwin |
| `-g` | Windows + MinGW/MSYS |
| `-n` | Windows 原生环境 |
| `-B` | BSD 系统 |
| `-E` | 已有配置时执行 `distclean` 后重新配置 |
| `-e` | 配置发生变化时执行 `distclean` |
| `-a <app-dir>` | 指定 `apps` 目录相对于 `nuttx` 的路径 |

选择 STM32F4 Discovery 的 NSH 配置：

```bash
./tools/configure.sh -l stm32f4discovery:nsh
```

选择电脑模拟器配置：

```bash
./tools/configure.sh -l sim:nsh
```

`configure.sh` 会根据板卡配置生成顶层 `.config`，并准备对应的构建设置。已经配置过其他板卡时，可以使用 `-E` 清理旧配置后重新配置：

```bash
./tools/configure.sh -E -l stm32f4discovery:nsh
```

> [!warning]
> 切换板卡或工具链时要清理旧配置。旧的 `.config` 和构建产物可能使新配置出现难以定位的编译问题。

---

## 4. 使用 Make 配置与编译

### 4.1 完整流程

```bash
cd nuttx
./tools/configure.sh -l stm32f4discovery:nsh
make menuconfig
make -j
```

其中：

| 命令 | 作用 |
| --- | --- |
| `./tools/configure.sh -l board:config` | 载入板卡默认配置 |
| `make menuconfig` | 修改 Kconfig 配置 |
| `make -j` | 使用可用处理器并行编译 |
| `make clean` | 清理编译产物，保留当前配置 |
| `make distclean` | 清理编译产物和当前配置 |

常见输出文件位于 `nuttx/` 顶层：

| 文件 | 用途 |
| --- | --- |
| `nuttx` | ELF 文件，用于符号分析和 GDB 调试 |
| `nuttx.bin` | 裸二进制固件，常用于烧录 |
| `nuttx.hex` | Intel HEX 固件，是否生成由板卡配置决定 |

### 4.2 保存配置修改

在 `menuconfig` 中完成修改后，可以执行：

```bash
make savedefconfig
```

该命令会生成精简后的 `defconfig`。准备提交自定义板卡配置时，再把它放入对应的板卡配置目录。

---

## 5. 使用 CMake 配置与编译

CMake 可以直接通过 `BOARD_CONFIG` 选择板卡配置，不需要提前运行 `configure.sh`：

```bash
cmake -B build -DBOARD_CONFIG=stm32f4discovery:nsh -GNinja
cmake --build build
```

打开配置界面：

```bash
cmake --build build -t menuconfig
```

清理构建产物：

```bash
cmake --build build -t clean
```

不同板卡可以使用不同构建目录：

```bash
cmake -B build-sim -DBOARD_CONFIG=sim:nsh -GNinja
cmake -B build-stm32 -DBOARD_CONFIG=stm32f4discovery:nsh -GNinja
```

这样可以同时保留多套配置与产物。

---

## 6. 使用模拟器验证环境

`sim:nsh` 可以先验证依赖、配置系统和编译流程，不需要连接开发板：

```bash
cd nuttx
./tools/configure.sh -E -l sim:nsh
make -j
./nuttx
```

出现以下提示符说明 NuttX 已经运行：

```text
nsh>
```

查看内置命令：

```text
nsh> help
```

退出模拟器：

```text
nsh> quit
```

---

## 7. 烧录到开发板

烧录方法由芯片、板载调试器和板卡配置共同决定。编译前应查阅目标板卡在 NuttX 官方平台文档中的说明。

部分板卡可以直接使用：

```bash
make flash
```

`make flash` 会先构建固件，再调用板卡 `Make.defs` 中定义的 `FLASH` 命令。只有定义了 `FLASH` 的板卡支持该目标；其他板卡需要使用 OpenOCD、esptool 等对应工具。`make download` 是已经废弃的同类目标。

### 7.1 STM32：使用 OpenOCD

以带 ST-Link 的 STM32 板卡为例，先安装 OpenOCD：

```bash
sudo apt install openocd
```

STM32F1 示例：

```bash
openocd \
  -f interface/stlink-v2.cfg \
  -f target/stm32f1x.cfg \
  -c "init" \
  -c "program nuttx.bin verify reset" \
  -c "shutdown"
```

STM32L4 示例：

```bash
openocd \
  -f interface/stlink.cfg \
  -f target/stm32l4x.cfg \
  -c "program nuttx.bin 0x08000000; reset run; exit"
```

OpenOCD 的 interface 配置、target 配置与烧录地址必须匹配实际芯片和板卡，不能直接套用其他型号的命令。

### 7.2 ESP32：使用构建系统调用 esptool

进入已经配置并编译的 `nuttx` 目录：

```bash
make bootloader
make flash ESPTOOL_PORT=/dev/ttyUSB0 ESPTOOL_BINDIR=./
```

指定烧录波特率：

```bash
make flash \
  ESPTOOL_PORT=/dev/ttyUSB0 \
  ESPTOOL_BAUD=921600 \
  ESPTOOL_BINDIR=./
```

ESP32 首次使用 NuttX，或 Flash 中存在其他固件布局时，应按照对应平台文档先完整擦除 Flash。

### 7.3 连接串口控制台

Linux 中查看串口设备：

```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

使用 `picocom` 连接 115200 波特率串口：

```bash
picocom -b 115200 /dev/ttyUSB0
```

设备复位后出现 `nsh>`，说明固件启动并进入 NSH。

如果当前用户没有串口权限，可加入 `dialout` 用户组，重新登录后生效：

```bash
sudo usermod -aG dialout "$USER"
```

---

## 8. 从配置到运行的命令清单

### 8.1 模拟器

```bash
git clone https://github.com/apache/nuttx.git nuttx
git clone https://github.com/apache/nuttx-apps.git apps
cd nuttx
./tools/configure.sh -l sim:nsh
make -j
./nuttx
```

### 8.2 STM32 板卡

```bash
cd nuttx
./tools/configure.sh -l <board>:nsh
make menuconfig
make -j
openocd -f <interface配置> -f <target配置> \
  -c "program nuttx.bin <烧录地址>; reset run; exit"
picocom -b 115200 /dev/ttyACM0
```

### 8.3 ESP32 板卡

```bash
cd nuttx
./tools/configure.sh -l <esp32-board>:nsh
make menuconfig
make -j
make bootloader
make flash ESPTOOL_PORT=/dev/ttyUSB0 ESPTOOL_BINDIR=./
picocom -b 115200 /dev/ttyUSB0
```

---

## 9. 常见问题定位

### 找不到板卡配置

```bash
./tools/configure.sh -L <板卡名称的一部分>
```

同时检查官方支持板卡列表以及 `boards/` 中是否存在对应目录。

### `arm-none-eabi-gcc: command not found`

检查工具链是否安装，以及工具链的 `bin` 目录是否位于 `PATH`：

```bash
which arm-none-eabi-gcc
arm-none-eabi-gcc --version
```

### 切换板卡后出现异常编译错误

清理配置并重新选择板卡：

```bash
make distclean
./tools/configure.sh -l <board>:<config>
make -j
```

也可以直接使用：

```bash
./tools/configure.sh -E -l <board>:<config>
make -j
```

### 烧录成功但没有串口输出

检查以下内容：

1. 板卡配置使用的 console UART。
2. 串口设备名称是否正确。
3. 波特率是否与配置一致，官方示例通常使用 115200 8N1。
4. TX、RX、GND 连接是否正确。
5. 固件烧录地址是否符合该板卡文档。

---

## 参考资料

- [NuttX Quickstart](https://nuttx.apache.org/docs/latest/quickstart/quickstart.html)
- [Installing](https://nuttx.apache.org/docs/latest/quickstart/install.html)
- [Configuring](https://nuttx.apache.org/docs/latest/quickstart/configuring.html)
- [Compiling with Make](https://nuttx.apache.org/docs/latest/quickstart/compiling_make.html)
- [Compiling with CMake](https://nuttx.apache.org/docs/latest/quickstart/compiling_cmake.html)
- [Running](https://nuttx.apache.org/docs/latest/quickstart/running.html)
- [Supported Platforms](https://nuttx.apache.org/docs/latest/platforms/index.html)
- [ESP32 平台文档](https://nuttx.apache.org/docs/latest/platforms/xtensa/esp32/index.html)
- [`configure.sh` 源码](https://github.com/apache/nuttx/blob/master/tools/configure.sh)
- [NuttX 源码仓库](https://github.com/apache/nuttx)
- [NuttX Apps 源码仓库](https://github.com/apache/nuttx-apps)
