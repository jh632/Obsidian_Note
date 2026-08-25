# TinyUSB - 嵌入式 USB 协议栈

## 简介

TinyUSB 是一个开源的、跨平台的 USB Host/Device 协议栈，专为嵌入式系统设计。它具有内存安全（无动态分配）和线程安全（所有中断延迟到非 ISR 任务函数处理）的特点。

## 核心特点

- **线程安全**：所有 USB 中断延迟到任务上下文处理
- **内存安全**：无动态分配，所有缓冲区静态分配
- **可移植性**：支持 50+ MCU 家族
- **全面性**：包含 CDC、HID、MSC、Audio、Host 等支持
- **RTOS 友好**：支持裸机、FreeRTOS、RT-Thread、Mynewt

## 目录结构

```
├── docs          # 文档
├── examples      # 示例代码（支持 make 和 cmake 构建系统）
├── hw/
│   ├── bsp       # 支持的板级支持包
│   └── mcu       # MCU 底层驱动
├── lib           # 第三方库（FreeRTOS、FatFs 等）
├── src           # TinyUSB 核心源码
├── test          # 测试代码（单元测试、fuzzing、硬件测试）
└── tools         # 内部工具
```

## 架构设计

### 设备栈（Device Stack）

支持多种设备配置，可动态更改 USB 描述符，支持低功耗功能（suspend、resume、remote wakeup）。

### 主机栈（Host Stack）

支持多种 USB 设备类型，包括 HID、MSC、CDC 等。

### 电源传输栈（Power Delivery Stack）

支持 USB Type-C 和 PD3.0（WIP，目前仅支持 STM32 G4）。

## API 命名约定

TinyUSB 使用一致的函数前缀来组织 API：

- `tusb_`：核心栈函数（初始化、中断处理）
- `tud_`：设备栈函数（如 `tud_task()`、`tud_cdc_write()`）
- `tuh_`：主机栈函数（如 `tuh_task()`、`tuh_cdc_receive()`）
- `tu_`：内部工具函数（通常不用于应用）

## USB 传输类型

### 控制传输（Control Transfers）
- 用于设备配置和控制命令
- 双向通信（使用 IN 和 OUT）
- 所有设备必须支持端点 0 的控制传输
- 配置：`CFG_TUD_ENDPOINT0_SIZE`（通常 64 字节）

### 批量传输（Bulk Transfers）
- 用于大量数据，无保证时序要求
- 单向通信（独立的 IN 和 OUT 端点）
- 配置：`CFG_TUD_MSC_EP_BUFSIZE`、`CFG_TUD_CDC_EP_BUFSIZE`

### 中断传输（Interrupt Transfers）
- 用于小型、时间敏感的数据
- 保证最大延迟
- 轮询间隔：1ms 到 255ms
- 配置：`CFG_TUD_HID`、`CFG_TUD_HID_EP_BUFSIZE`

### 等时传输（Isochronous Transfers）
- 用于时间关键的流数据
- 无错误纠正（速度优先于可靠性）
- 用于音频、视频流

## 支持的 USB 类

### 设备类
- Audio Class 2.0 (UAC2)
- Bluetooth Host Controller Interface (BTH HCI)
- Communication Device Class (CDC)
- Device Firmware Update (DFU)
- Human Interface Device (HID)
- Mass Storage Class (MSC)
- Musical Instrument Digital Interface (MIDI)
- Media Transfer Protocol (MTP/PTP)
- Network (RNDIS, ECM, NCM)
- Test and Measurement Class (USBTMC)
- Video class 1.5 (UVC)
- Vendor-specific class

### 主机类
- Human Interface Device (HID)
- Mass Storage Class (MSC)
- Communication Device Class (CDC-ACM)
- Vendor serial over USB (FTDI, CP210x, CH34x, PL2303)
- Hub（多级支持）

## 集成步骤

### 1. 获取 TinyUSB
```bash
git clone https://github.com/hathach/tinyusb tinyusb
cd tinyusb
python tools/get_deps.py -b stm32h743eval  # 或指定板子
```

### 2. 添加源文件
将 `tinyusb/src/` 下所有 `.c` 文件添加到项目构建系统。

### 3. 配置 TinyUSB
创建 `tusb_config.h`，配置以下宏：
- `CFG_TUSB_MCU`：MCU 类型
- `CFG_TUSB_OS`：操作系统类型
- 类启用标志（如 `CFG_TUD_CDC`、`CFG_TUD_MSC`）

### 4. 配置 include 路径
添加 `your_project/tinyusb/src` 和 `tusb_config.h` 所在目录到 include 路径。

### 5. 实现 USB 描述符
实现 `tud_descriptor_*_cb()` 回调函数。

### 6. 初始化 TinyUSB
在时钟/外设就绪后调用 `tusb_init()`：
```c
tusb_rhport_init_t dev_init = {
    .role = TUSB_ROLE_DEVICE,
    .speed = TUSB_SPEED_HIGH
};
tusb_init(0, &dev_init);
```

### 7. 处理中断
在 USB ISR 中调用 `tusb_int_handler(rhport, true)`：
```c
void USB0_IRQHandler(void) {
    tusb_int_handler(0, true);
}
```

### 8. 运行 USB 任务
在主循环中定期调用 `tud_task()`（设备）或 `tuh_task()`（主机）。

### 9. 实现类回调
提供启用类的回调函数，如 `tud_cdc_rx_cb()`、`tuh_msc_mount_cb()`。

## STM32CubeIDE 集成

1. 在 STM32CubeMX 中启用 USB_OTG_FS/HS，设置为 "Device_Only" 模式
2. 在 NVIC Settings 中启用 USB 全局中断
3. 在 main.c 中包含 `tusb.h` 并调用 `tusb_init()`
4. 在主循环中调用 `tud_task()`
5. 在生成的 `stm32xxx_it.c` 中修改 USB IRQ handler：
```c
void OTG_FS_IRQHandler(void) {
    tud_int_handler(0);
}
```

## 配置选项

### tusb_config.h 关键宏
- `CFG_TUSB_MCU`：MCU 类型
- `CFG_TUSB_OS`：操作系统（0=无OS，1=FreeRTOS等）
- `CFG_TUSB_DEBUG`：调试级别（0-3）
- `CFG_TUD_ENABLED`：启用设备栈
- `CFG_TUH_ENABLED`：启用主机栈
- `CFG_TUD_CDC`：启用 CDC 类
- `CFG_TUD_MSC`：启用 MSC 类
- `CFG_TUD_HID`：启用 HID 类

### 优化选项
- 禁用未使用的类
- 设置 `CFG_TUSB_DEBUG = 0` 用于发布版本
- 使用 `-Os` 优化编译

## 调试

### 日志配置
通过 `LOG=level` 启用内置日志，支持 Segger RTT（10x 更快）。

### 常见问题
- **设备未识别**：检查 USB 描述符实现和 `tusb_config.h` 设置
- **枚举失败**：启用日志（`LOG=2`）并检查 USB 协议错误
- **硬故障/崩溃**：验证中断处理程序设置和堆栈大小分配

## 示例项目

### cdc_msc 示例
创建同时具有虚拟串口（CDC）和大容量存储（MSC）的 USB 设备。

### cdc_msc_hid 示例
创建可连接 CDC、MSC 或 HID 接口 USB 设备的 USB 主机。

## 参考资源

- 官方文档：https://docs.tinyusb.org/
- GitHub 仓库：https://github.com/hathach/tinyusb
- 支持的开发板：https://docs.tinyusb.org/en/stable/reference/supported_boards.html