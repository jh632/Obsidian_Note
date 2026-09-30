---
date: 2026-09-25
tags: [embed_note, 程序构建原理, CMake]
---

# ESP-IDF 的 CMake 语法

> ESP-IDF 在 CMake 之上封装了一套组件（component）机制。通用 CMake 语法见 [[03-CMake基础语法]]，项目结构总览见 [[01-ESP-IDF-项目结构与构建工具]]。

## 1. 构建系统概览

- `idf.py` 是 CMake + Ninja 的封装，`idf.py build` 内部就是 cmake 配置加 ninja 编译
- 组件是构建的基本单位：应用代码放在 `main` 组件，自己的驱动和库放到 `components/` 目录
- 组件的 CMakeLists.txt 里核心命令只有一个：`idf_component_register()`

## 2. 项目结构

```
my_project/
├── CMakeLists.txt          # 项目级构建入口
├── sdkconfig               # menuconfig 生成的完整配置
├── sdkconfig.defaults      # 项目默认配置覆盖
├── main/
│   ├── CMakeLists.txt
│   └── main.c
├── components/
│   └── my_driver/
│       ├── CMakeLists.txt
│       ├── include/
│       └── src/
└── build/
```

## 3. 项目级 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.22)   # 以所用 IDF 版本的官方模板为准
include($ENV{IDF_PATH}/tools/cmake/project.cmake)   # 导入 ESP-IDF 构建系统
project(my_project)                    # 项目名 = 输出文件名 my_project.bin
```

三行顺序固定，`IDF_PATH` 指向 ESP-IDF 源码目录。

裁剪构建时在 include 之前 set（放在 cmake_minimum_required 之后）：

```cmake
cmake_minimum_required(VERSION 3.22)
set(COMPONENTS main driver nvs_flash)  # 只构建列出组件 + 递归依赖 + 通用组件
# set(EXCLUDE_COMPONENTS ...)          # 或者从初始集合剔除组件
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(my_project)
```

`main` 默认依赖其他所有组件，所以 main 总会被构建进去；组件通过 REQUIRES 声明的依赖也会自动补进 COMPONENTS。

## 4. 组件注册 idf_component_register

```cmake
idf_component_register(SRCS "src/led.c" "src/button.c"
                       INCLUDE_DIRS "include"
                       PRIV_INCLUDE_DIRS "priv_include"
                       REQUIRES driver esp_timer
                       PRIV_REQUIRES nvs_flash
                       EMBED_FILES "certs/server_root_cert.pem"
                       EMBED_TXTFILES "web/index.html")
```

| 参数 | 作用 |
| --- | --- |
| SRCS / SRC_DIRS | 源文件；SRCS 列文件，SRC_DIRS 按目录 glob，两者二选一（EXCLUDE_SRCS 排除个别文件） |
| INCLUDE_DIRS | 公共头文件目录，加入依赖方的搜索路径 |
| PRIV_INCLUDE_DIRS | 仅本组件源文件可见的头文件目录 |
| REQUIRES / PRIV_REQUIRES | 依赖的其他组件，见下节 |
| EMBED_FILES / EMBED_TXTFILES | 把二进制 / 文本文件嵌进 .rodata |
| LDFRAGMENTS | 链接片段（链接脚本级扩展） |
| REQUIRED_IDF_TARGETS | 限定支持的芯片型号 |
| WHOLE_ARCHIVE | 保留全库符号（默认链接器剔除未引用的目标文件） |
| KCONFIG / KCONFIG_PROJBUILD | 组件的 Kconfig 文件 |

用 SRC_DIRS glob 时无法再用 `set_source_files_properties` 给单个文件设编译属性。

## 5. 组件依赖 REQUIRES / PRIV_REQUIRES

- REQUIRES：当前组件**公共头文件**里 `#include` 的组件，语义上对应 `target_link_libraries` 的 PUBLIC
- PRIV_REQUIRES：只在**源文件**里 `#include` 或仅链接需要的组件，对应 PRIVATE
- 依赖关系不允许写成 `if(CONFIG_XXX)` 条件，依赖在 Kconfig 配置加载前就展开
- `main` 组件自动依赖所有其他组件，无需写 REQUIRES；把 main 改名后该特性消失

## 6. 组件内的变量与操作

```cmake
idf_component_register(SRCS "src/foo.c" INCLUDE_DIRS "include")

# 给本组件加编译选项，必须在 idf_component_register 之后
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-unused-variable)

# 按 Kconfig 配置切换编译选项
if(CONFIG_IDF_TARGET_ESP32S3)
    target_compile_options(${COMPONENT_LIB} PRIVATE -DS3_SUPPORT=1)
endif()

# 覆盖全局编译规范：在 project() 之后调用
idf_build_set_property(COMPILE_OPTIONS "-Wno-error" APPEND)
```

常用变量：

- `${COMPONENT_NAME}` / `${COMPONENT_LIB}`：组件名与对应的 CMake 库 target
- `${IDF_PATH}`：ESP-IDF 源码根目录
- `${IDF_TARGET}`：当前目标芯片
- `CONFIG_*`：每个 Kconfig 选项都映射为同名 CMake 变量（如 `CONFIG_FREERTOS_HZ`）
- `idf_build_get_property(var PROJECT_NAME)`：查询项目名等构建属性

## 7. Kconfig 与 sdkconfig

- 组件可带 `Kconfig` 文件（或注册时用 KCONFIG 参数指定），menuconfig 里就能看到该组件的选项
- `sdkconfig`：menuconfig 的完整输出
- `sdkconfig.defaults`：只写和默认值不同的项，重建 sdkconfig 时生效；可按芯片追加 `sdkconfig.defaults.esp32s3`

## 8. EMBED_FILES 嵌入文件

```c
// EMBED_TXTFILES "certs/ca.pem" 生成的符号
extern const uint8_t ca_pem_start[] asm("_binary_certs_ca_pem_start");
extern const uint8_t ca_pem_end[]   asm("_binary_certs_ca_pem_end");
```

- 符号名 = `_binary_` + 文件路径（`/`、`.` 替换为 `_`）+ `_start` / `_end`
- `EMBED_TXTFILES` 在内容末尾补 `\0`，可当字符串用；`EMBED_FILES` 是原始字节
- 内容位于 flash 的 .rodata 段

## 9. idf.py 常用命令

```bash
idf.py set-target esp32s3     # 切换芯片型号（会重新生成 sdkconfig）
idf.py menuconfig             # 图形化配置
idf.py build                  # 编译
idf.py flash monitor          # 烧录并打开串口监视器
idf.py size-components        # 各组件的 flash/ram 占用
idf.py fullclean              # 删除 build 目录
```

## 10. 组件依赖清单 idf_component.yml

组件目录下可放 `idf_component.yml` 声明对托管组件仓库（components.espressif.com）的依赖，构建时由组件管理器自动下载：

```yaml
dependencies:
  espressif/esp_websocket_client: "^1.2.0"
```

## 相关笔记

- [[02-Zephyr-CMake语法]]
- [[03-CMake基础语法]]
