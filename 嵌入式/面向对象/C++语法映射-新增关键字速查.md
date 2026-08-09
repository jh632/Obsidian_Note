---
date: 2026-08-06
tags: [cpp, keywords, explicit, override, embedded]
aliases: [C++语法映射 速查篇, C++ 新增关键字]
---

# C++ 语法映射 · 速查篇：新增关键字

> 系列笔记的**附录篇（不占章节编号）**：C 里没有、C++ 新增的关键字，按工程用途分组速查。
> 前置：第 1/2 章。用法：学完主线后当字典查，标"第 X 章/跳过"的按标注对待。

## 系列目录（学习过程中持续维护）

| 章节    | 主题                        | 状态    |
| ----- | ------------------------- | ----- |
| 第 1 章 | class 与封装                   | ✅ 已完成 |
| 第 2 章 | 继承与虚析构                    | ✅ 已完成 |
| 速查篇  | 新增关键字（本篇）                | ✅ 已完成 |
| 第 3 章 | 多态：虚函数与 vtable            | ✅ 已完成 |
| 第 4 章 | RAII 与智能指针                | ⬜ 待学  |
| 第 5 章 | 模板基础与 STL 机制              | ⬜ 待学  |
| 第 6 章 | 现代特性（lambda/constexpr/移动） | ⬜ 待学  |

---

## 0. 总览表

| 分组    | 关键字                                  | 干什么                 | 记忆锚点        | 归属          |
| ----- | ------------------------------------ | ------------------- | ----------- | ----------- |
| 构造/重写 | `explicit`                           | 禁止单参构造被隐式调用         | 只能显式构造      | 第 1 章已学     |
| 构造/重写 | `virtual`                           | 标记虚函数/虚析构，调用按真实类型分发 | 多态开关        | 第 2 章已学，第 3 章深挖 |
| 构造/重写 | `override`                           | 声明重写基类虚函数，签名错编译报错   | 重写声明书       | 本篇          |
| 构造/重写 | `final`                              | 禁止继承 / 禁止重写         | 到此为止        | 本篇          |
| 类型安全  | `nullptr`                            | 类型安全的空指针，替代 NULL/0  | 真正的空指针      | 本篇          |
| 类型安全  | `enum class`                         | 强类型枚举：不泄漏、不能隐式转 int | 枚举的 class 版 | 本篇          |
| 类型安全  | `static_cast` 等                      | C 强转的规范版（编译期检查）     | 强转三兄弟       | 本篇          |
| 编译期   | `constexpr`                          | 函数/变量编译期求值          | 比 const 更能算 | 本篇（第 6 章深挖） |
| 编译期   | `static_assert`                      | 编译期断言               | 编译时 if      | 本篇          |
| 编译期   | `noexcept`                           | 承诺不抛异常              | 我不会抛        | 本篇          |
| 组织    | `namespace` / `using`                | 命名空间 / 类型别名         | C 前缀的语法版    | 本篇          |
| 后学    | `template` / `typename`              | 模板                  |             | 第 5 章       |
| 跳过    | `try`/`catch`/`throw`、`dynamic_cast` | 异常 / RTTI 转换        |             | 嵌入式默认关闭     |
| 了解即可  | `friend` / `mutable`                 | 破坏封装 / 极少用          |             | 遇到再查        |

---

## 1. explicit：禁止隐式构造

单参构造函数默认允许隐式转换——`Sensor s = 0x34;` 会偷偷调 `Sensor(0x34)`，看着像赋值其实是构造。加 `explicit` 后这种写法编译报错，只能显式构造：

```cpp
class Sensor {
public:
    explicit Sensor(uint8_t addr);
};

Sensor s = 0x34;    // ❌ 编译错误
Sensor s(0x34);     // ✅
```

**工程惯例：所有单参构造函数一律加 explicit**（故意做隐式转换的类型几乎不存在）。

## 2. virtual 与 override：多态的开关与重写声明书（重点）

### 2.1 virtual：多态的开关

`virtual` 标记成员函数"参与多态"——通过基类指针/引用调用时，**运行期按对象的真实类型**找实现，而不是按指针的静态类型：

```cpp
class Sensor {
public:
    virtual esp_err_t read();   // 虚函数：调用按真实类型分发（第 3 章深挖）
    virtual ~Sensor() {}        // 虚析构：delete 时析构链完整（第 2 章已学）
};

Sensor *s = new GH3220(0x34);
s->read();   // 不写 virtual → 走 Sensor::read；写了 → 走 GH3220::read
```

- 两个用途：**普通虚函数**（第 3 章）+ **虚析构**（第 2 章）
- 成本：每个对象多一个 vptr（4 字节）+ 每类一张 vtable（FLASH）→ **按需加，不盲加**
- 惯例：设计基类时析构直接 virtual；普通函数只有真需要多态才加（嵌入式组合优先）

### 2.2 override：重写声明书

**不写 override 的坑**：派生类重写虚函数时签名写错（如参数少了），编译器认为这是**新函数**（重载）而不是重写——基类虚函数没被覆盖，调用时悄悄走基类实现。**不报错，静默出错**。

```cpp
class Sensor {
public:
    virtual esp_err_t read(uint8_t *buf, uint32_t len);
};

class GH3220 : public Sensor {
public:
    esp_err_t read(uint8_t *buf, uint32_t len) override;  // ✅ 编译器核对签名
    esp_err_t read(uint8_t *buf) override;                // ❌ 编译报错：基类没有匹配的虚函数
};
```

- 只对虚函数有效；非虚函数加 override 是编译错误
- **工程惯例：重写必写 override**；不写能编译，但等于放弃检查

## 3. final：到此为止

```cpp
class GH3220 final : public Sensor { ... };   // 谁都不能再继承 GH3220
class X : public GH3220 { ... };              // ❌ 编译错误

class Sensor {
public:
    virtual esp_err_t read() final;           // 派生类不能重写 read
};
```

用处：层级封死（防止乱继承），编译器可做去虚化优化。

## 4. nullptr：真正的空指针

`NULL` 在 C 里是 `0` / `(void*)0`，重载时产生歧义（调 `f(int)` 还是 `f(char*)`？）。`nullptr` 的类型是 `std::nullptr_t`，只匹配指针。

**惯例：指针"没指向"一律写 nullptr，不写 0/NULL。**

## 5. enum class：强类型枚举

C 枚举三个毛病：值泄漏到外层作用域（可能撞名）、能隐式转 int、两个不同枚举能互相比较。`enum class` 全修掉：

```cpp
enum class PinMode { INPUT, OUTPUT };
enum class PinPull { NONE, UP, DOWN };

PinMode m = PinMode::OUTPUT;
uint8_t v = m;              // ❌ 编译错误，要 static_cast<uint8_t>(m)
if (m == PinPull::NONE) {}  // ❌ 编译错误，不同枚举类型
```

**工程惯例**：状态机状态、错误码、配置选项用 `enum class`。
**注意**：位掩码（可组合的 flag，如 GPIO 模式）**不适合** enum class（不能 OR），用 `enum` + constexpr 位运算；调 C API 时 `static_cast` 转换（ESP-IDF 的 `gpio_mode_t` 是 C 枚举）。

## 6. static_cast / const_cast / reinterpret_cast：强转三兄弟

| 转换 | 用途 | 例子 | 风险 |
|---|---|---|---|
| `static_cast` | 常规：数值/枚举/`void*`↔`T*` | `static_cast<uint8_t>(x)` | 低，编译期检查 |
| `const_cast` | 去掉 const（只调老 C API 用） | `const_cast<char*>(str)` | 高，别改原值 |
| `reinterpret_cast` | 位级重解释 | `reinterpret_cast<volatile uint32_t*>(0x3FF44000)` | 高，寄存器/结构体映射用 |

- `dynamic_cast` 依赖 RTTI，ESP-IDF 默认关 → 不用
- **惯例：不用 C 风格 `(Type)x`；嵌入式最常写 static_cast**

## 7. constexpr：编译期求值

标记"能在编译期算出结果"的函数/变量，算不出来才留到运行期。替代"宏计算"，有类型检查。嵌入式经典用法：查表（正弦/CRC）、时间换算常量：

```cpp
constexpr uint32_t ms_to_ticks(uint32_t ms) {
    return ms * CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ * 1000;
}
static constexpr uint32_t kDelay = ms_to_ticks(100);   // 编译期就算好，零运行期开销
```

当前编译器是 C++23（ESP-IDF v5.5 默认 gnu++23），constexpr 能力很强，细节第 6 章。

## 8. static_assert：编译期 if

条件为假 → 编译失败 + 消息。嵌入式用来检查结构体大小/对齐/宏值：

```cpp
static_assert(sizeof(gpio_config_t) == 16, "gpio_config_t 大小变了，核对驱动");
```

配置漂移在编译期就炸出来，而不是运行期诡异行为。

## 9. noexcept：我不会抛

承诺函数不抛异常，抛了直接 terminate。嵌入式异常默认关闭，它更多是**文档声明**；惯例：不抛的函数标注。

## 10. namespace / using

`namespace` = C 命名前缀（`bsp_`/`esp_`）的语法版：

```cpp
namespace bsp {
class GpioPin { ... };
}  // namespace bsp
bsp::GpioPin led(...);
```

`using` = 类型别名，替代 `typedef`：`using cfg_t = bsp_gpio_config_t;`
`using namespace xxx` 慎用——把一堆名字拖进当前作用域，可能撞名。

---

## 11. 跳过清单（明确不学/以后学）

| 关键字 | 为什么 |
|---|---|
| `template` / `typename` | 第 5 章（ACM 用过的 vector 就是模板） |
| `try` / `catch` / `throw` | 嵌入式默认 `-fno-exceptions` |
| `dynamic_cast` | 依赖 RTTI，默认关 |
| `concept` / `requires` | C++20，第 6 章或跳过 |
| `friend` | 破坏封装，工程少用，了解即可 |
| `mutable` | 极少用，遇到再查 |

---

## 12. 一句话总结

**C++ 新增关键字几乎都干同一件事：把 C 里"靠纪律、靠注释、靠运气"的事变成编译器强制——explicit 挡隐式转换，override 挡签名写错，enum class 挡类型混乱，static_assert 挡配置漂移。**
