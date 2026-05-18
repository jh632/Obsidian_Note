## 1 CAN 总线基础与硬件层
### 1 can是什么
CAN 全称：

```
Controller Area Network
```

中文一般叫：

```
控制器局域网
```

它最早主要用于汽车电子，让汽车里多个控制器互相通信
一句话理解：

> CAN 是一种适合多个控制器在强干扰环境下可靠通信的总线协议。
### 2 can的通信思维
CAN 不只是“差分线”，它还包含很强的数据链路层机制。

CAN 天然支持：

```
多个节点挂在同一条总线上每个节点都可以主动发送多个节点同时发送时自动仲裁发送错误时自动检测必要时自动重发严重错误时节点自动退出总线
```

也就是说 CAN 不是简单地“发字节流”，而是发一条一条的 **报文 Message**。

例如：

```
ID = 0x101, Data = 电池电压
ID = 0x102, Data = 电池电流
ID = 0x201, Data = 电机转速
ID = 0x301, Data = 故障状态
```

重点：

> CAN 不是“发给某个设备地址”，而是“广播一个带 ID 的消息”。
### 3 can的通信模型
CAN 总线上的所有节点都接在同一对线上：
```
120Ω                                        120Ω
CAN_H ======================================= CAN_H
CAN_L ======================================= CAN_L
        |             |              |
      节点A          节点B           节点C
```

#### 3.1 多主通信
CAN 不是传统主从结构。

任何节点都可以主动发送。

CAN 是：

```
谁有重要消息，谁就可以发
```

#### 3.2 仲裁机制
如果两个 CAN 节点同时发送，会发生什么？
CAN 不会像普通总线一样直接乱掉，而是会做 **仲裁**。

CAN 的规则是：
```
ID 越小，优先级越高
```

例如：
```
节点 A 发送 ID = 0x100节点 B 发送 ID = 0x200
```

结果：
```
0x100 优先级更高节点 A 继续发送节点 B 自动停止，稍后重发
```

关键点：

> CAN 的仲裁是无损仲裁，高优先级报文不会被破坏。

这对实时控制很重要。

例如故障报文：

```
ID = 0x001
```

普通状态报文：

```
ID = 0x300
```

如果二者同时发送，故障报文会优先发出去。

#### 3.3 硬件错误检测
CAN 硬件层面内置很多错误检测机制，例如：

```
CRC 错误
ACK 错误
格式错误
位错误
填充错误
```

普通 UART 只给你一个字节流，最多有奇偶校验，工程上很多错误处理要自己写。

CAN 控制器会自动帮你处理很多事情。

#### 3.4 错误节点自动隔离
CAN 节点有错误状态管理。

常见状态：

```
Error ActiveError PassiveBus Off
```

如果某个节点一直出错，它可能进入 Bus Off 状态，暂时退出总线，避免它继续破坏通信。

这个机制在汽车和工业场景很关键。

### **7 can的硬件组成**

一个 MCU 要接 CAN，一般需要两部分：

```
CAN 控制器
CAN 收发器
```

结构如下：

```
MCU 内部 CAN 控制器
        |
        | CAN_TX / CAN_RX
        |
CAN 收发器芯片
        |
        | CAN_H / CAN_L
        |
CAN 总线
```

#### 7.1 can 控制器是什么？

CAN 控制器负责：

```
生成 CAN 帧
解析 CAN 帧
处理仲裁
处理 CRC
处理 ACK
处理错误状态
提供发送邮箱
提供接收 FIFO
```

很多 MCU 内部自带 CAN 控制器。

例如：

| 平台              | CAN 控制器名称 |
| --------------- | --------- |
| STM32F103       | bxCAN     |
| STM32G4/H7 部分型号 | FDCAN     |
| ESP32           | TWAI      |
| NXP MCU         | FlexCAN   |
| GD32 部分型号       | CAN       |

注意 ESP32 里一般不叫 CAN，而叫：

```
TWAI = Two-Wire Automotive Interface
```

它兼容 CAN 2.0。
#### 7.2 can 收发器是什么

CAN 控制器输出的通常是 MCU 逻辑电平，比如：

```
TXD / RXD3.3V 或 5V 逻辑
```

但真正总线上的信号是：

```
CAN_H / CAN_L 差分信号
```

所以中间需要一个 CAN 收发器。

常见芯片：

| 收发器        | 电压   | 说明           |
| ---------- | ---- | ------------ |
| TJA1050    | 5V   | 常见高速 CAN 收发器 |
| MCP2551    | 5V   | 老牌 CAN 收发器   |
| SN65HVD230 | 3.3V | ESP32 常用     |
| TJA1042    | 5V   | 工业/汽车常见      |
| VP230      | 3.3V | 常见模块用芯片      |
### 8 CAN_H 和 CAN_L 的电平逻辑
CAN 总线上有两种状态：

```
显性位 dominant
隐性位 recessive
```

你先记住：

```
显性位 = 0
隐性位 = 1
```

#### 8.1 隐性位 Recessive
隐性位时：

```
CAN_H ≈ 2.5V
CAN_L ≈ 2.5V
差分电压 ≈ 0V
```

也就是两根线电压差不多。

表示：

```
逻辑 1
```
#### 8.2 显性位 Dominant
显性位时：

```
CAN_H ≈ 3.5V
CAN_L ≈ 1.5V
差分电压 ≈ 2V
```

表示：

```
逻辑 0
```

## 2 CAN 帧格式、仲裁、ACK、错误机制
### 1 CAN的数据帧格式:
```
ID + 控制信息 + 数据 + CRC + ACK + 结束位
```

通常开发需要配置的项
```c
typedef struct {
    uint32_t id;       // CAN ID
    uint8_t  dlc;      // data length code
    uint8_t  data[8];  // payload
} can_frame_t;
```

### 2 CAN 标准帧和扩展帧
| 类型  |  ID 长度 |                     ID 范围 | 说明      |
| --- | -----: | ------------------------: | ------- |
| 标准帧 | 11 bit |           `0x000 ~ 0x7FF` | 最常用     |
| 扩展帧 | 29 bit | `0x00000000 ~ 0x1FFFFFFF` | ID 空间更大 |
#### 2.1 标准帧
标准帧 ID 是 11 位。

例如：

```
0x100
0x101
0x200
0x7FF
```

常见工程里会定义：

```
#define CAN_ID_BAT_VOLTAGE     0x101
#define CAN_ID_BAT_CURRENT     0x102
#define CAN_ID_MOTOR_SPEED     0x201
#define CAN_ID_FAULT_STATUS    0x301
```
#### 2.2拓展帧
扩展帧 ID 是 29 位。

例如：

```
0x18FF50E50
x0CF00400
```

一些行业协议会大量使用扩展帧，比如：

```
SAE J1939部分新能源/商用车协议部分工业自定义协议
```

入门阶段你优先掌握标准帧，后面再看扩展帧。
### 3 经典 CAN 数据帧结构
标准帧
```
SOF
Arbitration Field
Control Field
Data Field
CRC Field
ACK Field
EOF
```

简化理解
```
帧起始 + ID(id+RTR) + DLC + DATA + CRC + ACK + 帧结束
```
#### 3.1 SOF:帧起始
总线从空闲状态的隐性位 `1` 被拉成显性位 `0`，大家就知道一帧开始了。
#### 3.2 Arbitration Field：仲裁段
仲裁段是 CAN 的核心。

标准帧仲裁段主要包含：

```
11-bit ID + RTR
```

其中最重要的是：

```
ID
```

CAN ID 有两个作用：

```
1. 表示消息含义
2. 决定仲裁优先级
```

***CAN ID 本身不是固定含义，具体怎么定义由你的上层协议决定。***
ID越小,优先级越高
#### 3.3 RTR：数据帧和远程帧

##### 3.3.1 数据帧

数据帧就是正常发送数据：

```
ID = 0x101DLC = 2DATA = 0x12 0x34
```

实际工程里最常见。

---

##### 3.3.2 远程帧

远程帧不是携带数据，而是请求别人发送某个 ID 的数据。

例如节点 A 发：

```
ID = 0x101RTR = 1
```

意思是：

```
谁负责 0x101 这条数据，请发出来
```

不过现代工程里远程帧用得比较少。

很多系统更喜欢周期上报或者应用层请求响应。

你先记住：

> 常用的是数据帧，远程帧了解即可。
#### 3.4 Control Field：控制段

控制段里最重要的是：

```
DLC
```

DLC 全称：

```
Data Length Code
```

表示数据长度。

经典 CAN 中：

```
DLC = 0 ~ 8
```

也就是数据段最多 8 字节。

#### 3.5 ACK Field：应答段
CAN 的 ACK 不是应用层回复。

它不是说：

```
目标设备已经处理了这条命令
```

而是说：

```
总线上至少有一个节点正确收到了这一帧
```

只要有任意一个接收节点正确收到，并且 CRC 没问题，它就会在 ACK 位发送显性位。
### 4 常见帧类型
| 帧类型 | 作用        | 工程常用程度 |
| --- | --------- | ------ |
| 数据帧 | 携带数据      | 很常用    |
| 远程帧 | 请求某 ID 数据 | 较少用    |
| 错误帧 | 表示检测到错误   | 硬件自动处理 |
| 过载帧 | 节点暂时处理不过来 | 较少关注   |
### 5 can错误检测机制
| 错误类型        | 含义           |
| ----------- | ------------ |
| Bit Error   | 发送位和总线实际位不一致 |
| Stuff Error | 位填充规则错误      |
| CRC Error   | CRC 校验失败     |
| Form Error  | 固定格式字段错误     |
| ACK Error   | 没有收到 ACK     |
### 6 CAN 错误计数器

CAN 控制器内部通常有两个错误计数器：

```
TEC = Transmit Error CounterREC = Receive Error Counter
```

中文：

```
发送错误计数器接收错误计数器
```

当节点发送或接收出错时，对应计数器会增加。

错误少了，计数器可能下降。

根据错误计数，节点会进入不同错误状态。
### 7 can错误状态

| 状态            | 含义             |
| ------------- | -------------- |
| Error Active  | 正常活跃状态         |
| Error Passive | 错误较多，节点变得更“保守” |
| Bus Off       | 错误严重，节点退出总线    |
#### 6.1 Error Active
正常状态。
节点可以正常发送、接收。
检测到错误时，可以发送主动错误帧。
#### 6.2 Error Passive
说明节点错误较多。
节点仍然能通信，但对总线的干扰能力会降低，发送错误标志的方式也会变化。
你可以粗略理解：
```
这个节点有点不稳定，CAN 控制器开始限制它
```
#### 6.3 Bus Off
这是最严重状态。

节点进入 Bus Off 后，基本等于：

```
我错误太多了，先退出总线，避免继续影响别人
```

进入 Bus Off 后，节点通常不能继续正常发送，需要软件恢复或者控制器自动恢复。
### 8 busoff常见原因

```
1. 波特率不一致
2. CAN_H 和 CAN_L 接反
3. 没有终端电阻
4. 终端电阻数量错误
5. 总线上只有一个节点，没有 ACK
6. 对端没上电
7. 收发器 STB/EN 引脚状态错误
8. CAN_TX/CAN_RX 接反
9. GND 没接，地电位差太大
10. 线缆太长或分支太长
11. 电磁干扰严重
12. 收发器损坏
```

## 3 can在RTOS中的任务设计
### 3.1标准架构
*RX*
```c
CAN RX Interrupt
    ↓
读取 CAN FIFO / Message RAM
    ↓
投递 can_frame_t 到 rx_queue
    ↓
CAN RX Task
    ↓
过滤、解析、分发到应用模块
```
*TX*
```
Application Task
    ↓
can_send_async()
    ↓
投递 can_tx_msg_t 到 tx_queue
    ↓
CAN TX Task
    ↓
调用底层 CAN driver 发送
    ↓
TX Complete Interrupt
    ↓
释放 mailbox / 更新状态
```
*ERR*
```
CAN Error Interrupt
    ↓
记录错误状态
    ↓
通知 CAN Monitor Task
    ↓
处理 bus-off、error-passive、重初始化
```
### 3.2任务分配
| 任务                 | 职责                 | 优先级建议 |
| ------------------ | ------------------ | ----- |
| `can_rx_task`      | 处理接收报文、协议解析、分发     | 高     |
| `can_tx_task`      | 处理发送队列、统一发送        | 中高    |
| `can_monitor_task` | 错误状态、bus-off 恢复、统计 | 中/低   |
## 4 TI C2000 F28P65x 对can的支持
### 4.1 C2000 F28P65x上的can模块

| 模块       | 类型                   | 主要用途              |
| -------- | -------------------- | ----------------- |
| **DCAN** | Classic CAN          | 传统 CAN 2.0 通信     |
| **MCAN** | CAN FD / Classic CAN | 新项目、高吞吐、CAN FD 通信 |
### 4.2 demo
```c
#include "driverlib.h"
#include "device.h"

#define CAN_BASE            CANA_BASE
#define CAN_BITRATE         500000U

#define TX_MSG_OBJ_ID       1U
#define RX_MSG_OBJ_ID       2U

#define TX_CAN_ID           0x101U
#define RX_CAN_ID           0x201U

#define CAN_DLC             8U

volatile uint32_t txMsgCount = 0;
volatile uint32_t rxMsgCount = 0;
volatile uint32_t canErrorFlag = 0;

uint16_t txData[CAN_DLC];
uint16_t rxData[CAN_DLC];

__interrupt void canAISR(void);

static void initCANAWithInterrupt(void)
{
    CAN_initModule(CAN_BASE);

    CAN_setBitRate(CAN_BASE,
                   DEVICE_SYSCLK_FREQ,
                   CAN_BITRATE,
                   20U);

    //
    // 开启 CAN 模块中断：
    // IE0    : CAN interrupt line 0
    // ERROR  : 错误中断
    // STATUS : 状态中断
    //
    CAN_enableInterrupt(CAN_BASE,
                        CAN_INT_IE0 |
                        CAN_INT_ERROR |
                        CAN_INT_STATUS);

    Interrupt_register(INT_CANA0, &canAISR);
    Interrupt_enable(INT_CANA0);

    CAN_enableGlobalInterrupt(CAN_BASE,
                              CAN_GLOBAL_INT_CANINT0);

    //
    // TX object
    //
    CAN_setupMessageObject(CAN_BASE,
                           TX_MSG_OBJ_ID,
                           TX_CAN_ID,
                           CAN_MSG_FRAME_STD,
                           CAN_MSG_OBJ_TYPE_TX,
                           0U,
                           CAN_MSG_OBJ_TX_INT_ENABLE,
                           CAN_DLC);

    //
    // RX object
    //
    CAN_setupMessageObject(CAN_BASE,
                           RX_MSG_OBJ_ID,
                           RX_CAN_ID,
                           CAN_MSG_FRAME_STD,
                           CAN_MSG_OBJ_TYPE_RX,
                           0U,
                           CAN_MSG_OBJ_RX_INT_ENABLE,
                           CAN_DLC);

    CAN_startModule(CAN_BASE);
}

void main(void)
{
    Device_init();

    Interrupt_initModule();
    Interrupt_initVectorTable();

    initCANAWithInterrupt();

    EINT;
    ERTM;

    txData[0] = 0x11;
    txData[1] = 0x22;
    txData[2] = 0x33;
    txData[3] = 0x44;
    txData[4] = 0x55;
    txData[5] = 0x66;
    txData[6] = 0x77;
    txData[7] = 0x88;

    while(1)
    {
        if(canErrorFlag)
        {
            //
            // 工程里不要直接 ESTOP，应该读取状态、尝试恢复或上报错误。
            //
            asm(" ESTOP0");
        }

        CAN_sendMessage(CAN_BASE,
                        TX_MSG_OBJ_ID,
                        CAN_DLC,
                        txData);

        DEVICE_DELAY_US(1000000);

        txData[0]++;
    }
}

__interrupt void canAISR(void)
{
    uint32_t status;

    status = CAN_getInterruptCause(CAN_BASE);

    if(status == CAN_INT_INT0ID_STATUS)
    {
        //
        // 状态中断：读取 CAN 状态。
        // 注意：读取状态也会清除部分状态中断来源。
        //
        status = CAN_getStatus(CAN_BASE);

        //
        // 官方示例里会排除 TXOK/RXOK 后判断是否有错误。
        // 这里给一个简化处理。
        //
        if((status & ~(CAN_STATUS_TXOK | CAN_STATUS_RXOK)) != 0U)
        {
            canErrorFlag = 1;
        }
    }
    else if(status == TX_MSG_OBJ_ID)
    {
        CAN_clearInterruptStatus(CAN_BASE, TX_MSG_OBJ_ID);
        txMsgCount++;
        canErrorFlag = 0;
    }
    else if(status == RX_MSG_OBJ_ID)
    {
        CAN_readMessage(CAN_BASE, RX_MSG_OBJ_ID, rxData);

        CAN_clearInterruptStatus(CAN_BASE, RX_MSG_OBJ_ID);
        rxMsgCount++;
        canErrorFlag = 0;
    }
    else
    {
        //
        // Spurious interrupt
        //
    }

    CAN_clearGlobalInterruptStatus(CAN_BASE,
                                   CAN_GLOBAL_INT_CANINT0);

    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}
```