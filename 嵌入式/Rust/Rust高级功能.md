# Rust 语法笔记 — C 开发者视角

> C 有而 Rust 无的：宏（→ 声明宏）、goto（→ 无）、隐式转换（→ 显式转换）、NULL（→ `Option`）、野指针/内存泄漏（→ 所有权系统）、头文件（→ 模块系统）
>
> Rust 有而 C 无的：所有权、生命周期、`match`、`trait`、`Result`/`Option`、闭包、迭代器、模式解构

---

## 1. 所有权 (Ownership) — 核心

C 的 **手动 malloc/free** → Rust 的 **所有权编译器检查**，无 GC，无手动 free。

### 三条铁律

| C | Rust |
|---|---|
| `int *p = malloc(4); free(p);` 自己管 | 编译器在编译期决定何时 drop |
| `int *p = &x;` 指针可以悬垂 | 引用必须始终有效（生命周期检查） |
| `int a = b;` 隐式拷贝 | 默认 **move**，显式 `.clone()` 才深拷贝 |

### Move 语义

```rust
let s1 = String::from("hello");
let s2 = s1;           // s1 被 **move** 到 s2，s1 不再有效
// println!("{}", s1); // ❌ 编译错误 — s1 已被移动
```

**C 类比**：相当于 `memcpy` 后把原指针置 NULL，Rust 编译器自动做这件事。

### Copy 语义（栈上类型自动 Copy）

```rust
let x = 42;
let y = x;             // i32 实现了 Copy，x 仍有效
println!("{} {}", x, y); // ✅ OK
```

**规则**：所有 `整数` / `浮点` / `bool` / `char` / `元组(仅包含 Copy 类型)` 自动 Copy。

### Clone（显式深拷贝）

```rust
let s1 = String::from("hello");
let s2 = s1.clone();   // 堆数据深拷贝（类似 C 的 strdup）
```

---

## 2. 引用与借用 — 对照 C 指针

| C 指针 | Rust 引用 | 区别要点 |
|--------|-----------|---------|
| `int *p = &x` | `let p = &x` | Rust 引用编译期保证非空 |
| `int *p` (可读写) | `let p = &mut x` | Rust 互斥借用，C 无此限制 |
| `const int *p` | `let p = &x` （不可变引用） | 类似但 Rust 更强 |
| `int * const p` | 无直接对应 | Rust 引用自身不可变，但 `mut` 控制被引用者 |
| **NULL** | **不存在** → `Option<&T>` | Rust 没有空引用 |

### 借用规则（与 C 最大区别）

```rust
let mut x = 42;

// 规则一：任意数量不可变借用（类似 C 多线程只读）
let r1 = &x;
let r2 = &x;    // ✅ 多个 &T 共存
println!("{}, {}", r1, r2);

// 规则二：**最多一个**可变借用（C 无此限制，是 Rust 防数据竞争的关键）
let r3 = &mut x;  // ✅ 前面 &T 不再使用时可创建 &mut T

// let r1 = &x;   // ❌ 如果有 &mut T 活跃，不可再创建 &T
```

**C 角度理解**：Rust 的借用检查相当于编译期强制：
- 多个读指针可以共存
- 写指针与任何其他指针（读或写）**互斥**
- 无悬垂指针 — 引用永远不会指向已释放的内存

---

## 3. 生命周期 (Lifetimes) — C 没有的概念

生命周期是 Rust 用来**保证引用始终有效**的标注。

### 为什么需要

```rust
// C 版本 — 悬垂指针！
int* dangling() {
    int x = 42;
    return &x;  // ❌ x 离开函数就没了
}
```

```rust
// Rust 版本 — 编译器拒绝
fn dangling() -> &i32 {
    let x = 42;
    &x           // ❌ 编译错误：borrowed value does not live long enough
}
```

### 生命周期标注语法

```rust
// 'a 是一个生命周期参数，表示「两个引用的存活范围至少一样长」
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

**读法**："函数 `longest` 接受两个生命周期为 `'a` 的字符串切片，返回的切片也存活 `'a` 那么久。"

### 常用省略规则（不必每次都写）

| 场景 | 实际写法 | 等价于 |
|------|---------|-------|
| 只有一个输入引用 | `fn foo(x: &str)` | `fn foo<'a>(x: &'a str)` |
| 方法中 `&self` | `fn bar(&self) -> &str` | `fn bar<'a>(&'a self) -> &'a str` |
| 多个引用 | `fn baz(x: &str, y: &str)` | 需要手动标注 |

> **实用提示**：作为 C 开发者，你只需要明白生命周期是 Rust 在编译期做的「悬垂指针检查」。多数情况下编译器能自动推导，只在**⚠️ 函数返回引用时**才需要你手动写 `'a`。

---

## 4. 枚举与模式匹配 — C enum 的超级升级版

### C enum vs Rust enum

```c
// C 语言
enum Color { RED, GREEN, BLUE };
enum Color c = RED;
// C enum 只能是一个数字，不能附带数据
```

```rust
// Rust enum — 可以携带数据！
enum Color {
    Red,
    Green,
    Blue,
}

// Rust enum 的「代数数据类型」特性 — C 做不到
enum Message {
    Quit,                               // 无数据
    Move { x: i32, y: i32 },           // 匿名结构体
    Write(String),                      // 元组结构体
    ChangeColor(u8, u8, u8),            // 三个整数
}
```

### match 表达式（替代 C 的 switch）

```c
// C switch
switch (c) {
    case RED:   handle_red(); break;
    case GREEN: handle_green(); break;
    case BLUE:  handle_blue(); break;
    default:    break;  // 需要 default
}
```

```rust
// Rust match — 穷尽性检查，无需 break
match color {
    Color::Red => handle_red(),
    Color::Green => handle_green(),
    Color::Blue => handle_blue(),
    // 不需要 default — 编译器检查所有分支已覆盖
}

// 带数据解构的 match
match msg {
    Message::Quit => println!("退出"),
    Message::Move { x, y } => println!("移动到 ({}, {})", x, y),
    Message::Write(text) => println!("写入: {}", text),
    Message::ChangeColor(r, g, b) => println!("颜色 ({}, {}, {})", r, g, b),
}
```

**match vs switch 关键区别**：

| | C switch | Rust match |
|---|---|---|
| 穷尽性检查 | 无（容易漏分支） | **强制覆盖所有分支** |
| fall-through | 默认穿透（需 break） | **不穿透** |
| 数据类型 | 仅整数/字符 | **任意类型 + 模式解构** |
| default | 手动写 | `_ =>` 通配符 |

---

## 5. Option 与 Result — 替代 NULL 和错误码

### Option — Rust 没有 NULL

```c
// C — 用 NULL 表示"没有值"
int* find(int key) {
    return (key == 42) ? &value : NULL;  // 调用者需检查 NULL
}

int *p = find(10);
if (p != NULL) { ... }    // C 容易忘记检查
```

```rust
// Rust — Option<T> 显式表达「可能有值，可能为空」
fn find(key: i32) -> Option<i32> {
    if key == 42 { Some(100) } else { None }
}

let result = find(10);
match result {
    Some(value) => println!("找到: {}", value),
    None => println!("未找到"),  // ❗ 编译器强制处理 None
}

// 或使用快捷方法
let v = find(42).unwrap_or(0);           // 有值用值，无值用 0
let v = find(42).expect("找不到了！");   // None 时 panic 并打印消息
```

**C 类比**：`Option<T>` ≈ 一个带标记的联合体 `{ bool has_value; T value; }`，编译器强制你检查 `has_value`。

### Result — 替代 errno / 负数返回值

```c
// C — 通过返回值表示错误（容易忽略）
int divide(int a, int b, int *out) {
    if (b == 0) return -1;        // 错误码
    *out = a / b;
    return 0;
}
```

```rust
// Rust — Result<T, E> 显式表达「成功或失败」
fn divide(a: i32, b: i32) -> Result<i32, String> {
    if b == 0 {
        Err("除数不能为 0".to_string())  // 错误
    } else {
        Ok(a / b)                          // 成功
    }
}

// 使用
match divide(10, 0) {
    Ok(val) => println!("结果: {}", val),
    Err(e) => println!("错误: {}", e),    // ❗ 编译器强制处理
}

// 快捷操作符 ? — 错误自动传播（C 没有的语法糖）
fn calc() -> Result<i32, String> {
    let a = divide(10, 2)?;   // ❓ 如果 Err 则立即返回错误
    let b = divide(a, 3)?;    // 如果 Err 则立即返回错误
    Ok(b)
}
```

**核心差异**：
| | C 错误处理 | Rust Result |
|---|---|---|
| 是否强制处理 | ❌ 可忽略 | ✅ 编译器强制处理 |
| 错误类型 | 整数（含义模糊） | 自定义类型（信息丰富） |
| 传播方式 | `if (ret < 0) return ret;` 手动写 | `?` 操作符自动传播 |
| 错误链 | 无 | 支持 `.context()` 链式传递 |

---

## 6. trait — 类似 C 的虚函数表，但更灵活

trait ≈ C 里定义接口（纯虚函数表）+ 编译期多态 + 附加行为。

```c
// C — 用函数指针表模拟接口
typedef struct {
    void (*speak)(void);
    void (*walk)(int steps);
} AnimalVtable;
```

```rust
// Rust — trait 定义（类似接口）
trait Animal {
    fn speak(&self);           // 方法签名
    fn walk(&self, steps: i32); // 方法签名
    fn name(&self) -> &str;     // 方法签名
}

// 为类型实现 trait
struct Dog {
    name: String,
}

impl Animal for Dog {
    fn speak(&self) {
        println!("{}: 汪汪！", self.name);
    }
    fn walk(&self, steps: i32) {
        println!("{} 走了 {} 步", self.name, steps);
    }
    fn name(&self) -> &str {
        &self.name
    }
}
```

### trait 做参数（两种方式）

```rust
// 方式 1：泛型约束（编译期静态分发，类似 C++ 模板，无运行时开销）
fn make_speak<T: Animal>(animal: &T) {
    animal.speak();
}

// 方式 2：trait 对象（运行时动态分发，类似 C 虚函数表）
fn make_speak_dyn(animal: &dyn Animal) {
    animal.speak();
}
```

| | 泛型约束 `T: Animal` | trait 对象 `dyn Animal` |
|---|---|---|
| 分发方式 | 静态（编译期） | 动态（运行时） |
| 性能 | 零开销（单态化） | 有虚函数表间接调用 |
| 适用场景 | 性能敏感、类型确定 | 类型集合不确定、运行时多态 |

### 常用标准库 trait

| trait | 作用 | 类似 C 中的 |
|-------|------|-----------|
| `Clone` | 提供 `.clone()` 深拷贝 | `memcpy` + 深拷贝 |
| `Copy` | 按位拷贝栈布局 | 无，Rust 显式控制 |
| `Debug` | 提供 `{:?}` 格式化输出 | `printf` 格式化 |
| `Display` | 提供 `{}` 格式化输出 | `printf` 格式化 |
| `Default` | 提供默认值 `T::default()` | 无 |
| `PartialEq` | 提供 `==` 和 `!=` | 需手动写比较函数 |
| `Iterator` | 提供迭代能力 | 需手动写循环 |
| `Drop` | 析构逻辑（离开作用域时运行） | `free` / 析构函数 |

---

## 7. 模块系统 — 替代头文件

C 的 `#include "header.h"` → Rust 的 `mod` + `use`。

```c
// C 方式
// math.h — 声明
#ifndef MATH_H
#define MATH_H
int add(int a, int b);
#endif

// math.c — 实现
#include "math.h"
int add(int a, int b) { return a + b; }

// main.c — 使用
#include "math.h"
int main() { add(1, 2); }
```

```rust
// Rust 方式 — 无需头文件，无需 include guard

// src/math.rs
pub fn add(a: i32, b: i32) -> i32 { a + b }

// src/main.rs
mod math;                       // 声明模块（自动找 math.rs）
use math::add;                  // 导入

fn main() {
    let r = add(1, 2);          // 直接使用
}
```

### 可见性规则

```rust
mod inner {
    fn private() {}             // 默认私有，仅当前模块可见
    pub fn public() {}          // 公开
    pub(crate) fn restricted() {}  // 仅当前 crate 可见
    pub(super) fn parent_see() {}  // 仅父模块可见
}
```

**C 对应关系**：
| Rust | C |
|------|----|
| `mod` 声明模块 | 一个 `.c` 文件 + 对应 `.h` |
| `pub` 对外公开 | `.h` 中的声明 |
| 默认私有 | `static` 函数 / 内部链接 |
| `use path::to::item` | `#include "header.h"` |
| `as` 别名 | `typedef` / `#define` 别名 |
| `pub use` 重导出 | 在头文件中再次 `#include` |

### 文件组织

```
src/
├── main.rs           # crate 根
├── lib.rs            # 库 crate 根（如果同时是库）
├── math.rs           # mod math;
└── utils/
    ├── mod.rs        # mod utils;（旧风格）或
    └── helper.rs     # mod utils; + mod utils::helper（2021 edition）
```

---

## 8. 补充概念速览

### 模式解构 — C 没有

```rust
let tuple = (1, "hello", 3.14);
let (a, b, c) = tuple;          // 解构元组
println!("{} {} {}", a, b, c);

let point = (10, 20);
match point {
    (0, 0) => println!("原点"),
    (x, 0) => println!("X 轴上: {}", x),   // 部分匹配
    (0, y) => println!("Y 轴上: {}", y),
    (x, y) => println!("({}, {})", x, y),
}
```

### if let — match 的简洁形式

```rust
// 完整 match
match option_value {
    Some(v) => println!("值为 {}", v),
    None => (),
}

// 等价简写 — if let
if let Some(v) = option_value {
    println!("值为 {}", v);
}
```

### 闭包（匿名函数）— C 没有，C23 的 lambda 类似

```rust
// |参数| 表达式
let add = |a, b| a + b;          // 类型自动推导
println!("{}", add(2, 3));       // 5

// 捕获环境变量（C 做不到）
let x = 10;
let closure = || println!("{}", x);  // 捕获 x
closure();                            // 10
```

### 迭代器 — 替代手写 for 循环

```c
// C for 循环
int arr[] = {1, 2, 3, 4, 5};
for (int i = 0; i < 5; i++) {
    printf("%d\n", arr[i]);
}
```

```rust
// Rust 迭代器 — 更声明式
let arr = [1, 2, 3, 4, 5];

// 传统 for
for v in &arr {
    println!("{}", v);
}

// 迭代器链式操作（函数式风格）
arr.iter()
   .filter(|&&x| x > 2)
   .map(|x| x * 2)
   .for_each(|x| println!("{}", x));
// 输出: 6 8 10
```

---

## 9. 常见 C 模式 → Rust 对照表

| C 模式 | Rust 做法 |
|--------|----------|
| `int *p = malloc(n)` | `let mut v = Vec::with_capacity(n)` |
| `free(p)` | 作用域结束自动 `drop()`（类似 RAII） |
| `NULL` 表示无值 | `Option::None` |
| `-1` / `errno` 表示错误 | `Result::Err(e)` |
| `switch-case` | `match`（穷尽、无 fall-through） |
| `void *` 通用指针 | `enum` / 泛型 `T` / `dyn Trait` |
| 函数指针做回调 | 闭包 `\|args\| expr` |
| `struct { int x, y; } p = {1,2}` | `let p = Point { x: 1, y: 2 }` |
| `typedef struct { ... } Name;` | `struct Name { ... }`（无需 typedef） |
| `#define SIZE 100` | `const SIZE: usize = 100` |
| `for (int i=0; i<n; i++)` | `for i in 0..n { }` 或迭代器 |
| `// 注释` | `// 注释` 一样 |
| `/* 块注释 */` | `//` 或 `/* */` 或文档注释 `///` |

---

## 10. 快速语法卡片

### 变量声明

```rust
let x = 5;              // 不可变（类似 const，但可绑定复杂类型）
let mut y = 5;          // 可变
const MAX: u32 = 100;   // 编译期常量（必须标注类型）
static NAME: &str = "hello";  // 全局静态变量
```

### 函数定义

```rust
fn add(x: i32, y: i32) -> i32 {    // 类型在后：参数和返回值
    x + y                           // 最后一个表达式是返回值（无 return）
}

fn div(x: i32, y: i32) -> Option<i32> {
    if y == 0 { None } else { Some(x / y) }
}
```

### 控制流

```rust
// if 是表达式（可以赋值）
let result = if x > 0 { "正数" } else { "非正数" };

// 循环
loop { break; }                     // 无限循环
while condition { }                 // 条件循环
for i in 0..10 { }                  // 范围循环 0..9
for i in 0..=9 { }                  // 包含端点 0..=9
```

### 常用集合

```rust
let mut v: Vec<i32> = Vec::new();
v.push(1);                          // 动态数组（类似 C++ vector）
let x = v[0];                       // 索引访问

let mut map = std::collections::HashMap::new();
map.insert("key", 42);              // 哈希表
```
