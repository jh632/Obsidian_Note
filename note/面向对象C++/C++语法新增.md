---
date: 2026-10-13
tags:
  - 面向对象
aliases:
  - C++新增语法笔记
---

# C++ 语法新增

> 从 C 过渡到 C++，先记录新增语法的用途、基本写法和容易混淆的地方。

## 1. namespace：命名空间

### 1.1 用来解决什么问题

`namespace` 用来组织名字，避免不同模块的函数、变量、类型重名。

C 中通常靠前缀区分，例如 `sensor_init()`、`motor_init()`；C++ 可以把两个 `init()` 放进不同命名空间。

```cpp
namespace sensor {
    void init() {
        // 初始化传感器
    }
}

namespace motor {
    void init() {
        // 初始化电机
    }
}

int main() {
    sensor::init();
    motor::init();
}
```

- `namespace sensor { ... }`：里面声明的名字属于 `sensor` 命名空间。
- `sensor::init()`：通过作用域解析运算符 `::` 指定要调用哪个 `init()`。
- 命名空间不是对象，不需要实例化，也没有 `public` / `private` 访问控制。
- 同一个命名空间可以在多个位置、多个文件中继续添加声明和定义。

### 1.2 using：简化名字的写法

```cpp
#include <iostream>

int main() {
    std::cout << "hello\n";       // 完整写法：cout 属于 std

    using std::cout;              // 引入一个名字
    cout << "hello again\n";
}
```

`using namespace` 则让整个命名空间中的名字参与当前作用域的名字查找：

```cpp
namespace sensor {
    void init() {}
}

int main() {
    using namespace sensor;
    init();                      // 可以省略 sensor::
}
```

**使用习惯**：优先写 `sensor::init()`，需要简化时在较小作用域内使用 `using sensor::init;`。不要在头文件的全局作用域写 `using namespace std;`，否则包含该头文件的代码也会受影响，更容易发生名字冲突。

**为什么应尽量避免 `using namespace`：** 它扩大了未限定名字的查找范围。多个命名空间中存在同名函数时，调用可能产生歧义；以后新增函数或引入新头文件，也可能让原本能编译的代码出现冲突。

```cpp
namespace sensor {
    void init() {}
}

namespace motor {
    void init() {}
}

int main() {
    using namespace sensor;
    using namespace motor;

    // init();                   // 编译错误：两个 init() 都符合，无法确定调用哪个
    sensor::init();              // 显式指定，含义清楚
    motor::init();
}
```

| 使用位置 / 写法 | 建议 |
| --- | --- |
| 头文件的全局作用域使用 `using namespace` | 避免：会影响所有包含它的源文件 |
| `.cpp` 文件的全局作用域使用 `using namespace` | 尽量避免：影响范围较大 |
| 函数或小代码块内使用 `using namespace` | 可以按需使用，但仍要留意同名歧义 |
| `using sensor::init;` | 只引入需要的名字，影响较小，但仍可能与已有名字冲突 |
| `sensor::init()` | 优先使用，直接表明名字来源 |

### 1.3 命名空间嵌套

命名空间可以嵌套，用层级表达“项目 → 模块”，例如 `project::drivers`：

```cpp
namespace project {
    namespace drivers {
        void init() {}
    }
}

int main() {
    project::drivers::init();    // 逐层指定所属命名空间
}
```

**C++17 起**，可以把上面的嵌套定义写成：

```cpp
namespace project::drivers {
    void init() {}
}
```

两种定义方式等价，按项目启用的 C++ 标准选择。`drivers` 中的 `init` 需要通过 `project::drivers::init()` 访问，不能直接写成 `project::init()`。

`using namespace project;` 可以让你写 `drivers::init()`，但不会自动把子命名空间里的 `init` 变成可直接调用的 `init()`。嵌套层级仍然存在。

### 1.4 命名空间别名

命名空间嵌套后名字较长时，可以用别名缩短，同时保留名字来源：

```cpp
namespace project::drivers {     // C++17
    void init() {}
}

namespace drv = project::drivers;

int main() {
    drv::init();                  // 等价于 project::drivers::init()
}
```

`namespace drv = ...;` 只是给已有命名空间起短名字，不会复制其中的内容。

## 2. class：类

### 2.1 用来解决什么问题

`class` 定义一种自定义类型，把**数据（成员变量）**和**操作数据的函数（成员函数）**放在一起，并通过访问权限控制外部能使用哪些成员。

可以先类比 C：`struct` 保存状态，操作函数接收结构体指针；C++ 把这些操作直接放进类中。

```cpp
class Led {
public:
    void on() {
        is_on_ = true;
    }

    void off() {
        is_on_ = false;
    }

    bool is_on() const {
        return is_on_;
    }

private:
    bool is_on_ = false;
};                               // 类定义后需要分号

int main() {
    Led led;                     // 定义一个 Led 对象
    led.on();                    // 对象通过 . 调用成员函数
    bool state = led.is_on();

    Led* p = &led;
    p->off();                    // 对象指针通过 -> 调用成员函数

    // led.is_on_ = true;         // 编译错误：外部不能访问 private 成员
}
```

> 这里用布尔变量模拟 LED 状态，实际驱动中再把 `on()` / `off()` 对接 GPIO 操作。

- `Led` 是类型，`led` 是该类型的一个对象。
- 不同对象各自保存普通成员变量，操作 `led` 不会自动修改另一个 `Led` 对象。
- `is_on_` 的下划线后缀是成员命名习惯，不是 C++ 语法要求。
- `is_on() const` 表示这个成员函数不能修改对象的普通成员变量；`mutable` 成员是例外。

### 2.2 public、private、protected

| 关键字 | 访问范围 | 常见用途 |
| --- | --- | --- |
| `public` | 外部代码也能访问 | 对外提供的行为接口 |
| `private` | 类自身的成员和友元可以访问 | 内部状态、实现细节 |
| `protected` | 类自身、友元以及派生类成员可按规则访问 | 继承时提供给子类的成员 |

访问标签对后续成员生效，直到出现下一个访问标签。`class` 中没有写标签的成员默认是 `private`。

**C++ 中 `class` 与 `struct` 的核心区别是默认权限**：`class` 默认成员访问和默认继承都是 `private`，`struct` 都是 `public`。两者都能定义成员函数、构造函数和析构函数。工程中通常用 `struct` 表示简单数据，用 `class` 表示需要封装状态和行为的对象。

### 2.3 在类外定义成员函数

```cpp
class Led {
public:
    void on();                   // 类内声明

private:
    bool is_on_ = false;
};

void Led::on() {                 // 类外定义：必须标明所属类
    is_on_ = true;               // 成员函数可以访问自己的私有成员
}
```

`Led::on()` 中的 `Led::` 表示类作用域。类内声明通常放头文件，类外定义通常放 `.cpp` 文件。

成员函数操作的是调用它的对象；函数内部可用 `this` 指针访问当前对象，例如 `this->is_on_ = true;`，没有名字冲突时通常可以省略 `this->`。

### 2.4 namespace 与 class 一起使用

```cpp
namespace drivers {
    class Led {
    public:
        void on();

    private:
        bool is_on_ = false;
    };

    void Led::on() {
        is_on_ = true;
    }
}

int main() {
    drivers::Led led;            // :: 找到类型
    led.on();                    // . 操作具体对象
}
```

| 写法 | 含义 |
| --- | --- |
| `drivers::Led` | 命名空间 `drivers` 中的 `Led` 类型 |
| `Led::on` | 类 `Led` 中的成员函数 `on` |
| `led.on()` | 通过对象调用成员函数 |
| `p->on()` | 通过对象指针调用成员函数 |

### 2.5 构造函数：创建对象时初始化

**构造函数在对象创建时自动执行，让对象获得有效的初始状态。** 可以自定义，名字与类名相同，没有返回类型，可以接收参数，也可以提供多个重载。

```cpp
class Led {
public:
    explicit Led(int pin)
        : pin_(pin), is_on_(false) {
        // 成员初始化完成后，才执行构造函数体
    }

private:
    int pin_;
    bool is_on_;
};

void test() {
    Led led(5);                  // 自动调用 Led(5)
}                               // 离开作用域时销毁 led
```

创建对象时，先准备对象的存储，再初始化对象。构造过程先初始化基类部分（有继承时），再按成员在类中的**声明顺序**初始化成员，最后执行构造函数体。

冒号后面的 `pin_(pin), is_on_(false)` 叫作**成员初始化列表**：

```cpp
// 直接初始化成员，优先使用这种写法
Led(int pin) : pin_(pin), is_on_(false) {}

// 另一种写法：进入函数体后再给成员赋值
Led(int pin) {
    pin_ = pin;
    is_on_ = false;
}
```

上面是两种替代写法，不能同时定义在同一个类中。对于这里的 `int` 和 `bool`，最终值相同；如果成员本身是类对象，它在进入函数体前就已经完成构造。引用成员和没有类内初始值的 `const` 成员，需要通过初始化列表初始化。

**不写构造函数，不代表成员自动清零：**

```cpp
class Sensor {
public:
    int value;
};

void test() {
    Sensor s;                   // 隐式默认构造函数不会初始化这里的 value
    // 不能把 s.value 当作有效数值读取
}
```

可以用类内默认值明确初始状态，例如把成员声明改成 `int value = 0;`。

如果自己声明了带参数的构造函数，编译器就不会再自动提供无参数构造函数：

```cpp
class Sensor {
public:
    explicit Sensor(int addr) : addr_(addr) {}

private:
    int addr_;
};

Sensor a(0x48);                  // 正确：调用带参数构造函数
// Sensor b;                    // 错误：没有可用的无参数构造函数
```

嵌入式中可以让构造函数保存引脚、地址等配置并初始化软件状态，把依赖硬件就绪、可能失败的操作放到 `init()` 中，以便返回错误码。尤其要注意：全局对象可能在 `main()` 之前构造，此时硬件可能尚未初始化。

### 2.6 析构函数：销毁对象时清理

**析构函数在对象被销毁时执行清理工作。** 可以自定义，写成 `~类名()`，没有返回类型、不接收参数。

```cpp
class Led {
public:
    explicit Led(int pin) : pin_(pin) {}

    ~Led() {
        // 按需清理本对象管理的资源
    }

private:
    int pin_;
};

void test() {
    Led led(5);                  // 构造：初始化对象
}                               // 析构：离开作用域，自动清理对象
```

通常由对象离开作用域、执行 `delete` 等行为触发析构，不需要手动调用 `led.~Led()`。

| 对象的创建方式 | 析构时机 |
| --- | --- |
| 普通局部对象 `Led led(5);` | 离开所在作用域时，包括正常 `return` |
| `new` 创建的对象 | 对对应指针执行 `delete` 时；指针变量离开作用域不会自动删除对象 |
| 类中的成员对象 | 所属对象销毁时 |
| 全局对象、已完成初始化的静态对象 | 程序正常结束时；嵌入式程序通常一直运行，不能指望靠它关闭硬件 |

销毁对象时，先执行自定义析构函数体，再按声明的逆序销毁成员对象，最后销毁基类部分。

**不写析构函数时，编译器通常也会隐式生成一个，但不会自动释放普通指针指向的资源。** 例如 `std::string` 成员会通过自己的析构函数释放其管理的内存；`char*` 成员本身不会自动执行 `delete[]`。

```cpp
class Buffer {
public:
    Buffer() : data_(new char[128]) {}

    ~Buffer() {
        delete[] data_;          // 释放自己申请的数组
    }

    // 禁止复制，避免两个对象重复释放同一块内存
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;

private:
    char* data_;
};

void test() {
    Buffer buffer;
}                               // 自动调用 ~Buffer()，释放数组
```

`buffer` 对象本身的存储由局部作用域的机制处理；`new char[128]` 申请的内存由析构函数中的 `delete[]` 释放。析构提供自动执行清理代码的时机，具体资源由自己的代码或成员对象负责释放，这是 **RAII** 的基础。上例用于展示手动资源管理，实际代码也可以用标准容器或智能指针成员管理内存。

### 2.7 explicit：限制构造函数参与隐式转换

**构造函数前的 `explicit` 要求调用方明确表达创建对象的意图，防止编译器把其他类型隐式转换成该类。**

没有 `explicit` 时：

```cpp
class Sensor {
public:
    Sensor(int addr) : addr_(addr) {}

private:
    int addr_;
};

void read_sensor(Sensor sensor) {}

void test() {
    Sensor a(0x48);              // 明确创建 Sensor
    Sensor b = 0x48;             // 允许：int 隐式转换为 Sensor
    read_sensor(0x48);           // 允许：自动构造 Sensor 后传入
}
```

把构造函数改成 `explicit Sensor(int addr) : addr_(addr) {}` 后：

```cpp
Sensor a(0x48);                  // 正确：直接初始化
Sensor b{0x48};                  // 正确：直接列表初始化

// Sensor c = 0x48;             // 错误：不允许这种隐式转换
// Sensor d = {0x48};           // 错误：复制列表初始化不能使用 explicit 构造函数
// read_sensor(0x48);           // 错误：不能隐式把 int 转成 Sensor

read_sensor(Sensor{0x48});        // 正确：明确创建对象后传入
```

`explicit` 不检查地址取值是否合法，也不会禁止正常调用构造函数。这里的 `Sensor c = 0x48;` 是变量定义时的初始化，不是对已有对象赋值。

对于 `Sensor(int addr)` 这样的构造函数，通常加上 `explicit`：一个地址数字可以用来构造传感器对象，但不应在传参等场景中自动被当成传感器对象。

更多封装设计示例：[[C++语法映射-class与封装]]。
