---
date: 2026-09-25
tags: [embed_note, 程序构建原理, CMake]
---

# CMake 基础语法

> 通用 CMake 语法速查。ESP-IDF 与 Zephyr 的专用写法见 [[01-ESP-IDF-CMake语法]]、[[02-Zephyr-CMake语法]]。

## 1. CMake 是什么

CMake 是构建系统生成器：读取 CMakeLists.txt，生成 Makefile、Ninja 等实际构建文件。命令语法为 `命令名(参数1 参数2 ...)`，参数用空格分隔，命令名不区分大小写。

## 2. 变量

```cmake
set(MY_VAR "hello")
set(MY_LIST a b c)             # 列表就是分号分隔的字符串：a;b;c
message("Value: ${MY_VAR}")

# 作用域
set(VAR "child" PARENT_SCOPE)  # 函数内修改父作用域
set(VAR "def" CACHE STRING "") # CACHE 变量持久化到 CMakeCache.txt
set(VAR "x" CACHE STRING "" FORCE)  # 强制覆盖 cache 已有值
```

常用内置变量：

- `${PROJECT_NAME}`、`${PROJECT_SOURCE_DIR}`、`${PROJECT_BINARY_DIR}`
- `${CMAKE_CURRENT_SOURCE_DIR}`、`${CMAKE_CURRENT_BINARY_DIR}`
- `${CMAKE_C_COMPILER}`、`${CMAKE_BUILD_TYPE}`
- `${CMAKE_SYSTEM_NAME}`、`${CMAKE_SYSTEM_PROCESSOR}`

## 3. 条件与循环

```cmake
if(MY_VAR STREQUAL "hello")           # 字符串比较
elseif(MY_VAR MATCHES "^[0-9]+$")     # 正则匹配
elseif(DEFINED MY_VAR)                # 变量已定义
elseif(MY_VAR GREATER 10)             # 数字：GREATER/LESS/EQUAL/GREATER_EQUAL/LESS_EQUAL
elseif(EXISTS "/path/to/file")        # 文件存在；目录用 IS_DIRECTORY
endif()

# 逻辑：NOT / AND / OR
# 真值：TRUE ON YES 1 非零数字；假值：FALSE OFF NO 0 "" NOTFOUND

foreach(item IN LISTS MY_LIST)
    message("${item}")
endforeach()

foreach(i RANGE 0 10 2)               # 0,2,4,...,10
endforeach()

while(counter LESS 10)
    math(EXPR counter "${counter} + 1")
endwhile()

# 循环体内可用 continue() / break()
```

## 4. 函数与宏

```cmake
function(my_func arg1)
    message("Arg count: ${ARGC}")     # ARGC / ARGV / ARGN 取可变参数
    set(RESULT "done" PARENT_SCOPE)
endfunction()

macro(my_macro arg1)
    set(${arg1} "value")              # 宏直接修改调用者的变量
endmacro()
```

| 特性 | 函数 | 宏 |
| --- | --- | --- |
| 作用域 | 独立作用域 | 无，文本替换 |
| 修改变量 | 需要 PARENT_SCOPE | 直接修改调用者 |
| ARGV/ARGN | 真正的变量 | 字符串替换 |

## 5. 列表操作

```cmake
list(APPEND MY_LIST "d")
list(LENGTH MY_LIST LEN)
list(GET MY_LIST 0 FIRST)
list(FIND MY_LIST "b" IDX)
list(JOIN MY_LIST "," CSV)
list(FILTER MY_LIST INCLUDE REGEX "^a")
```

## 6. 目标构建（最常用）

```cmake
cmake_minimum_required(VERSION 3.22)
project(firmware LANGUAGES C ASM)

# 可执行体与库
add_executable(app src/main.c src/utils.c)
add_library(my_lib STATIC lib/src1.c)     # STATIC / SHARED / INTERFACE
file(GLOB SRC_FILES "src/*.c")            # 按目录搜源文件（新增文件不会触发重新配置，谨慎使用）

# 头文件路径：PRIVATE 本目标 / PUBLIC 本目标与依赖者 / INTERFACE 仅依赖者
target_include_directories(app PRIVATE include)

# 编译选项与宏定义
target_compile_options(app PRIVATE -Wall -O2)
target_compile_definitions(app PRIVATE STM32F407xx DEBUG=1)

# 链接
target_link_libraries(app PRIVATE my_lib pthread)
target_link_options(app PRIVATE -T${LINKER_SCRIPT} -Wl,--gc-sections)

# 自定义后处理
add_custom_command(TARGET app POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:app> firmware.bin
    COMMENT "Generating binary")

# 子目录与 cmake 模块
add_subdirectory(drivers)
include(cmake/modules.cmake)
```

## 7. 生成器表达式

构建时求值，常用于按配置区分选项：

```cmake
target_compile_options(app PRIVATE
    $<$<CONFIG:Debug>:-Og -g3>
    $<$<CONFIG:MinSizeRel>:-Os>
)
# 常用：$<TARGET_FILE:app> 目标文件路径；$<TARGET_FILE_DIR:app> 所在目录
```

## 8. 交叉编译工具链文件

```cmake
# cmake/arm-none-eabi-gcc.cmake
set(CMAKE_SYSTEM_NAME Generic)            # 裸机没有操作系统
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)  # 禁止运行编译器自检程序

set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
find_program(CMAKE_OBJCOPY arm-none-eabi-objcopy)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
```

```bash
cmake -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi-gcc.cmake -DCMAKE_BUILD_TYPE=Release -B build
cmake --build build -j
```

## 参考

- [CMake 官方文档](https://cmake.org/cmake/help/latest/)
