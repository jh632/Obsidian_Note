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
1.编译后信息估算
```
Total image size: 1777048 bytes (.bin may be padded larger)
```
粗略估计
2.