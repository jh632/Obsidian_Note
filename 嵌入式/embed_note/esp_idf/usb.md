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
Endpoint 不是“物理引脚”，而是逻辑通道。
常见端点类型：
- Control
- Bulk
- Interrupt
- Isochronous
### Control Endpoint
- 用于枚举、控制请求
- 每个 USB 设备必有 EP0
### Bulk Endpoint

- 大块数据，可靠传输
- 典型用于：
    - CDC 数据
    - MSC 存储读写
### Interrupt Transfer
`USB 通信是**主机(PC)说了算**，设备无法主动发送数据。中断传输的机制是：设备在初始化时告诉主机“我需要每隔 **N 毫秒** 被询问一次”。主机会严格遵守这个时间间隔，准时来查询设备是否有数据要发。`

|传输类型|保证可靠性？|保证实时性/带宽？|数据流向|典型数据量|典型设备|
|---|---|---|---|---|---|
|**控制 (Control)**|**是** (有重试)|否 (优先级最低)|双向|小 (< 64字节)|**所有设备** (用于枚举和配置)|
|**批量 (Bulk)**|**是** (有重试)|**否** (会堵车)|单向|大|U盘、打印机、串口|
|**中断 (Interrupt)**|**是** (有重试)|**是** (保证最大延迟)|单向|小 (几字节 ~ 几KB)|鼠标、键盘|
|**等时 (Isochronous)**|**否** (无重试，丢则丢)|**是** (保证带宽)|单向|大|麦克风、摄像头|
### Isochronous Transfer(等时传输)

## 2.3 类驱动是什么
USB 类驱动就是“标准化角色”。
比如：
- 你声明自己是 MSC
- 电脑就知道按 U 盘来跟你说话
这就是为什么“USB 模式切换”通常意味着**重新枚举**。  
因为你不是“功能开关变了”，而是“设备身份变了”。

# 3.ESP32 上的 USB 软件栈
esp_tinyusb是对Tinyusb的封装
[hathach/tinyusb: An open source cross-platform USB stack for embedded system](https://github.com/hathach/tinyusb)
## 3.1 Tinyusb干了什么
TinyUSB 是底层 USB 设备协议栈。  
ESP-IDF 里的 esp_tinyusb 是它的上层封装。
你现在最关键的 API：
`esp_err_t tinyusb_driver_install(const tinyusb_config_t *config);`
本地头文件已经写得很清楚：
- 初始化 USB 驱动
- 准备描述符
- 初始化 TinyUSB stack
- 创建并启动 USB 事件任务
见 tinyusb.h (line 146)
这句话非常关键：
**tinyusb_driver_install() 已经会创建 TinyUSB 任务。**
## 3.2 设备事件
- TINYUSB_EVENT_ATTACHED
- TINYUSB_EVENT_DETACHED
见 tinyusb.h (line 105)

它们表示：
- 设备被主机接上
- 设备从主机断开
这不是 CDC 专属，也不是 MSC 专属，是**USB 设备级**事件。
# 4.CDC模式怎么理解
## 4.1 cdc是什么
CDC 最常见的用途就是虚拟串口。  
电脑上看起来像 COM 口，但底层并不是 UART 协议，而是 USB CDC 类。
## 4.2 cdc典型坑
### 坑 1：把字节流当报文

CDC 收到的是字节流，不是天然分帧消息。

所以必须自己做：

- 半包拼接
- 粘包拆分
- 帧头同步
**一个重要的细节：缓冲区**

虽然CDC传输的是字节流，但TinyUSB底层会将字节流拆分成多个USB数据包进行传输。为了提高效率，TinyUSB内部以及ESP-IDF等框架通常会使用**缓冲区（Buffer）**来暂存数据。

例如，你可能遇到在回调函数里每次最多只能读取64字节的情况，这通常就是底层缓冲区大小限制导致的[](https://bbs.elecfans.com/jishu_2433730_1_1.html#lastpost)。但这属于底层实现的优化，不影响你从逻辑上将其视为连续的字节流进行读写。
### 坑 2：DTR 不是装饰

很多上位机串口工具只有真正打开串口后才拉 DTR。  
你如果用 DTR 判断“业务是否可发”，逻辑是对的。

### 坑 3：CDC 不能拿来推导 MSC 状态

CDC 的连接状态只代表 CDC。  
切到 MSC 后，CDC 那套状态就不该再拿来当 USB 总真相。

## 5.MSC怎么理解
# 5.1 MSC本质是什么
MSC = Mass Storage Class。  
你不是“真的变成一块磁盘”，而是**模拟一块磁盘协议设备**。

电脑认为自己在访问 U 盘。  
实际上背后可能是：
- SPI Flash
- SD 卡
- RAM Disk
你现在项目里是 SPI Flash FAT 分区。
## 5.2 存储所有权
```c
TINYUSB_MSC_STORAGE_MOUNT_USB
TINYUSB_MSC_STORAGE_MOUNT_APP
```
它的语义是：
- MOUNT_USB
    - 存储现在归主机
    - 电脑在用它
- MOUNT_APP
    - 存储现在归应用
    - ESP32 自己在用它