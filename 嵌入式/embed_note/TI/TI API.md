## 1 GPIO
gpio初始化流程
```
1. 配置 pin mux
2. 配置输入/输出方向
3. 配置 pad 属性
4. 配置输入同步/采样 qualification
5. 读写电平或配置中断
```

在tic2000中

| C2000                                | STM32 类比                                |
| ------------------------------------ | --------------------------------------- |
| `GPIO_setPinConfig()`                | GPIO alternate function(引脚复用) / pin mux |
| `GPIO_setDirectionMode()`            | GPIO input/output mode                  |
| `GPIO_setPadConfig()`                | pull-up / open-drain / push-pull        |
| `GPIO_setQualificationMode()`        | 输入采样/同步滤波                               |
| `GPIO_writePin()` / `GPIO_readPin()` | HAL_GPIO_WritePin / ReadPin             |
### 1 GPIO 的核心：Pin Mux
同一个物理引脚可能有多种功能：
```
普通 GPIO
I2C SDA / SCL
CAN TX / RX
SPI SIMO / SOMI / CLK / STE
SCI(uart) TX / RX
ePWM 输出
eCAP 输入
XINT 外部中断
```

所以第一步经常是：

```
GPIO_setPinConfig(GPIO_31_GPIO31);
```
这表示：
```
把 31 号引脚配置为 GPIO31 普通 IO 功能
```
如果作为外设引脚，可能是：

```
GPIO_setPinConfig(GPIO_33_CANA_RX);
GPIO_setPinConfig(GPIO_32_CANA_TX);
```
这表示：
```
把某个 GPIO 复用为 CANA_RX / CANA_TX
```

> 注意：不同 C2000 型号、不同封装、不同 LaunchPad，具体 pin map 可能不同，要查对应 datasheet 或 `pin_map.h`。TI 官方 GPIO API 也明确说，pin 的有效编号要参考设备 datasheet；即使某 GPIO 编号存在，也不代表它支持所有功能。
### 2 PadConfig：引脚电气属性
| 参数                     | 含义            | 场景        |
| ---------------------- | ------------- | --------- |
| `GPIO_PIN_TYPE_STD`    | 标准推挽输出 / 浮空输入 | LED、普通输出  |
| `GPIO_PIN_TYPE_PULLUP` | 输入上拉          | 按键、I2C 辅助 |
| `GPIO_PIN_TYPE_OD`     | 开漏输出          | I2C、线与逻辑  |
| `GPIO_PIN_TYPE_INVERT` | 输入极性反转        | 特殊输入逻辑    |
### 3 Qualification：输入同步/滤波
| 模式                  | 含义         |
| ------------------- | ---------- |
| `GPIO_QUAL_SYNC`    | 同步到 SYSCLK |
| `GPIO_QUAL_3SAMPLE` | 3 次采样确认    |
| `GPIO_QUAL_6SAMPLE` | 6 次采样确认    |
| `GPIO_QUAL_ASYNC`   | 不同步，异步输入   |
选择原则

| 信号类型        | 建议                        |
| ----------- | ------------------------- |
| 普通按键        | `GPIO_QUAL_3SAMPLE` 或软件消抖 |
| 普通低速输入      | `GPIO_QUAL_SYNC`          |
| CAN RX      | 通常 `GPIO_QUAL_ASYNC`      |
| I2C SDA/SCL | 通常 `GPIO_QUAL_ASYNC`      |
| 高速外设输入      | 通常 `GPIO_QUAL_ASYNC`      |
### 4 I2C引脚
```c
#define I2C_SDA_GPIO 104
#define I2C_SCL_GPIO 105

void i2c_gpio_init(void)
{
	//配置sda/scl
    GPIO_setPinConfig(GPIO_104_I2CA_SDA);
    GPIO_setPinConfig(GPIO_105_I2CA_SCL);
	
	//配置上拉电阻
    GPIO_setPadConfig(I2C_SDA_GPIO, GPIO_PIN_TYPE_PULLUP);
    GPIO_setPadConfig(I2C_SCL_GPIO, GPIO_PIN_TYPE_PULLUP);
	
	//异步输入
    GPIO_setQualificationMode(I2C_SDA_GPIO, GPIO_QUAL_ASYNC);
    GPIO_setQualificationMode(I2C_SCL_GPIO, GPIO_QUAL_ASYNC);
}
```
### 5 can引脚配置
```c
#define CAN_RX_GPIO 33
#define CAN_TX_GPIO 32

void can_gpio_init(void)
{
    GPIO_setPinConfig(GPIO_33_CANA_RX);
    GPIO_setPinConfig(GPIO_32_CANA_TX);

    GPIO_setQualificationMode(CAN_RX_GPIO, GPIO_QUAL_ASYNC);
}
```

### 6 GPIO 中断配置
GPIO 中断通常不是所有 GPIO 直接进 CPU，而是通过外部中断通道或 X-BAR/XINT 机制映射。

基础流程：

```
1. GPIO 配成输入
2. 配置 pad 和 qualification
3. 选择外部中断通道
4. 配置上升沿/下降沿/双边沿
5. 注册 ISR
6. 使能中断
7. ISR 中清标志、通知任务
```

简化伪代码：

```c
#define KEY_GPIO 32

__interrupt void xint1_isr(void)
{
    // 1. 清中断标志
    // 2. 通知任务或置标志
    // 3. ACK PIE group
}

void key_interrupt_init(void)
{
    GPIO_setPinConfig(GPIO_32_GPIO32);
    GPIO_setDirectionMode(KEY_GPIO, GPIO_DIR_MODE_IN);
    GPIO_setPadConfig(KEY_GPIO, GPIO_PIN_TYPE_PULLUP);
    GPIO_setQualificationMode(KEY_GPIO, GPIO_QUAL_3SAMPLE);

    GPIO_setInterruptPin(KEY_GPIO, GPIO_INT_XINT1);
    GPIO_setInterruptType(GPIO_INT_XINT1, GPIO_INT_TYPE_FALLING_EDGE);
    GPIO_enableInterrupt(GPIO_INT_XINT1);
}
```

官方 GPIO API 中，
`GPIO_INT_TYPE_FALLING_EDGE` 表示下降沿中断
`GPIO_INT_TYPE_RISING_EDGE` 表示上升沿中断
`GPIO_INT_TYPE_BOTH_EDGES` 表示双边沿中断。

### 7 api汇总
| API                           | 必须程度 | 含义           |     |
| ----------------------------- | ---: | ------------ | --- |
| `GPIO_setPinConfig()`         |  必须会 | 配置 pin mux   |     |
| `GPIO_setDirectionMode()`     |  必须会 | 配置输入/输出      |     |
| `GPIO_setPadConfig()`         |  必须会 | 配置上拉、开漏、标准模式 |     |
| `GPIO_setQualificationMode()` |  必须会 | 配置输入同步/滤波    |     |
| `GPIO_writePin()`             |  必须会 | 写输出电平        |     |
| `GPIO_readPin()`              |  必须会 | 读输入电平        |     |
| `GPIO_togglePin()`            |  会看懂 | 翻转输出         |     |
| `GPIO_setInterruptPin()`      |   了解 | GPIO 映射到外部中断 |     |
| `GPIO_setInterruptType()`     |   了解 | 配置中断边沿       |     |
| `GPIO_enableInterrupt()`      |   了解 | 使能 GPIO 中断   |     |

# 2 I2C
## 2.1 I2C基础api
### 2.1.1初始化类
```c
I2C_disableModule(I2CA_BASE);

I2C_initController(I2CA_BASE, DEVICE_SYSCLK_FREQ, 400000, I2C_DUTYCYCLE_50);
I2C_setConfig(I2CA_BASE, I2C_CONTROLLER_SEND_MODE);
I2C_setTargetAddress(I2CA_BASE, 0x50);

I2C_enableModule(I2CA_BASE);
```

| API                      | 作用               |
| ------------------------ | ---------------- |
| `I2C_disableModule()`    | 配置前先关闭模块         |
| `I2C_initController()`   | 设置 I2C 主机模式时钟    |
| `I2C_setConfig()`        | 配置发送/接收、主机/从机等模式 |
| `I2C_setTargetAddress()` | 设置目标从机地址         |
| `I2C_enableModule()`     | 使能 I2C 模块        |
