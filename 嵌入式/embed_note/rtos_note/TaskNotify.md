## 1 TaskNotify本质:
来自每个任务创建都会自带的TCB
```c
TCB
├── 栈
├── 优先级
├── 状态
├── 通知值(Notification Value)
└── 通知状态(Notification State)
```

## 2 api文档

FreeRTOS 从 V10.4.0 开始引入了 **任务通知数组（Task Notification Array）** 的概念。在此之前，每个任务只有 **一个** 32 位的通知值（就像只有一个邮箱）。  
而现在，每个任务可以拥有 **多个** 32 位的通知值，它们被组织成一个数组。

```c
/**
 * @file task_notifications_api.h
 * @brief FreeRTOS 任务通知 API（支持索引扩展）简洁笔记
 */

/* 1. 发送通知：轻量级二值信号量风格 ---------------------------------------- */

/**
 * @brief 向任务发送通知，将目标任务的通知值加 1（类似给出二值信号量）。
 * @param xTaskToNotify 目标任务句柄（若为 NULL 则向自身发送）。
 * @return 通常返回 pdPASS（总是成功，除非通知被禁用）。
 * @note 不能用于中断，中断请使用 vTaskNotifyGiveFromISR()。
 * @see xTaskNotifyGiveIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyGive( TaskHandle_t xTaskToNotify );
BaseType_t xTaskNotifyGiveIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify );

/**
 * @brief 从中断中向任务发送通知，将目标任务的通知值加 1。
 * @param xTaskToNotify 目标任务句柄。
 * @param pxHigherPriorityTaskWoken 若退出中断需要切换任务，则设为 pdTRUE。
 * @note 此函数是宏包装，实际无返回值。
 * @see vTaskNotifyGiveIndexedFromISR() 用于指定通知索引。
 */
void vTaskNotifyGiveFromISR( TaskHandle_t xTaskToNotify, BaseType_t *pxHigherPriorityTaskWoken );
void vTaskNotifyGiveIndexedFromISR( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify, BaseType_t *pxHigherPriorityTaskWoken );

/**
 * @brief 等待并获取通知（递减计数），类似二值或计数信号量的 take。
 * @param xClearCountOnExit 为 pdTRUE 则将通知值清零；为 pdFALSE 则减一（计数信号量模式）。
 * @param xTicksToWait 阻塞等待时间（系统节拍）。
 * @return 返回获取通知前的通知值（可判断是否成功）。
 * @note 调用此函数会清零或递减通知值，并清除通知状态。
 * @see ulTaskNotifyTakeIndexed() 用于指定通知索引。
 */
uint32_t ulTaskNotifyTake( BaseType_t xClearCountOnExit, TickType_t xTicksToWait );
uint32_t ulTaskNotifyTakeIndexed( UBaseType_t uxIndexToWaitOn, BaseType_t xClearCountOnExit, TickType_t xTicksToWait );

/* 2. 发送通知：完整消息（32位值） ----------------------------------------- */

/**
 * @brief 向任务发送通知，可附带任意 32 位值，并按指定方式更新目标任务的通知值。
 * @param xTaskToNotify 目标任务句柄。
 * @param ulValue 要设置的 32 位值。
 * @param eAction 更新方式：eSetBits（按位或）、eIncrement（加1）、eSetValueWithOverwrite等。
 * @return 除 eSetValueWithoutOverwrite 且值未改变时返回 pdFAIL 外，通常返回 pdPASS。
 * @note 中断中请使用 xTaskNotifyFromISR()。
 * @see xTaskNotifyIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotify( TaskHandle_t xTaskToNotify, uint32_t ulValue, eNotifyAction eAction );
BaseType_t xTaskNotifyIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify, uint32_t ulValue, eNotifyAction eAction );

/**
 * @brief 发送通知并查询目标任务原来的通知值（在更新之前复制出来）。
 * @param xTaskToNotify 目标任务句柄。
 * @param ulValue 要设置的 32 位值。
 * @param eAction 更新方式。
 * @param pulPreviousNotifyValue 输出参数，存储更新前的通知值。
 * @return 同 xTaskNotify()。
 * @see xTaskNotifyAndQueryIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyAndQuery( TaskHandle_t xTaskToNotify, uint32_t ulValue, eNotifyAction eAction, uint32_t *pulPreviousNotifyValue );
BaseType_t xTaskNotifyAndQueryIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify, uint32_t ulValue, eNotifyAction eAction, uint32_t *pulPreviousNotifyValue );

/**
 * @brief 从中断中发送通知（可附带值），并可选是否唤醒更高优先级任务。
 * @param xTaskToNotify 目标任务句柄。
 * @param ulValue 要设置的 32 位值。
 * @param eAction 更新方式。
 * @param pxHigherPriorityTaskWoken 若需要任务切换，则设为 pdTRUE。
 * @return 同 xTaskNotify()。
 * @see xTaskNotifyFromISRIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyFromISR( TaskHandle_t xTaskToNotify, uint32_t ulValue, eNotifyAction eAction, BaseType_t *pxHigherPriorityTaskWoken );
BaseType_t xTaskNotifyFromISRIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify, uint32_t ulValue, eNotifyAction eAction, BaseType_t *pxHigherPriorityTaskWoken );

/**
 * @brief 从中断中发送通知并查询原值。
 * @param xTaskToNotify 目标任务句柄。
 * @param ulValue 要设置的 32 位值。
 * @param eAction 更新方式。
 * @param pulPreviousNotifyValue 输出原值。
 * @param pxHigherPriorityTaskWoken 任务切换标志。
 * @return 同 xTaskNotify()。
 * @see xTaskNotifyAndQueryFromISRIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyAndQueryFromISR( TaskHandle_t xTaskToNotify, uint32_t ulValue, eNotifyAction eAction, uint32_t *pulPreviousNotifyValue, BaseType_t *pxHigherPriorityTaskWoken );
BaseType_t xTaskNotifyAndQueryFromISRIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToNotify, uint32_t ulValue, eNotifyAction eAction, uint32_t *pulPreviousNotifyValue, BaseType_t *pxHigherPriorityTaskWoken );

/* 3. 接收通知：阻塞等待并获取（可指定清除位） ------------------------------ */

/**
 * @brief 等待任务通知，可清除特定位，并返回接收到的通知值。
 * @param ulBitsToClearOnEntry 在等待前清除通知值中的这些位（通常设为 0x00）。
 * @param ulBitsToClearOnExit  成功获取通知后清除通知值中的这些位（通常设为 0xFFFFFFFF）。
 * @param pulNotificationValue 输出参数，存储收到通知时的通知值（可为 NULL）。
 * @param xTicksToWait 阻塞等待时间。
 * @return pdTRUE 成功收到通知，pdFALSE 超时。
 * @note 调用后通知状态会被自动清除（如果不使用位清除方式）。
 * @see xTaskNotifyWaitIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyWait( uint32_t ulBitsToClearOnEntry, uint32_t ulBitsToClearOnExit, uint32_t *pulNotificationValue, TickType_t xTicksToWait );
BaseType_t xTaskNotifyWaitIndexed( UBaseType_t uxIndexToWaitOn, uint32_t ulBitsToClearOnEntry, uint32_t ulBitsToClearOnExit, uint32_t *pulNotificationValue, TickType_t xTicksToWait );

/* 4. 状态与值管理 -------------------------------------------------------- */

/**
 * @brief 清除任务的通知状态（不改变通知值）。
 * @param xTaskToNotify 目标任务句柄。
 * @return pdTRUE 如果之前通知状态为挂起（pending），pdFALSE 否则。
 * @note 通常不需要手动调用，接收函数会自动清除。
 * @see xTaskNotifyStateClearIndexed() 用于指定通知索引。
 */
BaseType_t xTaskNotifyStateClear( TaskHandle_t xTaskToNotify );
BaseType_t xTaskNotifyStateClearIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToClear );

/**
 * @brief 清除任务通知值中的指定位，并返回清除前的通知值。
 * @param xTaskToNotify 目标任务句柄。
 * @param ulBitsToClear 要清除的位掩码。
 * @return 清除之前的通知值（整个 32 位）。
 * @note 此函数不改变通知状态（pending 标志）。
 * @see ulTaskNotifyValueClearIndexed() 用于指定通知索引。
 */
uint32_t ulTaskNotifyValueClear( TaskHandle_t xTaskToNotify, uint32_t ulBitsToClear );
uint32_t ulTaskNotifyValueClearIndexed( TaskHandle_t xTaskToNotify, UBaseType_t uxIndexToClear, uint32_t ulBitsToClear );
```

## 3 用法示例
```c
// 任务A：等待一个通知（类似 take 信号量）
void vTaskA(void *pv) {
    for(;;) {
        // 阻塞等待通知，收到后将通知值清零
        if(ulTaskNotifyTake(pdTRUE, portMAX_DELAY) != 0) {
            // 通知到达，执行操作
        }
    }
}

// 中断或任务B：发送通知
void vISR(void) {
    vTaskNotifyGiveFromISR(xTaskAHandle, NULL);
}
```