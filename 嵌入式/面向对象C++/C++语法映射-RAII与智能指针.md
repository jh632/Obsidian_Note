---
date: 2026-10-13
tags: [面向对象]
aliases: [C++语法映射 第4章, C++ RAII 与智能指针]
---

# C++ 语法映射 · 第 4 章：RAII 与智能指针

> 系列笔记：把 C 里手写的 ops + handle 模式映射到 C++ 语法。
> 前置：[[C++语法映射-class与封装]]、[[C++语法映射-继承与虚析构]]、[[C++语法映射-多态与虚函数]]。
> 本篇重点：谁负责释放资源、什么时候释放，以及怎样让编译器帮忙执行清理。
> 示例以 C++14 及以上为基础，各代码块按所在小节独立阅读。

## 系列目录（学习过程中持续维护）

| 章节 | 主题 | 状态 |
|---|---|---|
| 第 1 章 | [[C++语法映射-class与封装\|class 与封装]] | ✅ 已完成 |
| 第 2 章 | [[C++语法映射-继承与虚析构\|继承与虚析构]] | ✅ 已完成 |
| 速查篇 | [[C++语法映射-新增关键字速查\|新增关键字速查]] | ✅ 已完成 |
| 第 3 章 | [[C++语法映射-多态与虚函数\|多态：虚函数与 vtable]] | ✅ 已完成 |
| 第 4 章 | RAII 与智能指针（本篇） | ✅ 已完成 |
| 第 5 章 | 模板基础与 STL 机制 | ⬜ 待学 |
| 第 6 章 | 现代特性（lambda/constexpr/移动） | ⬜ 待学 |

## 1. RAII：把资源的清理绑定到对象生命周期

RAII 全称 **Resource Acquisition Is Initialization（资源获取即初始化）**。核心做法是：用对象表达资源所有权，获取资源后交给对象管理，在对象析构时释放。

资源不只包括内存，还包括文件、锁、设备句柄等需要成对获取和释放的东西。

| C 中手动配对 | C++ 中的管理方式 |
|---|---|
| `malloc` / `free` | 容器，或带对应删除器的资源包装对象 |
| `new` / `delete` | `std::unique_ptr` / `std::shared_ptr` |
| `fopen` / `fclose` | 文件包装类或自定义删除器 |
| 加锁 / 解锁 | `std::lock_guard` 等作用域守卫 |
| 驱动创建 / 驱动销毁 | 自定义 RAII 句柄类 |

### 1.1 为什么能避免遗漏清理

C 中函数有多个 `return` 时，需要保证每条路径都正确释放资源。RAII 将清理集中在析构函数里：正常离开作用域、提前 `return`，以及发生正常异常栈展开时，已构造的局部对象都会析构。

```cpp
#include <mutex>

std::mutex bus_mutex;

bool read_sensor(bool ready) {
    std::lock_guard<std::mutex> guard(bus_mutex); // 构造时加锁

    if (!ready) {
        return false;                           // 自动析构 guard，解锁
    }

    // 在锁保护下访问传感器
    return true;                                // 同样自动解锁
}
```

这是支持 `<mutex>` 的标准 C++ 环境示例；RTOS 的锁可以用对应 API 封装相同的作用域守卫。

**RAII 不要求堆分配，也不要求开启异常。** 上面的守卫就是普通局部对象。异常关闭时，正常作用域退出和 `return` 仍然触发析构。但复位、断电、强制终止或不执行 C++ 栈展开的任务删除，不能指望自动清理。

### 1.2 自动析构不等于自动清理任意指针

```cpp
void bad() {
    int* p = new int(10);
}   // p 是普通指针，离开作用域不会 delete 它指向的对象：内存泄漏
```

指针变量和它指向的对象有不同的生命周期。只有把资源交给负责释放它的对象，RAII 才能发挥作用。

## 2. 所有权：先确定谁负责释放

**拥有资源**表示负责在合适的时候释放它；**借用资源**表示暂时使用，由其他对象负责生命周期。

| 表达方式 | 常见含义 | 是否负责释放 |
|---|---|---|
| 普通对象 `GH3220 sensor;` | 对象由当前作用域或所属对象管理 | 自动析构 |
| `Sensor&` / `Sensor*` | 借用已有对象；指针可以表示空 | 通常不负责，须由接口约定 |
| `std::unique_ptr<Sensor>` | 独占所有权 | 是 |
| `std::shared_ptr<Sensor>` | 共享所有权 | 最后一个共享所有者释放 |
| `std::weak_ptr<Sensor>` | 观察共享对象，不延长其生命 | 否 |

智能指针是 `<memory>` 中的**类模板**，不是新关键字。`std::unique_ptr<Sensor>` 表示“管理 Sensor 对象的独占智能指针”；尖括号里是类型。

## 3. unique_ptr：一个资源只有一个所有者

### 3.1 替代手写 new / delete

下面是承接前两章的完整示例：

```cpp
#include <memory>

class Sensor {
public:
    virtual ~Sensor() = default;
    virtual int read() = 0;
};

class GH3220 : public Sensor {
public:
    explicit GH3220(int addr) : addr_(addr) {}

    int read() override {
        return addr_;                   // 示例值，实际替换为硬件读取
    }

private:
    int addr_;
};

int main() {
    std::unique_ptr<Sensor> sensor = std::make_unique<GH3220>(0x34);
    int value = sensor->read();
    (void)value;
}   // sensor 析构 → 删除 GH3220 对象 → 自动执行基类析构
```

`std::make_unique<GH3220>(0x34)` 创建 GH3220 对象，并把它交给返回的 `unique_ptr` 管理。`make_unique` 从 C++14 开始提供，`unique_ptr` 从 C++11 开始提供。

这里最终由 `unique_ptr<Sensor>` 的默认删除器通过 `Sensor*` 删除对象，所以 **Sensor 仍然需要虚析构**。智能指针不会自动修复错误的基类析构设计。

### 3.2 不能复制，可以移动

```cpp
auto a = std::make_unique<GH3220>(0x34); // auto：让编译器推导变量类型

// auto b = a;                          // 错误：unique_ptr 不允许复制
auto b = std::move(a);                  // 转移所有权，需要 <utility>

// 此时 a 为空，b 管理原来的对象
if (b) {
    b->read();
}
```

`std::move(a)` 本身不搬运资源，它允许这里调用 `unique_ptr` 的移动构造函数。移动构造将所有权交给 `b`，并把 `a` 置空；传感器对象本身没有因此重新构造。

### 3.3 get、reset、release 的区别

| 操作 | 含义 | 是否释放当前资源 |
|---|---|---|
| `p->read()` / `*p` | 访问所管理对象，前提是非空 | 否 |
| `p.get()` | 取得借用的普通指针，所有权仍归 p | 否 |
| `p.reset()` | 清空 p | 是，非空时调用删除器 |
| `p.release()` | 交出普通指针并放弃所有权，p 变空 | **否，接收者必须接管** |
| `std::move(p)` 用于移动构造或赋值 | 把所有权转给另一个智能指针 | 不销毁被转移的资源 |

不要 `delete p.get()`，否则智能指针之后还会再次删除。不要用 `p.get()` 再创建一个独立拥有同一对象的智能指针。`release()` 只适用于确实需要向其他所有者交接的接口，随手调用会造成泄漏。

### 3.4 只是使用对象，就传引用

沿用前面的 Sensor 定义：

```cpp
int sample(Sensor& sensor) {             // 借用，不接管
    return sensor.read();
}

void consume(std::unique_ptr<Sensor> sensor) { // 按值接收所有权
    sensor->read();                     // 本例约定传入非空指针
}                                      // 函数结束，删除所拥有的对象

void example() {
    auto sensor = std::make_unique<GH3220>(0x34);
    sample(*sensor);                    // 使用后所有权仍在本函数
    consume(std::move(sensor));         // 交出所有权，sensor 随后为空
}
```

不要为了调用一个读取函数就引入共享所有权。参数使用 `Sensor&`，调用者可以传栈对象，也可以传智能指针管理的对象。

## 4. shared_ptr：多个所有者共同决定生命周期

```cpp
#include <memory>

void example() {
    auto a = std::make_shared<int>(42);
    {
        auto b = a;                     // 共享同一个对象，没有复制 int
        // 在此单线程示例中，共有 a、b 两个共享所有者
    }                                   // b 析构，a 仍持有对象

    a.reset();                          // 最后一个共享所有者放手，销毁 int
}
```

`shared_ptr` 通常通过控制块维护共享计数及删除信息；最后一个共享所有者消失时销毁所管理对象。它适合多个独立模块确实需要共同持有一个对象的情况。

代价包括控制块存储、引用计数维护和更复杂的生命周期。计数机制提供的并发保证不等于所指对象的业务数据可以无锁读写；同一个 `shared_ptr` 变量的并发修改也需要同步或相应原子接口。

不要这样从同一个普通指针建立两套独立所有权：

```cpp
int* raw = new int(42);
std::shared_ptr<int> a(raw);
// std::shared_ptr<int> b(raw);           // 错误：独立控制块，最终重复删除
auto b = a;                             // 正确：共享同一控制块
```

## 5. weak_ptr：观察共享对象，避免循环引用

如果 A 用 `shared_ptr` 持有 B，B 又用 `shared_ptr` 持有 A，外部所有者退出后两者仍互相持有，引用计数无法降为零。

可以让其中不承担所有权的一端使用 `weak_ptr`：

```cpp
#include <memory>

struct Node {
    std::shared_ptr<Node> next;          // 拥有下一个节点
    std::weak_ptr<Node> previous;        // 只观察上一个节点
};

void example() {
    auto first = std::make_shared<Node>();
    auto second = std::make_shared<Node>();
    first->next = second;
    second->previous = first;

    if (auto previous = second->previous.lock()) {
        // lock 成功：临时获得 shared_ptr，使用期间对象保持存活
        (void)previous;
    }
}
```

`weak_ptr` 不增加共享所有者数量，不能直接 `->` 访问目标。`lock()` 在目标仍存活时返回一个 `shared_ptr`，否则返回空指针；优先直接检查 `lock()` 的结果，不要先检查 `expired()` 再假设对象一定还活着。

## 6. C 资源也能用 RAII：自定义删除器

默认 `unique_ptr<T>` 使用 `delete`，数组版本 `unique_ptr<T[]>` 使用 `delete[]`。C API 返回的资源需要匹配其释放函数，不能把 `malloc` 的结果交给默认 `delete`。

以文件为例，可以让 `unique_ptr` 析构时调用 `fclose`：

```cpp
#include <cstdio>
#include <memory>

struct FileCloser {
    void operator()(std::FILE* file) const noexcept {
        std::fclose(file);
    }
};

using FilePtr = std::unique_ptr<std::FILE, FileCloser>;

bool write_log() {
    FilePtr file(std::fopen("sensor.log", "w"));
    if (!file) {
        return false;                   // 打开失败，没有文件需要关闭
    }

    return std::fputs("sensor ready\n", file.get()) >= 0;
}                                       // 非空时自动调用 FileCloser → fclose
```

`operator()` 让 `FileCloser` 对象能够像函数一样被调用；它告诉智能指针“怎样释放资源”。`using FilePtr = ...` 是类型别名。`noexcept` 表示该函数不允许异常逃出。

此示例只报告写入调用的结果，不报告关闭时的刷新失败。若业务必须确认数据落盘或关闭成功，应提供可检查结果的显式关闭流程，析构作为兜底清理。驱动句柄也可采用相同思路，但非指针型句柄通常更适合专用包装类。

## 7. 嵌入式中怎么选

### 7.1 能直接管理生命周期，就不必动态分配

```cpp
void poll_once() {
    GH3220 sensor(0x34);                 // 直接创建局部对象
    Sensor& view = sensor;               // 引用也能使用多态
    view.read();
}
```

对象作为局部变量或成员时，不需要为了“使用 C++”而改成 `new`。需要运行时创建并交接所有权时，优先考虑 `unique_ptr`；确实有共同所有者时再考虑 `shared_ptr`。

### 7.2 init() 与析构清理如何配合

在禁止异常、需要返回错误码的驱动中，可以保留“构造时设置为空状态，`init()` 获取硬件资源”的设计。对象一旦获得资源，就负责在析构时释放，这是让 RAII 管理可空资源的一种方式。

需要保证：

1. 初始句柄为空，析构空对象是安全的。
2. `init()` 成功后记录资源所有权，重复初始化有明确规则。
3. 多步初始化中途失败时，已取得的资源能够回滚或由成员 RAII 对象清理。
4. 默认复制不会造成两个对象重复释放同一句柄；必要时禁止复制，再按需实现移动。
5. 资源依赖的驱动、总线、锁等必须比资源持有者活得更久。

### 7.3 成本与边界

- `unique_ptr` 配合无状态删除器时常被实现为接近一个普通指针的大小，但标准不保证固定字节数，有状态删除器可能增加空间。
- 智能指针不会消除动态分配耗时或堆碎片；实时路径、ISR 是否能使用分配和清理 API，要按平台约束设计。
- 释放动作在所有权结束时执行；尤其是 `shared_ptr`，最后一个持有者可能在不同任务中退出，要确认清理操作允许在该上下文执行。
- 默认的 `make_unique` / `make_shared` 分配失败不能当成普通的“返回空指针”处理。关闭异常时应按工具链和项目约定设计失败路径。
- 成员已经是容器或智能指针时，通常不需要手写析构函数；让成员自动清理，减少重复的资源管理代码（零法则）。

## 8. 语法速查与选择顺序

| 写法 | 要记住的含义 |
|---|---|
| `std::make_unique<T>(args...)` | 创建 T，并取得独占所有权 |
| `std::move(p)` | 允许移动；具体转移由接收方的移动操作完成 |
| `p.get()` | 借用普通指针，不交出所有权 |
| `p.reset()` | 释放当前资源并置空 |
| `p.release()` | 放弃所有权但不释放，必须有人接管 |
| `std::make_shared<T>(args...)` | 创建共享管理的对象 |
| `std::weak_ptr<T>` | 观察共享对象，不延长对象生命周期 |
| `weak.lock()` | 尝试获得临时共享所有权，失败返回空 |

选择顺序：**直接对象 / 成员 → 需要独占动态所有权时用 unique_ptr → 确需共享时用 shared_ptr → 观察共享对象用 weak_ptr。**

RAII 决定资源如何随对象生命周期清理；智能指针则把动态对象的所有权与清理规则封装成可复用类型。

## 参考

- C++ Core Guidelines：资源管理 R.1、R.20、R.21、R.24 与零法则 C.20。
- C++ 工作草案条款：`[unique.ptr]`、`[util.smartptr.shared]`、`[util.smartptr.weak]`。工作草案会演进，本文示例只使用上述标明的基础版本能力。
