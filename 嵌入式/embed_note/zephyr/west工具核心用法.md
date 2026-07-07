# West 工具核心用法

> 来源：https://x-gen-lab.github.io/zephyr-learning-system/stage1-foundation/west-tool/
> 整理日期：2026-07-02

## 概述

**west** 是 Zephyr 的**元工具（meta-tool）**，统一了源码管理、依赖解析、构建配置、固件烧录和调试等多个功能。

### 设计理念

```
west (meta-tool)
├── 项目管理     — 多仓库管理、依赖解析、版本控制
├── 构建系统     — CMake 集成、配置管理、增量构建
└── 烧录/调试    — 多种编程器支持、GDB 调试、串口监视
```

### 核心特性

- **统一接口**：一个 CLI 覆盖整个开发流程
- **多仓库支持**：通过 Manifest 文件管理多个 Git 仓库
- **可扩展性**：支持自定义命令和扩展
- **跨平台**：Linux / Windows / macOS
- **工具链无关**：支持多种编译器/调试器

---

## 核心命令

### west init — 初始化工作区

```bash
west init [-m MANIFEST_URL] [-mr MANIFEST_REVISION] [--mf MANIFEST_FILE] [PATH]
```

| 示例                                                                                    | 说明                |
| ------------------------------------------------------------------------------------- | ----------------- |
| `west init ~/zephyrproject`                                                           | 默认工作区             |
| `west init -m https://github.com/zephyrproject-rtos/zephyr --mr v3.5.0 ~/zephyr-v3.5` | 指定 manifest 仓库和分支 |
| `west init --mf my-manifest.yml ~/my-project`                                         | 使用本地 manifest 文件  |

**初始化后的目录结构：**

```
zephyrproject/
├── .west/
│   └── config
├── zephyr/
│   ├── west.yml
│   ├── CMakeLists.txt
│   └── ...
├── modules/         # 执行 west update 后出现
├── tools/
└── bootloader/
```

**最佳实践：**
- 不同项目/版本使用独立工作区
- 路径避免空格和中文
- `init` 后立即执行 `west update`
- 通过 `--mr` 使用稳定 LTS 版本，而非 main 分支

---

### west update — 更新依赖仓库

```bash
west update [--fetch {always,smart}] [--rebase] [PROJECT ...]
```

| 示例 | 说明 |
|------|------|
| `west update` | 更新所有项目 |
| `west update hal_nordic mcuboot` | 只更新指定项目 |
| `west update --fetch always` | 强制重新拉取 |
| `west update --rebase` | 更新时自动 rebase 本地修改 |

**注意事项：**
- 首次 update 下载约 1–2 GB
- 本地有修改可能导致失败
- 国内用户需配置 Git 代理或镜像
- **不要中断更新过程**

---

### west build — 构建固件

```bash
west build -b BOARD [-d BUILD_DIR] [SOURCE_DIR] [-- CMAKE_ARGS]
```

| 示例 | 说明 |
|------|------|
| `cd samples/hello_world && west build -b nrf52840dk_nrf52840` | 标准构建 |
| `west build -b nrf52840dk_nrf52840 -d build samples/hello_world` | 显式指定源码/构建目录 |
| `west build -b nrf52840dk_nrf52840 -p auto` | 自动清理重建 |
| `west build -b nrf52840dk_nrf52840 -- -DCONF_FILE=prj_custom.conf` | 传递 CMake 参数 |
| `west build` | 仅编译（不重新配置） |
| `west build -t menuconfig` | 打开配置菜单 |
| `west build -t clean` | 清理构建输出 |

**构建选项：**

| 选项 | 说明 | 示例 |
|------|------|------|
| `-b BOARD` | 指定目标板 | `-b nrf52840dk_nrf52840` |
| `-d BUILD_DIR` | 指定构建目录 | `-d build` |
| `-p auto` | 自动原语构建 | `-p auto` |
| `-p always` | 始终清理重建 | `-p always` |
| `-t TARGET` | 构建特定目标 | `-t menuconfig` |
| `--cmake-only` | 仅 CMake 配置，不编译 | `--cmake-only` |
| `-c` | 增量构建（默认） | `-c` |

**构建输出目录结构：**

```
build/
├── zephyr/
│   ├── zephyr.elf
│   ├── zephyr.hex
│   ├── zephyr.bin
│   ├── zephyr.dts
│   └── .config
├── CMakeCache.txt
└── compile_commands.json
```

---

### west flash — 烧录固件

```bash
west flash [-d BUILD_DIR] [--runner RUNNER] [--context] [RUNNER_ARGS]
```

| 示例 | 说明 |
|------|------|
| `west flash` | 使用默认 runner |
| `west flash -d build` | 指定构建目录 |
| `west flash --runner jlink` | 指定烧录器 |
| `west flash --context` | 列出支持的 runner |
| `west flash --runner jlink -- --speed 4000` | 传递 runner 参数 |

**Flash Runner 对照表：**

| Runner | 支持板型 | 说明 |
|--------|---------|------|
| `jlink` | Nordic, STM32, NXP 等 | 商用，性能优秀 |
| `openocd` | STM32, ESP32 等 | 开源，硬件支持广泛 |
| `pyocd` | ARM Cortex-M | 基于 Python，安装简单 |
| `nrfjprog` | Nordic nRF 系列 | Nordic 官方工具 |
| `stm32cubeprogrammer` | STM32 系列 | ST 官方工具 |
| `dfu-util` | DFU 能力板 | USB DFU 烧录 |
| `blackmagicprobe` | ARM Cortex-M | Black Magic Probe 调试器 |

---

### west debug — 调试

```bash
west debug [-d BUILD_DIR] [--runner RUNNER] [RUNNER_ARGS]
west debugserver                    # 仅启动 GDB Server
```

**GDB 常用命令：**

| 命令 | 说明 |
|------|------|
| `break main` | 设置断点 |
| `continue` | 继续执行 |
| `next` | 单步跳过（不进入函数） |
| `step` | 单步进入函数 |
| `print variable` | 打印变量值 |
| `backtrace` | 查看调用栈 |
| `info registers` | 查看寄存器 |
| `quit` | 退出调试 |

---

### 其他命令

| 命令 | 示例 | 说明 |
|------|------|------|
| `west attach` | `west attach -p /dev/ttyUSB0 -b 115200` | 连接串口 |
| `west boards` | `west boards nrf52` | 列出/搜索支持的板子 |
| `west config` | `west config -l` | 查看/设置配置 |
| `west topdir` | `west topdir` | 显示工作区根路径 |

**west config 常用配置：**

```bash
west config build.board nrf52840dk_nrf52840                 # 设置默认板子
west config build.dir-fmt "build/{board}"                    # 设置构建目录格式
west config build.cmake-generator "Ninja"                    # 设置 CMake 生成器
west config build.cmake-args -- -j8                          # 并行构建任务数
west config build.runner jlink                               # 设置默认烧录器
west config -d build.board                                   # 删除配置项
```

**全局 vs 本地配置：**

```bash
west config --global build.board nrf52840dk_nrf52840         # 全局（所有工作区）
west config build.board nrf52840dk_nrf52840                  # 本地（当前工作区）
west config -l --show-origin                                 # 查看配置来源
```

---

## Manifest 文件详解

### 文件结构 (`west.yml`)

```yaml
manifest:
  remotes:
    - name: zephyrproject-rtos
      url-base: https://github.com/zephyrproject-rtos
    - name: my-company
      url-base: https://github.com/my-company
  projects:
    - name: hal_nordic
      remote: zephyrproject-rtos
      revision: v2.5.0
      path: modules/hal/nordic
    - name: mcuboot
      remote: zephyrproject-rtos
      revision: main
      path: bootloader/mcuboot
    - name: my-custom-module
      remote: my-company
      revision: v1.0.0
      path: modules/my-module
      import: true
  self:
    path: zephyr
    west-commands: scripts/west-commands.yml
```

### 关键字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `remotes` | 定义远程 URL 基础 | `url-base: https://github.com/zephyrproject-rtos` |
| `projects` | 列出需要克隆的仓库 | （见上） |
| `name` | 项目唯一标识符 | `name: hal_nordic` |
| `remote` | 项目使用的 remote | `remote: zephyrproject-rtos` |
| `revision` | Git 分支、标签或 commit hash | `revision: v2.5.0` |
| `path` | 工作区内的路径 | `path: modules/hal/nordic` |
| `import` | 是否导入该项目的 manifest | `import: true` |
| `self` | 定义 manifest 仓库本身 | `path: zephyr` |
| `west-commands` | 自定义命令定义文件 | `west-commands: scripts/west-commands.yml` |

### 自定义 Manifest 示例

```yaml
manifest:
  remotes:
    - name: zephyrproject-rtos
      url-base: https://github.com/zephyrproject-rtos
    - name: my-org
      url-base: https://github.com/my-organization
  defaults:
    remote: zephyrproject-rtos
  projects:
    - name: zephyr
      revision: v3.5.0
      path: zephyr
      import: true
    - name: my-application
      remote: my-org
      revision: main
      path: application
    - name: my-bsp
      remote: my-org
      revision: v1.2.0
      path: boards/my-board
  self:
    path: manifest-repo
```

```bash
# 使用自定义 manifest 初始化
west init -m https://github.com/my-organization/my-project --mr main ~/my-workspace
west update
```

---

## 多仓库管理

### 工作区布局

```
my-workspace/
├── .west/
├── zephyr/
│   └── west.yml
├── modules/
│   ├── hal/
│   │   ├── nordic/        # 独立 Git 仓库
│   │   └── stm32/         # 独立 Git 仓库
│   └── lib/
│       └── mbedtls/
├── bootloader/
│   └── mcuboot/
├── tools/
└── application/           # 可独立 Git 仓库
```

### `west forall` — 批量操作所有仓库

```bash
west forall -c "git status"                             # 查看所有仓库状态
west forall -c "git branch --show-current"               # 查看当前分支
west forall -c "git pull"                                # 全部拉取最新
west forall -c "git diff --stat"                         # 查看未提交变更
west forall -p hal_nordic,mcuboot -c "git status"        # 只操作指定项目
```

### 本地修改流程

```bash
cd modules/hal/nordic
git checkout -b my-feature
# 编辑代码...
git add .
git commit -m "Add my feature"
west build -b nrf52840dk_nrf52840 application
git push origin my-feature
```

### 更新策略对比

| 策略 | 命令 | 适用场景 | 优点 | 缺点 |
|------|------|---------|------|------|
| **全量更新** | `west update` | 首次搭建或长期未更新 | 确保所有依赖最新 | 耗时 |
| **智能更新** | `west update --fetch smart` | 日常开发 | 只更新有变动的仓库 | 可能遗漏部分更新 |
| **强制更新** | `west update --fetch always` | 网络问题导致下载不完整 | 确保完整性 | 全部重新下载 |
| **部分更新** | `west update hal_nordic` | 只需要特定模块 | 快速、精准 | 需知道模块名 |
| **Rebase 更新** | `west update --rebase` | 保留本地修改 | 自动合并本地修改 | 可能产生冲突 |

---

## 常见问题与调试

### 1. west 命令找不到

**现象：** `bash: west: command not found`

**解决：**
```bash
pip3 install --user west
# 确保 PATH 包含 .local/bin
export PATH="$HOME/.local/bin:$PATH"    # Linux/macOS
# Windows：将 Python Scripts 目录添加到系统环境变量
```

### 2. west update 失败

**现象：** `fatal: unable to access 'https://github.com/...': Failed to connect`

**解决：**
- 配置 Git 代理：`git config --global http.proxy http://127.0.0.1:7890`
- 使用 SSH 替代 HTTPS：编辑 `~/.gitconfig`
- 使用国内镜像
- 增大超时：`git config --global http.lowSpeedTime 999999`
- 强制重新拉取：`west update --fetch always`

### 3. 构建失败

**现象：** `CMake Error: The source directory ".../zephyr" does not exist.`

**解决：**
- 确保在 west 工作区内
- 加载环境：`source ~/zephyrproject/zephyr/zephyr-env.sh`
- 设置默认板子：`west config build.board nrf52840dk_nrf52840`
- 清理重建：`west build -b nrf52840dk_nrf52840 -p auto`
- CMake 版本需 ≥ 3.20.0

### 4. 烧录失败

**现象：** `Error: unable to find a flash runner for board nrf52840dk_nrf52840`

**解决：**
- 安装所需的烧录工具（nrf-command-line-tools / J-Link / OpenOCD 等）
- 用 `lsusb` 或 `ls /dev/tty*` 检查板子连接
- 显式指定 runner：`west flash --runner jlink`
- 查看支持的 runner：`west flash --context`
- Linux 权限：将用户加入 dialout 组

### 5. 构建目录混淆

**现象：** `Error: build directory "build" does not exist`

**解决：**
- 指定构建目录：`west build -d build`
- 配置默认格式：`west config build.dir-fmt "build/{board}"`
- 使用绝对路径
- 从源码目录构建
- 清理重建：`rm -rf build && west build -b BOARD -p auto`

---

## 高级用法

### 自定义命令

**1. 定义命令文件 `scripts/west-commands.yml`：**

```yaml
west-commands:
  - file: scripts/my_command.py
    commands:
      - name: my-build
        class: MyBuildCommand
        help: Custom build command with extra features
```

**2. 实现 Python 类 `scripts/my_command.py`：**

```python
class MyBuildCommand(WestCommand):
    def __init__(self):
        super().__init__(
            'my-build',
            'a custom build command',
            'Longer description of my custom build command'
        )

    def do_add_parser(self, parser_adder):
        parser = parser_adder.add_parser(
            self.name,
            help=self.help,
            description=self.description
        )
        parser.add_argument('-b', '--board', required=True, help='target board')
        parser.add_argument('--optimize', action='store_true', help='enable optimizations')
        return parser

    def do_run(self, args, unknown_args):
        self.logger.info(f"Building for board: {args.board}")
        if args.optimize:
            self.logger.info("Optimizations enabled")
        self.run_west_command(['build', '-b', args.board])
```

**3. 使用：** `west my-build -b nrf52840dk_nrf52840 --optimize`

### 与 Git 工作流集成

```bash
# 在所有仓库创建相同分支
west forall -c "git checkout -b feature-xyz"
west forall -c "git checkout main"
west forall -c "git branch -vv"

# 查看变更
west forall -c "git status -s"

# 同步上游
cd zephyr && git pull upstream main
west update
west update --rebase    # 有本地修改时
```

---

## 参考资源

- [West 官方文档](https://docs.zephyrproject.org/latest/develop/west/index.html)
- [West Manifest 规范](https://docs.zephyrproject.org/latest/develop/west/manifest.html)
- [West 命令参考](https://docs.zephyrproject.org/latest/develop/west/west-commands.html)
- [West 扩展开发指南](https://docs.zephyrproject.org/latest/develop/west/extensions.html)
