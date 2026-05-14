# TI-RTOS 和 FreeRTOS API 映射速查

## 1. 使用范围和假设

- 这里的 **TI-RTOS** 默认指 **SYS/BIOS 内核层 API**，也就是常见的 `Task`、`Semaphore`、`Event`、`Mailbox`、`Clock`、`Hwi`、`Swi`、`Queue`。
- 这里的 **FreeRTOS** 默认指内核公开 API，以及常见配套组件：`queue.h`、`semphr.h`、`event_groups.h`、`timers.h`。
- 这份笔记的目标是 **方便面试回答和迁移理解**，不是追求“逐个函数机械替换”。
- 先记住一句话：**两者设计思想接近，但很多模块不是 1:1 对应，尤其是 `Swi`、`Hwi`、`Clock`、`Queue`。**

## 2. 一句话总览

| 场景    | TI-RTOS / SYS-BIOS                  | FreeRTOS                             | 面试回答关键词            |
| :---- | :---------------------------------- | :----------------------------------- | :----------------- |
| 任务管理  | `Task_*`                            | `xTask*` / `vTask*`                  | 都是优先级抢占式任务调度       |
| 延时    | `Task_sleep()`                      | `vTaskDelay()` / `vTaskDelayUntil()` | tick 延时，注意单位转换     |
| 信号量   | `Semaphore_*`                       | `xSemaphore*`                        | 二值/计数/互斥量          |
| 事件标志  | `Event_*`                           | `xEventGroup*`                       | 多 bit 同步           |
| 邮箱/消息 | `Mailbox_*`                         | `xQueue*`                            | FreeRTOS 用队列覆盖邮箱能力 |
| 软件定时  | `Clock_*`                           | `xTimer*`                            | 回调上下文不同            |
| 中断    | `Hwi_*`                             | 依赖端口/芯片，不是统一 API                     | FreeRTOS 不抽象中断创建   |
| 软中断   | `Swi_*`                             | 无直接等价物                               | 常用高优先级任务/通知替代      |
| 临界区   | `GateHwi` / `GateSwi` / `GateMutex` | `taskENTER_CRITICAL` / mutex         | 保护范围不同             |
| 内存管理  | `Memory_*` / `HeapMem_*`            | `pvPortMalloc()` / `vPortFree()`     | FreeRTOS 更偏简单堆管理   |
| 链表队列  | `Queue_*`                           | 无公开等价 API                            | 常自建链表或改用消息队列       |

## 3. 核心 API 映射表

### 3.1 任务 Task

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Task_create()` | `xTaskCreate()` / `xTaskCreateStatic()` | 创建任务 |
| `Task_delete()` | `vTaskDelete()` | 删除任务 |
| `Task_sleep(ticks)` | `vTaskDelay(ticks)` | 都是延时指定 tick |
| `Task_yield()` | `taskYIELD()` / `vTaskDelay(0)` | 主动让出 CPU |
| `Task_setPri()` | `vTaskPrioritySet()` | 动态改优先级 |
| `Task_getPri()` | `uxTaskPriorityGet()` | 读取优先级 |
| `Task_disable()` / `Task_restore()` | `vTaskSuspendAll()` / `xTaskResumeAll()` | 都会影响调度，但语义不完全相同 |
| `Task_Params_init()` | 无完全对应 | FreeRTOS 创建参数直接在 API 入参里传 |

**面试要点**

- `Task_sleep()` 和 `vTaskDelay()` 都依赖系统 tick。
- 真正项目里要警惕时间单位：TI 代码常直接传 tick，FreeRTOS 常写成 `pdMS_TO_TICKS(ms)`。
- 如果是“周期性任务”，FreeRTOS 更常用 `vTaskDelayUntil()`，这一点比 `Task_sleep()` 更容易回答出工程差异。

### 3.2 信号量 Semaphore

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Semaphore_create(count, ...)` | `xSemaphoreCreateBinary()` / `xSemaphoreCreateCounting()` / `xSemaphoreCreateMutex()` | FreeRTOS 把不同类型拆开 |
| `Semaphore_delete()` | `vSemaphoreDelete()` | 删除对象 |
| `Semaphore_pend(sem, timeout)` | `xSemaphoreTake(sem, timeout)` | 等待信号量 |
| `Semaphore_post(sem)` | `xSemaphoreGive(sem)` | 释放信号量 |
| `Semaphore_post()` from ISR | `xSemaphoreGiveFromISR()` | ISR 版本必须区分 |
| `Semaphore_pend(..., BIOS_WAIT_FOREVER)` | `xSemaphoreTake(..., portMAX_DELAY)` | 无限等待 |
| `Semaphore_pend(..., BIOS_NO_WAIT)` | `xSemaphoreTake(..., 0)` | 非阻塞获取 |

**面试要点**

- TI-RTOS 的 `Semaphore` 模块对“二值/计数”抽象更统一。
- FreeRTOS 明确区分 binary semaphore、counting semaphore、mutex、recursive mutex。
- **互斥量和信号量不要混答**：互斥量通常带优先级继承，普通信号量不强调“所有权”。

### 3.3 事件 Event

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Event_create()` | `xEventGroupCreate()` / `xEventGroupCreateStatic()` | 创建事件组 |
| `Event_delete()` | `vEventGroupDelete()` | 删除事件组 |
| `Event_post(event, bits)` | `xEventGroupSetBits(event, bits)` | 置位事件 bit |
| `Event_pend(event, andMask, orMask, timeout)` | `xEventGroupWaitBits()` | 等待一个或多个 bit |
| `Event_pend(..., BIOS_WAIT_FOREVER)` | `xEventGroupWaitBits(..., portMAX_DELAY)` | 无限等待 |
| `Event_pend(..., BIOS_NO_WAIT)` | `xEventGroupWaitBits(..., 0)` | 非阻塞检查 |

**面试要点**

- `Event` 和 `EventGroup` 是很接近的一组映射。
- 回答时要主动补一句：**FreeRTOS 事件组更偏 bitmask 同步，不适合传具体数据。**
- 如果题目在问“任务通知和事件组怎么选”，可以答：
  - 单任务单事件，高性能场景优先任务通知。
  - 多 bit 组合等待，多任务协作优先事件组。

### 3.4 邮箱 Mailbox / 消息传递

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Mailbox_create(msgSize, numMsgs, ...)` | `xQueueCreate(length, itemSize)` | FreeRTOS 用队列承载邮箱语义 |
| `Mailbox_delete()` | `vQueueDelete()` | 删除队列 |
| `Mailbox_post(mbx, msg, timeout)` | `xQueueSend(queue, msg, timeout)` | 发送消息 |
| `Mailbox_pend(mbx, msg, timeout)` | `xQueueReceive(queue, msg, timeout)` | 接收消息 |
| `Mailbox_post()` from ISR | `xQueueSendFromISR()` | ISR 版本发送 |
| `Mailbox_pend(..., BIOS_WAIT_FOREVER)` | `xQueueReceive(..., portMAX_DELAY)` | 无限等待 |

**面试要点**

- TI-RTOS 有明确的 `Mailbox` 模块。
- FreeRTOS 没有单独的 mailbox 类型，通常直接说：**邮箱用 queue 实现**。
- 如果消息体较大，工程里常传指针而不是整块拷贝。

### 3.5 软件定时器 Clock

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Clock_create()` | `xTimerCreate()` | 创建软件定时器 |
| `Clock_start()` | `xTimerStart()` | 启动 |
| `Clock_stop()` | `xTimerStop()` | 停止 |
| `Clock_delete()` | `xTimerDelete()` | 删除 |
| `Clock_setTimeout()` | `xTimerChangePeriod()` | 改周期/超时 |

**关键差异**

- **TI-RTOS `Clock` 回调通常运行在 `Swi` 上下文。**
- **FreeRTOS software timer 回调运行在 timer service task 上下文，不是中断上下文。**

**面试要点**

- 这是非常容易被追问的点。
- 如果面试官问“能不能在回调里阻塞”，回答要分开说：
  - TI-RTOS `Clock` 回调一般不能按普通任务那样随意阻塞。
  - FreeRTOS timer callback 运行在专用任务里，但仍然不建议长时间阻塞，否则会拖慢所有软件定时器。

### 3.6 中断 Hwi 和软中断 Swi

| TI-RTOS | FreeRTOS | 映射关系 |
| :-- | :-- | :-- |
| `Hwi_create()` | 无统一内核 API | 通常由芯片启动文件、NVIC、厂商 HAL 完成 |
| `Hwi_delete()` | 无统一内核 API | 同上 |
| `Hwi_disable()` / `Hwi_restore()` | `taskENTER_CRITICAL_FROM_ISR()` / `taskEXIT_CRITICAL_FROM_ISR()` 或端口宏 | 只能说“部分等价” |
| `Hwi_post()` | 无通用对应 | 一般不这么迁移 |
| `Swi_create()` | 无直接对应 | 常用高优先级任务、任务通知、deferred interrupt handling 替代 |
| `Swi_post()` | `vTaskNotifyGiveFromISR()` / `xTaskNotifyFromISR()` / `xSemaphoreGiveFromISR()` | 常见替代手段 |
| `Swi_disable()` / `Swi_restore()` | 无直接对应 | 视设计改写 |

**面试要点**

- **`Hwi` 和 `Swi` 是 TI-RTOS 比较有辨识度的地方。**
- FreeRTOS 不像 SYS/BIOS 那样把 `Hwi/Swi/Task` 做成一套完整分层抽象。
- 如果要迁移：
  - `Hwi` 保留在芯片中断层。
  - `Swi` 常改成“ISR 唤醒高优先级任务”。
  - 任务间同步常用 `task notification`，开销通常比 semaphore 更低。

### 3.7 临界区和互斥保护

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `GateMutex_enter()` / `GateMutex_leave()` | `xSemaphoreTake(mutex, ...)` / `xSemaphoreGive(mutex)` | 任务级互斥 |
| `GateHwi_enter()` / `GateHwi_leave()` | `taskENTER_CRITICAL()` / `taskEXIT_CRITICAL()` | 关闭中断保护临界区 |
| `GateSwi_enter()` / `GateSwi_leave()` | 无完全对等 | FreeRTOS 没有独立 `Swi` 层 |

**面试要点**

- `GateMutex` 偏“互斥锁”。
- `GateHwi` 偏“短临界区，直接关中断”。
- 回答时可以补一句：**关中断适合非常短的共享数据保护，不适合大段逻辑。**

### 3.8 内存管理

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Memory_alloc()` / `Memory_free()` | `pvPortMalloc()` / `vPortFree()` | 动态内存分配 |
| `HeapMem_create()` | 无直接公开等价 | FreeRTOS 常靠 `heap_1` ~ `heap_5` 实现 |
| `HeapBuf` | 无直接公开等价 | 常自行做固定块内存池 |

**面试要点**

- TI-RTOS 的内存模块化程度更高，支持不同 heap 实现。
- FreeRTOS 常见回答方式是：**内核提供统一分配接口，底层由 `heap_x.c` 决定策略。**
- 如果被问碎片问题：
  - `heap_1` 不支持释放。
  - `heap_4` 较常用，可合并相邻空闲块。
  - `heap_5` 支持多内存区域。

### 3.9 队列 Queue

| TI-RTOS | FreeRTOS | 说明 |
| :-- | :-- | :-- |
| `Queue_create()` / `Queue_put()` / `Queue_get()` | **无公开一一对应 API** | TI `Queue` 更像侵入式双向链表容器 |
| `Queue_empty()` | 无直接公开等价 | 需自己封装或改设计 |
| `Queue_remove()` | 无直接公开等价 | 同上 |

**面试要点**

- 这里最容易答错。
- TI-RTOS 的 `Queue` **不是** FreeRTOS 的 `Queue`。
- SYS/BIOS 的 `Queue` 更接近 Linux/RT-Thread 那种 **侵入式链表容器**。
- FreeRTOS 的 `queue` 是 **消息队列对象**，内部虽然也有链表/队列管理，但不是给业务代码直接当容器用的。

## 4. 常见迁移模式

### 4.1 Task + Semaphore

```c
/* TI-RTOS */
Semaphore_pend(sem, BIOS_WAIT_FOREVER);
Task_sleep(10);
Semaphore_post(sem);
```

```c
/* FreeRTOS */
xSemaphoreTake(sem, portMAX_DELAY);
vTaskDelay(10);
xSemaphoreGive(sem);
```

### 4.2 Event 等待多个 bit

```c
/* TI-RTOS */
Event_pend(evt, 0, BIT0 | BIT1, BIOS_WAIT_FOREVER);
```

```c
/* FreeRTOS */
xEventGroupWaitBits(evt, BIT0 | BIT1, pdTRUE, pdFALSE, portMAX_DELAY);
```

### 4.3 Mailbox 改 Queue

```c
/* TI-RTOS */
Mailbox_post(mbx, &msg, BIOS_NO_WAIT);
Mailbox_pend(mbx, &msg, BIOS_WAIT_FOREVER);
```

```c
/* FreeRTOS */
xQueueSend(queue, &msg, 0);
xQueueReceive(queue, &msg, portMAX_DELAY);
```

### 4.4 Swi 改“中断唤醒任务”

```c
/* TI-RTOS 思路 */
Hwi -> Swi_post() -> 软中断处理
```

```c
/* FreeRTOS 常见思路 */
ISR -> xTaskNotifyFromISR() -> 高优先级任务处理
```

## 5. 面试高频差异点

### 5.1 为什么说 TI-RTOS 和 FreeRTOS 不是完全一一映射？

- 因为 TI-RTOS 把 `Hwi`、`Swi`、`Task`、`Clock`、`Queue` 这些运行时对象抽象得更系统。
- FreeRTOS 更聚焦任务调度、同步、消息传递，本身不统一抽象“中断创建”和“软中断层”。

### 5.2 `Mailbox` 和 `Queue` 在两个系统里分别是什么意思？

- TI-RTOS：
  - `Mailbox` 是消息邮箱。
  - `Queue` 是侵入式链表容器。
- FreeRTOS：
  - `Queue` 是消息队列。
  - 没有公开给业务直接用的“SYS/BIOS Queue 等价容器”。

### 5.3 `Clock` 最大差异是什么？

- TI-RTOS `Clock` 回调更接近 `Swi` 语义。
- FreeRTOS software timer 回调运行在 timer task。
- 所以迁移时不能只替换函数名，还要重看“回调上下文能做什么”。

### 5.4 如果让我从 TI-RTOS 迁到 FreeRTOS，优先怎么做？

1. 先映射 `Task`、`Semaphore`、`Event`、`Mailbox` 这些最稳定的对象。
2. 再处理 `Clock`，重点确认回调上下文。
3. 最后处理 `Swi`、`Hwi`、`Queue` 这些非 1:1 模块，通常需要改设计，不只是改 API。

## 6. 最短记忆版

- `Task_*` -> `xTask* / vTask*`
- `Semaphore_*` -> `xSemaphore*`
- `Event_*` -> `xEventGroup*`
- `Mailbox_*` -> `xQueue*`
- `Clock_*` -> `xTimer*`
- `GateMutex_*` -> mutex
- `GateHwi_*` -> critical section
- `Swi_*` -> 无直接等价，常用 task notification 替代
- `Hwi_*` -> 无统一等价，依赖芯片/HAL
- `Queue_*` -> 无公开等价，别和 FreeRTOS queue 混为一谈

## 7. 一句面试收尾话术

> TI-RTOS 和 FreeRTOS 在任务、信号量、事件、邮箱这些基础能力上可以建立比较清晰的映射，但不是机械替换。真正迁移时最需要关注的是 `Swi/Hwi/Clock/Queue` 这些上下文和抽象层级不同的模块。
