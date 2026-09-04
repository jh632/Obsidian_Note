---
tags: [zephyr, rtos, api, 内核, 线程, 信号量, 消息队列, 日志, shell]
date: 2026-09-01
aliases: [Zephyr核心API, Zephyr RTOS API, zephyr核心api]
---

# Zephyr RTOS 核心 API 参考手册

> 适用版本：Zephyr ≥ 4.x  
> 目标芯片：ESP32-S3  

---

## 目录

1. [线程 (Threads)](#1-线程-threads)
2. [调度 (Scheduling)](#2-调度-scheduling)
3. [定时器 (Timers)](#3-定时器-timers)
4. [中断 (Interrupts)](#4-中断-interrupts)
5. [同步原语 (Semaphores & Mutexes)](#5-同步原语-semaphores--mutexes)
6. [数据传递 (Message Queues & FIFOs)](#6-数据传递-message-queues--fifos)
7. [日志系统 (Logging)](#7-日志系统-logging)
8. [Shell](#8-shell)
9. [完整示例](#9-完整示例)

---

## 1. 线程 (Threads)

### 1.1 两种创建方式

Zephyr 线程和 FreeRTOS 的 task 是同一个概念——拥有独立栈、优先级和执行函数。

**方式 A：编译时静态创建（推荐）**

```c
#include <zephyr/kernel.h>

/* 线程入口函数签名：void func(void *p1, void *p2, void *p3) */
void my_thread(void *arg1, void *arg2, void *arg3)
{
    while (1) {
        printk("Hello from my_thread\n");
        k_sleep(K_SECONDS(1));
    }
}

/* 一行搞定：定义栈 + TCB + tid，编译时完成 */
K_THREAD_DEFINE(my_tid,              /* 线程名（也是 k_tid_t 变量名） */
                2048,                /* 栈大小（字节） */
                my_thread,           /* 入口函数 */
                NULL, NULL, NULL,    /* 三个参数 */
                5,                   /* 优先级（数字越小优先级越高） */
                0,                   /* 选项（0 = 无特殊选项） */
                0);                  /* 延时启动（毫秒，0 = 立即） */
```

**方式 B：运行时动态创建**

```c
K_THREAD_STACK_DEFINE(my_stack, 2048);           /* 先定义栈 */
struct k_thread my_thread_data;                   /* TCB 变量 */

void main(void)
{
    k_tid_t tid = k_thread_create(&my_thread_data, my_stack,
                                  K_THREAD_STACK_SIZEOF(my_stack),
                                  my_thread,
                                  NULL, NULL, NULL,     /* 三个参数 */
                                  5,                    /* 优先级 */
                                  0,                    /* 选项 */
                                  K_NO_WAIT);           /* 立即启动 */
}
```

### 1.2 线程管理 API

| API | 作用 | 说明 |
|-----|------|------|
| `k_thread_abort(tid)` | 终止线程 | 线程不再运行 |
| `k_thread_suspend(tid)` | 挂起线程 | 暂停调度 |
| `k_thread_resume(tid)` | 恢复线程 | 继续调度 |
| `k_thread_priority_set(tid, prio)` | 改优先级 | 运行时调整 |
| `k_thread_join(tid, K_FOREVER)` | 等待线程结束 | 类似 pthread_join |
| `k_current_get()` | 获取当前线程 tid | 在函数内调用 |
| `k_sleep(K_SECONDS(n))` | 睡眠 n 秒 | 最常用的延时 |
| `k_msleep(n)` | 睡眠 n 毫秒 | 等效 K_MSEC(n) |
| `k_yield()` | 让出 CPU | 同优先级协作者 |

### 1.3 线程选项（options）

| 选项 | 作用 |
|------|------|
| `0` | 无特殊选项（默认） |
| `K_ESSENTIAL` | 关键线程——如果它退出会导致系统 panic |
| `K_FP_REGS` | 需要浮点寄存器（有 FPU 的核） |
| `K_SSE_REGS` | 需要 SSE 寄存器 |

### 1.4 用 `K_THREAD_DEFINE` 还是 `k_thread_create`？

| 方式 | 什么时候用 |
|------|-----------|
| `K_THREAD_DEFINE` | **大多数情况**。栈在 .bss 段，系统启动后自动就绪 |
| `k_thread_create` | 不确定是否需要创建、栈想动态分配、数量可变时 |

> ✅ 你的 PSA 项目里每个传感器有自己的采集线程——在 Zephyr 里就等价于 N 个 `K_THREAD_DEFINE`。

---

## 2. 调度 (Scheduling)

### 2.1 抢占式 vs 协作式

Zephyr 默认是**抢占式调度**（`CONFIG_PREEMPT_ENABLED=y`），即高优先级线程就绪时立即抢占低优先级线程。

**控制方式：**

```c
/* 协作式 yield——让出 CPU，同优先级或更高优先级的线程可以运行 */
k_yield();

/* 普通 sleep——也是抢占点 */
k_sleep(K_MSEC(10));

/* 锁定调度器（当前线程变成协作式，不被抢占） */
k_sched_lock();
/* ... 这段代码不参与抢占 ... */
k_sched_unlock();
```

### 2.2 优先级

- 数字越小优先级越高（0 最高）
- 典型的用户线程优先级范围：`5` ~ `10`
- 空闲线程优先级最低：`K_IDLE_PRIO`（通常是负数或 15 以上，取决于配置）
- **优先级上限**由 `CONFIG_NUM_PREEMPT_PRIORITIES` 和 `CONFIG_NUM_COOP_PRIORITIES` 决定

```c
/* 查看当前线程优先级 */
int prio = k_thread_priority_get(k_current_get());
```

### 2.3 Tickless 空闲

Zephyr 默认启用 tickless idle（`CONFIG_TICKLESS_KERNEL=y`）。没有线程就绪时，系统进入低功耗模式直到下一个定时器事件。**开发者不需要为此做任何额外工作。**

---

## 3. 定时器 (Timers)

Zephyr 的定时器是基于系统时钟周期的，不占用硬件定时器外设。

### 3.1 定义和初始化

```c
#include <zephyr/kernel.h>

/* 超时回调 */
void my_timer_handler(struct k_timer *timer)
{
    /* 在中断上下文中执行！必须简短，不能阻塞 */
    printk("Timer expired!\n");
}

/* 编译时定义 */
K_TIMER_DEFINE(my_timer, my_timer_handler, NULL);
/*                        ^回调函数       ^停止回调(NULL=不需要) */

/* 或者运行时初始化 */
struct k_timer my_timer;
k_timer_init(&my_timer, my_timer_handler, NULL);
```

### 3.2 启动和停止

```c
/* 一次性定时器：500ms 后触发一次，然后停止 */
k_timer_start(&my_timer, K_MSEC(500), K_NO_WAIT);

/* 周期性定时器：首次 1s 后触发，之后每 2s 触发一次 */
k_timer_start(&my_timer, K_SECONDS(1), K_SECONDS(2));

/* 停止定时器 */
k_timer_stop(&my_timer);

/* 重新启动（重置计数） */
k_timer_start(&my_timer, K_MSEC(500), K_MSEC(500));
```

### 3.3 查询定时器状态

```c
/* 读取过期次数（读取后自动清零） */
uint32_t count = k_timer_status_get(&my_timer);

/* 线程等待定时器过期（阻塞） */
uint32_t count = k_timer_status_sync(&my_timer);

/* 查询还有多久过期（0 = 已停止） */
uint32_t remaining = k_timer_remaining_get(&my_timer);

/* 查询定时器是否正在运行 */
bool running = k_timer_is_running(&my_timer);
```

### 3.4 不使用回调的轮询模式

很多开发者只在需要确认定时器状态时才处理，回调传 NULL：

```c
K_TIMER_DEFINE(my_timer, NULL, NULL);

void worker_thread(void)
{
    k_timer_start(&my_timer, K_SECONDS(5), K_SECONDS(5));

    while (1) {
        /* 阻塞直到定时器过期或被停止 */
        k_timer_status_sync(&my_timer);
        printk("5 seconds passed\n");
    }
}
```

### 3.5 关键注意事项

- **回调在中断上下文执行**——不能阻塞（不能 `k_sleep`、`k_sem_take(K_FOREVER)` 等）
- 回调应该**非常简短**，仅做标记或给信号量
- 通常做法：回调里 `k_sem_give`，线程里等信号量

---

## 4. 中断 (Interrupts)

### 4.1 静态中断连接（推荐）

所有参数必须在编译时已知：

```c
#include <zephyr/kernel.h>
#include <zephyr/irq.h>

#define MY_GPIO_IRQ   5       /* IRQ 线号（硬件相关） */
#define MY_GPIO_PRIO  2       /* 中断优先级 */
#define MY_IRQ_FLAGS  0       /* 架构相关标志 */

void my_isr(const void *arg)
{
    /* ISR 代码——不能阻塞！ */
    uint32_t dev = (uint32_t)arg;
    /* ... */
}

void install_isr(void)
{
    IRQ_CONNECT(MY_GPIO_IRQ,     /* IRQ 号 */
                MY_GPIO_PRIO,    /* 优先级 */
                my_isr,          /* 处理函数 */
                (void *)0,       /* 传给 ISR 的参数 */
                MY_IRQ_FLAGS);   /* 标志 */
    irq_enable(MY_GPIO_IRQ);     /* 使能中断 */
}
```

### 4.2 动态中断连接

运行时参数不能确定的场合：

```c
irq_connect_dynamic(MY_GPIO_IRQ, MY_GPIO_PRIO, my_isr, (void *)dev, 0);
irq_enable(MY_GPIO_IRQ);
```

### 4.3 中断使能/禁用的其他函数

```c
irq_disable(irq_num);       /* 关闭某个中断 */
irq_lock();                 /* 关全局中断（返回当前 key） */
irq_unlock(key);            /* 恢复之前的状态 */
```

### 4.4 ISR 中的约束

**在 ISR 中可以做的事情：**

| 操作 | 可以？ |
|------|--------|
| `k_sem_give` | ✅ |
| `k_msgq_put` | ✅（但 `timeout` 必须 `K_NO_WAIT`） |
| `k_msgq_get` | ✅（但 `timeout` 必须 `K_NO_WAIT`） |
| `k_fifo_put` | ✅ |
| `k_is_in_isr()` | ✅ 检测是否在 ISR 中 |
| `k_sleep()` | ❌ |
| `k_sem_take(K_FOREVER)` | ❌ |
| `k_mutex_lock()` | ❌ |
| `k_timer_status_sync()` | ❌ |

---

## 5. 同步原语 (Semaphores & Mutexes)

### 5.1 信号量 (k_sem)

Zephyr 的信号量是**计数信号量**。`count` 表示当前可用资源的数量，`limit` 是最大值。

```c
#include <zephyr/kernel.h>

/* 编译时定义：初始 count=0, 最大 limit=1（即二值信号量） */
K_SEM_DEFINE(my_sem, 0, 1);

/* 运行时初始化 */
struct k_sem my_sem;
k_sem_init(&my_sem, 0, 1);   /* count=0, limit=1 */
```

**使用：**

```c
/* ISR 或线程中：给信号量 */
k_sem_give(&my_sem);

/* 线程中：等信号量，无限等待 */
k_sem_take(&my_sem, K_FOREVER);

/* 线程中：等 100ms，超时返回非 0 */
if (k_sem_take(&my_sem, K_MSEC(100)) != 0) {
    printk("Timeout waiting for semaphore\n");
}

/* 查询当前 count */
uint32_t count = k_sem_count_get(&my_sem);
```

**典型模式——ISR 通知线程：**

```c
K_SEM_DEFINE(data_ready, 0, 1);

void sensor_isr(const void *arg)
{
    k_sem_give(&data_ready);    /* ISR 中通知线程 */
}

void sensor_thread(void *p1, void *p2, void *p3)
{
    while (1) {
        k_sem_take(&data_ready, K_FOREVER);   /* 等数据 */
        read_sensor();                         /* 处理数据 */
    }
}
```

### 5.2 互斥锁 (k_mutex)

Zephyr 的 mutex 支持**可重入锁定**（同一线程可以重复 lock）和**优先级继承**（防止优先级反转）。

```c
K_MUTEX_DEFINE(my_mutex);     /* 编译时定义 */

/* 运行时 */
k_mutex_lock(&my_mutex, K_FOREVER);    /* 无限等待锁 */
/* 临界区 */
k_mutex_unlock(&my_mutex);

/* 超时 */
if (k_mutex_lock(&my_mutex, K_MSEC(100)) == 0) {
    /* 成功获取锁 */
    /* ... */
    k_mutex_unlock(&my_mutex);
} else {
    printk("Cannot acquire mutex\n");
}
```

**关于优先级继承：**  
如果低优先级线程持有锁，高优先级线程来等这把锁——Zephyr 内核会暂时提升低优先级线程到接近高优先级的水平，让它尽快用完释放。`CONFIG_PRIORITY_CEILING` 可以设置提升的上限。

### 5.3 信号量 vs 互斥锁

| | `k_sem` | `k_mutex` |
|--|---------|-----------|
| 用途 | 通知/计数 | 互斥访问 |
| 可以在 ISR 用？ | give ✅ / take ❌（不能等） | ❌ |
| 优先级继承 | ❌ | ✅ |
| 可重入 | ❌ | ✅ |
| 谁 unlock | 任意线程 | 必须 owner |

---

## 6. 数据传递 (Message Queues & FIFOs)

### 6.1 消息队列 (k_msgq)

固定大小的消息队列，数据是**拷贝传递**的（不是指针）。适合传输固定长度的结构化数据。

```c
#include <zephyr/kernel.h>

struct sensor_data {
    uint16_t value;
    uint64_t timestamp;
};

/* 编译时定义：10 个槽位，每个 sizeof(struct sensor_data) 字节 */
K_MSGQ_DEFINE(sensor_msgq, sizeof(struct sensor_data), 10, 1);
/*                                                                 ^对齐（1 即可） */
```

**使用：**

```c
/* 发送（生产者） */
struct sensor_data data = {.value = 42, .timestamp = k_uptime_get()};
while (k_msgq_put(&sensor_msgq, &data, K_NO_WAIT) != 0) {
    /* 队列满了——清空旧数据 */
    k_msgq_purge(&sensor_msgq);
}

/* 发送到队首（优先级消息） */
k_msgq_put_front(&sensor_msgq, &data);

/* 接收（消费者）——阻塞等待 */
struct sensor_data rx;
k_msgq_get(&sensor_msgq, &rx, K_FOREVER);

/* 非阻塞接收 */
if (k_msgq_get(&sensor_msgq, &rx, K_NO_WAIT) == 0) {
    /* 取到了 */
}

/* 偷看（不移除） */
k_msgq_peek(&sensor_msgq, &rx);

/* 队列状态 */
uint32_t used = k_msgq_num_used_get(&sensor_msgq);
uint32_t free = k_msgq_num_free_get(&sensor_msgq);
```

### 6.2 FIFO (k_fifo)

传递**任意大小**的数据块，但传递的是**指针**（数据本身由发送者管理生命期，或者用 `k_fifo_alloc_put` 自动分配）。

```c
K_FIFO_DEFINE(my_fifo);

/* 注意：放入 FIFO 的数据结构的第一个字被 FIFO 内部占用！ */
struct data_item {
    void *fifo_reserved;   /* ← 必须放在第一个字段 */
    uint32_t payload;
    /* ... */
};
```

**使用：**

```c
/* 发送（放入指针） */
struct data_item *item = k_malloc(sizeof(struct data_item));
item->payload = 100;
k_fifo_put(&my_fifo, item);

/* 自动分配模式（不用自己保留第一个字） */
k_fifo_alloc_put(&my_fifo, &data, sizeof(data));

/* 接收 */
struct data_item *rx = k_fifo_get(&my_fifo, K_FOREVER);
/* 用完记得 free */
k_free(rx);

/* 批量发送 */
k_fifo_put_list(&my_fifo, head_of_list);    /* 用链表头的 sys_snode_t */
k_fifo_put_slist(&my_fifo, &slist);         /* 用 sys_slist_t */
```

### 6.3 Queue (k_queue)

`k_queue` 是 FIFO 和 LIFO 的底层实现。通常你直接用 `k_fifo` 或 `k_lifo` 就行，但 Queue 提供了append/prepend 的灵活性。

### 6.4 选哪个？

| 场景 | 选哪个 |
|------|--------|
| 固定大小的结构体流 | `k_msgq` |
| 变长数据或大数据块 | `k_fifo` |
| 后进先出需求 | `k_lifo` |

---

## 7. 日志系统 (Logging)

Zephyr 的日志系统远强于 `printk`——支持等级、模块名、运行时过滤、格式化输出。

### 7.1 基本用法

```c
#include <zephyr/logging/log.h>

/* 注册模块名（每个 .c 文件只能调用一次） */
/* 第二个参数是编译时日志级别 */
LOG_MODULE_REGISTER(my_sensor, CONFIG_MY_SENSOR_LOG_LEVEL);

void read_data(void)
{
    LOG_INF("Sensor initialized, address 0x%02x", 0x76);    /* 信息 */
    LOG_WRN("Reading delayed by %d ms", 5);                  /* 警告 */
    LOG_ERR("Communication failed! err=%d", -5);             /* 错误 */
    LOG_DBG("raw data: %d %d %d", a, b, c);                 /* 调试 */
}
```

### 7.2 日志级别

> ⚠️ 勘误（2026-09-01 整理时修正）：原笔记此处写 `LOG_ERR=0`，与官方 `log_core.h` 及 [[02-Zephyr-项目结构与构建配置]] 中的定义矛盾。官方日志级别为 **0=关闭、1=ERR、2=WRN、3=INF、4=DBG**，修正如下。

| 宏 | 级别 | 说明 |
|----|------|------|
| 不启用（`LOG_LEVEL_NONE`） | 0 | 关闭 |
| `LOG_ERR` | 1 | 错误 |
| `LOG_WRN` | 2 | 警告 |
| `LOG_INF` | 3 | 信息（默认） |
| `LOG_DBG` | 4 | 调试 |

**每个模块的日志级别在 Kconfig 中控制：**

```kconfig
# prj.conf 或 Kconfig 中
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3               # 默认信息级
CONFIG_MY_SENSOR_LOG_LEVEL=0             # 关闭这个模块的日志
```

### 7.3 多文件模块

一个模块如果有多个 `.c` 文件，只有**一个文件** `LOG_MODULE_REGISTER`，其他文件用 `LOG_MODULE_DECLARE`：

```c
/* sensor_core.c */
LOG_MODULE_REGISTER(my_sensor, CONFIG_MY_SENSOR_LOG_LEVEL);

/* sensor_utils.c */
LOG_MODULE_DECLARE(my_sensor, CONFIG_MY_SENSOR_LOG_LEVEL);  /* 共享同一个模块 */
```

### 7.4 带限速的日志

防止高频触发时刷屏：

```c
/* 使用默认限速间隔（由 CONFIG_LOG_RATELIMIT_INTERVAL_MS 决定） */
LOG_WRN_RATELIMIT("Warning: %d", code);

/* 自定义限速间隔（毫秒） */
LOG_INF_RATELIMIT_RATE(2000, "Status: %d", count);
```

### 7.5 一次性日志

```c
/* 只打印一次 */
LOG_WRN_ONCE("This warning appears only once");
```

### 7.6 与 `printk` 的对比

| | `printk` | Logging |
|--|----------|---------|
| 等级过滤 | ❌ | ✅ |
| 模块名标签 | ❌ | ✅ |
| 运行时过滤 | ❌ | ✅ |
| 16 进制 dump | ❌ | `LOG_HEXDUMP_INF` / `LOG_HEXDUMP_ERR` |
| 限速 | ❌ | ✅ |
| 可关闭的开销 | 一直存在 | 编译时完全剔除 |

> **建议：新代码直接用 logging，不用 printk。**

---

## 8. Shell

Zephyr 内建一个串口 shell，可以交互式调用你注册的命令。

### 8.1 启用

```kconfig
# prj.conf
CONFIG_SHELL=y
```

### 8.2 注册自定义命令

```c
#include <zephyr/shell/shell.h>

/* 命令处理函数 */
static int cmd_read_sensor(const struct shell *sh, size_t argc, char **argv)
{
    int val = read_sensor_value();
    shell_print(sh, "Sensor value: %d", val);
    return 0;
}

/* 注册到 "sensor" 子命令组 */
SHELL_SUBCMD_SET_CREATE(sensor_commands,
    SHELL_CMD(read, NULL, "Read sensor value", cmd_read_sensor),
    SHELL_CMD(calibrate, NULL, "Run calibration", cmd_calibrate),
    SHELL_SUBCMD_SET_END
);

/* 注册顶层命令 */
SHELL_CMD_REGISTER(sensor, &sensor_commands, "Sensor commands", NULL);
```

**烧录后用串口连接，输入 `sensor read` 即可调用。**

### 8.3 内置命令

启用 shell 后默认就有：

| 命令 | 作用 |
|------|------|
| `kernel threads` | 列出所有线程 |
| `kernel stack` | 显示栈使用统计 |
| `kernel uptime` | 显示运行时间 |
| `device list` | 列出所有设备 |
| `log enable` / `log disable` | 运行时打开/关闭日志 |
| `help` | 命令列表 |

### 8.4 调试利器：shell + logging 配合

```c
/* 默认日志等级设置得高一些 */
CONFIG_LOG_DEFAULT_LEVEL=3

/* 运行时通过 shell 关闭特定模块的日志 */
uart:~$ log disable my_sensor

/* 再打开 */
uart:~$ log enable my_sensor
```

---

## 9. 完整示例

以下完整程序演示了线程 + 信号量 + 消息队列 + 日志 + shell 的综合使用：

**CMakeLists.txt：**
```cmake
cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(sensor_demo)

target_sources(app PRIVATE src/main.c)
```

**prj.conf：**
```kconfig
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3
CONFIG_SHELL=y
```

**src/main.c：**
```c
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/shell/shell.h>

LOG_MODULE_REGISTER(sensor_demo, LOG_LEVEL_INF);

/* ===== 数据定义 ===== */
struct sensor_reading {
    uint16_t temp;
    uint16_t hum;
    uint64_t ts;
};

/* 消息队列：存放传感器数据 */
K_MSGQ_DEFINE(sensor_msgq, sizeof(struct sensor_reading), 5, 1);

/* 信号量：通知数据已采集 */
K_SEM_DEFINE(data_sem, 0, 1);

/* ===== ISR 模拟（用定时器替代实际硬件中断） ===== */
K_TIMER_DEFINE(sample_timer, NULL, NULL);

/* 采集线程 */
void collector_thread(void *p1, void *p2, void *p3)
{
    struct sensor_reading data;
    uint32_t seq = 0;

    k_timer_start(&sample_timer, K_SECONDS(1), K_SECONDS(1));

    while (1) {
        /* 等定时器到期 */
        k_timer_status_sync(&sample_timer);

        /* 模拟读取传感器 */
        data.temp = 20 + (seq++ % 10);
        data.hum = 50 + (seq % 20);
        data.ts = k_uptime_get();

        LOG_INF("Sampled: temp=%d, hum=%d", data.temp, data.hum);

        /* 放入消息队列——满了就清空旧的 */
        while (k_msgq_put(&sensor_msgq, &data, K_NO_WAIT) != 0) {
            LOG_WRN("Queue full, purging old data");
            k_msgq_purge(&sensor_msgq);
        }

        /* 通知消费者 */
        k_sem_give(&data_sem);
    }
}

/* 处理线程 */
void processor_thread(void *p1, void *p2, void *p3)
{
    struct sensor_reading data;

    while (1) {
        /* 等数据就绪 */
        k_sem_take(&data_sem, K_FOREVER);

        /* 取所有可用数据 */
        while (k_msgq_get(&sensor_msgq, &data, K_NO_WAIT) == 0) {
            LOG_INF("Processed: temp=%d, hum=%d, ts=%llu",
                    data.temp, data.hum, data.ts);
        }
    }
}

/* 定义线程 */
K_THREAD_DEFINE(collector_tid, 2048,
                collector_thread, NULL, NULL, NULL,
                5, 0, 0);
K_THREAD_DEFINE(processor_tid, 1024,
                processor_thread, NULL, NULL, NULL,
                5, 0, 0);

/* ===== Shell 命令 ===== */
static int cmd_status(const struct shell *sh, size_t argc, char **argv)
{
    shell_print(sh, "Queue used: %u / 5",
                k_msgq_num_used_get(&sensor_msgq));
    shell_print(sh, "Sem count: %u",
                k_sem_count_get(&data_sem));
    return 0;
}

SHELL_CMD_REGISTER(status, NULL, "Show sensor status", cmd_status);

/* ===== entry point ===== */
void main(void)
{
    LOG_INF("Sensor demo starting...");
}
```

---

## 快速参考卡

```
┌────────────────────────────────────────────┐
│              Zephyr API 速查               │
├────────────────────────────────────────────┤
│ 线程创建 (编译时)                          │
│   K_THREAD_DEFINE(name, stack, entry,       │
│                   p1,p2,p3, prio, opt,delay)│
│ 线程创建 (运行时)                          │
│   k_thread_create(&tcb, &stack, size,       │
│                   entry, p1,p2,p3, prio,    │
│                   opt, delay)               │
│ 线程管理                                    │
│   k_thread_abort/suspend/resume/join        │
│ 定时器                                      │
│   K_TIMER_DEFINE(name, fn, stop_fn)         │
│   k_timer_start/stop/status_sync            │
│ 中断                                        │
│   IRQ_CONNECT(irq, prio, isr, arg, flags)   │
│   irq_enable/disable                        │
│ 信号量                                      │
│   K_SEM_DEFINE(name, init, limit)           │
│   k_sem_give/take/count_get                 │
│ 互斥锁                                      │
│   K_MUTEX_DEFINE(name)                      │
│   k_mutex_lock/unlock                       │
│ 消息队列                                    │
│   K_MSGQ_DEFINE(name, size, max, align)     │
│   k_msgq_put/get/peek/purge                 │
│ 日志                                        │
│   LOG_MODULE_REGISTER(name, level)          │
│   LOG_ERR/WRN/INF/DBG(...)                  │
│ 常用时间值                                   │
│   K_FOREVER     = 永远等待                   │
│   K_NO_WAIT     = 不等待                     │
│   K_SECONDS(n)  = n 秒                       │
│   K_MSEC(n)     = n 毫秒                     │
│   K_USEC(n)     = n 微秒                     │
└────────────────────────────────────────────┘
```

---

## 学习建议

1. **熟读这张表**，对着你自己的 PSA 项目思考每个部件对应 Zephyr 的哪个 API
2. **在 native_sim 或 qemu_x86 上跑这些例子**，不用烧录可以直接看到输出
3. 把你的 PSA 传感器采集管线用 Zephyr 重写一遍——这是最好的巩固方式
4. 学会用 `menuconfig` 搜索符号：
   ```bash
   west build -t menuconfig
   ```
5. 遇到不懂的 API 去 `zephyr/include/zephyr/` 下看头文件，注释写得很详细
