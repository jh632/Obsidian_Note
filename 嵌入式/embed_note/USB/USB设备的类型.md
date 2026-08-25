根据USB-IF（USB开发者论坛）的定义，USB设备的类别（Class）由一个字节（8位）的“基类（Base Class）”代码表示。这意味着理论上最多可以有 **256 种**（0x00 到 0xFF）不同的基类。

不过，这其中的大部分数值是保留或未定义的。目前，USB-IF官方已定义并投入使用的基类（Base Class）有 **20 多种**。

以下是目前已定义的基类及其用途汇总：

| 基类代码 (Base Class) | 类别名称 (Class Name) | 典型设备示例 |
| :--- | :--- | :--- |
| **0x00** | 设备描述符中定义 (Device) | 表示设备的具体功能由其**接口描述符**来定义 |
| **0x01** | 音频 (Audio) | 声卡、USB麦克风、USB耳机 |
| **0x02** | 通信与CDC控制 (Communications and CDC Control) | 调制解调器、USB转串口适配器、USB网卡 |
| **0x03** | 人机接口设备 (HID) | **键盘、鼠标**、游戏手柄 |
| **0x05** | 物理接口设备 (Physical) | 力反馈摇杆等 |
| **0x06** | 图像 (Image) / 静止图像捕捉 (Still Imaging) | 扫描仪、数码相机（用于图像传输） |
| **0x07** | 打印机 (Printer) | 打印机 |
| **0x08** | 海量存储 (Mass Storage) | **U盘、移动硬盘** |
| **0x09** | 集线器 (Hub) | USB集线器 |
| **0x0A** | CDC数据 (CDC-Data) | 常与Class 0x02配合，用于数据传输 |
| **0x0B** | 智能卡 (Smart Card) | USB智能卡读卡器 |
| **0x0D** | 内容安全 (Content Security) | 用于数字版权管理（DRM）的设备 |
| **0x0E** | 视频 (Video) | **USB摄像头** |
| **0x0F** | 个人健康设备 (Personal Healthcare) | 血糖仪、血压计等 |
| **0x10** | 音视频设备 (Audio/Video Devices) | 集音频和视频功能于一体的设备 |
| **0x11** | 广告牌设备 (Billboard) | 用于描述USB-C Alternate Mode等功能的设备 |
| **0x12** | USB-C桥接设备 (USB Type-C Bridge) | 用于USB Type-C接口桥接的设备 |
| **0x3C** | I3C设备 (I3C Device) | 遵循I3C总线规范的设备 |
| **0xDC** | 诊断设备 (Diagnostic Device) | 用于设备诊断和调试 |
| **0xE0** | 无线控制器 (Wireless Controller) | 蓝牙等无线设备 |
| **0xEF** | 杂项 (Miscellaneous) | 用于包含多个接口的复合设备 |
| **0xFE** | 特定应用 (Application Specific) | 不适用标准类别的特定功能设备 |
| **0xFF** | 厂商自定义 (Vendor Specific) | 由设备制造商自己定义，无统一标准 |

> 完整的定义可参考USB-IF官网的[已定义类别代码](https://www.usb.org/defined-class-codes)页面。

简单来说，虽然理论上限是256种，但目前USB-IF官方定义并投入使用的基类有20多种。