---
date: 2026-09-02
tags: [esp-idf, esp32, esp_event, event-loop, 事件总线, publish-subscribe]
aliases: [esp_event, ESP-IDF事件循环, 事件循环库, ESP-IDF事件总线]
---

# ESP-IDF 事件循环与事件总线（esp_event）

> 2026-09-02 对照[官方文档《事件循环库》](https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/esp_event.html)与 `esp-idf/components/esp_event/` 源码整理。
> 相关笔记：[[zbus]]（Zephyr 的事件总线，本笔记多处对比）[[嵌入式设计模式-事件总线]]（Event/Command/State 区分等设计原则）[[04-ESP-IDF-WiFi与网络]]（esp_event 在 WiFi 里的实际用法）

## 1. 一句话

> **esp_event = 基于"事件循环 + 回调"的发布订阅事件总线**（ESP-IDF 官方 `esp_event` 组件，事件驱动开发的基础设施）。

组件只负责 `esp_event_post(...)` 发事件，谁注册了 handler 谁响应，发布者不知道订阅者：

```text
WiFi驱动 ──post──► [ 默认事件循环 sys_evt ] ──回调──► 应用 / 其他组件
  │
  └─ 系统事件（WIFI_EVENT / IP_EVENT / ...）
```

所有事件先进入循环的**事件队列**，由事件循环任务取出后**按顺序调用注册的回调**——天然串行化，handler 之间不会并发。

## 2. 核心概念：事件 / 事件循环 / 处理程序

- **事件（Event）**：用**两段式标识符**定位：`事件根基(event_base) + 事件ID(event_id)`，官方比喻为"姓 + 名"：
  - **事件根基** `esp_event_base_t`：本质是 `const char*` 全局变量，标识一组相关事件。命名规范：大写、以 `_EVENT` 结尾（如 `WIFI_EVENT`、`IP_EVENT`、`ETHERNET_EVENT`）。
  - **事件ID** `int32_t`：该组内的具体事件，建议用枚举定义（如 `WIFI_EVENT_STA_START`）。
- **事件循环（Event Loop）**：连接"事件源"和"处理程序"的桥梁。事件源 post 事件进循环的队列，循环的任务取出并分发。有**默认事件循环**和**用户事件循环**两种。
- **处理程序（Handler）**：注册到循环的回调函数，事件命中时被调用。签名固定为：

```c
void handler(void *event_handler_arg, esp_event_base_t event_base,
             int32_t event_id, void *event_data);
```

### 2.1 默认事件循环 vs 用户事件循环

| | 用户事件循环 | 默认事件循环 |
| --- | --- | --- |
| 创建 | `esp_event_loop_create(&args, &handle)` | `esp_event_loop_create_default()` |
| 句柄 | 拿到 `esp_event_loop_handle_t`，自己管理 | **句柄隐藏**，不可直接操作 |
| 用途 | 应用自定义事件 | 系统事件（WiFi/IP/以太网…） |
| 注册 | `esp_event_handler_register_with(loop,...)` | `esp_event_handler_register(...)` |
| 发布 | `esp_event_post_to(loop,...)` | `esp_event_post(...)` |
| 删除 | `esp_event_loop_delete(handle)` | `esp_event_loop_delete_default()` |

默认事件循环的实现（源码 `components/esp_event/default_event_loop.c`）：

```c
esp_event_loop_args_t loop_args = {
    .queue_size      = CONFIG_ESP_SYSTEM_EVENT_QUEUE_SIZE,      /* 默认 32 */
    .task_name       = "sys_evt",
    .task_stack_size = ESP_TASKD_EVENT_STACK,                   /* CONFIG_ESP_SYSTEM_EVENT_TASK_STACK_SIZE，默认 2304 */
    .task_priority   = ESP_TASKD_EVENT_PRIO,                    /* CONFIG_ESP_SYSTEM_EVENT_TASK_PRIO，默认 23 */
    .task_core_id    = 0,
};
```

> 行为上默认循环和用户循环**没有区别**：完全可以把自定义事件也 post 到默认循环，省一个循环的资源。WiFi 初始化时的 `esp_event_loop_create_default()` 就是为了让 `esp_wifi` 能发布 `WIFI_EVENT`/`IP_EVENT` 系统事件。

## 3. 最小使用流程

### 3.1 声明并定义自定义事件（放公共头文件）

```c
/* app_events.h —— 声明（extern 全局变量） */
#include "esp_event.h"

ESP_EVENT_DECLARE_BASE(SENSOR_EVENT);   /* 声明：告诉别人"存在这个事件根基" */

enum {
    SENSOR_EVENT_READY,      /* 传感器就绪 */
    SENSOR_EVENT_ERROR,      /* 传感器出错 */
};
```

```c
/* app_events.c —— 定义（分配全局变量） */
#include "app_events.h"

ESP_EVENT_DEFINE_BASE(SENSOR_EVENT);    /* 定义：真正定义出这个全局变量，全工程唯一一次 */
```

### 3.2 创建事件循环（app_main 启动时）

```c
esp_event_loop_create_default();        /* 系统事件 + 自定义事件都能用 */
```

### 3.3 注册 handler

```c
static void sensor_handler(void *arg, esp_event_base_t base,
                           int32_t id, void *data)
{
    if (id == SENSOR_EVENT_READY) {
        sensor_data_t *d = (sensor_data_t *)data;   /* data 是事件数据的指针 */
        /* ...处理... */
    }
}

ESP_ERROR_CHECK(esp_event_handler_register(SENSOR_EVENT, SENSOR_EVENT_READY,
                                          &sensor_handler, NULL));
```

### 3.4 发布事件（任意任务/模块）

```c
sensor_data_t data = { .temperature = 25, .humidity = 60 };
ESP_ERROR_CHECK(esp_event_post(SENSOR_EVENT, SENSOR_EVENT_READY,
                               &data, sizeof(data), portMAX_DELAY));
```

> `esp_event_post` 会把 `event_data` **拷贝一份**进事件队列，库自动管理这份拷贝的释放——handler 收到的数据永远有效，发布者的局部变量在 post 返回后即可丢弃。

### 3.5 完整生命周期

```text
app_main
  │ 1. esp_event_loop_create_default()      // 创建循环（含 sys_evt 任务）
  │ 2. esp_event_handler_register(...)      // 注册 handler
  │ 3. 任意任务 esp_event_post(...)         // 事件进队列（数据已拷贝）
  ▼
sys_evt 任务：取事件 → 匹配 base+id → 顺序调用匹配的 handler
```

## 4. 注册的通配方式（很重要）

`esp_event_handler_register` 的 `event_base`/`event_id` 参数支持三种匹配粒度：

| 注册参数 | 匹配范围 |
| --- | --- |
| `(MY_BASE, MY_ID)` | 只匹配这一个具体事件 |
| `(MY_BASE, ESP_EVENT_ANY_ID)` | 该根基下的**所有事件** |
| `(ESP_EVENT_ANY_BASE, ESP_EVENT_ANY_ID)` | 循环里的**所有事件**（慎用） |

```c
esp_event_handler_register(MY_BASE, MY_ID, h1, NULL);          /* 命中 MY_BASE+MY_ID */
esp_event_handler_register(MY_BASE, ESP_EVENT_ANY_ID, h2, NULL); /* 命中 MY_BASE 下所有 ID */
esp_event_handler_register(ESP_EVENT_ANY_BASE, ESP_EVENT_ANY_ID, h3, NULL); /* 命中一切 */
```

## 5. 常见系统事件（WiFi 场景）

```c
/* WiFi 事件根基：WIFI_EVENT */
WIFI_EVENT_STA_START        // STA 启动完成 → 在这里调 esp_wifi_connect()
WIFI_EVENT_STA_CONNECTED    // 已连上 AP（还没 IP）
WIFI_EVENT_STA_DISCONNECTED // 断开 → 需要用户自己重连
WIFI_EVENT_AP_STACONNECTED / WIFI_EVENT_AP_STADISCONNECTED

/* IP 事件根基：IP_EVENT */
IP_EVENT_STA_GOT_IP         // DHCP 拿到 IP → 网络真正就绪（event_data 是 ip_event_got_ip_t*）
```

## 6. 从 ISR 发布事件

中断上下文不能用普通 `esp_event_post`（可能阻塞），用专用变体：

```c
/* 需要开启：CONFIG_ESP_EVENT_POST_FROM_ISR=y */
BaseType_t task_unblocked = pdFALSE;
esp_event_isr_post(SENSOR_EVENT, SENSOR_EVENT_READY,
                   &data, sizeof(data), &task_unblocked);
/* 若 task_unblocked==pdTRUE 且有更高优先级任务被唤醒，应请求上下文切换 */
```

注意：`esp_event_isr_post` 的 `event_data_size` **最大 4 字节**；若 ISR 放在 IRAM，还需 `CONFIG_ESP_EVENT_POST_FROM_IRAM_ISR=y`。

## 7. 用户事件循环（自定义专用循环）

需要把某类事件隔离、或给事件循环单独分配任务属性时，创建用户循环：

```c
esp_event_loop_args_t args = {
    .queue_size      = 16,
    .task_name       = "ui_evt",          /* 设为 NULL 则不自建任务 */
    .task_priority   = 5,
    .task_stack_size = 4096,
    .task_core_id    = 1,                 /* 双核可固定到某个核 */
};
esp_event_loop_handle_t loop;
esp_event_loop_create(&args, &loop);

esp_event_handler_register_with(loop, UI_EVENT, ESP_EVENT_ANY_ID, ui_handler, NULL);
esp_event_post_to(loop, UI_EVENT, UI_EVENT_REFRESH, NULL, 0, portMAX_DELAY);
```

> `task_name = NULL` 时不创建专用任务，需要自己定期调用 `esp_event_loop_run(loop, ticks_to_run)` 手动分发。

## 8. 重要问题：队列满了会丢事件

事件是"post 进队列 → 任务取出分发"。如果**发布速度 > 消费速度**，队列满时：

- `esp_event_post` 会按 `ticks_to_wait` **阻塞等待**队列有空位；
- `esp_event_isr_post` 在队列满时直接失败（`ESP_FAIL`），事件**被丢弃**。

所以高频数据（传感器原始流、音频等）不适合走事件总线——和 zbus 的结论一致（官方建议高频大块数据用别的机制）。事件总线适合"低频、状态变化、系统通知"。

## 9. 常见坑

1. **handler 里不能注册/注销 handler**（除非注销它自己）：事件循环在分发过程中修改注册表会导致未定义行为。官方明确允许"处理程序自行注销"，但禁止在该循环上做其他注册/注销。
2. **handler 会串行执行**：所有匹配的 handler 在**事件循环任务上下文**按"先注册先执行"顺序跑。handler 里做长耗时操作会卡住整个循环，拖慢所有后续事件 → 重活丢给独立任务/队列。
3. **`event_handler_arg` 是借用不是拷贝**：库不持有它的副本，使用期间必须保证指向的内存有效。
4. **注销通配符不连带具体事件**：用 `ESP_EVENT_ANY_ID` 注销，不会把用具体 ID 注册的 handler 注销掉（防止误伤其他组件）。
5. **默认循环只能建一次**：重复 `esp_event_loop_create_default()` 返回 `ESP_ERR_INVALID_STATE`。
6. **WiFi 要 post 事件必须先有默认循环**：`esp_wifi` 发布系统事件依赖默认循环，初始化顺序固定为 `esp_netif_init() → esp_event_loop_create_default() → esp_wifi_init()`。

## 10. esp_event vs zbus（Zephyr）

| 维度 | ESP-IDF esp_event | Zephyr zbus |
| --- | --- | --- |
| 模型 | 事件**队列 + 回调**分发（异步） | **Channel 保存最新消息** + 通知观察者 |
| 事件标识 | `base`(字符串全局变量) + `id`(枚举) | 静态 Channel（`ZBUS_CHAN_DEFINE`） |
| 注册方式 | **运行时** `esp_event_handler_register` | **编译期**静态宏 + 链接器 section |
| 订阅者执行 | 统一在**事件循环任务**上下文（串行） | Listener 同步（发布者上下文）/ Subscriber 独立线程 |
| 消息投递 | 事件进队列，**队列满会丢/阻塞** | Channel 只保存最新，普通 Subscriber **会被覆盖** |
| 事件数据 | post 时**拷贝**进队列，handler 读到副本 | 共享内存，reader 加锁拷贝读 |
| 解耦 | 发布者不知道订阅者 | 发布者不知道订阅者 |
| 适用 | 系统事件、WiFi/IP、模块状态通知 | 状态同步、系统事件、模块解耦广播 |
| 不适合 | 高频大数据流 | 高速数据流、大块连续数据（用 Pipe） |

**本质区别一句话**：esp_event 是"**事件队列 + 回调**"（异步、有缓冲队列）；zbus 是"**共享最新状态 + 通知**"（读的是 Channel 里的当前数据）。前者更像"发一条通知给循环去处理"，后者更像"维护一个最新值并广播变更"。

## 11. 设计建议

- **区分 Event / Command / State**：命名严格 `EVENT_xxx`（已发生的事实）/ `CMD_xxx`（请求执行）/ 状态机状态，不要把"请求"和"事实"混在一个枚举里。详见 [[嵌入式设计模式-事件总线]]。
- **不要搞万能事件总线 + 巨大 enum**：按领域定义事件根基（`SENSOR_EVENT`、`POWER_EVENT`、`OTA_EVENT`…），一个 base 一个主题。
- **内部动作不绕总线**：模块内部函数调用别发事件，总线只表达"其他模块可能关心的事"。
- **高频数据走队列/DMA/ringbuffer**，事件总线只做通知。
- **性能分析**：开启 `CONFIG_ESP_EVENT_LOOP_PROFILING=y`，用 `esp_event_dump(stdout)` 查看各循环收发/丢弃数量和 handler 调用次数、耗时。

## 12. 参考

- 官方文档（事件循环库）：https://docs.espressif.com/projects/esp-idf/zh_CN/latest/esp32/api-reference/system/esp_event.html
- 源码：`esp-idf/components/esp_event/`（`esp_event.c` / `default_event_loop.c` / `include/esp_event.h` / `include/esp_event_base.h`）
- 官方示例：`examples/system/esp_event/default_event_loop`、`examples/system/esp_event/user_event_loops`
- 相关笔记：[[zbus]] [[嵌入式设计模式-事件总线]] [[04-ESP-IDF-WiFi与网络]]
