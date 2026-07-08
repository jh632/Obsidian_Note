# Rust 基础语法 — C 开发者视角

> **C 有而 Rust 无的**：隐式类型转换、`NULL`、野指针、手动内存管理（malloc/free）、头文件、`#define` 宏、`goto`
>
> **Rust 有而 C 无的**：所有权系统、借用检查、生命周期、模式匹配、`Option`/`Result`、零成本抽象

---

## 1. 变量定义

### 核心差异

| 场景 | C | Rust | 说明 |
|------|----|------|------|
| 不可变变量 | `const int x = 5;` | `let x = 5;` | Rust 默认不可变，C 需要 `const` |
| 可变变量 | `int x = 5;` | `let mut x = 5;` | Rust 需要显式 `mut` |
| 常量 | `#define X 5` 或 `const int X = 5;` | `const X: i32 = 5;` | Rust 必须标注类型 |
| 静态变量 | `static int x = 5;` | `static X: i32 = 5;` | Rust 需要标注类型 |

### 变量绑定

```rust
// 1. 标准不可变绑定
let x = 5;              // ✅ 默认不可变，类似 C 的 const

// 2. 可变绑定
let mut y = 5;          // ✅ 需要 mut 才能修改
y = 10;                 // ✅ OK

// 3. 同名遮蔽 (Shadowing)
let x = 5;
let x = "hello";        // ✅ 允许！新变量遮蔽旧变量，可以改变类型
// 注意：C 不允许同名变量

// 4. 延迟初始化
let z;                  // ✅ 可以先声明
z = 5;                  // ✅ 使用前赋值即可
println!("{}", z);
```

**C 对比**：
```c
// C 语言
int x = 5;              // 可变
const int y = 5;        // 不可变
#define Z 5             // 宏常量
static int w = 5;       // 静态变量
```

**Rust 特点**：
- 默认不可变，需要 `mut` 才能修改（C 相反，默认可变）
- 可以先声明后赋值（只要在使用前赋值）
- 支持同名遮蔽（C 不允许）

---

## 2. 数据类型

### 基本类型对照

| Rust 类型 | C 类型 | 说明 |
|-----------|--------|------|
| `i8/i16/i32/i64/isize` | `int8_t/int16_t/int32_t/int64_t/ssize_t` | 有符号整数 |
| `u8/u16/u32/u64/usize` | `uint8_t/uint16_t/uint32_t/uint64_t/size_t` | 无符号整数 |
| `f32/f64` | `float/double` | 浮点数 |
| `bool` | `_Bool` (C99) | 布尔值 |
| `char` | `char` | Unicode 字符（4字节） |

```rust
// 整数类型（必须明确指定或让编译器推断）
let x: i32 = 42;        // 32位有符号
let y: u8 = 255;        // 8位无符号
let z = 100;            // 编译器默认 i32

// 浮点数
let f: f64 = 3.14;      // 64位浮点（默认）
let g: f32 = 2.7;       // 32位浮点

// 布尔值
let b: bool = true;     // true 或 false

// 字符
let c: char = 'A';      // Unicode 字符，4字节
```

**C 对比**：
```c
// C 语言
int x = 42;             // 可能是 16/32/64 位，取决于平台
unsigned char y = 255;  // 8位无符号
float f = 3.14f;        // 32位浮点
double d = 3.14;        // 64位浮点
```

**Rust 特点**：
- 整数类型大小明确（`i32` 一定是 32 位）
- 无符号类型用 `u` 前缀（`u8`, `u16`, `u32`）
- `isize`/`usize` 类似 C 的 `ssize_t`/`size_t`，与平台相关

### 复合类型

```rust
// 元组 (Tuple) - C 没有直接对应
let tup: (i32, f64, bool) = (500, 6.4, true);
let (x, y, z) = tup;          // 解构
println!("{} {} {}", x, y, z);
let first = tup.0;            // 索引访问

// 数组 (Array) - 固定大小，类似 C 数组
let arr: [i32; 5] = [1, 2, 3, 4, 5];  // 类型; 长度
let first = arr[0];           // 索引访问
let length = arr.len();       // 获取长度

// 切片 (Slice) - 对数组的部分引用
let slice = &arr[1..3];       // 索引 1 到 2（左闭右开）
```

**C 对比**：
```c
// C 语言 - 没有元组
struct { int x; double y; bool z; } tup = {500, 6.4, 1};

// C 数组
int arr[5] = {1, 2, 3, 4, 5};
int first = arr[0];
```

**Rust 特点**：
- 元组可以包含不同类型，类似 C 的匿名结构体
- 数组长度是类型的一部分（`[i32; 5]` 和 `[i32; 6]` 是不同类型）
- 切片是对数组的部分引用，编译器会检查边界

---

## 3. 函数定义

### 基本语法

```rust
// 函数定义（类型在参数名后面）
fn add(x: i32, y: i32) -> i32 {    // 返回值类型用 ->
    x + y                           // 最后一个表达式是返回值（无 return）
}

// 使用 return 显式返回
fn divide(a: i32, b: i32) -> i32 {
    if b == 0 {
        panic!("除数不能为 0");      // panic 类似 C 的 abort
    }
    return a / b;                   // 可以用 return，但通常省略
}

// 无返回值的函数
fn print_message() {                // 省略 -> ()
    println!("Hello, World!");
}

// 多返回值（用元组）
fn swap(a: i32, b: i32) -> (i32, i32) {
    (b, a)                          // 返回元组
}
```

**C 对比**：
```c
// C 语言
int add(int x, int y) {            // 类型在参数名前面
    return x + y;                   // 必须用 return
}

int divide(int a, int b) {         // 类型在参数名前面
    if (b == 0) {
        abort();                    // 类似 panic
    }
    return a / b;                   // 必须用 return
}

void print_message() {
    printf("Hello, World!\n");
}
```

**Rust 特点**：
- 类型标注在参数名后面（`x: i32`），C 在前面（`int x`）
- 最后一个表达式自动作为返回值，可以省略 `return`
- 多返回值用元组，C 只能用指针参数
- 函数名使用蛇形命名法（`snake_case`），C 通常用蛇形或驼峰

### 函数调用

```rust
fn main() {
    let result = add(5, 3);         // 调用函数
    println!("5 + 3 = {}", result);
    
    let (a, b) = swap(1, 2);        // 接收多返回值
    println!("交换后: {} {}", a, b);
}
```

**C 对比**：
```c
int main() {
    int result = add(5, 3);
    printf("5 + 3 = %d\n", result);
    
    int a, b;
    swap(1, 2, &a, &b);            // C 只能通过指针参数返回多值
    printf("交换后: %d %d\n", a, b);
    return 0;
}
```

---

## 4. 控制流

### if 表达式

```rust
let number = 5;

// 基本 if-else
if number > 0 {
    println!("正数");
} else if number < 0 {
    println!("负数");
} else {
    println!("零");
}

// if 是表达式（可以返回值）— C 不支持
let result = if number > 0 {
    "positive"
} else {
    "non-positive"
};
println!("{}", result); // positive
```

**C 对比**：
```c
// C 语言 - if 是语句，不能返回值
if (number > 0) {
    printf("正数\n");
} else if (number < 0) {
    printf("负数\n");
} else {
    printf("零\n");
}

// C 想要类似效果需要三元运算符
const char *result = (number > 0) ? "positive" : "non-positive";
```

**Rust 特点**：
- 条件必须是 `bool` 类型，不会自动转换（C 会把非零当作 true）
- `if` 是表达式，可以返回值（类似三元运算符，但更强大）

### loop 循环

```rust
// 无限循环
loop {
    println!("一直执行");
    break; // 手动跳出
}

// break 返回值 — C 不支持
let mut counter = 0;
let result = loop {
    counter += 1;
    if counter == 10 {
        break counter * 2; // 返回 20
    }
};
println!("{}", result); // 20

// 循环标签 — 跳出外层循环
'outer: for i in 0..5 {
    for j in 0..5 {
        if i == 2 && j == 3 {
            break 'outer;  // 跳出外层循环
        }
        println!("({}, {})", i, j);
    }
}
```

**C 对比**：
```c
// C 没有无限循环的专用结构，通常用 while(1)
while (1) {
    printf("一直执行\n");
    break;
}

// C 不能从循环返回值
// C 不能用标签跳出多层循环（goto 不推荐使用）
```

**Rust 特点**：
- `loop` 是无限循环，必须手动 `break`
- `break` 可以返回值（类似函数返回）
- 循环标签可以控制跳出哪层循环（替代 goto）

### while 循环

```rust
let mut n = 3;
while n > 0 {
    println!("{}", n);
    n -= 1;
}
println!("发射！");

// 条件必须是 bool 类型
// while 是语句，不能返回值
```

**C 对比**：
```c
int n = 3;
while (n > 0) {
    printf("%d\n", n);
    n--;
}
printf("发射！\n");
```

### for 循环

```rust
// 范围遍历（左闭右开）
for i in 0..5 {
    println!("{}", i); // 0 1 2 3 4
}

// 闭区间
for i in 0..=5 {
    println!("{}", i); // 0 1 2 3 4 5
}

// 反向遍历
for i in (0..5).rev() {
    println!("{}", i); // 4 3 2 1 0
}

// 遍历数组
let arr = [10, 20, 30];
for elem in arr {
    println!("{}", elem);
}

// 带索引遍历
for (index, value) in arr.iter().enumerate() {
    println!("arr[{}] = {}", index, value);
}

// 遍历 Vec（借用）
let v = vec!["a", "b", "c"];
for s in &v {
    println!("{}", s);
}
```

**C 对比**：
```c
// C 语言
for (int i = 0; i < 5; i++) {   // 需要手动管理索引
    printf("%d\n", i);
}

// C 遍历数组需要知道长度
int arr[] = {10, 20, 30};
int len = sizeof(arr) / sizeof(arr[0]);
for (int i = 0; i < len; i++) {
    printf("%d\n", arr[i]);
}
```

**Rust 特点**：
- `for` 是最常用的循环，遍历迭代器
- `0..5` 是左闭右开区间，`0..=5` 是闭区间
- 不需要手动管理索引，直接遍历元素
- 支持 `.enumerate()` 同时获取索引和值

### match 表达式

```rust
let number = 3;

// 基本匹配
match number {
    1 => println!("一"),
    2 => println!("二"),
    3 => println!("三"),
    _ => println!("其他"), // 必须覆盖所有可能
}

// 匹配返回值
let x = 2;
let desc = match x {
    0 => "零",
    1 | 2 => "一或二",   // 多模式用 |
    3..=5 => "三到五",   // 范围匹配
    _ => "其他",
};
println!("{}", desc); // 一或二

// 解构元组
let pair = (0, -1);
match pair {
    (0, y) => println!("x=0, y={}", y),
    (x, 0) => println!("x={}, y=0", x),
    _ => println!("都不匹配"),
}

// 守卫（if 条件）
let n = 5;
match n {
    x if x < 0 => println!("负数"),
    x if x % 2 == 0 => println!("偶数"),
    _ => println!("正奇数"),
}
```

**C 对比**：
```c
// C switch
switch (number) {
    case 1:
        printf("一\n");
        break;              // 需要 break，否则会穿透
    case 2:
        printf("二\n");
        break;
    case 3:
        printf("三\n");
        break;
    default:
        printf("其他\n");
        break;
}

// C switch 只能匹配整数/字符
// C switch 没有穷尽性检查
// C switch 会穿透（fall-through）
```

**Rust 特点**：
- `match` 是表达式，可以返回值
- 必须穷尽所有可能（用 `_` 通配符）
- 支持多模式、范围、解构
- 不会穿透（不需要 break）
- 可以匹配任意类型（不仅仅是整数）

---

## 5. 结构体

### 基本结构体

```rust
// 定义结构体
struct Point {
    x: i32,
    y: i32,
}

// 创建实例
let p = Point { x: 10, y: 20 };

// 访问字段
println!("({}, {})", p.x, p.y);

// 可变实例（整个实例可变，不能只让某个字段可变）
let mut p = Point { x: 10, y: 20 };
p.x = 15;  // OK
```

**C 对比**：
```c
// C 语言
struct Point {
    int x;
    int y;
};

struct Point p = {10, 20};
// 或者
struct Point p;
p.x = 10;
p.y = 20;

// C 可以让单个字段可变（const 结构体）
const struct Point p = {10, 20};  // 所有字段不可变
// C 没有"部分可变"的概念
```

### 元组结构体

```rust
// 元组结构体（没有字段名）
struct Color(u8, u8, u8);  // RGB 颜色
struct Meters(f64);        // 带单位的数值

let red = Color(255, 0, 0);
let distance = Meters(100.0);

// 解构
let Color(r, g, b) = red;
let Meters(d) = distance;
```

**C 对比**：
```c
// C 没有直接对应，通常用 typedef
typedef struct {
    uint8_t r, g, b;
} Color;

typedef struct {
    double value;
} Meters;
```

### 方法实现

```rust
struct Rectangle {
    width: f64,
    height: f64,
}

// 为结构体实现方法
impl Rectangle {
    // 关联函数（类似 C 的构造函数，但不是必须的）
    fn new(width: f64, height: f64) -> Self {
        Self { width, height }
    }
    
    // 方法（第一个参数是 &self）
    fn area(&self) -> f64 {
        self.width * self.height
    }
    
    // 可变方法（第一个参数是 &mut self）
    fn scale(&mut self, factor: f64) {
        self.width *= factor;
        self.height *= factor;
    }
}

// 使用
let mut rect = Rectangle::new(10.0, 5.0);  // 调用关联函数
println!("面积: {}", rect.area());          // 调用方法
rect.scale(2.0);                           // 调用可变方法
```

**C 对比**：
```c
// C 语言没有方法，通常用函数 + 指针
typedef struct {
    double width;
    double height;
} Rectangle;

// 构造函数
Rectangle* rectangle_new(double width, double height) {
    Rectangle* r = malloc(sizeof(Rectangle));
    r->width = width;
    r->height = height;
    return r;
}

// 方法
double rectangle_area(const Rectangle* r) {
    return r->width * r->height;
}

// 使用
Rectangle* rect = rectangle_new(10.0, 5.0);
printf("面积: %f\n", rectangle_area(rect));
free(rect);  // 需要手动释放
```

**Rust 特点**：
- `impl` 块定义方法，`&self`/`&mut self`/`self` 作为第一个参数
- 关联函数用 `::` 调用（类似 C 的静态函数）
- 方法用 `.` 调用（类似 C 的 `->` 调用）
- 不需要手动释放内存

---

## 6. 枚举

### 基本枚举

```rust
// 定义枚举
enum Direction {
    Up,
    Down,
    Left,
    Right,
}

// 使用枚举
let dir = Direction::Up;

// match 匹配枚举
match dir {
    Direction::Up => println!("上"),
    Direction::Down => println!("下"),
    Direction::Left => println!("左"),
    Direction::Right => println!("右"),
}
```

**C 对比**：
```c
// C 语言
enum Direction {
    UP,
    DOWN,
    LEFT,
    RIGHT,
};

enum Direction dir = UP;

// C switch
switch (dir) {
    case UP:    printf("上\n"); break;
    case DOWN:  printf("下\n"); break;
    case LEFT:  printf("左\n"); break;
    case RIGHT: printf("右\n"); break;
}
```

### 带数据的枚举

```rust
// Rust 枚举可以携带数据（C 不支持）
enum Message {
    Quit,                               // 无数据
    Move { x: i32, y: i32 },           // 匿名结构体
    Write(String),                      // 元组结构体
    ChangeColor(u8, u8, u8),            // 三个整数
}

// 使用带数据的枚举
let msg = Message::Write(String::from("hello"));

match msg {
    Message::Quit => println!("退出"),
    Message::Move { x, y } => println!("移动到 ({}, {})", x, y),
    Message::Write(text) => println!("写入: {}", text),
    Message::ChangeColor(r, g, b) => println!("颜色 ({}, {}, {})", r, g, b),
}
```

**C 对比**：
```c
// C 需要用结构体 + 类型标签模拟
typedef struct {
    enum { QUIT, MOVE, WRITE, CHANGE_COLOR } type;
    union {
        struct { int x, y; } move;
        char* write;
        struct { uint8_t r, g, b; } color;
    } data;
} Message;
```

**Rust 特点**：
- 枚举变体可以携带不同类型的数据
- `match` 可以直接解构数据
- 编译器确保覆盖所有变体

---

## 7. 错误处理

### Option — 替代 NULL

```rust
// Rust 没有 NULL，用 Option<T> 表示可能为空
fn find(key: i32) -> Option<i32> {
    if key == 42 { Some(100) } else { None }
}

// 使用 Option
let result = find(10);
match result {
    Some(value) => println!("找到: {}", value),
    None => println!("未找到"),
}

// 快捷方法
let v = find(42).unwrap_or(0);           // 有值用值，无值用 0
let v = find(42).expect("找不到了！");   // None 时 panic
```

**C 对比**：
```c
// C 用 NULL 表示无值
int* find(int key) {
    if (key == 42) {
        static int value = 100;
        return &value;
    }
    return NULL;  // 容易忘记检查
}

int *p = find(10);
if (p != NULL) {  // 容易忘记检查
    printf("找到: %d\n", *p);
}
```

### Result — 替代错误码

```rust
// Rust 用 Result<T, E> 表示成功或失败
fn divide(a: i32, b: i32) -> Result<i32, String> {
    if b == 0 {
        Err("除数不能为 0".to_string())
    } else {
        Ok(a / b)
    }
}

// 使用 Result
match divide(10, 0) {
    Ok(val) => println!("结果: {}", val),
    Err(e) => println!("错误: {}", e),
}

// ? 操作符自动传播错误
fn calc() -> Result<i32, String> {
    let a = divide(10, 2)?;   // 如果 Err 则立即返回
    let b = divide(a, 3)?;
    Ok(b)
}
```

**C 对比**：
```c
// C 用返回值或 errno 表示错误
int divide(int a, int b, int *out) {
    if (b == 0) {
        errno = EINVAL;
        return -1;  // 错误码
    }
    *out = a / b;
    return 0;  // 成功
}

int result;
if (divide(10, 0, &result) != 0) {
    printf("错误: %d\n", errno);
}
```

**Rust 特点**：
- 编译器强制处理错误（必须 match 或 unwrap）
- `?` 操作符简化错误传播
- 错误类型丰富（可以是任何类型）

---

## 8. 引用与借用

### 基本引用

```rust
// 不可变引用（只读）
let x = 5;
let r = &x;           // r 是 x 的引用
println!("{}", r);    // 5

// 可变引用（读写）
let mut y = 5;
let r = &mut y;       // r 是 y 的可变引用
*r = 10;              // 通过引用修改值
println!("{}", y);    // 10
```

**C 对比**：
```c
// C 语言
int x = 5;
int *p = &x;          // p 是 x 的指针
printf("%d\n", *p);   // 5

int y = 5;
int *q = &y;
*q = 10;              // 通过指针修改
printf("%d\n", y);    // 10
```

### 借用规则

```rust
let mut x = 42;

// 规则一：任意数量不可变借用
let r1 = &x;
let r2 = &x;          // ✅ 多个 &T 共存
println!("{}, {}", r1, r2);

// 规则二：最多一个可变借用
let r3 = &mut x;      // ✅ 前面 &T 不再使用时可创建 &mut T

// let r1 = &x;        // ❌ 如果有 &mut T 活跃，不可再创建 &T
```

**C 对比**：
```c
// C 没有借用检查，可以同时有多个读写指针
int x = 42;
int *p = &x;          // 读指针
int *q = &x;          // 另一个读指针
int *r = &x;          // 写指针
*p = 10;              // 可能导致数据竞争
*q = 20;              // 可能导致数据竞争
```

**Rust 特点**：
- 编译器确保引用始终有效（无悬垂指针）
- 不可变引用和可变引用不能同时存在（防数据竞争）
- 引用必须始终有效（生命周期检查）

---

## 9. 类型转换

### 显式转换

```rust
// Rust 不允许隐式类型转换，必须显式转换
let x: i32 = 5;
let y: f64 = x as f64;      // 整数转浮点
let z: i32 = y as i32;      // 浮点转整数（截断）

// 字符串转数字
let s = "42";
let n: i32 = s.parse().unwrap();  // 解析字符串
```

**C 对比**：
```c
// C 允许隐式转换（可能导致精度丢失）
int x = 5;
double y = x;           // 隐式转换
int z = y;              // 隐式转换（截断）

// 显式转换
int a = (int) 3.14;     // 强制转换
```

**Rust 特点**：
- 不允许隐式类型转换（避免意外的精度丢失）
- 必须用 `as` 关键字显式转换
- 字符串转数字需要解析（`parse()`）

---

## 10. 注释

```rust
// 单行注释（和 C 一样）

/* 
 * 多行注释（和 C 一样）
 */

/// 文档注释（支持 Markdown）
/// 用于生成文档
/// 
/// # 示例
/// 
/// ```
/// let result = add(2, 3);
/// assert_eq!(result, 5);
/// ```
fn add(x: i32, y: i32) -> i32 {
    x + y
}

//! 模块级文档注释
//! 用于说明整个模块
```

**C 对比**：
```c
// C 单行注释（C99）
// 这是注释

/* 
 * C 多行注释
 */

/**
 * C 文档注释（通常用 Doxygen 格式）
 * @param x 第一个数
 * @param y 第二个数
 * @return 两数之和
 */
int add(int x, int y) {
    return x + y;
}
```

**Rust 特点**：
- `///` 用于函数/结构体等的文档注释
- `//!` 用于模块/文件的文档注释
- 支持 Markdown 格式
- 可以用 `cargo doc` 生成文档

---

## 11. 输入输出

### 标准输入输出

```rust
use std::io;

// 输出（类似 printf）
println!("Hello, {}!", "world");       // 换行
print!("Hello, {}!", "world");         // 不换行

// 格式化输出
let name = "Alice";
let age = 30;
println!("Name: {}, Age: {}", name, age);
println!("Name: {name}, Age: {age}");  // 直接使用变量名

// 输入
let mut input = String::new();
println!("请输入你的名字:");
io::stdin().read_line(&mut input).expect("读取失败");
let name = input.trim();  // 去除换行符
```

**C 对比**：
```c
#include <stdio.h>

// 输出
printf("Hello, %s!\n", "world");

// 输入
char name[100];
printf("请输入你的名字: ");
fgets(name, sizeof(name), stdin);
name[strcspn(name, "\n")] = 0;  // 去除换行符
```

**Rust 特点**：
- `println!`/`print!` 是宏（注意 `!`）
- 格式化更灵活（支持位置参数、命名参数）
- 输入需要处理 `Result`（可能失败）

---

## 12. 常见 C 模式 → Rust 对照表

| C 模式 | Rust 做法 | 说明 |
|--------|----------|------|
| `int x = 5;` | `let x = 5;` | Rust 默认不可变 |
| `const int x = 5;` | `let x = 5;` | Rust 变量默认不可变 |
| `#define X 5` | `const X: i32 = 5;` | Rust 用常量 |
| `malloc/free` | `Vec::new()` 等 | Rust 自动管理内存 |
| `NULL` | `Option::None` | Rust 没有 NULL |
| `switch-case` | `match` | 穷尽、无穿透 |
| `struct { ... }` | `struct { ... }` | 类似但不需要 typedef |
| `enum { ... }` | `enum { ... }` | Rust 可以携带数据 |
| `int *p = &x` | `let p = &x` | Rust 引用非空 |
| 函数指针 | 闭包 | 闭包更强大 |
| `for (int i=0; i<n; i++)` | `for i in 0..n` | 更简洁 |
| `// 注释` | `// 注释` | 一样 |

---

## 13. 快速语法卡片

### 变量声明

```rust
let x = 5;                    // 不可变
let mut y = 5;                // 可变
const MAX: u32 = 100;         // 编译期常量
static NAME: &str = "hello";  // 全局静态变量
```

### 函数定义

```rust
fn add(x: i32, y: i32) -> i32 {    // 类型在后
    x + y                           // 最后一个表达式是返回值
}

fn div(x: i32, y: i32) -> Option<i32> {
    if y == 0 { None } else { Some(x / y) }
}
```

### 控制流

```rust
// if 是表达式
let result = if x > 0 { "正数" } else { "非正数" };

// 循环
loop { break; }                     // 无限循环
while condition { }                 // 条件循环
for i in 0..10 { }                  // 范围循环
for i in 0..=9 { }                  // 包含端点
```

### 结构体

```rust
struct Point {
    x: i32,
    y: i32,
}

let p = Point { x: 10, y: 20 };

impl Point {
    fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }
    
    fn distance(&self) -> f64 {
        ((self.x * self.x + self.y * self.y) as f64).sqrt()
    }
}
```

### 枚举

```rust
enum Color {
    Red,
    Green,
    Blue,
}

enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(u8, u8, u8),
}
```

### 错误处理

```rust
// Option
fn find(key: i32) -> Option<i32> {
    if key == 42 { Some(100) } else { None }
}

// Result
fn divide(a: i32, b: i32) -> Result<i32, String> {
    if b == 0 { Err("除数不能为 0".to_string()) } else { Ok(a / b) }
}

// ? 操作符
fn calc() -> Result<i32, String> {
    let a = divide(10, 2)?;
    let b = divide(a, 3)?;
    Ok(b)
}
```

---

## 14. 嵌入式开发相关

### 位操作

```rust
// Rust 位操作与 C 类似
let mut x: u8 = 0b1010;

x |= 0b0001;      // 设置位（OR）
x &= 0b1110;      // 清除位（AND）
x ^= 0b0010;      // 翻转位（XOR）
x >>= 1;          // 右移
x <<= 1;          // 左移

// 位掩码
const BIT0: u8 = 1 << 0;
const BIT1: u8 = 1 << 1;
const BIT2: u8 = 1 << 2;

if x & BIT0 != 0 {
    // BIT0 被设置
}
```

**C 对比**：
```c
// C 语言
uint8_t x = 0b1010;

x |= 0b0001;      // 设置位
x &= 0b1110;      // 清除位
x ^= 0b0010;      // 翻转位
x >>= 1;          // 右移
x <<= 1;          // 左移

// 位掩码
#define BIT0 (1 << 0)
#define BIT1 (1 << 1)
#define BIT2 (1 << 2)

if (x & BIT0) {
    // BIT0 被设置
}
```

### 寄存器操作（伪代码）

```rust
// Rust 风格的寄存器操作
struct Gpio {
    moder: *mut u32,  // 模式寄存器
    odr: *mut u32,    // 输出数据寄存器
    idr: *mut u32,    // 输入数据寄存器
}

impl Gpio {
    fn set_output(&self, pin: u32) {
        unsafe {
            let moder = &mut *self.moder;
            *moder &= !(0b11 << (pin * 2));  // 清除位
            *moder |= 0b01 << (pin * 2);     // 设置为输出模式
        }
    }
    
    fn set_pin(&self, pin: u32) {
        unsafe {
            let odr = &mut *self.odr;
            *odr |= 1 << pin;
        }
    }
    
    fn clear_pin(&self, pin: u32) {
        unsafe {
            let odr = &mut *self.odr;
            *odr &= !(1 << pin);
        }
    }
}
```

**注意**：Rust 的 `unsafe` 块用于绕过编译器检查，通常用于底层硬件操作。

---

## 15. 常见陷阱

### 1. 所有权问题

```rust
let s1 = String::from("hello");
let s2 = s1;           // s1 被移动
// println!("{}", s1); // ❌ 编译错误

// 解决：使用克隆或引用
let s1 = String::from("hello");
let s2 = s1.clone();   // 深拷贝
println!("{}", s1);    // ✅ OK
```

### 2. 借用冲突

```rust
let mut x = 5;
let r1 = &x;
let r2 = &mut x;       // ❌ 编译错误
println!("{}", r1);

// 解决：确保引用不重叠
let mut x = 5;
let r1 = &x;
println!("{}", r1);    // r1 不再使用
let r2 = &mut x;       // ✅ OK
```

### 3. 生命周期问题

```rust
// ❌ 悬垂引用
fn dangling() -> &String {
    let s = String::from("hello");
    &s  // s 离开作用域就被释放
}

// 解决：返回所有权
fn not_dangling() -> String {
    let s = String::from("hello");
    s  // 转移所有权给调用者
}
```

---

## 16. 总结

### Rust 的优势（对比 C）

1. **内存安全**：所有权系统防止内存泄漏和野指针
2. **无数据竞争**：借用检查器防止并发问题
3. **零成本抽象**：高级特性不牺牲性能
4. **模式匹配**：比 switch 更强大
5. **错误处理**：强制处理错误，避免忽略

### C 的优势（对比 Rust）

1. **简单直接**：语法更简单，学习曲线更平缓
2. **生态成熟**：库和工具链更成熟
3. **嵌入式支持**：更多硬件平台支持
4. **控制力强**：可以完全控制内存布局

### 学习建议

1. 先掌握基础语法（变量、函数、控制流）
2. 理解所有权和借用（核心概念）
3. 多写代码实践
4. 逐步学习高级特性（trait、生命周期等）

---

> **参考资源**：
> - [The Rust Programming Language](https://doc.rust-lang.org/book/)
> - [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
> - [Rust for embedded](https://docs.rust-embedded.org/book/)
