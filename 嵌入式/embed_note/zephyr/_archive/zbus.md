---
date: 2026-09-01
tags: [zephyr, zbus, publish-subscribe, 事件总线]
aliases: [zbus, Zephyr bus, zbus笔记]
---

# zbus（Zephyr 软件消息总线）

> 2026-09-01 按老师讲解整理，并对照[官方文档](https://docs.zephyrproject.org/latest/services/zbus/index.html)与 `zephyr/include/zephyr/zbus/zbus.h` 源码逐条核对；与官方不一致之处见文末「勘误」。
> 相关笔记：[[嵌入式设计模式-事件总线]]（含 VDED / iterable section 实现剖析） [[zephyr核心api]]

## 1. 一句话

> **zbus = 基于 Channel 的发布订阅消息总线**（Zephyr 3.3 引入，many-to-many 线程通信）。

你的模块不需要直接调用其他模块，生产者只负责 `zbus_chan_pub(...)`，消费者监听 Channel：

```text
Sensor ──pub──► [ sensor_chan ] ──通知──► UI / Storage / System Manager
```

## 2. 核心概念：Message / Channel / Observer

- **Message**：普通 C struct，Channel 内部保存一份当前 Message（共享内存）。
- **Channel**：某一种消息的公共通信通道，例如 `sensor_chan`、`power_chan`、`ota_chan`。
- **Observer**：对 Channel 感兴趣的一方，共 4 种：

| 类型 | 执行方式 | 内部机制 | 消息是否拷贝 | 特点 |
| --- | --- | --- | --- | --- |
| Listener | 同步回调 | 发布者上下文直接调回调 | 否（直接读共享消息） | 快，但阻塞发布者 |
| Async Listener | Work Queue 异步回调 | 消息拷贝 → 工作队列 | 是（net_buf 拷贝） | 不阻塞发布者，又不用建线程 |
| Subscriber | 线程等待 | k_msgq 塞 **channel 指针** | 否（只收通知，需自己 read） | 慢处理、任务阻塞等待；**无投递保证** |
| Message Subscriber | 线程等待 | k_fifo 塞 **完整消息拷贝** | 是（net_buf） | 每条消息都不能丢的消费者 |

## 3. 最小使用流程

### 3.1 开启 zbus

```conf
CONFIG_ZBUS=y
```

用到 Message Subscriber / Async Listener 时额外开启（见「勘误 3」）：

```conf
CONFIG_ZBUS_MSG_SUBSCRIBER=y
CONFIG_ZBUS_ASYNC_LISTENER=y
```

### 3.2 定义消息（建议单独放 `app/include/app_messages.h`）

```c
struct sensor_msg {
    int temperature;
    int humidity;
};
```

### 3.3 定义 Observer（如 UI 用 Subscriber）

```c
#include <zephyr/zbus/zbus.h>

ZBUS_SUBSCRIBER_DEFINE(ui_subscriber, 4);  /* 4 = 通知队列能存 4 个 channel 指针 */
```

> Subscriber 收到的是 **Channel 通知（channel 指针）**，不是 Message 本身——所以读数据要分两步（见 3.6）。

### 3.4 定义 Channel

```c
ZBUS_CHAN_DEFINE(
    sensor_channel,                    /* 名字 */
    struct sensor_msg,                 /* 消息类型 */
    NULL,                              /* validator（可空） */
    NULL,                              /* user_data（可空） */
    ZBUS_OBSERVERS(ui_subscriber),     /* 观察者列表，顺序 = 通知优先级 */
    ZBUS_MSG_INIT(0)                   /* 初始消息：{0} 清零 */
);
```

参数顺序：`名字, 消息类型, validator, user_data, observers, 初始值`。

### 3.5 发布（任意模块 / 线程 / ISR）

```c
zbus_chan_pub(&sensor_channel, &msg, K_MSEC(100));
```

> ISR 中发布 timeout 必须 `K_NO_WAIT`。

### 3.6 订阅读取（Subscriber 分两步）

```c
void ui_thread(void)
{
    const struct zbus_channel *chan;

    while (1) {
        zbus_sub_wait(&ui_subscriber, &chan, K_FOREVER);  /* 1. 等通知，拿到 channel 指针 */

        if (chan == &sensor_channel) {
            struct sensor_msg msg;
            zbus_chan_read(chan, &msg, K_MSEC(100));      /* 2. 从 channel 拷贝一份出来 */
        }
    }
}
```

**为什么分两步**：zbus 的模型是"Channel 保存一份共享 Message + 通知多个 Subscriber"，发布、读取都是对共享内存的加锁拷贝。大家读的都是 Channel 的**当前数据**。

## 4. 重要问题：普通 Subscriber 会丢消息

```text
publish A → publish B → publish C（连续发布）
```

Subscriber 收到了 3 次通知，但它去读时 Channel 里已是 C。后一次发布会覆盖前一次消息——**官方文档明确警告**：如果 Subscriber 在两次发布之间没有及时读取，第二次发布会覆盖第一次的数据，这适用"只看最新状态"的场景。

不能丢消息（关键事件、命令）→ 用 **Message Subscriber**：

```c
ZBUS_MSG_SUBSCRIBER_DEFINE(data_subscriber);   /* 注意：只有一个参数，没有队列大小 */

ZBUS_CHAN_DEFINE(
    sensor_channel,
    struct sensor_msg,
    NULL,
    NULL,
    ZBUS_OBSERVERS(data_subscriber),
    ZBUS_MSG_INIT(0)
);
```

接收端直接用 `zbus_sub_wait_msg()` 拿消息副本（内部 FIFO 无限长，实际受 net_buf pool 容量限制，见勘误 3）。

## 5. Listener：同步回调

```c
void sensor_listener_callback(const struct zbus_channel *chan)
{
    const struct sensor_msg *msg = zbus_chan_const_msg(chan);  /* 只读访问，无需拷贝 */
}

ZBUS_LISTENER_DEFINE(sensor_listener, sensor_listener_callback);
```

**注意**：Listener 在**发布者上下文同步执行**（VDED 分发时通道仍加锁），回调里绝不能：

- `k_sleep()` / 阻塞 → 发布者被卡住
- 长时间计算 / IO / 文件操作 / 网络请求
- 对同一 Channel 再发布（死锁）

适合：更新简单状态、置位标志、快速通知。

## 6. Async Listener：异步回调

```c
ZBUS_ASYNC_LISTENER_DEFINE(my_async, my_async_callback);
```

发布者只把消息 + 工作项提交到工作队列（默认系统工作队列 `k_sys_work_q`，可用 `zbus_async_listener_set_work_queue()` 换），回调在队列上下文执行，Publisher 不等它。

适用：事件发生后需要异步处理，又不想专门创建一个线程。

## 7. Channel Validator（发布校验）

限制谁能发布什么数据，发布前校验，非法返回 `-ENOMSG` 拒绝：

```c
static bool battery_validator(const void *msg, size_t msg_size)
{
    const struct battery_msg *battery = msg;
    return battery->percentage >= 0 && battery->percentage <= 100;
}

ZBUS_CHAN_DEFINE(
    battery_chan,
    struct battery_msg,
    battery_validator,
    NULL,
    ZBUS_OBSERVERS(...),
    ZBUS_MSG_INIT(.percentage = 100)
);
```

## 8. zbus vs FreeRTOS Queue / k_msgq

| | FreeRTOS Queue | zbus Channel |
| --- | --- | --- |
| 模型 | 点对点，消息进队列 | 发布订阅，**Channel 保存最新消息** + 通知观察者 |
| 解耦 | 发布者知道消费者 | 发布者不知道谁在听 |
| 适合 | 数据搬运 | 状态同步、系统事件、模块解耦、多模块广播 |
| 不适合 | —— | 高速数据流、大块连续数据、DMA 缓冲、音频（官方建议这类用 **Pipe** 或其它机制） |

## 9. 设计建议：区分 Event 和 State（最容易混淆的点）

### State Channel（如 battery=80%、wifi=connected、system_mode）

> 只关心最新状态，中间丢一次没关系 → **普通 Subscriber**

### Event Channel（如 OTA_START/OTA_FINISHED、LOW_BATTERY、SHUTDOWN_REQUEST）

> 每个事件都可能需要被消费 → **Message Subscriber**（或 k_msgq）

### 高频数据

```text
Driver → Direct API / RingBuffer / FIFO
```

### 状态更新

```text
Module → zbus Channel → Subscribers
```

### 系统事件

```text
Module → Event Channel → System Manager
```

### 必须保证顺序的数据

```text
Message Subscriber / k_msgq / FIFO
```

## 10. 跨文件使用

定义只能有一处（如 `bus.c`），其他文件：

```c
/* bus.h */
#include <zephyr/zbus/zbus.h>

ZBUS_CHAN_DECLARE(sensor_channel);   /* extern channel */
ZBUS_OBS_DECLARE(ui_subscriber);     /* extern observer（用到时） */
```

## 11. 与 PSA 架构结合（按领域划分 Channel）

不要搞一个万能 EventBus + 巨大 enum，而是按领域划分 Channel：

```text
sensor_chan      power_chan       ota_chan
      │                │              │
      └─────── system_event_chan ─────┘
                      │
                      ▼
             System Manager（State Machine）
             NORMAL / RECORDING / OTA / CHARGING / SHUTDOWN
```

```text
Sensor Manager ──pub──► sensor_chan       System Manager
Power Manager  ──pub──► power_chan   ──subscribe──► 统一处理系统级状态转换
OTA Service    ──pub──► ota_chan
```

架构分层：

```text
Application（System Manager / Sensor / Power / OTA / Storage）
        │            zbus
Zephyr Kernel（Thread / WorkQueue / Timer / Mutex / Semaphore / FIFO）
```

## 12. 勘误（与官方不一致/需补充处）

1. **`ZBUS_MSG_INIT()` 空参数不合法**（老师多处写空参数）。源码定义是 `#define ZBUS_MSG_INIT(_val, ...) {_val, ##__VA_ARGS__}`，至少需要 1 个参数：`ZBUS_MSG_INIT(0)` 表示 `{0}`（清零整个 struct），或指定初始化 `ZBUS_MSG_INIT(.temperature = 0, .humidity = 0)`。
2. **Async Listener 其实也拷贝消息**。老师表格写 Async Listener"消息是否复制=否"，但源码中 async listener 结构带 `message_fifo`，官方文档也说明 net_buf pool 服务于 message subscriber **和 async listener**——因为回调在工作队列上下文执行，必须拷贝一份消息带过去。正确表格见第 2 节。
3. **需要补充的 Kconfig**：Message Subscriber 需 `CONFIG_ZBUS_MSG_SUBSCRIBER=y`，Async Listener 需 `CONFIG_ZBUS_ASYNC_LISTENER=y`；两个功能的消息传递依赖 net_buf，容量由 `CONFIG_ZBUS_MSG_SUBSCRIBER_NET_BUF_POOL_SIZE` 和 `CONFIG_HEAP_MEM_POOL_ADD_SIZE_ZBUS` 决定，池太小会影响投递保证。
4. **跨文件声明不止 channel**：观察者（subscriber/listener）也要 `ZBUS_OBS_DECLARE(...)`，老师只提了 `ZBUS_CHAN_DECLARE`。
5. 其余核对无误：macros 参数个数与含义、`zbus_chan_pub/read/const_msg` 与 `zbus_sub_wait` 签名、Listener 同步阻塞发布者、Subscriber 丢消息警告、validator 签名 `bool (*)(const void *, size_t)`、"高频数据用 Pipe" 均与官方一致。

## 13. 参考

- 官方文档：https://docs.zephyrproject.org/latest/services/zbus/index.html
- 源码：`zephyr/include/zephyr/zbus/zbus.h` + `zephyr/subsys/zbus/zbus.c`
- 官方示例：`zephyr/samples/subsys/zbus/`