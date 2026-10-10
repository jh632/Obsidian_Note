---
tags: [embed_note, NuttX]
date: 2026-10-10
aliases: [NuttX基础API, NuttX核心API, NuttX POSIX API, NuttX任务与线程]
---

# NuttX 基础 API

NuttX 应用主要使用 **POSIX 接口**：用 `pthread_*` 创建线程和同步，用 `open/read/write/ioctl` 访问文件与设备，用 `sem_*` 和 `mq_*` 传递事件与消息。掌握这些接口后，大部分应用代码可以在不同板卡之间复用。

前置笔记：[[01-NuttX-环境配置和编译烧录流程]]。

> [!note] 使用范围
> 本文面向应用层，接口和配置以 NuttX 官方 `latest` 文档及源码为参考。实际能使用哪些功能由板卡配置和 NuttX 版本决定；示例中的设备节点也需要板级代码注册。

---

## 目录

1. [接口风格与错误处理](#1-接口风格与错误处理)
2. [任务与线程](#2-任务与线程)
3. [优先级与调度](#3-优先级与调度)
4. [延时与时间](#4-延时与时间)
5. [互斥锁、信号量与条件变量](#5-互斥锁信号量与条件变量)
6. [消息队列](#6-消息队列)
7. [文件读写](#7-文件读写)
8. [设备访问与 GPIO](#8-设备访问与-gpio)
9. [定时器与中断边界](#9-定时器与中断边界)
10. [内存与日志](#10-内存与日志)
11. [完整示例：线程与共享计数器](#11-完整示例线程与共享计数器)
12. [把示例加入 apps 并运行](#12-把示例加入-apps-并运行)
13. [常见问题与接口速查](#13-常见问题与接口速查)

---

## 1. 接口风格与错误处理

### 1.1 头文件与接口层次

NuttX 应用源码通常先包含配置头文件，再包含所需的标准头文件：

```c
#include <nuttx/config.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
```

| 接口类型 | 例子 | 使用位置 |
| --- | --- | --- |
| POSIX 接口 | `pthread_create()`、`sem_wait()`、`open()` | 应用层优先使用 |
| NuttX 应用扩展 | `task_create()`、`sem_setprotocol()` | 需要 NuttX 特有功能时使用 |
| 内核内部接口 | `nxtask_*`、`nxsem_*`、`nxmq_*` | 内核或驱动开发，不能直接当成普通应用 API |

### 1.2 三种返回方式

**不能把所有 API 的错误判断都写成 `ret < 0`。**

| 接口 | 成功 | 失败 | 如何查看原因 |
| --- | --- | --- | --- |
| `open()` | 非负文件描述符，`0` 也有效 | `-1` | `errno`、`perror()` |
| `read()` / `write()` | 实际处理的字节数 | `-1` | `errno` |
| `sem_wait()` / `mq_send()` | `0` | `-1` | `errno` |
| `pthread_create()` / `pthread_mutex_lock()` 等 | `0` | 正的错误码 | `strerror(ret)` |
| `malloc()` | 非空指针 | `NULL` | 检查指针 |

普通 POSIX 文件接口的错误处理：

```c
int fd = open("/dev/ttyS1", O_RDWR);
if (fd < 0)
  {
    perror("open");
    return -1;
  }
```

pthread 接口的错误处理：

```c
int ret = pthread_create(&tid, NULL, worker, NULL);
if (ret != 0)
  {
    fprintf(stderr, "pthread_create: %s\n", strerror(ret));
    return -1;
  }
```

这两段是接口用法片段；完整源码还需要声明 `tid`、`worker`，并包含 `<fcntl.h>`、`<stdio.h>`、`<string.h>` 等相应头文件。

`errno` 只在接口报告失败时有意义。需要保留错误原因时，应在后续调用其他函数前保存它。

---

## 2. 任务与线程

### 2.1 `task_create()` 与 `pthread_create()`

NuttX 区分 task 与 pthread，两者都能被调度，但资源组织方式不同：

| 对比项 | `task_create()` | `pthread_create()` |
| --- | --- | --- |
| 头文件 | `<sched.h>` | `<pthread.h>` |
| 入口函数 | `int entry(int argc, char *argv[])` | `void *entry(void *arg)` |
| 参数 | 以 `NULL` 结尾的字符串数组 | 一个 `void *` 参数 |
| 资源关系 | 创建新的任务组，具有独立的文件描述符表等资源 | 属于调用者的任务组，共享文件描述符等资源 |
| 优先级和栈 | 创建时直接传入 | 使用 `pthread_attr_t` 设置 |
| 创建返回值 | 成功返回 PID；失败返回 `-1` | 成功返回 `0`；失败返回错误码，线程 ID 写入参数 |
| 等待结束 | 根据配置使用 `waitpid()` 等机制 | `pthread_join()` |
| 典型用途 | 启动独立应用、后台服务 | 一个应用内的采集、处理、通信线程 |

> [!important] 任务独立不等于内存隔离
> 常见的 FLAT 构建中，task 与 pthread 都运行在同一个地址空间。PROTECTED / KERNEL 构建的内存保护和地址环境需要另行理解，不能直接套用 Linux 进程模型。

### 2.2 创建一个 task

```c
#include <nuttx/config.h>
#include <sched.h>
#include <stdio.h>
#include <unistd.h>

static int worker_task(int argc, char *argv[])
{
  /* NuttX 自动把任务名放入 argv[0]，传入的参数从 argv[1] 开始。 */
  printf("task=%s, arg=%s\n", argv[0], argc > 1 ? argv[1] : "none");

  for (int i = 0; i < 3; i++)
    {
      printf("worker: %d\n", i);
      sleep(1);
    }

  return 0;
}

int main(int argc, char *argv[])
{
  char *args[] = {"sensor", NULL};
  int pid = task_create("worker", 100, 2048, worker_task, args);

  if (pid < 0)
    {
      perror("task_create");
      return 1;
    }

  printf("created pid=%d\n", pid);
  return 0;
}
```

- `100`：任务优先级。
- `2048`：栈大小，单位是**字节**，需要按实际调用深度和局部变量调整。
- `args`：只包含附加参数，不需要再手动传入任务名；字符串会由创建接口复制。
- 入口函数返回后，task 自动退出。

### 2.3 pthread 的生命周期

| API | 作用 |
| --- | --- |
| `pthread_create(&tid, &attr, entry, arg)` | 创建并启动线程；`attr == NULL` 使用默认属性 |
| `pthread_self()` | 获取当前 pthread 的 ID |
| `pthread_join(tid, &result)` | 等待可连接线程退出，回收资源并取得返回值 |
| `pthread_detach(tid)` | 设为分离线程，退出时自动回收，之后不能 join |
| `pthread_exit(result)` | 退出当前线程；线程入口 `return result` 也可退出 |
| `pthread_attr_setstacksize(&attr, bytes)` | 设置新线程的栈大小 |

创建线程后，它可能立即运行，所以参数指向的数据必须已经初始化。传入的 `void *` 不会自动复制；如果传入局部变量地址，该变量必须在线程使用期间保持有效。

可连接线程退出后应由其他线程 `join`。分离只改变资源回收方式；**主任务退出仍可能结束整个任务组中的 pthread**，后台线程需要由主任务维持应用生命周期。

通常通过停止标志或消息通知线程自行结束。强行 `task_delete()` 或 `pthread_cancel()` 需要考虑持锁、内存和设备资源的清理。

---

## 3. 优先级与调度

### 3.1 数字越大，优先级越高

NuttX 优先级通常为 `1～255`，`0` 用于空闲任务。代码可以通过 `sched_get_priority_min(SCHED_FIFO)` 和 `sched_get_priority_max(SCHED_FIFO)` 查询可用范围。

例如：`150` 的线程可以抢占 `100` 的线程。这个方向与 Zephyr 常见的线程优先级编号不同。

| API / 策略 | 作用 |
| --- | --- |
| `sched_getparam(pid, &param)` | 查询 task 的优先级；`pid == 0` 表示当前调用者 |
| `sched_setparam(pid, &param)` | 修改 task 的优先级 |
| `pthread_getschedparam(tid, &policy, &param)` | 查询 pthread 的策略与优先级 |
| `pthread_setschedparam(tid, policy, &param)` | 修改 pthread 的策略与优先级 |
| `sched_yield()` | 主动把 CPU 让给同优先级的其他就绪线程 |
| `SCHED_FIFO` | 同优先级线程不依靠时间片自动轮转，需阻塞、让出或退出 |
| `SCHED_RR` | 同优先级线程按时间片轮转，需要配置支持 |

高优先级线程持续运行、不阻塞，会使低优先级线程得不到执行。单纯调用 `sched_yield()` 不能解决这种饥饿问题。

### 3.2 新 pthread 的调度属性

需要在创建时指定策略和优先级，可以设置：

```c
/* attr 已通过 pthread_attr_init() 初始化；逐个检查返回值。 */
struct sched_param param = {.sched_priority = 100};

pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
pthread_attr_setschedparam(&attr, &param);
```

`PTHREAD_EXPLICIT_SCHED` 表示使用属性对象中的调度设置；选择 `PTHREAD_INHERIT_SCHED` 时，会继承创建者的调度设置。

`SCHED_RR` 需要非零的 `CONFIG_RR_INTERVAL`，该配置的单位为毫秒。

---

## 4. 延时与时间

### 4.1 常用接口

| API | 单位 / 用途 | 注意点 |
| --- | --- | --- |
| `sleep(seconds)` | 秒级延时 | 返回未睡完的秒数 |
| `usleep(usec)` | 微秒参数的相对延时 | 参数单位不等于实际调度精度 |
| `nanosleep(&req, &rem)` | `timespec` 相对延时 | 失败返回 `-1`；信号打断时可继续睡剩余时间 |
| `clock_gettime(CLOCK_MONOTONIC, &ts)` | 获取单调时间 | 适合测量耗时和安排周期 |
| `clock_gettime(CLOCK_REALTIME, &ts)` | 获取系统实时时间 | 可能受 RTC 初始化、校时影响 |
| `clock_nanosleep(clock, flags, &ts, &rem)` | 按指定时钟睡眠 | 可用 `TIMER_ABSTIME` 指定绝对期限；失败直接返回错误码 |

`struct timespec` 中，`tv_sec` 是秒，`tv_nsec` 是纳秒，后者必须满足 `0 <= tv_nsec < 1000000000`。

### 4.2 一个处理信号打断的毫秒延时函数

```c
#include <errno.h>
#include <time.h>

static int delay_ms(unsigned int ms)
{
  struct timespec req =
  {
    .tv_sec  = ms / 1000,
    .tv_nsec = (long)(ms % 1000) * 1000000L
  };
  struct timespec rem;

  while (nanosleep(&req, &rem) < 0)
    {
      if (errno != EINTR)
        {
          return -1;
        }

      req = rem;
    }

  return 0;
}
```

普通应用延时会使当前线程阻塞，让其他线程运行。延时精度受系统时钟、定时器实现和调度延迟影响，不能用 `usleep(1)` 保证精确的 1 μs 波形。

### 4.3 周期任务避免累计漂移

`采集 → delay_ms(100)` 的实际周期是“采集耗时 + 100 ms”。如果希望每 100 ms 启动一次采集，应以 `CLOCK_MONOTONIC` 记录下一次绝对期限，每轮把期限增加 100 ms，再使用绝对时间等待。

若处理耗时超过周期，需要明确选择立即追赶还是跳过过期周期，避免连续空转。添加时间时也要处理纳秒进位。

---

## 5. 互斥锁、信号量与条件变量

### 5.1 按需求选同步方式

| 需求 | 接口 | 核心含义 |
| --- | --- | --- |
| 多线程保护共享变量或设备 | `pthread_mutex_*` | 同一时刻只有一个线程持锁 |
| 通知发生了一次事件 | `sem_*` | 计数累计，等待者每次取走一个计数 |
| 等待共享状态满足条件 | `pthread_cond_*` + mutex | 状态受锁保护，通知用于唤醒等待者 |
| 传递每一条数据 | `mq_*` | 在队列中保存消息内容 |

### 5.2 互斥锁

```c
#include <pthread.h>

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned int g_counter;

static int add_one(void)
{
  int ret = pthread_mutex_lock(&g_lock);
  if (ret != 0)
    {
      return ret;
    }

  g_counter++;
  return pthread_mutex_unlock(&g_lock);
}
```

| API | 作用 |
| --- | --- |
| `pthread_mutex_init()` / `pthread_mutex_destroy()` | 动态初始化 / 销毁互斥锁 |
| `pthread_mutex_lock()` | 等待并获得锁 |
| `pthread_mutex_trylock()` | 立即尝试，锁被占用时返回 `EBUSY` |
| `pthread_mutex_timedlock()` | 等待到绝对期限 |
| `pthread_mutex_unlock()` | 释放当前线程持有的锁 |

只把共享资源操作放在持锁区间内，避免持锁执行长延时或阻塞 I/O。普通互斥锁不能由其他线程代为解锁，也不能在中断中使用。

有优先级反转风险时，可结合 `CONFIG_PRIORITY_INHERITANCE` 和 `pthread_mutexattr_setprotocol(..., PTHREAD_PRIO_INHERIT)` 使用优先级继承。

### 5.3 信号量：等待与通知

```c
#include <errno.h>
#include <semaphore.h>

static sem_t g_event;

static int event_init(void)
{
  if (sem_init(&g_event, 0, 0) < 0)
    {
      return -1;
    }

  /* 这是事件通知信号量，不用于资源持有，应关闭优先级继承。 */
  if (sem_setprotocol(&g_event, SEM_PRIO_NONE) < 0)
    {
      int saved_errno = errno;
      sem_destroy(&g_event);
      errno = saved_errno;
      return -1;
    }

  return 0;
}

static int event_wait(void)
{
  int ret;
  do
    {
      ret = sem_wait(&g_event);
    }
  while (ret < 0 && errno == EINTR);

  return ret;
}

/* event_init() 成功后，通知方调用 sem_post(&g_event)，并检查返回值。 */
```

`sem_init(&sem, 0, 0)` 的第二个 `0` 表示同一进程 / 任务组内共享，第三个 `0` 表示初始没有事件。第三个参数设成 `1` 时，第一次等待可以立即通过。

| API | 作用 |
| --- | --- |
| `sem_wait()` | 计数为 0 时阻塞；成功后计数减 1 |
| `sem_trywait()` | 不阻塞，没有计数时失败，`errno == EAGAIN` |
| `sem_timedwait()` | 等待至 `CLOCK_REALTIME` 的绝对期限，超时为 `ETIMEDOUT` |
| `sem_post()` | 增加计数，唤醒等待者 |
| `sem_destroy()` | 不再有使用者和等待者时销毁 |

`sem_setprotocol()` 是 NuttX 扩展。事件通知的发送者和接收者不是同一个“锁持有者”，启用优先级继承时必须正确区分事件信号量与资源锁。

信号量只记录事件次数，不保存每次采样数据。如果每条样本都需要处理，应使用消息队列或受保护的缓冲区。

### 5.4 条件变量

`pthread_cond_wait(&cond, &mutex)` 必须在已经持有 mutex 时调用。它会原子地释放 mutex 并等待，返回前重新获得 mutex。

等待方式应为 `while (!condition) pthread_cond_wait(...)`；唤醒后再次检查真实状态。通知方在同一把锁保护下修改状态，再调用 `pthread_cond_signal()` 或 `pthread_cond_broadcast()`。

条件变量不累计通知次数。状态应保存在共享变量中，不能只依赖“曾经 signal 过”。

---

## 6. 消息队列

### 6.1 基本接口

头文件：`<mqueue.h>`。

| API | 作用 |
| --- | --- |
| `mq_open(name, flags, mode, &attr)` | 创建或打开命名队列；创建时提供后两个参数 |
| `mq_send(mq, data, len, prio)` | 复制一条消息到队列 |
| `mq_receive(mq, buffer, size, &prio)` | 取出一条消息，返回实际消息字节数 |
| `mq_timedsend()` / `mq_timedreceive()` | 使用绝对期限等待，超时报告 `ETIMEDOUT` |
| `mq_getattr()` | 查询队列最大消息大小、容量、当前消息数等 |
| `mq_close()` | 关闭当前描述符 |
| `mq_unlink(name)` | 删除队列名称，最后一个描述符关闭后释放对象 |

队列满时发送阻塞，队列空时接收阻塞。使用 `O_NONBLOCK` 可改为立即失败，`errno == EAGAIN`。消息优先级数字越大越先接收；同消息优先级按 FIFO 顺序接收。

### 6.2 创建、发送、接收、清理

下面在同一线程中演示完整生命周期。实际应用中，生产者和消费者可以各自通过相同名称打开队列。

```c
#include <nuttx/config.h>
#include <errno.h>
#include <fcntl.h>
#include <mqueue.h>
#include <stdint.h>
#include <stdio.h>

struct sample_s
{
  uint32_t id;
  uint32_t value;
};

static int queue_demo(void)
{
  const char *name = "/api_demo_events";
  struct mq_attr attr = {0};
  struct sample_s tx = {.id = 1, .value = 42};
  struct sample_s rx;
  ssize_t n;
  int ret;
  int result = 1;

  attr.mq_maxmsg  = 4;
  attr.mq_msgsize = sizeof(struct sample_s);

  /* O_EXCL 保证新建对象，避免复用属性不匹配的旧队列。 */
  mqd_t mq = mq_open(name, O_CREAT | O_EXCL | O_RDWR, 0600, &attr);
  if (mq == (mqd_t)-1)
    {
      perror("mq_open");
      return 1;
    }

  do
    {
      ret = mq_send(mq, (const char *)&tx, sizeof(tx), 0);
    }
  while (ret < 0 && errno == EINTR);

  if (ret < 0)
    {
      perror("mq_send");
      goto out;
    }

  do
    {
      n = mq_receive(mq, (char *)&rx, sizeof(rx), NULL);
    }
  while (n < 0 && errno == EINTR);

  if (n < 0)
    {
      perror("mq_receive");
      goto out;
    }

  if ((size_t)n != sizeof(rx))
    {
      fprintf(stderr, "unexpected message size\n");
      goto out;
    }

  printf("id=%lu, value=%lu\n",
         (unsigned long)rx.id, (unsigned long)rx.value);
  result = 0;

out:
  if (mq_close(mq) < 0)
    {
      perror("mq_close");
      result = 1;
    }

  if (mq_unlink(name) < 0)
    {
      perror("mq_unlink");
      result = 1;
    }

  return result;
}
```

注意：

- 接收缓冲区必须至少为队列的 `mq_msgsize`，不是只要大于当前消息长度即可。
- 打开已有队列时，`attr` 不会重新设置原队列的大小与容量；可以用 `mq_getattr()` 查询。
- 队列复制消息字节，但不会复制消息中指针指向的数据；跨地址空间传递裸指针尤其不合适。
- `mq_close()` 不等于删除队列。共享队列应由明确的拥有者负责 `mq_unlink()`。
- 示例遇到 `EEXIST` 时应先确认旧队列归属，不要直接删除仍被其他任务使用的队列。

---

## 7. 文件读写

### 7.1 常用接口

头文件：`<fcntl.h>`、`<unistd.h>`；文件信息使用 `<sys/stat.h>`。

| API | 作用 |
| --- | --- |
| `open(path, flags[, mode])` | 打开文件，创建文件时传入权限参数 |
| `read(fd, buf, len)` | 读取最多 `len` 字节 |
| `write(fd, buf, len)` | 写入最多 `len` 字节 |
| `lseek(fd, offset, whence)` | 调整文件偏移；串口等设备通常不支持 |
| `close(fd)` | 关闭文件描述符 |
| `fsync(fd)` | 请求同步写入，实际支持情况取决于文件系统 / 驱动 |
| `stat(path, &st)` | 查询文件大小、类型等信息 |

常用打开标志：`O_RDONLY`、`O_WRONLY`、`O_RDWR`、`O_CREAT`、`O_TRUNC`、`O_APPEND`、`O_NONBLOCK`。

`O_TRUNC` 会清空已有文件内容；`O_APPEND` 则在末尾追加。路径的文件系统需要已经挂载，不能假设任意目录都可写。

### 7.2 不要假设一次 write 就写完

```c
#include <errno.h>
#include <stddef.h>
#include <unistd.h>

/* 用于允许分次写入的字节流，fd 应为阻塞模式。 */
static int write_all(int fd, const void *buffer, size_t length)
{
  const char *p = buffer;

  while (length > 0)
    {
      ssize_t n = write(fd, p, length);
      if (n < 0)
        {
          if (errno == EINTR)
            {
              continue;
            }

          return -1;
        }

      if (n == 0)
        {
          errno = EIO;
          return -1;
        }

      p += n;
      length -= (size_t)n;
    }

  return 0;
}
```

`read()` 也可能短读，串口的一次读取不一定对应完整协议帧。普通文件的 `read() == 0` 表示到达 EOF；设备的零长度结果应结合驱动语义处理。

非阻塞 I/O 遇到 `EAGAIN` 时应等待就绪后再重试，不能在高优先级线程里无限忙轮询。具有固定记录 / 事务语义的设备，要按驱动协议读写，不能直接套用上述字节流函数。

---

## 8. 设备访问与 GPIO

### 8.1 设备也通过文件描述符访问

NuttX 常把驱动注册为 `/dev` 下的节点，应用用统一接口访问：

```text
应用 → open / read / write / ioctl → VFS → 设备驱动 → 硬件
```

| 设备 | 常见节点示例 | 常用接口 |
| --- | --- | --- |
| 串口 | `/dev/ttyS0`、`/dev/ttyS1` | `read()`、`write()`、`tcgetattr()`、`tcsetattr()` |
| 通用 GPIO | `/dev/gpio0` 等 | `ioctl()` + `GPIOC_*` 命令 |
| 用户 LED | `/dev/userleds` | `ioctl()` + LED 驱动命令 |
| I²C 字符设备 | `/dev/i2c0` 等 | `ioctl()` + I²C 传输结构 |
| ADC | `/dev/adc0` 等 | `read()` + ADC 采样结构 |

设备路径和能力由板卡决定，节点编号不一定等于芯片管脚号。用 `ls /dev` 查看已注册的设备，再查对应驱动头文件。

### 8.2 GPIO 输出与读回

示例要求 `/dev/gpio0` 已由板级代码注册为可写输出 GPIO，并支持电平读取：

```c
#include <nuttx/config.h>
#include <nuttx/ioexpander/gpio.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int gpio_demo(void)
{
  bool level = false;
  int result = 1;
  int fd = open("/dev/gpio0", O_RDWR);
  if (fd < 0)
    {
      perror("open gpio");
      return 1;
    }

  /* WRITE 的参数是数值 0 / 1。 */
  if (ioctl(fd, GPIOC_WRITE, 1UL) < 0)
    {
      perror("GPIOC_WRITE");
      goto out;
    }

  /* READ 的参数是 bool *，通过 ioctl 的整数参数传入。 */
  if (ioctl(fd, GPIOC_READ, (unsigned long)(uintptr_t)&level) < 0)
    {
      perror("GPIOC_READ");
      goto out;
    }

  printf("gpio level=%d\n", level);
  result = 0;

out:
  if (close(fd) < 0)
    {
      perror("close gpio");
      result = 1;
    }

  return result;
}
```

`ioctl(fd, request, arg)` 的 `arg` 有时是数值，有时是指针，必须按具体命令定义传入。GPIO 输入输出方向、上下拉及中断能力取决于板级配置和驱动，不能仅根据打开方式推断。

芯片专用的底层 GPIO 函数更适合板级或驱动代码；应用优先使用已注册的通用设备接口。

### 8.3 用 poll 等待设备就绪

```c
#include <poll.h>
#include <stdio.h>

/* fd 是已经打开的设备描述符；驱动需要支持 poll。 */
struct pollfd pfd = {.fd = fd, .events = POLLIN};
int ret = poll(&pfd, 1, 1000);  /* 超时参数单位为毫秒 */

if (ret < 0)
  {
    perror("poll");
  }
else if (ret == 0)
  {
    printf("timeout\n");
  }
else if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL))
  {
    printf("device error or disconnect\n");
  }
else if (pfd.revents & POLLIN)
  {
    /* 有数据就绪，再调用 read() 并检查实际返回值。 */
  }
```

`poll()` 超时为 `-1` 表示无限等待，`0` 表示立即检查。就绪并不代表一次 `read()` 能得到完整帧；其他线程也可能先取走数据。

---

## 9. 定时器与中断边界

### 9.1 POSIX 定时器

头文件：`<time.h>`、`<signal.h>`。

| API | 作用 |
| --- | --- |
| `timer_create(clockid, &event, &timerid)` | 创建定时器，初始未启动 |
| `timer_settime(timerid, flags, &value, NULL)` | 设置首次到期时间与重复周期 |
| `timer_gettime(timerid, &value)` | 查询剩余时间和周期 |
| `timer_delete(timerid)` | 停止并删除定时器 |

`struct itimerspec` 中，`it_value` 是首次到期时间，`it_interval` 是重复间隔；重复间隔为零表示单次，首次到期时间为零表示停止。

通知机制由 `struct sigevent` 指定，例如 `SIGEV_SIGNAL`。支持的时钟和通知方式应查所用版本，不应直接假设 Linux 的全部定时器功能都可用。

入门时，持续运行的采集线程加定时等待通常更容易理解。需要独立超时通知时，再使用 POSIX 定时器。

### 9.2 中断与信号处理不是普通线程代码

应用层通常通过驱动的 `read()`、`poll()` 或通知接口接收硬件事件；底层中断注册属于架构、板级和驱动开发。

| 执行上下文 | 适合的操作 | 应避免的操作 |
| --- | --- | --- |
| 普通线程 | 阻塞等待、mutex、文件 I/O、复杂处理 | 长时间占用高优先级 CPU |
| 硬件中断 | 清中断、记录必要状态、通过受支持的机制通知线程 | 睡眠、等待锁、普通阻塞 I/O、复杂日志 |
| 异步信号处理函数 | 使用允许的异步信号安全接口通知正常执行路径 | `printf()`、`malloc()`、`pthread_mutex_lock()` |

NuttX 支持从中断中进行部分通知操作，例如适当使用信号量；驱动还可使用 work queue 把处理延后到工作线程。具体使用哪一层接口需要按驱动上下文确认。

调度锁只改变调度行为，不等于关闭中断，也不能自动充当 SMP 共享数据保护。普通应用共享资源优先使用 mutex；驱动的临界区则遵循 NuttX 中断与 SMP 规则。

---

## 10. 内存与日志

### 10.1 内存

| API | 头文件 | 作用 |
| --- | --- | --- |
| `malloc(size)` | `<stdlib.h>` | 申请堆内存，内容未初始化 |
| `calloc(count, size)` | `<stdlib.h>` | 申请并清零 |
| `realloc(ptr, size)` | `<stdlib.h>` | 调整分配大小，可能移动地址 |
| `free(ptr)` | `<stdlib.h>` | 释放堆内存 |

应用使用标准分配接口，内核使用的 `kmm_*` 不应直接用于普通用户应用。

栈大小包括函数调用、局部变量和运行库调用开销。较大的采样缓冲区应放在合适的静态存储或堆中，避免直接放入只有几 KB 的线程栈。

调用 `realloc()` 时用临时指针接收结果；申请失败时，原内存仍需要保留和释放。实时路径中还要考虑动态分配的耗时与碎片。

### 10.2 日志

```c
#include <stdio.h>
#include <syslog.h>

printf("counter=%u\n", counter);
syslog(LOG_INFO, "sensor started\n");
syslog(LOG_ERR, "sensor read failed: %d\n", error_code);
```

`printf()` 适合入门和控制台输出；`syslog()` 提供日志等级，输出通道与可见级别由配置决定。频繁打印会影响时序，不要把它当成中断或高频采样路径的常规操作。

---

## 11. 完整示例：线程与共享计数器

下面的程序创建两个 pthread，每个线程每隔 100 ms 累加一次，共执行 5 次；主任务等待两者退出，再打印最终值。它不依赖外设，适合先在 `sim:nsh` 中验证。

保存为 `api_basics_main.c`：

```c
#include <nuttx/config.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned int g_counter;

static int delay_ms(unsigned int ms)
{
  struct timespec req =
  {
    .tv_sec  = ms / 1000,
    .tv_nsec = (long)(ms % 1000) * 1000000L
  };
  struct timespec rem;

  while (nanosleep(&req, &rem) < 0)
    {
      if (errno != EINTR)
        {
          return -1;
        }

      req = rem;
    }

  return 0;
}

static void *counter_worker(void *arg)
{
  int *status = arg;
  *status = 0;

  for (int i = 0; i < 5; i++)
    {
      int ret = pthread_mutex_lock(&g_lock);
      if (ret != 0)
        {
          *status = ret;
          return NULL;
        }

      g_counter++;

      ret = pthread_mutex_unlock(&g_lock);
      if (ret != 0)
        {
          *status = ret;
          return NULL;
        }

      if (delay_ms(100) < 0)
        {
          *status = errno;
          return NULL;
        }
    }

  return NULL;
}

int main(int argc, char *argv[])
{
  pthread_t threads[2];
  int status[2] = {0, 0};
  int created = 0;
  int result = 0;
  int ret;

  /* 上一次运行已 join 全部线程，可以安全重置计数器。 */
  g_counter = 0;

  for (int i = 0; i < 2; i++)
    {
      ret = pthread_create(&threads[i], NULL, counter_worker, &status[i]);
      if (ret != 0)
        {
          fprintf(stderr, "pthread_create: %s\n", strerror(ret));
          result = 1;
          break;
        }

      created++;
    }

  /* 即使后续创建失败，也等待已经成功启动的线程。 */
  for (int i = 0; i < created; i++)
    {
      ret = pthread_join(threads[i], NULL);
      if (ret != 0)
        {
          fprintf(stderr, "pthread_join: %s\n", strerror(ret));
          return 1;
        }

      if (status[i] != 0)
        {
          fprintf(stderr, "worker: %s\n", strerror(status[i]));
          result = 1;
        }
    }

  printf("counter=%u, expected=10\n", g_counter);
  return result;
}
```

理解要点：

1. pthread 的参数指向 `status[i]`，主任务在 join 完成前一直保留这些局部变量。
2. 两个线程对 `g_counter` 的读改写必须由同一把 mutex 保护；`volatile` 不能替代锁。
3. `nanosleep()` 在锁外执行，避免另一个线程因无关延时等待 mutex。
4. 主任务在 join 后读取线程结果和计数器，此时工作线程已经停止修改它们。
5. 示例使用默认 pthread 属性，实际项目要评估默认栈大小与调度策略。

---

## 12. 把示例加入 apps 并运行

以下使用第 01 篇的 Make 构建方式，把完整示例作为内置应用加入现有 `apps`：

```text
nuttxspace/
├── nuttx/
└── apps/
    └── examples/
        └── api_basics/
            ├── Kconfig
            ├── Make.defs
            ├── Makefile
            └── api_basics_main.c
```

### 12.1 Kconfig

```kconfig
config EXAMPLES_API_BASICS
    bool "NuttX basic API demo"
    default n
    depends on !DISABLE_PTHREAD
```

### 12.2 Make.defs

```makefile
ifeq ($(CONFIG_EXAMPLES_API_BASICS),y)
CONFIGURED_APPS += $(APPDIR)/examples/api_basics
endif
```

### 12.3 Makefile

```makefile
include $(APPDIR)/Make.defs

PROGNAME  = api_basics
PRIORITY  = 100
STACKSIZE = 2048
MODULE    = $(CONFIG_EXAMPLES_API_BASICS)
MAINSRC   = api_basics_main.c

include $(APPDIR)/Application.mk
```

入口写成 `int main(int argc, char *argv[])`，由 `Application.mk` 处理内置应用的入口命名与注册。这个写法与当前官方 hello 示例一致。

### 12.4 配置、编译、运行

在已经配置为 `sim:nsh` 的 `nuttx` 目录执行：

```bash
make menuconfig
make -j
./nuttx
```

在 `menuconfig` 中确认 pthread 支持未被禁用，然后选择 `Application Configuration → Examples → NuttX basic API demo`。使用 NSH 内置命令执行还需要启用内置应用支持，通常涉及 `CONFIG_BUILTIN=y` 与 `CONFIG_NSH_BUILTIN_APPS=y`。

新应用选项未出现时，先执行 `make clean`，再运行 `make menuconfig`，让构建系统重新生成应用配置入口。

```text
nsh> api_basics
counter=10, expected=10
```

这只是正常运行时的预期输出。两个线程并发执行，通常约半秒完成，实际时间受调度影响。真实开发板使用相同应用构建步骤，之后按第 01 篇烧录并打开串口。

---

## 13. 常见问题与接口速查

### 13.1 功能需要配置支持

在 `make menuconfig` 中用 `/` 搜索配置符号。带 `DISABLE_` 的开关是反向含义：要使用功能，就不能启用对应的禁用选项。

| 功能 | 重点配置 / 前提 |
| --- | --- |
| pthread | `CONFIG_DISABLE_PTHREAD` 不启用 |
| POSIX 消息队列 | `CONFIG_DISABLE_MQUEUE` 不启用，并评估容量与消息内存 |
| POSIX 定时器 | `CONFIG_DISABLE_POSIX_TIMERS` 不启用；通知方式还需相应信号支持 |
| 同优先级时间片 | `CONFIG_RR_INTERVAL` 非零，并使用 `SCHED_RR` |
| 优先级继承 | `CONFIG_PRIORITY_INHERITANCE` 及合适的锁协议 |
| GPIO 设备节点 | `CONFIG_DEV_GPIO` 及实际板级注册 |
| 串口、文件系统、日志 | 对应驱动、挂载与输出通道已配置 |

### 13.2 常见问题

| 现象 | 优先检查 |
| --- | --- |
| `pthread_create()` 没有检测到失败 | 是否错误地写成 `ret < 0`；应判断 `ret != 0` |
| 高优先级线程导致其他任务不运行 | 是否在忙轮询；是否应阻塞在事件或设备上 |
| 创建后线程参数异常 | 参数对象是否已失效，是否被调用者提前修改 |
| 线程退出后资源持续增加 | 可连接线程是否缺少 join；队列是否只 close 未 unlink |
| `mq_receive()` 报 `EMSGSIZE` | 接收缓冲区是否小于队列的 `mq_msgsize` |
| `open("/dev/...")` 报 `ENOENT` | 节点路径、驱动配置和板级注册是否正确 |
| 串口读取内容不完整 | 是否把短读当成整帧；是否缺少协议组帧逻辑 |
| 复杂函数中异常崩溃 | 线程栈是否太小，是否有大数组或深层调用 |

### 13.3 从其他 RTOS 迁移时的对应关系

| 常见需求 | FreeRTOS 常见接口 | NuttX 常见接口 |
| --- | --- | --- |
| 创建应用内部线程 | `xTaskCreate()` | `pthread_create()` |
| 任务延时 | `vTaskDelay()` | `nanosleep()` / `usleep()` |
| 保护共享资源 | mutex semaphore | `pthread_mutex_*` |
| 事件计数通知 | counting semaphore / task notification | `sem_*`，按需求选择其他通知机制 |
| 复制消息到队列 | `xQueueSend()` / `xQueueReceive()` | `mq_send()` / `mq_receive()` |
| 访问设备 | SDK / HAL 专用 API | 通常为 `open/read/write/ioctl` |

这些是用途对应，参数、超时单位、资源生命周期和中断适用范围并不相同。尤其不要把 FreeRTOS 的 tick 超时直接当成 NuttX 的毫秒或绝对时间参数。

---

## 参考资料

- [NuttX Userspace API](https://nuttx.apache.org/docs/latest/reference/user/index.html)
- [Task Control Interfaces](https://nuttx.apache.org/docs/latest/reference/user/01_task_control.html)
- [Task Scheduling Interfaces](https://nuttx.apache.org/docs/latest/reference/user/02_task_scheduling.html)
- [Pthread Interfaces](https://nuttx.apache.org/docs/latest/reference/user/08_pthread.html)
- [Counting Semaphore Interfaces](https://nuttx.apache.org/docs/latest/reference/user/05_counting_semaphore.html)
- [Named Message Queue Interfaces](https://nuttx.apache.org/docs/latest/reference/user/04_message_queue.html)
- [Clocks and Timers](https://nuttx.apache.org/docs/latest/reference/user/06_clocks_timers.html)
- [File System Interfaces](https://nuttx.apache.org/docs/latest/reference/user/10_filesystem.html)
- [Custom Apps How-to](https://nuttx.apache.org/docs/latest/guides/build/customapps.html)
- [GPIO ioctl 定义](https://github.com/apache/nuttx/blob/master/include/nuttx/ioexpander/gpio.h)
- [信号量头文件与事件通知说明](https://github.com/apache/nuttx/blob/master/include/semaphore.h)
- [任务创建实现](https://github.com/apache/nuttx/blob/master/sched/task/task_create.c)
- [官方 hello 应用](https://github.com/apache/nuttx-apps/tree/master/examples/hello)
