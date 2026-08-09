---
date: 2026-08-06
tags: [cpp, oop, polymorphism, vtable, virtual, embedded]
aliases: [C++语法映射 第3章, C++ 多态与虚函数]
---

# C++ 语法映射 · 第 3 章：多态：虚函数与 vtable

> 系列笔记：把 C 里手写的 ops + handle 模式映射到 C++ 语法。
> 前置：第 1 章 class 与封装、第 2 章继承与虚析构。
> 本篇配套代码思路：传感器族（GH3220/MPU6050）继承基类 Sensor，统一管理。

## 系列目录（学习过程中持续维护）

| 章节    | 主题                        | 状态    |
| ----- | ------------------------- | ----- |
| 第 1 章 | class 与封装                   | ✅ 已完成 |
| 第 2 章 | 继承与虚析构                    | ✅ 已完成 |
| 速查篇  | 新增关键字速查                   | ✅ 已完成 |
| 第 3 章 | 多态：虚函数与 vtable（本篇）        | ✅ 已完成 |
| 第 4 章 | RAII 与智能指针                | ⬜ 待学  |
| 第 5 章 | 模板基础与 STL 机制              | ⬜ 待学  |
| 第 6 章 | 现代特性（lambda/constexpr/移动） | ⬜ 待学  |

---

## 1. 为什么需要多态

**继承本身只解决"复用代码"**（基类的成员函数/变量直接继承）。真正的价值在多态：**统一接口，不同实现，运行期分发**——多个具体传感器用同一个 `read()`，执行谁看真实类型。

### 1.1 C 的做法（已有）：ops 函数指针表

```c
typedef struct sensor_ops {
    int (*read)(void *ctx, uint8_t *buf, uint32_t len);
    int (*get_state)(const void *ctx);
} sensor_ops_t;

typedef struct Sensor {
    const sensor_ops_t *ops;   // 函数指针表
    void *ctx;                 // 每个设备自己的上下文
} Sensor;

static int gh3220_read(void *ctx, ...) { ... }
static const sensor_ops_t gh3220_ops = { .read = gh3220_read, ... };

Sensor s = { .ops = &gh3220_ops, .ctx = &gh3220_data };
s.ops->read(s.ctx, buf, len);   // 多态：运行期才确定执行 gh3220_read
```

这是 Linux `file_operations`、FreeRTOS 对象、用户 ops+handle 模式的精髓。

## 2. 虚函数：vtable 是编译器生成的 ops 表

```cpp
class Sensor {   // 基类 = 接口
public:
    virtual esp_err_t read(uint8_t *buf, uint32_t len) = 0;  // ★ 纯虚函数
    virtual ~Sensor() {}
};

class GH3220 : public Sensor {
public:
    esp_err_t read(uint8_t *buf, uint32_t len) override { /* 自己的实现 */ }
};

class MPU6050 : public Sensor {
public:
    esp_err_t read(uint8_t *buf, uint32_t len) override { /* 自己的实现 */ }
};
```

### 2.1 C ↔ C++ 对照

| C（手写的） | C++（编译器生成的） |
|---|---|
| `sensor_ops_t` 函数指针表 | **vtable** |
| 每个设备手动填 ops 表 | 每个类定义时自动生成 |
| `s.ops->read(s.ctx, ...)` | `sensor->read(...)` |
| ctx 手工传递 | this 隐式传递 |

### 2.2 运行机制

对象开头有 **vptr**（= ops 表里的 ops 字段），指向 vtable；vtable 按声明顺序排着虚函数地址。
运行期 `sensor->read(...)` 实际执行 `sensor->vptr->read(this, ...)`——和 C 的 `s.ops->read(s.ctx, ...)` 是同一个动作。

## 3. 纯虚函数与抽象类（接口）

- 结尾 `= 0` = **纯虚函数**：基类不写实现，只声明"必须有这个接口"
- 有纯虚函数的类 = **抽象类，不能实例化**（`Sensor s;` 编译报错）
- 派生类必须实现**全部**纯虚函数才能实例化
- 对应 C：ops 表只定接口，实现靠具体设备 → OOP"抽象"概念的语法化

## 4. 典型场景：工厂 / 异构容器

```cpp
Sensor *get_sensor(int id) {          // 工厂：运行期才决定返回谁
    if (id == 0) return new GH3220(0x34);
    return new MPU6050(0x68);
}

Sensor *sensors[] = { new GH3220(0x34), new MPU6050(0x68) };  // 异构容器
for (auto *s : sensors) s->read(buf, len);   // 统一接口，各自实现
```

框架场景：驱动框架不关心具体传感器，只存 `Sensor*`，统一 poll。

## 5. 与虚析构配套（闭环）

用基类指针管理派生类对象（new 出来存 `Sensor*`）→ `delete` 时要按真实类型析构 → 基类析构必须 `virtual`（第 2 章）。
**有虚函数管理 → 必有虚析构，一套的。**

## 6. 嵌入式取舍

- 成本：虚函数调用 = 一次间接跳转（略慢于直接调用）；每对象 +4B vptr；每类一张 vtable（占 FLASH）
- **什么时候值得**：多个具体类 + 统一管理（框架/工厂/异构容器）；只有一两个型号，直接写类，别上虚函数
- 组合优先仍然成立：Device 组合类装具体传感器，不用继承

---

## 7. 嵌入式继承应用方法（实战总结）

> 应用方法总结（仅针对 MCU/RTOS 嵌入式开发）：继承主要就三个用途，其余都是这三个的延伸。

### 7.1 用途一：定义统一接口 ⭐⭐⭐⭐⭐（最常见）

接口类只声明不实现，业务代码依赖接口、不依赖具体芯片：

```cpp
class Sensor
{
public:
    virtual bool init() = 0;
    virtual bool read() = 0;

    virtual ~Sensor() = default;
};
```

```text
          Sensor
         /   |   \
        /    |    \
  MPU6050 GH3220 AHT30
```

换芯片 = 换实例，业务代码一行不改：

```cpp
Sensor *sensor = new GH3220();

sensor->init();
sensor->read();

// 以后换芯片：sensor = new MPU6050();
```

典型接口类：**Sensor / Motor / Display / Storage / FileSystem / Comm / OTA Backend**

### 7.2 用途二：复用公共逻辑 ⭐⭐⭐⭐

公共流程放基类，差异点留给子类实现（模板方法）：

```cpp
class Device
{
public:
    bool init()
    {
        power_on();
        return do_init();   // 差异点
    }

protected:
    virtual bool do_init() = 0;
};

class Camera : public Device
{
protected:
    bool do_init() override { ... }
};
```

公共逻辑（上电 / 检查参数 / 初始化状态）只有一份。很多框架喜欢的写法。

### 7.3 用途三：多态（运行时切换实现） ⭐⭐⭐

同一接口、不同实现、运行期分发（插件化思想）：

```cpp
class Comm { public: virtual void send(const uint8_t *d, uint32_t n) = 0; ... };
// UART / CAN / BLE / TCP 各自实现

void upload(Comm *comm) { comm->send(data); }

upload(&uart); upload(&can); upload(&ble);   // 调用的是不同实现
```

### 7.4 实际项目怎么组织：接口继承 + 组合成员

```text
           接口(继承)
              │
      ┌───────┴────────┐
      │                │
 GH3220           MPU6050
      │                │
      ├────SPI         ├────I2C
      ├────GPIO        ├────GPIO
      └────DMA         └────Timer
```

只有 **"GH3220 是 Sensor"** 才继承；SPI / GPIO / DMA 都是成员（组合）。

### 7.5 is-a 判断规则（写 `class A : public B` 前先问自己）

> **A 是不是一种 B？**

| 可以继承（是） | 改成组合（不是） |
|---|---|
| GH3220 是一种 Sensor | GH3220 使用 SPI |
| Flash 是一种 Storage | Motor 使用 PID |
| FATFS 是一种 FileSystem | Screen 使用 Button |
| | Wifi 使用 Socket |

反例：`Motor → PID`、`Wifi → Socket` 都是错误继承（Motor **不是** PID），应改成组合。

### 7.6 成熟项目的比例：组合 80%，继承 20%

ESP-IDF / STM32 / Qt / Zephyr 大致如此。大部分驱动是：

```cpp
class GH3220
{
private:
    SPI spi;
    GPIO cs;
    Timer timer;
    Mutex mutex;
};
```

而不是 `class SPI : public GPIO` 这种奇怪继承。

### 7.7 建议：继承限制在接口层即可

```text
IDevice / ISensor / IMotor / IStorage / IComm / IDisplay
```

所有具体驱动去实现这些接口，驱动内部大量使用组合（SPI / I2C / DMA / GPIO / Queue / Mutex 等）——这是嵌入式项目中最清晰、也最容易维护的组织方式。

---

## 8. 语法映射总表

| C（你的写法） | C++ | 约束 |
|---|---|---|
| `sensor_ops_t` 函数指针表 | `virtual` 函数 + vtable | 编译器生成 |
| 每个设备手动填 ops 表 | 每个派生类 `override` | override 核对签名 |
| 注释"接口只声明" | 纯虚函数 `= 0` + 抽象类 | 不能实例化 |
| `s.ops->read(s.ctx, ...)` | `sensor->read(...)` | this 隐式传递 |
| 手工管理 ctx | this 指针 | 隐式 |

---

## 9. 一句话总结

**虚函数 = 编译器自动生成并填好的函数指针表（ops 表）；纯虚函数 = 只声明接口的抽象类；多态 = 同一接口、不同实现、运行期分发。**
