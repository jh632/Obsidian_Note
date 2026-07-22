---
tags:
  - freertos
  - rtos
  - coding_style
created: 2026-07-14
---

# FreeRTOS 中不同前缀的含义（x, ul, pv 等）

FreeRTOS 采用 **类匈牙利命名法**，通过前缀快速传达变量类型和函数返回值信息。掌握这些前缀有助于阅读 FreeRTOS 源码。

---

## 1. 变量前缀

变量前缀由**类型标识**组合而成，顺序为：指针（p） → 符号（u） → 基本类型。

### 1.1 基本类型

| 前缀 | 含义 | 等价类型 |
|------|------|----------|
| `c` | char | `char` |
| `s` | short | `short` / `int16_t` |
| `l` | long | `long` / `int32_t` |
| `x` | BaseType_t / 非标准类型 | `portBASE_TYPE`、句柄、结构体等 |
| `e` | 枚举（enum） | enum |

### 1.2 组合前缀

| 前缀 | 含义 | 等价类型 | 示例 |
|------|------|----------|------|
| `uc` | unsigned char | `uint8_t` | `ucPriority` |
| `us` | unsigned short | `uint16_t` | `usStackDepth` |
| `ul` | unsigned long | `uint32_t` | `ulValue` |
| `ux` | unsigned BaseType_t | `UBaseType_t` | `uxPriority`、`uxTaskNumber` |

### 1.3 指针前缀

| 前缀 | 含义 | 示例 |
|------|------|------|
| `p` + 上述类型 | 指向该类型的指针 | — |
| `pc` | pointer to char → 字符串 | `pcTaskName` |
| `px` | pointer to x（句柄/结构体指针） | `pxCurrentTCB`、`pxTaskHandle` |
| `pv` | pointer to void → 泛型指针 | `pvParameters` |
| `pp` | 二级指针 | `ppxTimerList` |

> **解读规则：** 从左到右展开。例如 `ppx` = `p` + `px` → 指向"非标准类型指针"的指针（二级句柄指针）。

### 1.4 完整示例

```c
uint8_t          ucTaskState;     // u + c → unsigned char
uint32_t         ulNotificationValue; // u + l → unsigned long
UBaseType_t      uxSavedInterruptStatus; // u + x → unsigned BaseType
TaskHandle_t     xTaskHandle;     // x → 非标准类型(句柄)
char            *pcTaskName;      // p + c → 指向 char 的指针
void            *pvParameters;    // p + v → 泛型指针
TCB_t           *pxCurrentTCB;   // p + x → 指向结构体的指针
```

---

## 2. 函数前缀

函数前缀标识**返回值类型**或**可见性**。

| 前缀 | 含义 | 示例 |
|------|------|------|
| `v` | 返回 void | `vTaskDelay()`、`vTaskDelete()` |
| `x` | 返回 `BaseType_t` 或非 void 类型 | `xTaskCreate()`、`xQueueSend()` |
| `prv` | **私有函数**（static，不出现在公开 API） | `prvAddTaskToReadyList()` |
| `pv` | 返回 `void *` | `pvPortMalloc()` |
| `e` | 返回枚举 | `eTaskGetState()` |
| `ul` | 返回 `unsigned long` | `ulTaskGetRunTime()` |
| `ux` | 返回 `UBaseType_t` | `uxTaskGetStackHighWaterMark()` |
| `pc` | 返回 `char *` | `pcTaskGetName()` |

> **注意：** 返回 `pdTRUE`/`pdFALSE` 的函数用 `x` 前缀，因为 `pdTRUE`/`pdFALSE` 是 `BaseType_t`。

### 常见 API 对照

```c
// v 开头 → 无返回值
void vTaskSuspend(TaskHandle_t xTask);

// x 开头 → 返回 pdPASS / pdFAIL (BaseType_t)
BaseType_t xTaskCreate(TaskFunction_t pxTaskCode, ...);

// ux 开头 → 返回无符号整数
UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t xTask);

// e 开头 → 返回枚举
eTaskState eTaskGetState(TaskHandle_t xTask);
```

---

## 3. 宏前缀

FreeRTOS 宏也遵循一定命名规律：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `pd` | ProjDefs 系列宏 | `pdPASS`、`pdFAIL`、`pdTRUE`、`pdFALSE` |
| `port` | 移植层宏 | `portMAX_DELAY`、`portTICK_PERIOD_MS` |
| `config` | 配置宏（FreeRTOSConfig.h） | `configUSE_PREEMPTION` |
| `trace` | 追踪宏 | `traceTASK_SWITCHED_IN()` |
| `trace` + 大写 | 追踪 hook | `traceTASK_INCREMENT_TICK(xTickCount)` |
| `task` | task.h 控制宏 | `taskYIELD()`、`taskENTER_CRITICAL()` |

---

## 4. 快速对照表

| 看到 | 类型 | 场合 |
|------|------|------|
| `uc` | `uint8_t` / `unsigned char` | 小数值、状态标志 |
| `us` | `uint16_t` | 中等数值 |
| `ul` | `uint32_t` / `unsigned long` | 计数值、时间戳 |
| `ux` | `UBaseType_t` | 优先级、中断状态 |
| `pc` | `char *` | 字符串（任务名等） |
| `px` | 句柄/结构体指针 | TCB、队列句柄等 |
| `pv` | `void *` | 泛型参数/返回值 |
| `v` (函数) | 返回 void | 纯副作用操作 |
| `x` (函数) | 返回 `BaseType_t` | 可能失败的操作 |
| `prv` (函数) | 私有 static 函数 | 内核内部实现 |
| `e` (函数) | 返回枚举 | 状态查询 |
| `pd` (宏) | `pdTRUE`/`pdPASS` 等 | 逻辑/状态值 |
| `port` (宏) | 移植层定义 | `portMAX_DELAY` 等 |

---

## 5. 为什么这么设计？

1. **源码即文档** — 看到 `uxPriority` 立刻知道它是 `UBaseType_t` 类型
2. **跨平台一致** — 不同架构下 `int` 的长度不同，用 `l`/`s` 前缀比直接用 `int` 更清晰
3. **降低误用** — 函数前缀 `x`/`v` 让调用者一眼知道是否需要检查返回值
4. **区分公开/私有** — `prv` 前缀明确标识内核内部函数，防止误调用

> **核心原则：** 不看声明/定义，仅凭名称就能推断类型和用途。
