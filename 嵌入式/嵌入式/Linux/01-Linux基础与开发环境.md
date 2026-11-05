---
date: 2026-11-04
tags:
  - 嵌入式
  - Linux
aliases:
  - Linux基础第一章
  - 讲解Linux基础第一章
---

# Linux 基础与开发环境

## 1. Linux、GNU 与 Ubuntu

![[image/linux01-system-architecture.png]]

| 名称 | 含义 | 具体组成或职责 |
| --- | --- | --- |
| Linux | 操作系统内核，通常称为 Linux Kernel | 进程调度、内存管理、文件系统、设备驱动、网络管理 |
| GNU | 提供大量用户空间软件的项目 | Bash、GCC、GDB、Coreutils 等 |
| Ubuntu | 基于 Linux 内核构建的发行版 | 将内核、系统库、命令行工具、软件包和系统服务组合成可使用的系统 |

Bash、GCC、Python 和自己编写的应用程序都运行在用户空间。Bash 负责解释命令、处理重定向以及启动程序；程序启动后，可以通过系统库和系统调用请求内核服务。

例如执行：

```bash
cat /proc/cpuinfo
```

1. Bash 解析命令，启动 `cat`。
2. `cat` 通过文件接口打开 `/proc/cpuinfo`。
3. 内核中的 procfs 根据当前系统信息提供内容。
4. `cat` 读取内容，将结果写入标准输出。
5. 标准输出连接终端时，终端显示这些内容。

## 2. 用户空间、内核空间与系统调用

### 2.1 用户空间与内核空间

| 执行区域 | 运行内容 | 权限与职责 |
| --- | --- | --- |
| 用户空间（User Space） | Shell、工具、普通 C/C++ 程序、系统库 | 在进程的虚拟地址空间中运行，通过受控接口申请系统资源 |
| 内核空间（Kernel Space） | Linux Kernel、内核驱动 | 以较高的处理器权限管理内存、调度任务、访问设备并检查访问权限 |

普通程序访问未映射的地址，或者违反内存访问权限时，通常会收到 `SIGSEGV`，默认行为是终止进程。进程隔离限制了普通程序能够直接访问的内存范围。

| 内核子系统 | 职责 |
| --- | --- |
| Process Scheduler | 为可运行的线程分配 CPU 执行时间 |
| Memory Management | 管理虚拟内存、地址映射和物理内存 |
| VFS | 为不同文件系统提供统一的文件操作接口 |
| Device Drivers | 管理设备，并提供相应的访问方法 |
| Networking | 处理网络协议和数据收发 |
| IPC | 支持进程之间交换数据和通知 |

### 2.2 系统调用

**系统调用（System Call）是用户空间请求内核服务的主要接口。** 发生系统调用时，处理器进入内核执行相应操作，完成后返回用户空间。

| 接口名称 | 作用 |
| --- | --- |
| `open()` / `openat()` | 打开文件，成功后返回文件描述符 |
| `read()` | 从文件描述符读取数据 |
| `write()` | 向文件描述符写入数据 |
| `close()` | 关闭文件描述符 |
| `fork()` | 创建子进程 |
| `execve()` | 用指定程序替换当前进程正在执行的程序内容 |
| `mmap()` | 建立内存映射 |
| `ioctl()` | 对文件描述符执行设备或对象特有的控制操作 |
| `socket()` | 创建用于通信的 socket |

应用程序通常调用 libc 提供的接口。库函数与底层系统调用之间的对应关系由 libc 和处理器架构决定。例如，`open()` 在某些系统上会通过 `openat()` 完成请求。

### 2.3 C 标准库、POSIX API 与系统调用

| 层次 | 示例 | 说明 |
| --- | --- | --- |
| C 标准库 API | `printf()`、`fopen()`、`malloc()` | 提供格式化输出、文件流、内存分配等功能 |
| POSIX API | `read()`、`write()`、`fork()`、`pthread_create()` | 定义 Unix 类系统的通用编程接口 |
| Linux 系统调用 | `read`、`write`、`clone`、`execve` | Linux 内核实际接收的请求 |

`printf()` 负责格式化输出，并使用 C 标准库的缓冲机制。缓冲区需要输出时，库通常通过 `write()` 等系统调用提交数据。向终端输出和向文件重定向输出时，缓冲方式可能不同，一次 `printf()` 与一次 `write()` 之间没有固定的一对一关系。

### 2.4 读取普通文件的过程

```c
read(fd, buffer, sizeof(buffer));
```

1. 用户程序通过 libc 接口发起读取请求。
2. 系统调用进入内核。
3. 内核根据文件描述符 `fd` 找到对应的文件对象。
4. VFS 调用相应文件系统的读取操作。
5. 数据已经位于缓存时，可以从缓存取得；需要读取存储设备时，由相关驱动完成 I/O。
6. 内核将读取结果提供给用户空间缓冲区，返回读取的字节数或错误信息。

## 3. 文件接口与目录结构

![[image/linux01-file-interfaces.png]]

Linux 通过文件描述符和一组通用操作访问多种资源。普通文件、内核信息接口和设备节点都可以使用文件操作，但各自支持的操作及其行为由对应实现决定。

| 路径示例 | 对应资源 | 读取时发生的事情 |
| --- | --- | --- |
| `hello.txt` | 普通文件 | 读取文件保存的内容 |
| `/proc/cpuinfo` | procfs 提供的内核信息 | 获取内核提供的 CPU 信息 |
| `/sys/class/net/lo/address` | sysfs 提供的设备属性 | 获取 `lo` 网络接口的地址属性 |
| `/dev/tty` | 当前进程的控制终端接口 | 根据终端状态和设置接收输入 |

### 3.1 从根目录开始的目录树

```text
/
├── bin       基础用户命令
├── dev       设备节点及相关接口
├── etc       系统配置
├── home      普通用户的个人目录
├── lib       系统库及相关文件
├── proc      进程与内核信息接口
├── sys       设备模型与内核对象接口
├── tmp       临时文件目录
├── usr       用户空间程序、库和资源
└── var       日志、缓存等可变数据
```

所有路径都以根目录 `/` 为起点。不同文件系统可以挂载到这棵目录树中的不同位置。现代 Ubuntu 中，`/bin`、`/lib` 等目录通常通过符号链接连接到 `/usr` 下的对应目录。

## 4. /proc、/sys 与 /dev

### 4.1 /proc：进程与内核运行信息

`/proc` 通常挂载 procfs，其中许多内容由内核动态提供。

| 路径                   | 提供的信息                 |
| -------------------- | --------------------- |
| `/proc/cpuinfo`      | CPU 信息                |
| `/proc/meminfo`      | 内存统计                  |
| `/proc/uptime`       | 系统运行时间、各 CPU 空闲时间的累计值 |
| `/proc/version`      | 内核版本及构建信息             |
| `/proc/<PID>/status` | 对应进程的状态、UID、GID、内存等信息 |
| `/proc/<PID>/fd`     | 对应进程打开的文件描述符          |
| `/proc/self`         | 指向访问这个路径的进程所对应的目录     |

```bash
cat /proc/cpuinfo
cat /proc/meminfo
cat /proc/uptime
cat /proc/version
```

观察进程时需要注意 `/proc/self` 的访问者：

```bash
# 这里显示 cat 进程的信息
cat /proc/self/status

# 在 Bash 中，$$ 表示当前 Bash 的 PID
cat /proc/$$/status
ls -l /proc/$$/fd
```

内核维护 `task_struct` 等运行信息，procfs 将其中一部分内容通过文件接口提供给用户空间。读取结果会随系统和进程状态变化。

### 4.2 /sys：设备模型与内核对象

`/sys` 通常挂载 sysfs，用于呈现设备、驱动、总线以及其他内核对象的属性和关系。

| 路径 | 观察对象 |
| --- | --- |
| `/sys/class` | 按类别组织的设备接口 |
| `/sys/class/net` | 网络接口 |
| `/sys/class/tty` | 终端相关设备 |
| `/sys/devices/system/cpu` | CPU 相关对象与属性 |
| `/sys/class/thermal` | 系统提供的温度相关接口 |
| `/sys/bus/i2c/devices` | 系统中已注册的 I2C 设备 |

```bash
ls /sys/class
ls /sys/class/net
ls /sys/devices/system/cpu
cat /sys/class/net/lo/address
```

Linux 的设备模型涉及 **Device、Driver、Bus**：内核注册设备与驱动，根据相应总线的匹配规则建立联系，并通过 sysfs 呈现相关对象。

WSL 中能够观察到的设备和属性取决于 WSL 内核及其提供的设备。温度传感器、I2C 设备和 USB 串口等接口的可用情况需要结合当前环境判断。

### 4.3 /dev：通过设备节点访问驱动

`/dev` 包含设备节点，也可以包含符号链接、子目录和其他接口。设备节点通过设备类型与主设备号、次设备号关联内核中的驱动实现。

| 设备类型 | 访问特点 | 常见示例 |
| --- | --- | --- |
| 字符设备 | 驱动提供读取、写入、控制等操作，具体语义由设备决定 | 终端、串口、`/dev/null` |
| 块设备 | 支持按块寻址的存储访问 | 磁盘、SSD 及其分区 |

```bash
ls -l /dev/tty /dev/null /dev/zero
```

例如一行设备信息可能包含：

```text
crw-rw-rw- 1 root tty 5, 0 ... /dev/tty
```

| 字段 | 含义 |
| --- | --- |
| `c` | 字符设备；块设备使用 `b` |
| `rw-rw-rw-` | 所有者、所属用户组、其他用户的权限 |
| `root` | 所有者 |
| `tty` | 所属用户组 |
| `5, 0` | 主设备号与次设备号 |

以 USB 串口为例，程序打开 `/dev/ttyUSB0` 后获得文件描述符，再通过 `read()`、`write()` 等接口交换数据。串口参数通常通过 `termios` 相关接口配置。设备名称和访问权限由当前系统决定。

## 5. 进程、线程、状态与信号

![[image/linux01-process-threads.png]]

### 5.1 进程与线程

**进程（Process）是程序运行时的一个实例。** 一个进程通常包含虚拟地址空间、文件描述符表、身份和权限信息，以及一个或多个线程。

**线程（Thread）是内核调度的执行实体。** 同一个进程中的线程共享地址空间、全局变量、动态分配的内存和文件描述符表；每个线程分别具有自己的 stack、寄存器上下文、线程 ID 和调度状态。

Linux 内核使用 `task_struct` 表示可调度任务，通过资源共享关系组织进程与线程。已有的 FreeRTOS Task 调度经验可以帮助理解线程的就绪、运行和等待过程。

```bash
# 查看进程列表
ps aux

# 持续观察进程与资源使用情况，按 q 退出
top

# 在 Bash 中查看当前 Shell 的进程信息
ps -p "$$" -o pid,ppid,stat,comm
```

### 5.2 常见进程状态

| 状态 | 名称 | 含义 |
| --- | --- | --- |
| `R` | Running / Runnable | 正在运行，或者已经就绪、等待 CPU |
| `S` | Interruptible Sleep | 等待事件，可以被相应信号唤醒 |
| `D` | Uninterruptible Sleep | 处于内核中的不可中断等待，常与 I/O 有关 |
| `T` | Stopped | 暂停执行 |
| `Z` | Zombie | 已经退出，父进程尚未通过 `wait()` 等接口取得退出状态 |

`sleep` 等待定时器期间通常显示为 `S`。进程处于 `D` 状态时，即使收到终止信号，也可能需要等待相关内核操作结束后才能处理。`ps` 的 `STAT` 字段还可能带有其他标记。

### 5.3 信号

信号（Signal）用于向进程或线程传递异步事件通知。

| 信号 | 用途 |
| --- | --- |
| `SIGINT` | 请求中断；终端中的 `Ctrl+C` 通常向前台进程组发送该信号 |
| `SIGTERM` | 请求终止；程序可以注册处理函数以完成清理 |
| `SIGKILL` | 强制终止，不能被捕获、屏蔽或忽略 |
| `SIGSEGV` | 通知发生非法内存访问等错误 |
| `SIGSTOP` | 暂停执行，不能被捕获、屏蔽或忽略 |
| `SIGCONT` | 继续执行已经暂停的进程 |

`kill` 用于发送信号。常见的终止操作使用 `SIGTERM`，给程序完成清理的机会。使用信号名称可以直接表达操作含义。

## 6. Linux 开发工具

### 6.1 GCC：编译程序

GCC 是 GNU Compiler Collection，支持 C、C++ 等语言。

```bash
gcc -Wall -Wextra -g -O0 main.c -o app
./app
```

| 参数 | 作用 |
| --- | --- |
| `-Wall` | 开启一组常用警告 |
| `-Wextra` | 开启额外警告 |
| `-g` | 生成调试信息 |
| `-O0` | 使用适合基础调试的优化级别 |
| `-o app` | 将输出文件命名为 `app` |

### 6.2 GDB：观察程序执行

GDB 是 GNU Debugger，可以设置断点、单步执行、读取变量、查看函数调用关系和分析崩溃位置。

| GDB 命令 | 作用 |
| --- | --- |
| `break main` | 在 `main()` 设置断点 |
| `run` | 启动程序 |
| `next` | 执行到下一条源码语句，经过函数调用时执行完整调用 |
| `step` | 单步执行，需要时进入函数 |
| `print iteration` | 输出当前作用域中 `iteration` 的值 |
| `backtrace` | 显示当前函数调用关系 |
| `continue` | 继续执行 |
| `quit` | 退出 GDB |

### 6.3 Make 与 CMake：组织工程构建

| 工具 | 输入 | 负责的工作 |
| --- | --- | --- |
| Make | `Makefile` | 根据目标、依赖和命令执行构建，按需要重新构建目标 |
| CMake | `CMakeLists.txt` | 生成供 Make、Ninja 等工具使用的构建文件，并提供统一的构建入口 |

典型的 CMake 构建过程：

```text
CMakeLists.txt
      │ cmake -S . -B build
      ▼
build/ 中的构建文件
      │ cmake --build build
      ▼
Make / Ninja 调用 GCC 等工具
      ▼
目标文件与可执行程序
```

### 6.4 strace：观察系统调用

`strace` 用于观察程序发起的系统调用、返回值以及收到的信号，适合分析文件访问、权限问题、动态库加载和 I/O 行为。

```bash
strace ./app

# 只观察指定的系统调用
strace -e trace=openat,read,write ./app
```

程序启动时可能出现 `execve`、`mmap`、`openat` 等调用；输出文字时通常能观察到 `write`；进程结束时可能出现 `exit_group`。具体调用顺序与程序、libc 和系统环境有关。

## 7. 实践

以下命令在 WSL Ubuntu 的 Bash 中执行。实践所需软件包：

```bash
sudo apt update
sudo apt install build-essential gdb cmake strace
```

### 7.1 观察系统与文件接口

```bash
uname -a
cat /proc/cpuinfo
cat /proc/meminfo
cat /proc/uptime
ls /sys/class
ls /sys/class/net
ls -l /dev/tty /dev/null /dev/zero
```

观察目标：内核版本从哪里获取，CPU 和内存信息通过什么接口提供，sysfs 如何组织设备，以及设备节点的类型、权限和设备号。

### 7.2 观察进程与信号

在同一个 Bash 中执行：

```bash
sleep 1000 &
sleep_pid=$!

ps -p "$sleep_pid" -o pid,ppid,stat,comm
cat "/proc/$sleep_pid/status"

kill -STOP "$sleep_pid"
ps -p "$sleep_pid" -o pid,ppid,stat,comm

kill -CONT "$sleep_pid"
ps -p "$sleep_pid" -o pid,ppid,stat,comm

kill -TERM "$sleep_pid"
wait "$sleep_pid"
```

`$!` 保存最近启动的后台任务 PID。可以观察 `sleep` 的等待状态、暂停后的 `T` 状态以及继续执行后的变化。信号的处理需要调度时间；紧接着执行的状态查询可能仍显示此前的状态。

最后的 `wait` 等待子进程结束并取得退出状态。由于示例通过 `SIGTERM` 终止子进程，`wait` 返回非零状态属于该操作的预期结果。

### 7.3 编译并运行 C 程序

在自己的学习目录中创建 `main.c`：

```c
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>

int main(void)
{
    int iteration = 0;

    printf("Hello Linux\n");
    printf("PID: %ld\n", (long)getpid());
    printf("PPID: %ld\n", (long)getppid());

    while (iteration < 3) {
        sleep(1);
        ++iteration;
        printf("Running: %d\n", iteration);
    }

    return 0;
}
```

```bash
gcc -Wall -Wextra -g -O0 main.c -o app
./app
```

程序输出自身 PID、父进程 PPID，以及三次运行提示，然后正常退出。

### 7.4 使用 GDB 调试

```bash
gdb ./app
```

进入 GDB 后执行：

```gdb
break main
run
next
print iteration
backtrace
continue
quit
```

`next` 执行初始化语句后，可以观察 `iteration` 的值。使用 `next` 或 `step` 继续执行时，可以观察变量和源码位置如何变化。

### 7.5 使用 strace 观察程序与内核交互

```bash
strace -e trace=write,nanosleep,clock_nanosleep ./app
strace -e trace=openat,read,write cat /proc/uptime
```

第一条命令用于观察输出与睡眠操作。第二条命令用于观察打开、读取 `/proc/uptime` 并输出结果的过程。`cat` 启动时加载运行库等操作，也可能产生额外的文件访问。

## 8. 自测

1. Linux Kernel、GNU 与 Ubuntu 分别负责什么？
2. 用户程序调用 `read()` 时，怎样请求内核完成读取？
3. `/proc`、`/sys`、`/dev` 分别提供什么接口？网卡的设备属性可以从哪里观察？
4. `/dev/ttyUSB0` 通常属于什么类型的设备节点？
5. 同一个进程中的线程共享哪些资源？每个线程分别保存哪些执行信息？
6. `S`、`D`、`T`、`Z` 分别表示什么状态？
7. `SIGTERM`、`SIGKILL` 和 `SIGSTOP` 分别用于什么操作？
8. GCC、GDB、CMake、Make 和 strace 分别解决什么问题？

> [!tip]- 参考答案
> 1. Linux Kernel 管理系统资源；GNU 提供大量用户空间工具；Ubuntu 将内核和软件组织成发行版。
> 2. 通过系统调用进入内核，由内核根据文件描述符和对应文件操作处理请求。
> 3. `/proc` 提供进程和内核运行信息；`/sys` 呈现设备、驱动和内核对象；`/dev` 提供设备节点等接口。网卡属性可以从 `/sys/class/net` 观察。
> 4. 字符设备节点。
> 5. 共享地址空间、全局变量、动态分配的内存和文件描述符表；分别具有 stack、寄存器上下文、线程 ID 和调度状态。
> 6. `S` 为可中断睡眠，`D` 为不可中断睡眠，`T` 为暂停执行，`Z` 为已退出且等待父进程取得退出状态。
> 7. `SIGTERM` 请求终止，`SIGKILL` 强制终止，`SIGSTOP` 暂停执行。
> 8. GCC 编译程序；GDB 调试源码执行；CMake 生成构建文件；Make 执行构建规则；strace 观察系统调用和信号。

## 来源与相关笔记

- [讲解 Linux 基础第一章](https://chatgpt.com/c/6aeae0b3-b574-83e8-9e00-a82c6e10c36a)
- [[linux常用命令]]
