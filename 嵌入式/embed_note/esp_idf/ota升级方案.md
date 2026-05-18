# 1 ota分区方案
## 1.1 常见ota分区表

```csv
# Name,     Type, SubType, Offset,   Size
nvs,        data, nvs,     0x9000,   0x6000
otadata,    data, ota,     0xf000,   0x2000
phy_init,   data, phy,     0x11000,  0x1000
factory,    app,  factory, 0x20000,  1M
ota_0,      app,  ota_0,   ,         2M
ota_1,      app,  ota_1,   ,         2M
```

| 分区         | 作用                |
| ---------- | ----------------- |
| `factory`  | 出厂固件，可选           |
| `ota_0`    | OTA 固件槽位 0        |
| `ota_1`    | OTA 固件槽位 1        |
| `otadata`  | 记录当前应该启动哪个固件槽位    |
| `nvs`      | 保存 Wi-Fi、配置、设备参数等 |
| `phy_init` | RF 校准相关数据         |
factory可取消,程序运行在ota1或者ota2

## 1.2 otadata作用是什么
`otadata` 不是存放固件的地方，它只存放 **启动选择信息**。

你可以把它理解成一个启动指针：
```
otadata = 当前应该启动 ota_0
```
或者：
```
otadata = 当前应该启动 ota_1
```
启动时：
```
bootloader 读取 otadata    
	↓
知道应该启动 ota_0 还是 ota_1   
    ↓
加载对应 app
```
OTA 成功后，应用程序会调用类似下面的逻辑：
```
esp_ota_set_boot_partition(update_partition);esp_restart();
```
这一步本质上就是：
```
修改 otadata告诉 bootloader 下次启动新固件
```
`官方分区表文档说明，data/ota 分区用于存储当前选中的 OTA app slot 信息，通常大小应为 0x2000 字节。`
## 1.3 ota分区大小如何估算

```
Total image size: 1777048 bytes (.bin may be padded larger)
```
# 2 espidf ota升级api
## 2.1 分区查询与引导控制

| 函数                                        | 功能                                                                    |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `esp_ota_get_next_update_partition(NULL)` | 获取应该被写入的**非活动 OTA 分区**（即 `ota_1` 或 `ota_0`）。这是 `esp_ota_begin` 需要的参数。 |
| `esp_ota_get_running_partition()`         | 获取**当前正在运行**的分区。                                                      |
| `esp_ota_get_boot_partition()`            | 获取**下次启动**时 Bootloader 会引导的分区（可能与运行分区不同）。                             |
| `esp_ota_set_boot_partition(partition)`   | **设置下次启动的分区**。在所有数据写入并验证成功后调用，让系统重启后进入新固件。                            |
## 2.2 固件写入流程

这是升级链路的执行核心，三个函数必须按顺序调用。

| 函数                                              | 功能                                                           |
| ----------------------------------------------- | ------------------------------------------------------------ |
| `esp_ota_begin(partition, image_size, &handle)` | 初始化 OTA 写入会话。传入目标分区和预期固件总大小（可传 `OTA_SIZE_UNKNOWN`），获得写入句柄。   |
| `esp_ota_write(handle, data, data_len)`         | 向分区写入一块数据。可循环调用，传入你从任意接口接收到的固件块。**必须在 `esp_ota_begin` 后调用**。 |
| `esp_ota_end(handle)`                           | 结束写入会话，会进行**校验和验证**（如检查镜像完整性）。**验证通过后，该分区才会被标记为可用**。         |
## 2.3 回滚与安全确认
| 函数                                               | 功能                                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| `esp_ota_mark_app_valid_cancel_rollback()`       | **必须在新固件中调用**。一旦新固件启动并完成核心功能自检，调用此函数将分区状态从 `PENDING_VERIFY` 改为 `VALID`，阻止自动回滚。 |
| `esp_ota_mark_app_invalid_rollback_and_reboot()` | **立即主动触发回滚并重启**。如果新固件自检发现严重错误，可主动调用此函数，放弃当前固件并返回旧版本。                           |
