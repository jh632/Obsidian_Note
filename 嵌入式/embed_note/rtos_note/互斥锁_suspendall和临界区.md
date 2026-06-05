## 互斥锁和临界区

互斥锁和临界区的实现与区别详见[[嵌入式八股文]]

## vTaskSuspendAll和xTaskResumeAll
`vTaskSuspendAll()` 的实现为:暂停调度器（Scheduler），但不关闭中断。
具体实现原理
```c
//vTaskSuspendAll() 函数非常简单，其核心操作仅仅执行
//++uxSchedulerSuspended;
//每次系统节拍中断（Systick）到来时，调度器都会检
//查 `uxSchedulerSuspended` 的值。只有当该值为 0（未挂起）时，它才会执行任
//务切换这个钩子机制是后续逻辑成立的基石。
```

恢复机制：xTaskResumeAll() 和 "一次性还清"
`xTaskResumeAll` 函数的实现比挂起复杂许多，它肩负着"结算"挂起期间所有欠账的任务[](https://www.programmersought.com/article/59219942660/)：

1. **计数器递减**：对 `uxSchedulerSuspended` 进行减 1 操作。如果结果不为 0，表示仍处于嵌套挂起中，函数直接返回，不做进一步处理[](https://www.programmersought.com/article/59219942660/)。
    
2. **处理挂起期间的就绪任务**：任何在调度器挂起期间就绪的任务（例如，由中断释放了信号量导致任务就绪），都不会被直接放入就绪链表，而是先被放入一个专门的临时链表 `xPendingReadyList` 中[](https://www.programmersought.com/article/59219942660/)。恢复时，调度器会**将这个链表中的所有任务，一次性全部转移到它们各自正确的就绪链表中**[](https://www.programmersought.com/article/59219942660/)。
    
3. **"一次性还清"系统节拍**：调用 `xTaskIncrementTick()` 的循环来"偿还"之前累积在 `uxPendedTicks` 里的所有节拍。**关键的是，这个循环并非简单地只增加节拍计数**，它会检查是否有任务因为 `vTaskDelay` 到期而需要就绪，并执行相应的链表移动操作。因此，这个"还债"过程是可能会很耗时的[](https://blog.csdn.net/2402_83411382/article/details/151804646)。
    
4. **最终抉择**：完成以上步骤后，调度器会再次检查系统中是否存在比当前任务**优先级更高的就绪任务**。如果存在，`xTaskResumeAll()` 会返回 `pdTRUE`，并**触发一次手动上下文切换**，让高优先级任务获得 CPU[](https://blog.csdn.net/2402_83411382/article/details/151804646)。
## 临界区 互斥锁 suspendall对比

| 维度          | 临界区 (`taskENTER_CRITICAL`) | 互斥锁 (`Mutex`)   | 调度器挂起 (`vTaskSuspendAll`) |
| ----------- | -------------------------- | --------------- | ------------------------- |
| 本质          | 关闭中断                       | 任务间资源锁          | 暂停调度器                     |
| 保护对象        | CPU执行流                     | 共享资源            | 调度器状态                     |
| 是否禁止任务切换    | ✔                          | 间接（拿不到锁会阻塞）     | ✔                         |
| 是否禁止中断      | ✔                          | ✘               | ✘                         |
| ISR能否运行     | ✘                          | ✔               | ✔                         |
| ISR能否访问保护资源 | 不建议                        | ❌（Mutex不能用于ISR） | ✔                         |
| 是否会阻塞任务     | ✘                          | ✔               | ✘                         |
| 是否发生上下文切换   | ✘                          | 可能              | 恢复时可能                     |
| 是否支持优先级继承   | ✘                          | ✔               | ✘                         |
| 持续时间        | 极短                         | 可长              | 中等                        |
| 适用范围        | 几条指令                       | 共享设备/共享数据       | 内核数据结构操作                  |
| 是否可嵌套       | ✔                          | ✔               | ✔                         |
| ISR中能否调用    | 部分端口支持 FromISR 版本          | ❌               | ❌                         |
| 实时性影响       | 最大                         | 较小              | 中等                        |