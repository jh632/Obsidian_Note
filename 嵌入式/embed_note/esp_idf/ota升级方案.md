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

## 1.2 