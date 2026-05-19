# 1.usb基础世界观
## 1.1 USB 里谁是主，谁是从
最重要的一句：

**USB 一定有 Host 和 Device。**

- Host
    - 电脑
    - 手机（某些 OTG 场景）
    - 负责发起枚举和总线管理
- Device
    - 你的 ESP32-S3 板子
    - 不能主动“想发就发”
    - 必须按 Host 规定的方式响应
## 1.2 usb不是串口
USB 是总线协议。  
串口只是 USB 上的一种**设备类表现形式**。
常见表现：
- CDC
    - 虚拟串口
    - 电脑上表现成 COM 口
- MSC
    - 大容量存储
    - 电脑上表现成 U 盘
- HID
    - 键盘、鼠标
- Audio
    - 麦克风、声卡
## 1.3 枚举是什么
你插上 USB 后，电脑不会立刻知道你是什么设备。  
它会做一套识别流程，这就叫**枚举**。

可以粗略理解成：

1. 设备插入
2. Host 复位总线
3. Host 读设备描述符
4. Host 读配置描述符
5. Host 知道你有几个接口、每个接口干什么
6. Host 加载对应驱动
7. 设备开始正常工作

所以“USB 插上没反应”，经常不是业务逻辑问题，而是：
- 描述符不对
- 类配置不对
- PHY / 供电 / 线材问题
- TinyUSB 没正确启动
# 2.usb的核心对象
所有 API 都是在操作这些对象。
## 2.1 Device / Configuration / Interface / Endpoint

你可以这样理解：

- Device
    - 整个 USB 设备
- Configuration
    - 设备的一个工作配置
- Interface
    - 一个功能块
- Endpoint
    - 数据收发通道
## 2.2 Endpoint是什么
