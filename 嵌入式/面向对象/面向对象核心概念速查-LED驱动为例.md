---
date: 2026-08-03
tags: [oop, c, embedded-systems, led, 面向对象]
aliases: [OOP Cheatsheet with LED, 面向对象速查]
---

# 面向对象核心概念速查（以 LED 驱动为例）

> 一句话：面向对象 = 把"数据"和"操作数据的函数"绑成"对象"。
> **封装**隐藏细节，**继承**复用代码，**多态**统一接口、各干各的，**抽象**只定契约。
>
> 嵌入式里 Linux 驱动、HAL 库、RTOS 源码全是这套东西。C 语言没有原生 OOP 语法，靠 **struct 嵌套（继承）+ 函数指针表（多态）** 模拟。

---

## 需求驱动的演进：一个 LED 的故事

每个概念不是凭空出现的，都是被真实需求"逼"出来的。

### 第 1 步：面向过程（裸写）

```c
// 全局变量：LED 的状态
uint8_t led_state = 0;
GPIO_TypeDef *led_port = GPIOB;
uint16_t led_pin = GPIO_PIN_0;

void led_on(void) {
    HAL_GPIO_WritePin(led_port, led_pin, GPIO_PIN_SET);
    led_state = 1;
}
void led_off(void) {
    HAL_GPIO_WritePin(led_port, led_pin, GPIO_PIN_RESET);
    led_state = 0;
}
```

**问题**：板子上有电源灯、状态灯、WiFi 灯三个 LED 怎么办？复制三份变量和函数？`led_state` 是全局的，谁都能乱改。

### 第 2 步：封装（Encapsulation）——LED 变成"对象"

把"引脚、状态"这些**数据**和"开、关"这些**操作**绑进一个结构体：

```c
/* led.h —— 对外只暴露定义和接口 */
typedef struct {
    GPIO_TypeDef *port;
    uint16_t      pin;
    uint8_t       state;      // 内部状态：只允许通过函数改
} Led;

void led_init(Led *l, GPIO_TypeDef *port, uint16_t pin);
void led_on(Led *l);
void led_off(Led *l);

/* led.c */
void led_on(Led *l) {
    HAL_GPIO_WritePin(l->port, l->pin, GPIO_PIN_SET);
    l->state = 1;             // 状态和操作一起更新，不会不一致
}
```

使用：

```c
Led power_led, status_led, wifi_led;
led_init(&power_led, GPIOB, GPIO_PIN_0);
led_init(&status_led, GPIOB, GPIO_PIN_1);
led_init(&wifi_led,  GPIOB, GPIO_PIN_2);

led_on(&power_led);      // 三个独立对象，互不干扰
led_off(&wifi_led);
```

- `Led` 定义 = **类**（图纸）；`power_led`、`status_led` = **对象/实例**（造出来的灯）。
- 以后内部实现随便改（换寄存器、加防抖），外面调用方一行不用动。

### 第 3 步：需求升级 → 继承（Inheritance）

产品改版：电源灯要能**呼吸**（PWM 调光），还要接一个 **I2C 驱动芯片**上的灯。但"开/关/状态"是所有灯都有的公共部分——抽出来当父类：

```c
/* 父类：所有 LED 的公共部分 */
typedef struct {
    uint8_t state;      // 所有灯都有"开没开"
} Led;

/* 子类 1：PWM 灯 "是一个" LED，多出占空比控制 */
typedef struct {
    Led base;                   // ★ 第一个成员放父类 = C 语言里的继承
    TIM_HandleTypeDef *htim;
    uint32_t channel;
} PwmLed;

/* 子类 2：I2C 灯 "也是一个" LED，多出总线地址 */
typedef struct {
    Led base;
    I2C_HandleTypeDef *hi2c;
    uint8_t chip_addr;          // 驱动芯片的 I2C 地址
    uint8_t ch;                 // 芯片上的通道号
} I2cLed;
```

**关键点：`base` 必须放在结构体第一个成员**——地址相同，子类对象才能当父类对象用，父类函数直接操作子类：

```c
// 父类方法写一次，所有子类自动继承
void led_set_state(Led *l, uint8_t on) { l->state = on; }

PwmLed breath;
I2cLed panel;
led_set_state(&breath.base, 1);   // 子类直接用父类的方法
led_set_state(&panel.base, 1);
```

继承解决**复用**：公共数据（state）和行为（开/关）写一份，子类只写差异（PWM 通道、I2C 地址）。

### 第 4 步：需求再升级 → 多态（Polymorphism）

上层要写"**心跳闪烁**"逻辑，三种灯都要闪。若每种灯写一份 `heartbeat_gpio()` / `heartbeat_pwm()` / `heartbeat_i2c()`，以后每加一种灯就多一份。

解法：定义**统一接口**（函数指针表 = 虚表），每种灯填自己的实现：

```c
/* 接口：LED 能干什么 */
typedef struct {
    void (*on)(void *obj);
    void (*off)(void *obj);
    void (*set_brightness)(void *obj, uint8_t percent);
} LedOps;
```

每种硬件的实现（各写各的，互不认识）：

```c
/* ===== GPIO 灯的实现 ===== */
typedef struct { GPIO_TypeDef *port; uint16_t pin; } GpioLed;

static void gpio_on(void *obj) {
    GpioLed *l = obj;
    HAL_GPIO_WritePin(l->port, l->pin, GPIO_PIN_SET);
}
static void gpio_set_brightness(void *obj, uint8_t pct) {
    GpioLed *l = obj;
    /* GPIO 灯只能开关：亮度只有 0% 和 100% */
    HAL_GPIO_WritePin(l->port, l->pin, pct ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
const LedOps gpio_led_ops = { gpio_on, gpio_off, gpio_set_brightness };

/* ===== PWM 灯的实现：亮度是"真"的 ===== */
typedef struct { TIM_HandleTypeDef *htim; uint32_t channel; } PwmLed;

static void pwm_set_brightness(void *obj, uint8_t pct) {
    PwmLed *l = obj;
    __HAL_TIM_SET_COMPARE(l->htim, l->channel, pct * 100);  // 改 CCR 调占空比
}
const LedOps pwm_led_ops = { pwm_on, pwm_off, pwm_set_brightness };

/* ===== I2C 灯的实现：通过总线写驱动芯片 ===== */
typedef struct { I2C_HandleTypeDef *hi2c; uint8_t chip_addr; uint8_t ch; } I2cLed;

static void i2c_on(void *obj) {
    I2cLed *l = obj;
    /* 往芯片 l->chip_addr 的 l->ch 通道寄存器写开灯命令 */
}
const LedOps i2c_led_ops = { i2c_on, i2c_off, i2c_set_brightness };
```

**调用方只认接口，不认具体灯**：

```c
/* 心跳逻辑只写这一次 —— 什么灯都能闪 */
void heartbeat(const LedOps *ops, void *obj) {
    for (;;) {
        ops->on(obj);
        HAL_Delay(500);
        ops->off(obj);
        HAL_Delay(500);
    }
}

heartbeat(&gpio_led_ops, &status_led);   // 普通灯在闪
heartbeat(&pwm_led_ops,  &breath_led);   // 呼吸灯在闪
heartbeat(&i2c_led_ops,  &panel_led);    // 芯片灯在闪
```

`ops->on(obj)` 这**同一行代码**：传 GPIO 的 ops 就是置引脚，传 PWM 的 ops 就是写 CCR，传 I2C 的 ops 就是发总线命令——**同一个接口，不同的行为 = 多态**。

### 第 5 步：抽象（Abstraction）/ 接口

`LedOps` 只有函数指针、没有任何数据——它就是**接口**：只约定"LED 能干什么"，不规定"怎么干"。无法"造一个 LedOps 对象"，它是契约不是实物（C++ 里对应含纯虚函数的**抽象类**，不能实例化）。

最大收益——新增 **WS2812 彩灯**只需新建 `ws2812.c`，实现一份 `LedOps`：

```c
heartbeat(&ws2812_led_ops, &rainbow_led);   // 调用方代码一个字不用改
```

新增功能不动旧代码（开闭原则）。

---

## 重载（Overload）vs 重写（Override）

| | 重载 Overload | 重写 Override |
|---|---|---|
| 位置 | 同一个类里 | 子类覆盖父类的方法 |
| 判定依据 | 参数个数/类型不同 | 函数签名完全相同 |
| 决定时机 | 编译期 | 运行期（虚函数） |
| 和继承的关系 | 无关 | 依赖继承 |

```c
// 重载：同名不同参，C 里只能靠函数名区分（C++ 支持真重载）
led_set_brightness_pct(l, 50);    // 亮度 0–100
led_set_brightness_raw(l, 255);   // 亮度 0–255 —— 其实是另一个函数

// 重写：子类提供自己的版本（C 里就是往自己的 ops 表里放不同函数指针）
static void pwm_set_brightness(void *obj, uint8_t pct) { /* PWM 版本 */ }
```

多态 = **继承 + 重写**组合的效果：通过父类接口调虚函数，实际执行子类的重写版本。

---

## 术语速查表

| 名词 | 含义 | 对应到 C |
|---|---|---|
| 类（Class） | 模板/图纸 | struct 定义 |
| 对象/实例（Object） | 按图纸造出来的实物 | 声明的结构体变量 |
| 实例化（instantiate） | 用类创建对象 | 声明 + `xxx_init()` |
| 成员变量/属性（attribute） | 对象的数据 | 结构体成员 |
| 方法/成员函数（method） | 对象的操作 | 操作该结构体的函数 |
| 封装（encapsulation） | 数据 + 操作绑定，隐藏内部 | struct + 操作函数 |
| 继承（inheritance） | 子类自动拥有父类成员并扩展 | 父结构体放在第一个成员 |
| 多态（polymorphism） | 同一接口、不同实现 | 函数指针表（ops） |
| 抽象/接口（interface） | 只定义"能做什么" | 只有函数指针的 struct |
| 虚函数/虚表（virtual/vtable） | 多态的实现机制 | ops 结构体（函数指针表） |
| 重载（overload） | 同名函数不同参数 | 改名区分（C） |
| 重写（override） | 子类覆盖父类虚函数 | 往自己的 ops 表放不同函数指针 |
| 构造/析构（constructor/destructor） | 创建时初始化 / 销毁时清理 | `xxx_init()` / `xxx_deinit()` |
| this / self | 指向对象自己的指针 | 函数的第一个参数 |
| 组合（composition） | 对象持有另一个对象（has-a） | 结构体嵌套（不放在第一位） |

---

## 嵌入式实战提示

- **继承用得少，ops 表（多态）用得最多**。Linux 内核驱动的 `file_operations` 就是 `LedOps` 的超集（`open/read/write/ioctl` 全是函数指针）。
- 这就是 **ops + handle 模式**：`ops` = 静态的接口表（只读、可共享），`handle` = 对象（结构体实例，持有私有数据）。Linux 里对应 `file_operations` + `inode`/`private_data`。
- 多态带来的可扩展性：**新硬件 = 新文件**，不动旧代码。
- C++ 就是把这套手搓的东西变成语言原生支持：`class` = struct + 方法，`virtual` = 编译器自动生成 vtable（即 ops 表），`继承` = base 成员自动处理。理解了 C 的模拟，C++ 语法是窗户纸。

## 学习顺序建议

1. **封装** → 2. **继承** → 3. **多态**（最难）→ 4. **抽象/接口**
2. 在 C 里练熟了 ops + handle，再看 C++ 的 class/virtual/继承语法做对照。
3. 去源码里找实例：Linux `file_operations`、STM32 HAL 的 `UART_HandleTypeDef`、FreeRTOS 的队列/任务对象——全是"struct + 函数指针"的 OOP。
