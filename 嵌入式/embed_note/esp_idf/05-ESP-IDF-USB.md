---
tags: [esp-idf, esp32, usb, tinyusb, cdc, msc, hid]
date: 2026-09-01
aliases: [USB, TinyUSB, ESP32 USB, esp_tinyusb, USB协议]
---

# ESP-IDF USB

> 2026-09-01 由原《usb》整理结构化。USB 协议栈整体架构见 [[USB/USB协议栈架构]]、[[USB/USB设备的类型]]。

---

## 目录

1. [USB 基础世界观](#1-usb-基础世界观)
2. [USB 核心对象](#2-usb-核心对象)
3. [传输类型](#3-传输类型)
4. [ESP32 上的 USB 软件栈](#4-esp32-上的-usb-软件栈)
5. [CDC 模式](#5-cdc-模式)
6. [MSC 模式](#6-msc-模式)
7. [HID 模式](#7-hid-模式)

---

## 1. USB 基础世界观

### 1.1 谁是主，谁是从

最重要的一句：**USB 一定有 Host 和 Device。**

| 角色 | 例子 | 职责 |
|---|---|---|
| **Host** | 电脑、手机（某些 OTG 场景） | 发起枚举、总线管理 |
| **Device** | 你的 ESP32-S3 板子 | 不能主动"想发就发"，必须按 Host 规定的方式响应 |

### 1.2 USB 不是串口

USB 是总线协议。串口只是 USB 上的一种**设备类表现形式**：

| 设备类 | 表现 |
|---|---|
| CDC | 虚拟串口，电脑上表现成 COM 口 |
| MSC | 大容量存储，电脑上表现成 U 盘 |
| HID | 键盘、鼠标 |
| Audio | 麦克风、声卡 |

### 1.3 枚举是什么

插上 USB 后，电脑不知道你是什么设备，会做一套识别流程——**枚举**：

```
1. 设备插入
2. Host 复位总线
3. Host 读设备描述符
4. Host 读配置描述符
5. Host 知道你有几个接口、每个接口干什么
6. Host 加载对应驱动
7. 设备开始正常工作
```

> "USB 插上没反应"经常不是业务逻辑问题，而是：描述符不对 / 类配置不对 / PHY·供电·线材问题 / TinyUSB 没正确启动。

---

## 2. USB 核心对象

所有 API 都是在操作这些对象：

| 对象 | 理解 |
|---|---|
| **Device** | 整个 USB 设备 |
| **Configuration** | 设备的一个工作配置 |
| **Interface** | 一个功能块 |
| **Endpoint** | 数据收发通道 |

### Endpoint 是什么

Endpoint 不是"物理引脚"，而是**逻辑通道**。常见端点类型：

| 类型 | 说明 |
|---|---|
| Control | 枚举、控制请求（每个 USB 设备必有 EP0） |
| Bulk | 大块数据、可靠传输（CDC 数据、MSC 存储读写） |
| Interrupt | 短数据、保证最大延迟（鼠标、键盘） |
| Isochronous | 保证带宽、无重试（麦克风、摄像头） |

> Interrupt 本质：USB 通信是主机说了算，设备无法主动发送。设备在初始化时告诉主机"每 N 毫秒来问一次"，主机会准时查询设备是否有数据要发。

### 类驱动是什么

USB 类驱动就是"标准化角色"——你声明自己是 MSC，电脑就知道按 U 盘来跟你说话。
**"USB 模式切换"通常意味着重新枚举**，因为不是"功能开关变了"，而是"设备身份变了"。

---

## 3. 传输类型

| 传输类型 | 保证可靠性？ | 保证实时性/带宽？ | 数据流向 | 典型数据量 | 典型设备 |
|---|---|---|---|---|---|
| **控制 (Control)** | 是（有重试） | 否（优先级最低） | 双向 | 小（<64字节） | 所有设备（枚举和配置） |
| **批量 (Bulk)** | 是（有重试） | 否（会堵车） | 单向 | 大 | U盘、打印机、串口 |
| **中断 (Interrupt)** | 是（有重试） | 是（保证最大延迟） | 单向 | 小（几字节~几KB） | 鼠标、键盘 |
| **等时 (Isochronous)** | 否（无重试，丢则丢） | 是（保证带宽） | 单向 | 大 | 麦克风、摄像头 |

---

## 4. ESP32 上的 USB 软件栈

```
应用代码
  ↓
esp_tinyusb（ESP-IDF 对 TinyUSB 的封装）
  ↓
TinyUSB（底层 USB 设备协议栈，hathach/tinyusb）
  ↓
USB 硬件 PHY
```

TinyUSB 是底层 USB 设备协议栈；ESP-IDF 里的 `esp_tinyusb` 是它的上层封装。

### 4.1 关键 API：`tinyusb_driver_install`

```c
esp_err_t tinyusb_driver_install(const tinyusb_config_t *config);
```

本地头文件（tinyusb.h line 146）写明其职责：
- 初始化 USB 驱动
- 准备描述符
- 初始化 TinyUSB stack
- **创建并启动 USB 事件任务**

> 关键结论：**`tinyusb_driver_install()` 已经会创建 TinyUSB 任务。**

### 4.2 设备事件

| 事件 | 含义 |
|---|---|
| `TINYUSB_EVENT_ATTACHED` | 设备被主机接上 |
| `TINYUSB_EVENT_DETACHED` | 设备从主机断开 |

> 这不是 CDC 专属，也不是 MSC 专属，是 **USB 设备级**事件。

---

## 5. CDC 模式

### 5.1 CDC 是什么

CDC 最常见的用途就是**虚拟串口**：电脑上看起来像 COM 口，但底层并不是 UART 协议，而是 USB CDC 类。

### 5.2 CDC 典型坑

**坑 1：把字节流当报文**
CDC 收到的是字节流，不是天然分帧消息。必须自己做：半包拼接、粘包拆分、帧头同步。
> 底层细节：TinyUSB 会将字节流拆成多个 USB 数据包传输，回调里每次可能最多只读 64 字节——这是底层缓冲区限制，不影响逻辑上当作连续字节流读写。

**坑 2：DTR 不是装饰**
很多上位机串口工具只有真正打开串口后才拉 DTR。用 DTR 判断"业务是否可发"逻辑是对的。

**坑 3：CDC 不能拿来推导 MSC 状态**
CDC 的连接状态只代表 CDC。切到 MSC 后，CDC 那套状态就不该再当 USB 总真相。

---

## 6. MSC 模式

### 6.1 MSC 本质

MSC = Mass Storage Class。你不是"真的变成一块磁盘"，而是**模拟一块磁盘协议设备**。

电脑认为自己在访问 U 盘，实际背后可能是：SPI Flash、SD 卡、RAM Disk。

### 6.2 存储所有权

```c
TINYUSB_MSC_STORAGE_MOUNT_USB
TINYUSB_MSC_STORAGE_MOUNT_APP
```

| 宏 | 语义 |
|---|---|
| `MOUNT_USB` | 存储现在归主机（电脑在用） |
| `MOUNT_APP` | 存储现在归应用（ESP32 自己在用） |

---

## 7. HID 模式

HID = Human Interface Device。它不是"键盘鼠标专用类"，而是一个**通用报告通道**：

> 本质：主机和设备之间，通过**报告描述符**约定数据格式，然后用中断端点双向传输结构化的短数据。

可以用它做：
- 键盘、鼠标、游戏手柄
- 自定义控制面板（调音台按钮、快捷键小键盘）
- 绕过驱动直接传私有数据（无驱通信）

TinyUSB 里 HID 的关键：
- 一份**报告描述符**，告诉主机每个字节代表什么
- 一个**中断 IN 端点**给设备上报
- 一个可选的**中断 OUT 端点**给主机下发（如键盘 LED）

---

## 参考

- TinyUSB 源码仓库：https://github.com/hathach/tinyusb
- ESP-IDF USB 文档：https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/usb_device.html

## 相关笔记

- [[USB/USB协议栈架构]] — USB 协议栈整体架构
- [[USB/USB设备的类型]] — USB 设备类型
- [[USB/USB协议栈架构 图示]] — 架构图
- [[01-ESP-IDF-项目结构与构建工具]] — 构建与烧录
