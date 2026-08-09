---
date: 2026-08-04
tags: [cpp, oop, class, encapsulation, embedded]
aliases: [C++语法映射 第1章, C++ class 与封装]
---

# C++ 语法映射 · 第 1 章：class 与封装

> 系列笔记：把 C 里手写的 ops + handle 模式映射到 C++ 语法。
> 前置知识：已理解 OOP 四大概念（见《面向对象核心概念速查-LED驱动为例.md》）。
> 本篇配套代码思路：传感器驱动（I2C 地址 + 上下文 + read/get_state）。

## 系列目录（学习过程中持续维护）

| 章节    | 主题                        | 状态    |
| ----- | ------------------------- | ----- |
| 第 1 章 | class 与封装（本篇）             | ✅ 已完成 |
| 第 2 章 | 继承与虚析构                    | ✅ 已完成 |
| 速查篇  | 新增关键字速查                   | ✅ 已完成 |
| 第 3 章 | 多态：虚函数与 vtable            | ✅ 已完成 |
| 第 4 章 | RAII 与智能指针                | ⬜ 待学  |
| 第 5 章 | 模板基础与 STL 机制              | ⬜ 待学  |
| 第 6 章 | 现代特性（lambda/constexpr/移动） | ⬜ 待学  |

---

## 1. class 与访问控制

### 1.1 关键字速览

| 关键字         | 作用                                               | 类比          |
| ----------- | ------------------------------------------------ | ----------- |
| `class`     | 定义"一种新类型"——C 里 `struct` 的升级版（能装数据 + 能装函数 + 能设权限） | 公司制度        |
| `public`    | 对外接口，谁都能用                                        | ATM 插卡口、取款键 |
| `private`   | 内部实现，只有类自己能用                                     | ATM 内部现金、账本 |
| `protected` | 自己和子类能用（第 2 章继承再展开）                              | 员工内部通道      |

### 1.2 class vs struct：语法几乎相同，工程分工不同

**语法层面**：唯一差别是**默认访问权限**——`class` 默认私有，`struct` 默认公有（其余能力完全一样，struct 也能有成员函数/构造析构）。

**工程层面（现代 C++ 约定，重点记这个）**：

| | struct | class |
|---|---|---|
| 用途 | **纯数据**：DTO / Packet / Config / Coordinate | **对象**：负责管理资源 |
| 业务逻辑 | 没有 | 有状态、有行为、有封装 |
| 成员 | 通常全公开 | 私有状态 + 行为接口 |

```cpp
/* struct：纯数据，没有逻辑 */
struct Point {
    int x;
    int y;
};

struct SensorConfig {
    uint8_t addr;
    float   gain;
};

/* class：对象，管理资源 */
class UART {
public:
    void send(const uint8_t *buf, uint32_t len);
private:
    UART_HandleTypeDef *huart_;   // 管理的资源
};
```

选型口诀：**"这是数据 → struct；这是对象 → class"。**

嵌入式补充：C 库/HAL 里全是 struct（句柄、配置、寄存器映射位域），所以 struct 在嵌入式里出现频率很高；自己写的"有行为的实体"（传感器、UART、任务）用 class。

### 1.3 关键认知：编译期检查

这些关键字是**编译期检查**，不是运行时魔法——外部访问 `private` 成员直接**编译报错**。
C 里靠"文件分离 + 自觉"，C++ 里靠"编译器强制"。

### 1.4 和 C 的对照

| C（已有做法） | C++ 关键字 |
|---|---|
| `.h` 里公开的接口函数 | `public:` |
| `.c` 里的不透明 struct 定义 | `private:` |
| `typedef struct Sensor Sensor;` | `class Sensor` |

---

## 2. 完整对照：传感器驱动的封装

> 先看整体骨架，语法点在第 3 节逐个展开。

### 2.1 C 版（不透明指针）

```c
/* sensor.h —— 对外只暴露接口 */
typedef struct Sensor Sensor;
Sensor *sensor_create(uint8_t addr, float offset, float gain);
void    sensor_delete(Sensor *s);
int     sensor_read(Sensor *s, uint8_t *buf, uint32_t len);
int     sensor_get_state(const Sensor *s);

/* sensor.c —— 内部细节藏在这里 */
struct Sensor {
    uint8_t  addr;
    int16_t  raw;
    uint32_t last_update;
    float    offset, gain;
};
```

### 2.2 C++ 版

```cpp
// sensor.h
class Sensor {
public:                                            // 从这里开始是公开接口
    Sensor(uint8_t addr, float offset, float gain);     // 构造函数 = create
    ~Sensor();                                          // 析构函数 = delete
    int read(uint8_t *buf, uint32_t len);
    int get_state() const;
private:                                           // 从这里开始是私有，外部碰不到
    uint8_t  addr_;          // 上下文 → 私有成员
    int16_t  raw_;
    uint32_t last_update_;
    float    offset_;
};

// sensor.cpp
Sensor::Sensor(uint8_t addr, float offset, float gain)
    : addr_(addr)            // ★ 成员初始化列表（冒号后）
    , raw_(0)
    , last_update_(0)
    , offset_(offset)
{}

Sensor::~Sensor() { /* 对应 delete 里的清理 */ }

int Sensor::read(uint8_t *buf, uint32_t len) { /* ... */ }
int Sensor::get_state() const { return raw_; }
```

---

## 3. 语法点逐个过

### 3.1 成员函数与 this

- `Sensor::read` 里的 `Sensor::` = **类作用域**（对应 C 的 `sensor_` 前缀）
- 成员函数内部有隐式 **`this` 指针** = C 里第一个参数 `s`；`raw_ = 1` 实际是 `this->raw_ = 1`
- 声明放 `.h`、定义放 `.cpp`（定义时写 `Sensor::` 前缀）——和 `.h`/`.c` 分离一个套路

`this` 通常省略，但**同名遮蔽**和**链式调用**时必须显式写：

```cpp
class Sensor {
public:
    void set_addr(uint8_t addr) {
        this->addr_ = addr;       // ★ 参数和成员同名，必须 this 区分
    }
    Sensor &set_gain(float g) {   // ★ 返回 *this 支持链式调用
        gain_ = g;
        return *this;
    }
private:
    uint8_t addr_;
    float   gain_ = 1.0f;
};

s.set_gain(2.0f).set_addr(0x50);  // 链式调用：一次写多个属性
```

### 3.2 构造函数（create 的映射）

- 名字 = 类名，**没有返回值**
- **成员初始化列表**（冒号后）：是"初始化"不是"赋值"，直接构造省一次默认构造
- **`const` 成员和引用成员只能在初始化列表里初始化**，函数体里赋值是编译错误
- 初始化列表优先级高于类内默认初始化（`int raw_ = 0;`）
- `explicit`：禁止单参构造函数被隐式调用（`Sensor temp = 0x48;` 这类写法）

```cpp
class Sensor {
    const float offset_;              // const 成员
public:
    Sensor(float off) : offset_(off)  // 只能在这里初始化
    {}
};
```

### 3.3 析构函数（delete 的映射）+ RAII

- 名字 = `~类名`，**对象离开作用域时自动调用**
- create/delete 配对是**语法保证**的，不可能忘记释放 → 这就是 **RAII**（资源获取即初始化）
- C++ 对 C 的最大红利：C 里漏调 `sensor_delete` 几个月后才翻车，C++ 里这个错误不存在
- 不写也有默认析构（成员逐个清理）；成员都是普通类型时**不需要自己写**

### 3.4 const 成员函数

`int get_state() const;` —— `const` 放参数列表后，承诺"调用时不修改对象"，编译器强制。
对应 C 的 `sensor_get_state(const Sensor *s)`，只是从"指针 const"变成"成员函数层面的 const"。

---

## 4. 语法映射总表

| C（你的写法） | C++ | 约束 |
|---|---|---|
| 注释"别直接改字段" | `private:` | 编译器强制 |
| `.h` 不透明 + `.c` 定义 | `.h` 声明 + `.cpp` 定义 | 同样分离 |
| `sensor_create(addr, ...)` | 构造函数 `Sensor(addr, ...)` | 自动调用 |
| `sensor_delete(s)` | `~Sensor()` | 自动调用，不会忘 |
| 函数第一个参数 `Sensor *s` | 成员函数 + `this` | 隐式 |
| `sensor_get_state(const Sensor *s)` | `int get_state() const` | 编译器强制只读 |
| 上下文结构体 | 私有成员变量 | 外部访问报错 |
| 字段命名 `addr` | `addr_`（惯例：成员加下划线后缀） | 无 |

---

## 5. 嵌入式初始化设计：构造函数不碰硬件，`init()` 才碰硬件

> 普通 C++（PC 开发）惯例：初始化放构造函数（RAII）。
> **嵌入式（MCU/RTOS）惯例相反：构造函数只保存参数，可能失败的事全放 `init()`**——这是嵌入式 C++ 与普通 C++ 最大的区别之一（ESP-IDF / STM32 HAL 项目通用）。

**为什么不能放构造函数：**

1. 构造函数不能返回错误码——异常被 `-fno-exceptions` 关闭，初始化失败没法上报
2. 全局/静态对象在 `main()` 之前构造——外设（I2C/SPI）还没初始化，构造里碰硬件直接崩
3. 初始化失败要能 `return ESP_FAIL` 交给上层处理，而不是直接 abort

**分工：**

| 职责 | 位置 |
|---|---|
| 保存配置参数（`addr_`、`spi_host_`、`cs_gpio_`、`i2c_port_`） | 构造函数 |
| 初始化普通变量（`state_ = IDLE`） | 构造函数 |
| 创建 STL 容器 | 构造函数 |
| 可能失败的一切：`spi_bus_add_device()` / `gpio_config()` / `uart_driver_install()` / `esp_wifi_init()` / `nvs_flash_init()` | `init()` |

```cpp
class GH3220 {
public:
    explicit GH3220(uint8_t addr) : addr_(addr) {}   // 构造：只记录参数

    esp_err_t init() {                               // init：所有可能失败的
        ESP_RETURN_ON_ERROR(spi_bus_add_device(...));
        ESP_RETURN_ON_ERROR(gh3220_reset());
        return ESP_OK;
    }
    esp_err_t read();

private:
    uint8_t addr_;
};

GH3220 gh(0x34);
ESP_ERROR_CHECK(gh.init());     // 失败能上报，而不是崩溃
while (1) { gh.read(); }
```

**组合类同样套路：构造函数组装，`init()` 逐个初始化：**

```cpp
class Device {
public:
    Device()
        : gh3220(I2C_NUM_0, 0x34)      // 构造只"组装"
        , mpu6050(I2C_NUM_0, 0x68)
    {}
    esp_err_t init() {
        ESP_RETURN_ON_ERROR(gh3220.init());
        ESP_RETURN_ON_ERROR(mpu6050.init());
        return ESP_OK;
    }
private:
    GH3220  gh3220;
    MPU6050 mpu6050;
};
```

**口诀：构造函数不碰硬件，`init()` 才碰硬件。**
备选方案：静态工厂（`static Sensor *create(...)`，失败返回 `nullptr`）。

---

## 6. 嵌入式专属的坑

1. **拷贝构造会被偷偷调用**：`Sensor a = b;` 逐成员浅拷贝，句柄/指针成员会导致重复释放 → 句柄类直接禁掉：`Sensor(const Sensor&) = delete;`
2. **类内定义的成员函数默认 `inline`**：小函数（getter 类）写类内没问题；大实现放 `.cpp`，否则每个包含 .h 的文件都生成一份代码。

> 理念提醒：别为每个私有成员写 getter/setter（`setAddr()`/`getAddr()` 是把 private 变回 public）。
> 设计**行为接口**（`read()` / `get_state()`）才是好封装——传感器接口本来就该行为导向。

---

## 7. 一句话总结

`class` 画边界，`public`/`private` 设门禁，构造函数/析构函数替掉 create/delete，`const` 成员函数替掉 const 指针——
**C 里靠纪律维持的封装，C++ 里全部变成编译器强制。**
