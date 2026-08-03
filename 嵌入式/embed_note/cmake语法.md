# CMake 语法笔记

## 1. 基础概念

CMake 是一个跨平台的构建系统生成器，不直接构建软件，而是生成标准的构建文件（如 Makefile、Ninja 文件等）。

### 1.1 CMake 文件结构

```
project/
├── CMakeLists.txt          # 主构建文件
├── cmake/
│   ├── toolchain.cmake     # 工具链文件（交叉编译）
│   └── modules/            # 自定义模块
└── src/
    └── CMakeLists.txt      # 子目录构建文件
```

### 1.2 基本语法

```cmake
# 注释
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES C ASM)

# 命令语法：命令名(参数1 参数2 ...)
# 命令名不区分大小写，参数用空格或换行分隔
```

## 2. 变量

### 2.1 变量定义与使用

```cmake
# 定义变量
set(MY_VAR "hello")
set(MY_LIST a b c d)          # 列表用分号分隔
set(MY_LIST "a;b;c;d")        # 等价写法

# 引用变量
message("Value: ${MY_VAR}")
message("List: ${MY_LIST}")
```

### 2.2 变量作用域

```cmake
# 普通变量：当前作用域及子目录可见
set(VAR "parent")

# PARENT_SCOPE：只影响父作用域
function(my_func)
    set(VAR "child" PARENT_SCOPE)  # 修改父作用域的变量
endfunction()

# CACHE 变量：持久化到 CMakeCache.txt
set(MY_CACHE_VAR "default" CACHE STRING "Description")

# 强制覆盖 cache
set(MY_CACHE_VAR "new_value" CACHE STRING "" FORCE)
```

### 2.3 常用内置变量

```cmake
# 项目相关
${PROJECT_NAME}          # 项目名称
${PROJECT_SOURCE_DIR}    # 项目根目录
${PROJECT_BINARY_DIR}    # 构建目录

# 当前目录
${CMAKE_CURRENT_SOURCE_DIR}  # 当前 CMakeLists.txt 所在目录
${CMAKE_CURRENT_BINARY_DIR}  # 当前构建输出目录

# 编译器
${CMAKE_C_COMPILER}      # C 编译器
${CMAKE_CXX_COMPILER}    # C++ 编译器
${CMAKE_C_FLAGS}         # C 编译标志

# 构建类型
${CMAKE_BUILD_TYPE}      # Debug/Release/MinSizeRel/RelWithDebInfo

# 目标平台
${CMAKE_SYSTEM_NAME}     # 目标系统名称
${CMAKE_SYSTEM_PROCESSOR} # 目标处理器
```

## 3. 条件语句

### 3.1 if 语法

```cmake
if(condition)
    # commands
elseif(condition2)
    # commands
else()
    # commands
endif()
```

### 3.2 条件判断

```cmake
# 字符串比较
if(MY_VAR STREQUAL "hello")     # 相等
if(MY_VAR MATCHES "^[0-9]+$")  # 正则匹配

# 变量检查
if(DEFINED MY_VAR)              # 变量已定义
if(MY_VAR)                      # 变量为真值

# 数字比较
if(MY_VAR GREATER 10)
if(MY_VAR LESS 10)
if(MY_VAR EQUAL 10)
if(MY_VAR GREATER_EQUAL 10)
if(MY_VAR LESS_EQUAL 10)

# 文件检查
if(EXISTS "/path/to/file")
if(IS_DIRECTORY "/path/to/dir")

# 逻辑运算
if(NOT condition)
if(condition1 AND condition2)
if(condition1 OR condition2)
```

### 3.3 真值判断

```cmake
# 真值
# TRUE, ON, YES, 1, 非零数字

# 假值
# FALSE, OFF, NO, 0, "", NOTFOUND
```

## 4. 循环

### 4.1 foreach 循环

```cmake
# 基本语法
foreach(item IN LISTS MY_LIST)
    message("Item: ${item}")
endforeach()

# 范围循环
foreach(i RANGE 1 10)
    message("Number: ${i}")
endforeach()

# 带步长
foreach(i RANGE 0 10 2)  # 0, 2, 4, 6, 8, 10
    message("Even: ${i}")
endforeach()
```

### 4.2 while 循环

```cmake
set(counter 0)
while(counter LESS 10)
    message("Counter: ${counter}")
    math(EXPR counter "${counter} + 1")
endwhile()
```

### 4.3 循环控制

```cmake
foreach(item IN LISTS MY_LIST)
    if(item STREQUAL "skip")
        continue()  # 跳过当前迭代
    endif()
    if(item STREQUAL "stop")
        break()     # 退出循环
    endif()
    message("Processing: ${item}")
endforeach()
```

## 5. 函数与宏

### 5.1 函数 function()

```cmake
function(my_function arg1 arg2)
    # arg1, arg2 是局部变量
    # 函数有独立的作用域
    message("Args: ${arg1}, ${arg2}")

    # 修改父作用域变量
    set(RESULT "done" PARENT_SCOPE)
endfunction()

# 调用
my_function("hello" "world")
message("Result: ${RESULT}")
```

### 5.2 可变参数

```cmake
function(my_func)
    message("Arg count: ${ARGC}")
    message("All args: ${ARGV}")

    # 遍历可变参数
    foreach(arg IN LISTS ARGN)
        message("Extra arg: ${arg}")
    endforeach()
endfunction()

# 调用
my_func(one two extra1 extra2)
```

### 5.3 宏 macro()

```cmake
# 宏没有独立作用域，类似文本替换
macro(my_macro arg1)
    set(${arg1} "value")  # 直接修改调用者的变量
endmacro()

my_macro(MY_VAR)
message("${MY_VAR}")  # 输出: value
```

### 5.4 函数 vs 宏

| 特性 | 函数 | 宏 |
|------|------|-----|
| 作用域 | 独立作用域 | 无作用域（文本替换） |
| 变量修改 | 需要 PARENT_SCOPE | 直接修改调用者 |
| ARGV/ARGN | 真正的变量 | 字符串替换 |
| return() | 正常返回 | 退出调用者作用域 |

## 6. 列表操作

```cmake
# 创建列表
set(MY_LIST "a" "b" "c")
list(APPEND MY_LIST "d")        # 追加元素
list(PREPEND MY_LIST "z")       # 插入到开头
list(INSERT MY_LIST 1 "x")      # 在索引1处插入

# 访问
list(LENGTH MY_LIST LEN)        # 获取长度
list(GET MY_LIST 0 FIRST)       # 获取第一个元素
list(GET MY_LIST -1 LAST)       # 获取最后一个元素

# 搜索
list(FIND MY_LIST "b" IDX)      # 查找元素，返回索引
list(FILTER MY_LIST INCLUDE REGEX "^a")  # 过滤

# 排序
list(SORT MY_LIST)

# 转换
list(JOIN MY_LIST "," CSV)      # 列表转字符串
list(POP_BACK MY_LIST ITEM)     # 弹出最后一个
list(POP_FRONT MY_LIST ITEM)    # 弹出第一个
```

## 7. 常用命令

### 7.1 项目定义

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject
    VERSION 1.0.0
    LANGUAGES C CXX ASM
    DESCRIPTION "My embedded project"
)
```

### 7.2 源文件收集

```cmake
# 显式列出源文件
add_executable(my_app
    src/main.c
    src/utils.c
    startup.s
)

# 使用 file(GLOB)
file(GLOB SRC_FILES "src/*.c")
add_executable(my_app ${SRC_FILES})

# 递归搜索
file(GLOB_RECURSE SRC_FILES "src/*.c")
```

### 7.3 头文件包含

```cmake
target_include_directories(my_app
    PRIVATE                 # 仅本目标使用
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/drivers
    PUBLIC                  # 本目标和依赖者都使用
        ${CMAKE_SOURCE_DIR}/api
)
```

### 7.4 编译选项

```cmake
# 全局选项
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra")

# 目标选项（推荐）
target_compile_options(my_app PRIVATE
    -Wall
    -Wextra
    -O2
)

# 生成器表达式（按配置区分）
target_compile_options(my_app PRIVATE
    $<$<CONFIG:Debug>:-Og -g3>
    $<$<CONFIG:Release>:-O2>
    $<$<CONFIG:MinSizeRel>:-Os>
)
```

### 7.5 预处理定义

```cmake
# 全局定义
add_definitions(-DDEBUG -DUSE_HAL_DRIVER)

# 目标定义（推荐）
target_compile_definitions(my_app PRIVATE
    DEBUG=1
    STM32F407xx
    HSE_VALUE=8000000U
)

# 条件定义
target_compile_definitions(my_app PRIVATE
    $<$<CONFIG:Debug>:DEBUG=1>
    $<$<CONFIG:Release>:NDEBUG=1>
)
```

### 7.6 链接库

```cmake
# 链接库
target_link_libraries(my_app
    PRIVATE
        my_lib               # 链接 my_lib
        pthread              # 链接系统库
        ${CMAKE_SOURCE_DIR}/lib/libfoo.a  # 直接指定库文件
)

# 链接选项
target_link_options(my_app PRIVATE
    -T${LINKER_SCRIPT}
    -Wl,--gc-sections
    -Wl,--print-memory-usage
)
```

### 7.7 库生成

```cmake
# 静态库
add_library(my_lib STATIC
    lib/src1.c
    lib/src2.c
)

# 动态库
add_library(my_lib SHARED
    lib/src1.c
    lib/src2.c
)

# 接口库（仅传递头文件）
add_library(my_headers INTERFACE)
target_include_directories(my_headers INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

### 7.8 自定义命令

```cmake
# 后处理命令（生成 hex/bin）
add_custom_command(TARGET my_app POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex
        $<TARGET_FILE:my_app>
        $<TARGET_FILE_DIR:my_app>/firmware.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary
        $<TARGET_FILE:my_app>
        $<TARGET_FILE_DIR:my_app>/firmware.bin
    COMMAND ${CMAKE_SIZE} -B $<TARGET_FILE:my_app>
    COMMENT "Generating firmware images"
)

# 生成文件命令
add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/generated.h
    COMMAND ${CMAKE_COMMAND} -E env
        python3 ${CMAKE_SOURCE_DIR}/scripts/gen.py
        > ${CMAKE_BINARY_DIR}/generated.h
    DEPENDS ${CMAKE_SOURCE_DIR}/scripts/gen.py
    COMMENT "Generating header file"
)
```

### 7.9 子目录

```cmake
# 添加子目录
add_subdirectory(src)
add_subdirectory(libs/my_lib)

# include 其他 cmake 文件
include(${CMAKE_SOURCE_DIR}/cmake/modules.cmake)
```

## 8. 生成器表达式

生成器表达式在构建时求值，支持条件配置：

```cmake
# 条件判断
$<$<CONFIG:Debug>:-Og -g3>
$<$<NOT:$<CONFIG:Debug>>:-O2>

# 目标属性
$<TARGET_FILE:my_app>           # 目标文件路径
$<TARGET_FILE_DIR:my_app>       # 目标文件目录
$<TARGET_OBJECTS:my_lib>        # 对象文件列表

# 字符串操作
$<LOWER_CASE:HELLO>             # 转小写
$<UPPER_CASE:hello>             # 转大写
$<JOIN:my_list;,>               # 列表连接

# 逻辑
$<AND:cond1,cond2>
$<OR:cond1,cond2>
$<NOT:condition>
```

## 9. 嵌入式开发常用模式

### 9.1 工具链文件 (toolchain.cmake)

```cmake
# cmake/toolchains/arm-none-eabi-gcc.cmake
cmake_minimum_required(VERSION 3.20)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# 禁用编译器测试（裸机环境无法运行测试程序）
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# 交叉编译器
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)

# 工具链工具
find_program(CMAKE_OBJCOPY arm-none-eabi-objcopy)
find_program(CMAKE_OBJDUMP arm-none-eabi-objdump)
find_program(CMAKE_SIZE arm-none-eabi-size)

# 仅在目标系统搜索库和头文件
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 9.2 Cortex-M 项目模板

```cmake
cmake_minimum_required(VERSION 3.20)
project(firmware LANGUAGES C ASM)

# 链接脚本
set(LINKER_SCRIPT ${CMAKE_SOURCE_DIR}/linker/stm32f407.ld)

# 主目标
add_executable(${PROJECT_NAME}.elf
    src/main.c
    src/system.c
    startup/startup_stm32f407xx.s
)

# 头文件
target_include_directories(${PROJECT_NAME}.elf PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/CMSIS/Include
)

# 编译选项
target_compile_options(${PROJECT_NAME}.elf PRIVATE
    -mcpu=cortex-m4
    -mthumb
    -mfloat-abi=hard
    -mfpu=fpv4-sp-d16
    -ffunction-sections
    -fdata-sections
    -Wall
)

# 链接选项
target_link_options(${PROJECT_NAME}.elf PRIVATE
    -T${LINKER_SCRIPT}
    -Wl,--gc-sections
    -Wl,--print-memory-usage
    --specs=nosys.specs
    --specs=nano.specs
    -lc -lm -lnosys
)

# 后处理：生成 hex/bin
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex
        $<TARGET_FILE:${PROJECT_NAME}.elf>
        ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary
        $<TARGET_FILE:${PROJECT_NAME}.elf>
        ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>
    COMMENT "Generating firmware images"
)
```

### 9.3 使用方法

```bash
# 使用工具链文件
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../cmake/toolchains/arm-none-eabi-gcc.cmake ..

# 或指定构建类型
cmake -DCMAKE_BUILD_TYPE=Release ..

# 构建
make -j4
```

## 10. 常用 CMake 变量速查

| 变量 | 说明 |
|------|------|
| `CMAKE_SOURCE_DIR` | 顶层源目录 |
| `CMAKE_BINARY_DIR` | 顶层构建目录 |
| `CMAKE_CURRENT_SOURCE_DIR` | 当前 CMakeLists 所在目录 |
| `CMAKE_CURRENT_BINARY_DIR` | 当前构建输出目录 |
| `CMAKE_C_COMPILER` | C 编译器路径 |
| `CMAKE_CXX_COMPILER` | C++ 编译器路径 |
| `CMAKE_BUILD_TYPE` | 构建类型 |
| `CMAKE_C_FLAGS` | 全局 C 编译标志 |
| `CMAKE_EXE_LINKER_FLAGS` | 全局链接标志 |
| `CMAKE_SYSTEM_NAME` | 目标系统名称 |
| `CMAKE_SYSTEM_PROCESSOR` | 目标处理器 |
| `CMAKE_OBJCOPY` | objcopy 工具路径 |
| `CMAKE_SIZE` | size 工具路径 |

## 参考资料

- [CMake 官方文档](https://cmake.org/cmake/help/latest/)
- [CMake 教程](https://cmake.org/cmake/help/latest/guide/tutorial/)
- [Mastering CMake](https://cmake.org/cmake/help/book/mastering-cmake/)
