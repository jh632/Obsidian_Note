---
date: 2026-06-09
tags: [rtos, freertos, power-management, tickless-idle, low-power, cortex-m]
aliases: [Tickless Idle Mode, 无Tick空闲模式, configUSE_TICKLESS_IDLE]
---

# Tickless IDLE 模式

## 概述

Tickless IDLE（无 Tick 空闲模式）是 FreeRTOS 提供的一种低功耗技术，核心思想是：**在系统空闲期间停止周期性 SysTick 中断，允许 MCU 进入深度睡眠，直到有任务需要执行或外部中断唤醒时才恢复**。传统 RTOS 即使所有任务都处于阻塞态，仍会以固定频率（通常 1ms）产生 Tick 中断，频繁唤醒 CPU 造成不必要的能量消耗。

## 核心概念

- **configUSE_TICKLESS_IDLE** — FreeRTOS 的编译期开关，控制是否启用 Tickless 模式（取值 0/1/2）
- **portSUPPRESS_TICKS_AND_SLEEP()** — 核心宏，由 Idle 任务调用，执行实际的睡眠进入/退出流程
- **eTaskConfirmSleepModeStatus()** — 睡眠前检查函数，返回 `eAbortSleep` / `eStandardSleep` / `eNoTasksWaitingTimeout`
- **vTaskStepTick()** — 唤醒后校正系统 Tick 计数值，补偿睡眠期间丢失的 Tick
- **configEXPECTED_IDLE_TIME_BEFORE_SLEEP** — 进入睡眠的最小空闲时间阈值（Tick 数），防止过于频繁地进出睡眠
- **configPRE_SLEEP_PROCESSING / configPOST_SLEEP_PROCESSING** — 睡眠前后的用户钩子宏，用于关闭/恢复外设时钟

## 细节

### 1. 配置选项

```c

// FreeRTOSConfig.h

// 0 = 禁用（默认），1 = 使用内置实现，2 = 用户自定义实现
#define configUSE_TICKLESS_IDLE              1

// 空闲时间低于此值时跳过睡眠（单位：Tick）
#define configEXPECTED_IDLE_TIME_BEFORE_SLEEP 4

// 仅当 SysTick 频率 ≠ CPU 核心频率时需要显式定义
#define configSYSTICK_CLOCK_HZ               ( 1000000UL )

// 可选：睡眠前后钩子
#define configPRE_SLEEP_PROCESSING( x )       MyPreSleepHook( x )
#define configPOST_SLEEP_PROCESSING( x )      MyPostSleepHook( x )
```

| `configUSE_TICKLESS_IDLE` | 含义 |
|---|---|
| **0** | 禁用 Tickless 模式，系统始终产生周期性 Tick 中断 |
| **1** | 使用 FreeRTOS 提供的默认实现（Cortex-M 端口已有内置实现） |
| **2** | 用户完全自定义实现，需自行提供 `portSUPPRESS_TICKS_AND_SLEEP()` |

### 2. 工作原理与完整流程

系统检测到所有应用任务进入阻塞态或挂起态后，Idle 任务开始运行，并触发 Tickless 流程：

```
                    Idle 任务开始运行
                           │
                           ▼
              计算预期空闲时间 (xExpectedIdleTime)
              即 "距离下一个任务到期还有多少 Tick"
                           │
                           ▼
               ┌─ xExpectedIdleTime < threshold?
               │     是 ──→ 不进入睡眠，直接 yield
               │
               ▼ 否
          portSUPPRESS_TICKS_AND_SLEEP(xExpectedIdleTime)
               │
               ├── 1. 关中断 (cpsid i)，进入临界区
               ├── 2. eTaskConfirmSleepModeStatus()
               │      ├── eAbortSleep → 恢复中断，退出
               │      ├── eNoTasksWaitingTimeout → 可无限期睡眠
               │      └── eStandardSleep → 设置定时器按时唤醒
               ├── 3. (可选) configPRE_SLEEP_PROCESSING()
               ├── 4. 停止 SysTick，读取当前计数值
               ├── 5. 计算并设置 SysTick 重装载值为睡眠时长
               ├── 6. 执行 WFI 指令进入低功耗模式
               │
               │     ◄===== 被中断或定时器唤醒 =======►
               │
               ├── 7. (可选) configPOST_SLEEP_PROCESSING()
               ├── 8. 开中断 → 关中断（让 ISR 先跑，防漂移）
               ├── 9. 读取 SysTick 当前值，计算实际睡眠时间
               ├── 10. vTaskStepTick(ulCompleteTickPeriods)
               │         ← 校正系统 Tick 计数
               ├── 11. 恢复 SysTick 为正常周期
               └── 12. 开中断 (cpsie i)
                           │
                           ▼
                    返回 Idle 任务循环
```

### 3. 关键函数详解

#### 3.1 `eTaskConfirmSleepModeStatus()`

在进入低功耗前调用，确认是否应该睡眠：

| 返回值 | 含义 | 处理方式 |
|---|---|---|
| `eAbortSleep` | 有任务已就绪或上下文切换待处理 | **不睡眠**，立即恢复中断并返回 |
| `eStandardSleep` | 可以睡眠，但需设置唤醒定时器 | 按 `xExpectedIdleTime` 配置 SysTick 或替代定时器 |
| `eNoTasksWaitingTimeout` | 没有任务等待超时（所有阻塞任务都是无限等待） | **可无限期睡眠**，直到外部中断唤醒，无需唤醒定时器 |

> 只要有软件定时器（Software Timer）运行，就不会返回 `eNoTasksWaitingTimeout`。

#### 3.2 `vTaskStepTick(xTicksToStep)`

唤醒后调用，**将系统 Tick 计数值 `xTickCount` 向前跳跃** `xTicksToStep` 个 Tick。同时会处理在这段"被跳过"的时间中应该到期的任务延时列表（即那些 `vTaskDelay` 或同步对象超时本应在这段时间内触发的情况）。

```c
void vTaskStepTick( TickType_t xTicksToStep );
```

- `xTicksToStep`：睡眠期间实际经过的完整 Tick 数
- 这个函数确保 `vTaskDelay()`、`xSemaphoreTake(timeout)` 等超时行为在睡眠后仍然正确

#### 3.3 `portSUPPRESS_TICKS_AND_SLEEP()` — Cortex-M 内置实现

FreeRTOS 官方为 ARM Cortex-M 提供了弱符号（`__attribute__((weak))`）的默认实现，开发者可按需 override。其核心步骤（基于 GCC ARM_CM4F 移植）：

```c
__attribute__((weak)) void vPortSuppressTicksAndSleep( TickType_t xExpectedIdleTime )
{
    // 1. 防溢出：裁剪 xExpectedIdleTime 到 xMaximumPossibleSuppressedTicks

    // 2. 关中断 (cpsid i) + DSB + ISB

    // 3. 确认睡眠状态
    if( eTaskConfirmSleepModeStatus() == eAbortSleep ) {
        __asm volatile( "cpsie i" ::: "memory" );
        return;
    }

    // 4. 停止 SysTick，读取剩余计数值
    ulSysTickDecrementsLeft = portNVIC_SYSTICK_CURRENT_VALUE_REG;

    // 5. 计算重装载值
    ulReloadValue = ulSysTickDecrementsLeft
                  + ( ulTimerCountsForOneTick * ( xExpectedIdleTime - 1UL ) );

    // 6. 设置重装载并启动
    portNVIC_SYSTICK_LOAD_REG = ulReloadValue;
    portNVIC_SYSTICK_CURRENT_VALUE_REG = 0UL;
    portNVIC_SYSTICK_CTRL_REG |= portNVIC_SYSTICK_ENABLE_BIT;

    // 7. 用户钩子
    configPRE_SLEEP_PROCESSING( xModifiableIdleTime );

    // 8. WFI 指令进入睡眠
    __asm volatile( "dsb" ::: "memory" );
    __asm volatile( "wfi" );
    __asm volatile( "isb" ::: "memory" );

    // 9. 用户钩子（唤醒后）
    configPOST_SLEEP_PROCESSING( xExpectedIdleTime );

    // 10. 开中断让 ISR 执行，再关中断（防漂移）

    // 11. 根据唤醒原因分两支处理：
    //     分支 A — SysTick 计数到零唤醒：计算剩余微小时间
    //     分支 B — 其他中断唤醒：计算实际经过了多少个完整 Tick 周期

    // 12. 恢复 SysTick 为正常周期
    portNVIC_SYSTICK_LOAD_REG = ulTimerCountsForOneTick - 1UL;

    // 13. 校正 Tick 计数
    vTaskStepTick( ulCompleteTickPeriods );

    // 14. 开中断
    __asm volatile( "cpsie i" ::: "memory" );
}
```

### 4. 唤醒后的 Tick 校正机制

唤醒后需要处理两种场景：

**场景 A — SysTick 计数到零自然唤醒**（即睡眠时间到了）
- 直接取 `xExpectedIdleTime - 1` 作为完整经过的 Tick 数
- 剩余的微量时间通过设置 SysTick 当前值来补偿

**场景 B — 被其他中断提前唤醒**（比如 UART 接收中断）
- 读取 SysTick 当前计数值，计算实际减少的计数量
- `ulCompleteTickPeriods = 实际减少量 / ulTimerCountsForOneTick`
- 将 SysTick 重装载为余数部分

两种场景最终都调用 `vTaskStepTick()` 来完成整体 Tick 校正。

### 5. SysTick 与睡眠时长限制

SysTick 是 24 位递减计数器，这限制了单次最长睡眠时间：

```
// 相关静态变量在 vPortSetupTimerInterrupt() 中初始化
ulTimerCountsForOneTick       = configSYSTICK_CLOCK_HZ / configTICK_RATE_HZ
xMaximumPossibleSuppressedTicks = portMAX_24_BIT_NUMBER / ulTimerCountsForOneTick
ulStoppedTimerCompensation     = portMISSED_COUNTS_FACTOR / (configCPU_CLOCK_HZ / configSYSTICK_CLOCK_HZ)
```

| SysTick 时钟 | configTICK_RATE_HZ | 单次最长睡眠 |
|---|---|---|
| 1 MHz | 1000 (1ms) | ~16777 个 Tick ≈ **16.7 秒** |
| 10 MHz | 1000 (1ms) | ~1677 个 Tick ≈ **1.67 秒** |
| 100 MHz | 1000 (1ms) | ~167 个 Tick ≈ **0.167 秒** |

> 如果需要更长的单次睡眠，可以：
> - 使用外部低功耗定时器（LPTIM、RTC）作为唤醒源
> - 设置 `configUSE_TICKLESS_IDLE = 2`，提供自定义 `portSUPPRESS_TICKS_AND_SLEEP()` 实现

### 6. 自定义实现（configUSE_TICKLESS_IDLE = 2）

当内置实现不满足需求时（如需使用 RTC 代替 SysTick、或需要更深的睡眠模式），可完全自定义：

```c
// FreeRTOSConfig.h
#define configUSE_TICKLESS_IDLE              2
#define portSUPPRESS_TICKS_AND_SLEEP(xIdleTime)    vApplicationSleep(xIdleTime)

// 用户实现
void vApplicationSleep( TickType_t xExpectedIdleTime )
{
    // 1. 读取外部定时器当前值（该定时器在睡眠期间仍需运行）
    uint32_t ulLowPowerTimeBeforeSleep = ulGetExternalTimer();

    // 2. 停止 SysTick 中断定时器
    prvStopTickInterruptTimer();

    // 3. 关中断（不能屏蔽唤醒源的中断优先级）
    portDISABLE_INTERRUPTS();

    // 4. 确认是否仍可睡眠
    if( eTaskConfirmSleepModeStatus() == eAbortSleep ) {
        prvStartTickInterruptTimer();
        portENABLE_INTERRUPTS();
        return;
    }

    // 5. 配置唤醒源
    if( eTaskConfirmSleepModeStatus() != eNoTasksWaitingTimeout ) {
        vSetWakeTimer( xExpectedIdleTime );  // 设置 RTC 或 LPTIM
    }

    // 6. 进入深度睡眠
    configPRE_SLEEP_PROCESSING( xExpectedIdleTime );
    prvEnterDeepSleep();   // 例如 STM32 的 HAL_PWR_EnterSLEEPMode()
    configPOST_SLEEP_PROCESSING( xExpectedIdleTime );

    // 7. 唤醒后：计算实际睡眠时间
    uint32_t ulLowPowerTimeAfterSleep = ulGetExternalTimer();

    // 8. 校正 Tick 计数
    uint32_t ulTicksSlept = ( ulLowPowerTimeAfterSleep - ulLowPowerTimeBeforeSleep );
    vTaskStepTick( ulTicksSlept );

    // 9. 恢复 Tick 定时器
    prvStartTickInterruptTimer();
    portENABLE_INTERRUPTS();
}
```

### 7. 与 ESP-IDF Auto Light-sleep 的关系

在 ESP-IDF 中，Tickless IDLE 是 **Auto Light-sleep** 功能的基础。当所有任务都阻塞、所有电源锁被释放时，ESP-IDF 的电源管理组件利用 FreeRTOS 的 Tickless IDLE 钩子，自动判断闲置时长是否超过 `CONFIG_FREERTOS_IDLE_TIME_BEFORE_SLEEP`，若满足则配置定时器唤醒源并进入 Light-sleep。

关键配置途径：
- `menuconfig` → `Component config → FreeRTOS → Kernel` 中启用 Tickless IDLE
- 同时配置 `Power Management → wakeup source` 相关项

详见 [[../低功耗/esp32低功耗支持.md]]。

### 8. 常见问题与最佳实践

| 问题 | 建议 |
|---|---|
| **睡眠太短，频繁进出** | 调大 `configEXPECTED_IDLE_TIME_BEFORE_SLEEP`（典型值 4~10 Tick），避免为极短空闲时间支付睡眠唤醒开销 |
| **SysTick 24 位限制** | 使用外部低功耗定时器（LPTIM/RTC），设置 `configUSE_TICKLESS_IDLE = 2` 自定义实现 |
| **外设在睡眠期间耗电** | 在 `configPRE_SLEEP_PROCESSING` 中关闭外设时钟，`configPOST_SLEEP_PROCESSING` 中恢复 |
| **Tick 计数漂移** | 始终用一个**在睡眠期间仍运行的定时器**测量实际睡眠时间，传给 `vTaskStepTick()` |
| **中断优先级冲突** | 睡眠期间只屏蔽优先级低于 `configMAX_SYSCALL_INTERRUPT_PRIORITY` 的中断，高优先级中断应能唤醒 MCU |
| **软件定时器阻止无限睡眠** | 只要有软件定时器激活，`eTaskConfirmSleepModeStatus()` 永远不会返回 `eNoTasksWaitingTimeout` |

## 参考

- [FreeRTOS Low Power Support - Official Documentation](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/07-Lower-power-support)
- [FreeRTOS ARM Cortex-M Low Power](https://www.freertos.org/low-power-ARM-cortex-rtos.html)
- [FreeRTOS Kernel Source - port.c (Cortex-M)](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/main/portable/GCC/ARM_CM4F/port.c)
- [FreeRTOS vTaskStepTick Documentation](https://www.freertos.org/Documentation/02-Kernel/04-API-references/04-RTOS-kernel-control/07-vTaskStepTick)

## 相关笔记

- [[../低功耗/esp32低功耗支持.md]] — ESP32 低功耗模式（DFS / Light-sleep / Deep-sleep），含 Auto Light-sleep 与 Tickless IDLE 的结合
- [[../低功耗/低功耗的评估标准.md]] — 低功耗评估方法与指标
- [[任务和协程.md]] — FreeRTOS 任务调度基础（Idle 任务是触发 Tickless 的前提）
