---
date: 2026-06-16
tags: [i2c-bus, communication-protocol, embedded]
aliases: [I2C-协议, I2C-protocol]
---

# I2C 协议

## 概述

I2C (Inter-Integrated Circuit) 是由 Philips 在 1980 年代开发的一种**同步、半双工、多主机**的串行通信总线。它只需要 **SCL（时钟线）** 和 **SDA（数据线）** 两根线即可挂载多个从设备，每个设备通过唯一的 7 位或 10 位地址区分。因其引脚少、接线简单，I2C 是嵌入式系统中极常用的片间通信协议，广泛应用于 EEPROM、传感器、ADC/DAC、RTC 等外设。

## 引脚定义

| 信号 | 方向 | 说明 |
|---|---|---|
| SCL | 主机输出 | Serial Clock — 由主机驱动，同步数据传输 |
| SDA | 双向开漏 | Serial Data — 主机和从机都可以拉低，数据双向传输 |
| VCC / GND | 电源 | 供电和参考地，非总线信号但必须接 |

SCL 和 SDA 均为 **开漏（open-drain）** 结构，必须外接上拉电阻到 VCC。

## 工作原理

### 空闲状态
SCL 和 SDA 都被上拉电阻拉到高电平（VCC）。总线空闲时两根线都是高。

### 时序基础

```
       起始条件           数据位传输             停止条件
                       
SCL    ┌──┐  ┌──┐  ┌──┐    ┌──┐  ┌──┐  ┌──┐    ┌──┐
       │  │  │  │  │  │ ... │  │  │  │  │  │    │  │
       ┘  └──┘  └──┘  └──  ┘  └──┘  └──┘  └──  ┘  └─────
       
SDA  ──┘                       ┌──┐           ┌──────────
                               │  │           │
       ────────────────────────┘  └───────────┘
       ^                       ^   ^           ^
       SDA先拉低               SCL低时SDA变化  SDA释放为高
       然后SCL拉低             SCL高时读取SDA
```

### 起始条件 (START Condition)
SCL 为高电平时，SDA 从高电平切换到低电平。这是一个**电平跳变信号**，表示总线事务开始。

> START 条件是总线的"注意"信号。任何从机看到这个跳变就知道要准备收地址了。

### 停止条件 (STOP Condition)
SCL 为高电平时，SDA 从低电平切换到高电平。表示总线事务结束，总线释放为空闲状态。

### 数据位传输
每个数据位在 SCL 的一个时钟周期内传输：
- **SCL 低电平期间**：SDA 可以变化（发送方设置数据）
- **SCL 高电平期间**：SDA 必须保持稳定（接收方采样读取）

### ACK / NACK
每传输完 **8 位数据**（一个字节）后，接收方在第 9 个 SCL 时钟周期拉低 SDA 表示 **ACK**（确认），或不拉低（保持高）表示 **NACK**（非确认）。

| 信号 | 含义 | 典型场景 |
|---|---|---|
| ACK (SDA 低) | 字节已收到，继续 | 正常传输 |
| NACK (SDA 高) | 未收到/无法接收/无此设备 | 地址无应答、接收方忙、传输结束 |

### 7 位地址读写流程

一个完整的 I2C 事务由以下步骤组成：

```
主机写流程:
┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────┐
│ START   │→ │ 地址+R/W │→ │ 等待从机ACK  │→ │ 数据字节 │→ │ STOP     │
│(SDA↓高) │  │ (1字节)  │  │ (第9 SCL)    │  │(1+N字节) │  │(SDA↑高)  │
└─────────┘  └──────────┘  └──────────────┘  └─────────┘  └──────────┘
                  ↓
            地址高7位 + R/W位
            (R/W=0 表示写)

主机读流程:
┌─────────┐  ┌──────────┐  ┌──────┐  ┌──────────┐  ┌──────┐  ┌─────────┐
│ START   │→ │ 地址+R/W │→ │ ACK  │→ │ 从机发数据│→ │ NACK │→ │ STOP    │
│(SDA↓高) │  │ (R/W=1)  │  │      │  │ (1+N字节)│  │(结束)│  │(SDA↑高) │
└─────────┘  └──────────┘  └──────┘  └──────────┘  └──────┘  └─────────┘
```

**写一字节流程 (以 AT24C02 EEPROM 为例，设备地址 0x50):**

1. 主机发送 START
2. 主机发送 0xA0 (7 位地址 0x50 + W=0)
3. 从机应答 ACK
4. 主机发送内部寄存器地址（如 0x00）
5. 从机应答 ACK
6. 主机发送要写入的数据字节
7. 从机应答 ACK
8. 主机发送 STOP

**读一字节流程:**

1. 主机发送 START
2. 主机发送 0xA0 (地址 + W)
3. 从机应答 ACK
4. 主机发送要读取的寄存器地址
5. 从机应答 ACK
6. 主机发送 **RESTART**（即再次发送 START）
7. 主机发送 0xA1 (地址 + R=1)
8. 从机应答 ACK
9. 从机发送数据字节
10. 主机发送 NACK（通知从机不再需要数据）
11. 主机发送 STOP

> 为什么读之前要先写一次地址？因为 EEPROM 内部有地址指针，要先通过"伪写"把指针设到目标位置，然后再读。

## 速率模式

| 模式                          | 最大速率       | 典型 SCL 频率 | 说明                 |
| --------------------------- | ---------- | --------- | ------------------ |
| 标准模式 (Standard Mode)        | 100 kbit/s | 100 kHz   | 最早的 I2C 速率，兼容性最好   |
| 快速模式 (Fast Mode, FM)        | 400 kbit/s | 400 kHz   | 最常见的速率，多数现代传感器支持   |
| 快速+模式 (Fast Mode Plus, Fm+) | 1 Mbit/s   | 1 MHz     | 驱动能力更强，可驱动更大总线电容   |
| 高速模式 (High-Speed Mode, Hs)  | 3.4 Mbit/s | 3.4 MHz   | 需要额外的电流源上拉，主机有特殊协议 |
| 超快速模式 (Ultra Fast, UFm)     | 5 Mbit/s   | 5 MHz     | 单向传输（不再需要 ACK），非开漏 |

实际应用中 **400 kHz 快速模式** 是性能和可靠性的最佳平衡点，绝大多数嵌入式项目使用此模式。

## 上拉电阻选择

上拉电阻的取值需要平衡**上升时间**和**电流消耗**。

### 阻值范围
- **最小值限制**：由输出驱动器的灌电流能力决定。电阻太小 → SDA/SCL 无法拉低到逻辑 0 的阈值。
  - 常规 I2C 引脚：`R_min ≈ (VCC - Vol_max) / Iol_max`
  - 典型值：**1.6 kΩ** (Vol=0.4V, Iol=3mA 时)
- **最大值限制**：由总线电容决定上升时间。电阻太大 → 信号上升沿太慢，波形畸变。
  - `R_max ≈ Tr_max / (0.8473 × Cb)` — Tr_max = 1 μs (快速模式)
  - 典型值：**4.7 kΩ 到 10 kΩ**

### 经验选值

| VCC  | 标准模式 (400 pF)  | 快速模式 (200 pF)   | 备注                 |
| ---- | -------------- | --------------- | ------------------ |
| 1.8V | 4.7 kΩ         | 2.2 kΩ          | 低电压、较多设备用 4.7k     |
| 3.3V | 4.7 kΩ ~ 10 kΩ | 2.2 kΩ ~ 4.7 kΩ | **4.7k 是通用值**      |
| 5.0V | 4.7 kΩ ~ 10 kΩ | 4.7 kΩ          | 5V 系统上升沿更陡，稍大的电阻也可 |

> **4.7 kΩ** 是嵌入式 I2C 中最通用的上拉电阻值，适用于绝大多数 3.3V / 5V 的标准和快速模式场景。不确走时用 4.7k 不会有大问题。
> 如果总线上只有 1-2 个设备且走线很短（<10 cm），10 kΩ 也完全可以使用，且更省电。

## 多主机仲裁

I2C 支持多个主机共享同一总线，这是它相比 SPI 的重要优势。

### 仲裁过程
1. **SCL 线或逻辑**：多个主机各自产生 SCL，但 SCL 是开漏 + 上拉，只要有一个主机拉低 SCL，SCL 就是低 —— 这自动同步了所有主机到最慢的那个。
2. **SDA 竞争**：多个主机在 SDA 上同时发送数据。每个主机发送数据位的同时会监控 SDA 实际电平。
3. **决定胜负**：如果某主机试图拉高 SDA（发 1）但检测到 SDA 实际为低（被另一个试图拉低的机器控制），它就**知道自己输了**，立即停止驱动 SDA，退出竞争。
4. **胜者继续**：赢得仲裁的主机继续完成整个事务，不影响任何从机。

```
主机A(发送 0b1010...):  ──高──┐  ┌──┐  ┌──┐  ┌──
                              │  │  │  │  │  │
主机B(发送 0b1001...):  ──高──┘  └──┘  └──┘  └──
                              ↑此处B要发1但SDA被A拉低 → B失利退出
```

### 仲裁规则
- **数据低电平优先**：发送低电平的主机总是赢得仲裁。
- **地址和数据的仲裁无区别**：可以在地址阶段或数据阶段仲裁，机制完全相同。
- **丢失仲裁的主机**必须释放 SDA 和 SCL，等待下一次总线空闲后再重试。

> 多主机仲裁是 I2C 的核心特性之一。它不像 CAN 的 CSMA/CD 那样需要冲突检测窗口，I2C 的"线或 + 监听"结构天然解决了这个问题。

## 应用要点

- **速率选择**：400 kHz 是通用最优解。如果线缆很长（>20 cm）或设备较多，降回 100 kHz 更可靠。
- **上拉电阻**：不确定时用 **4.7 kΩ**。如果总线设备很多（>8 个），需要更小的电阻（~2.2 kΩ）以对抗更大的总线电容。
- **电平转换**：不同 VCC 的 I2C 设备需要电平转换。专用 I2C 电平转换器（如 PCA9306）或使用分立 MOS 管搭建。
- **SDA/SCL 不要接反**：接反后设备会完全无法通信，示波器上 SCL 无时钟 —— 这是最常见的低级错误。
- **软件模拟 vs 硬件 I2C**：
  - 硬件 I2C：CPU 负担小、速率稳定，但引脚固定
  - GPIO 模拟：任意引脚可用、调试方便，但占用 CPU。低频场景（100 kHz）下效果很好。
- **10 位地址**：少数场景使用，在 7 位地址后扩展。前 5 位固定为 11110，后跟高 2 位地址 + R/W，再加剩余 8 位地址。日常使用很少见。



## 代码示例：软件模拟 I2C 读写 AT24C02

以下是用 GPIO 模拟 I2C 时序读写 AT24C02 EEPROM 的 C 代码示例。假设 SDA 接 GPIO 1，SCL 接 GPIO 2。

```c
#include <stdint.h>

/* ============ GPIO 模拟层 ============ */
/* 实际使用时替换为平台 HAL 调用 */
#define SDA_GPIO  1
#define SCL_GPIO  2

static void gpio_set(int pin, int val) { /* 写 GPIO 电平 */ }
static int  gpio_get(int pin)           { return 0; }
static void gpio_dir(int pin, int out)  { /* 设置 GPIO 方向 */ }

/* ============ I2C 时序原语 ============ */
#define I2C_DELAY 5   /* ~100 kHz 标准模式 */

static inline void sda_out(void)    { gpio_dir(SDA_GPIO, 1); }
static inline void sda_in(void)     { gpio_dir(SDA_GPIO, 0); }
static inline void scl_high(void)   { gpio_set(SCL_GPIO, 1); }
static inline void scl_low(void)    { gpio_set(SCL_GPIO, 0); }
static inline void sda_high(void)   { gpio_set(SDA_GPIO, 1); }
static inline void sda_low(void)    { gpio_set(SDA_GPIO, 0); }
static inline int  sda_read(void)   { return gpio_get(SDA_GPIO); }

static void i2c_start(void)
{
    sda_out();
    sda_high();
    scl_high();
    delay_us(I2C_DELAY);
    sda_low();            /* SCL 高时 SDA 下降沿 -> START */
    delay_us(I2C_DELAY);
    scl_low();
}

static void i2c_stop(void)
{
    sda_out();
    sda_low();
    scl_high();
    delay_us(I2C_DELAY);
    sda_high();           /* SCL 高时 SDA 上升沿 -> STOP */
    delay_us(I2C_DELAY);
}

static int i2c_write_byte(uint8_t byte)
{
    int ack;
    sda_out();
    for (int i = 7; i >= 0; i--) {
        if (byte & (1 << i)) sda_high();
        else                 sda_low();
        scl_high();  delay_us(I2C_DELAY);
        scl_low();   delay_us(I2C_DELAY);
    }
    /* 释放 SDA，等待从机 ACK */
    sda_in();
    scl_high();  delay_us(I2C_DELAY / 2);
    ack = sda_read();     /* 0 = ACK, 1 = NACK */
    scl_low();   delay_us(I2C_DELAY);
    return ack;
}

static uint8_t i2c_read_byte(int send_nack)
{
    uint8_t byte = 0;
    sda_in();
    for (int i = 7; i >= 0; i--) {
        scl_high();  delay_us(I2C_DELAY / 2);
        if (sda_read()) byte |= (1 << i);
        scl_low();   delay_us(I2C_DELAY);
    }
    /* 主机发送 ACK 或 NACK */
    sda_out();
    if (send_nack) sda_high();   /* NACK */
    else           sda_low();    /* ACK */
    scl_high();  delay_us(I2C_DELAY);
    scl_low();   delay_us(I2C_DELAY);
    sda_in();
    return byte;
}

/* ============ AT24C02 读写 ============ */
#define AT24C02_ADDR   0x50       /* 7 位设备地址 */

int eeprom_write_byte(uint16_t addr, uint8_t data)
{
    int ack;
    i2c_start();
    ack = i2c_write_byte((AT24C02_ADDR << 1) | 0);  /* + W */
    if (ack) { i2c_stop(); return -1; }
    ack = i2c_write_byte(addr & 0xFF);               /* 内部地址 */
    if (ack) { i2c_stop(); return -1; }
    ack = i2c_write_byte(data);                      /* 数据 */
    if (ack) { i2c_stop(); return -1; }
    i2c_stop();
    delay_us(5000);                                  /* 写周期 ~5ms */
    return 0;
}

int eeprom_read_byte(uint16_t addr, uint8_t *out)
{
    int ack;
    /* 阶段 1: 伪写，设置内部地址指针 */
    i2c_start();
    ack = i2c_write_byte((AT24C02_ADDR << 1) | 0);  /* + W */
    if (ack) { i2c_stop(); return -1; }
    ack = i2c_write_byte(addr & 0xFF);
    if (ack) { i2c_stop(); return -1; }
    /* 阶段 2: RESTART + 读 */
    i2c_start();                                     /* RESTART */
    ack = i2c_write_byte((AT24C02_ADDR << 1) | 1);  /* + R */
    if (ack) { i2c_stop(); return -1; }
    *out = i2c_read_byte(1);                         /* NACK 结束 */
    i2c_stop();
    return 0;
}
```

> 以上代码是教学演示用途。实际产品中建议用 MCU 的硬件 I2C 外设（如 ESP32 的 i2c_master_write 或 STM32 的 HAL I2C 驱动），速率和可靠性都更好。但理解 GPIO 模拟的每一行才能真正掌握 I2C 时序。


## 参考

- NXP I2C-bus specification and user manual (UM10204)
- AT24C02 / AT24C256 datasheet (典型 I2C EEPROM)
- Wikipedia: I2C

## 相关笔记

- [[can总线]]
- [[modbus]]
- [[embed_note/esp_idf/04-ESP-IDF-WiFi与网络]]
