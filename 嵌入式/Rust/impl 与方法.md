# impl 与方法 — C 开发者视角

> `struct` = 数据，`impl` = 给数据添加行为

---

## 1. 基本用法

```rust
struct Person {
    name: String,
    age: u8,
}

impl Person {
    fn say_hello(&self) {
        println!("Hello, I'm {}", self.name);
    }

    fn is_adult(&self) -> bool {
        self.age >= 18
    }
}

// 调用
let p = Person { name: String::from("Tom"), age: 20 };
p.say_hello();       // Hello, I'm Tom
println!("{}", p.is_adult());  // true
```

**对比 C++**：

| C++ | Rust |
|-----|------|
| `class Person { void hello(); };` | `struct Person { ... }` + `impl Person { fn hello(&self) {} }` |

Rust 把数据和方法故意分开，好处：定义清晰、可分多个 impl、可给外部类型实现 Trait。

---

## 2. self 的三种形式

| 写法 | 含义 | 类比 C |
|------|------|--------|
| `&self` | 不可变借用，只读 | `const Person* this` |
| `&mut self` | 可变借用，可修改 | `Person* this` |
| `self` | 获得所有权，调用后对象不可再用 | `Person this`（值传递，move） |

```rust
impl Counter {
    fn add(&mut self) {          // &mut self: 修改自身
        self.value += 1;
    }
}

impl User {
    fn consume(self) {           // self: 获得所有权
        println!("{}", self.name);
    }
    // 调用后 User 不可再用
}
```

---

## 3. 关联函数（无 self）

没有 `self` 参数的函数叫**关联函数**，类似 C++ 的静态方法或 Java 的类方法：

```rust
impl Person {
    fn new(name: String, age: u8) -> Person {
        Person { name, age }
    }
}

// 调用用 :: 而不是 .
let p = Person::new(String::from("Tom"), 20);
```

习惯上用作构造函数，虽然 Rust 没有真正的 constructor。

---

## 4. 多个 impl 块

一个类型可以有多个 impl 块，编译器会合并：

```rust
impl Person { /* 基本方法 */ }
impl Person { /* 网络相关 */ }
impl Person { /* 文件相关 */ }
```

大型项目常用，按功能分组。

---

## 5. impl Trait（接口实现）

```rust
trait Animal {
    fn speak(&self);
}

struct Dog;

impl Animal for Dog {
    fn speak(&self) {
        println!("wang");
    }
}
```

| 写法 | 含义 |
|------|------|
| `impl Person` | 为 Person 添加固有方法 |
| `impl Trait for Person` | 为 Person 实现 Trait（类似接口） |

---

## 6. 对应关系速查

| 概念 | C++ | Rust |
|------|-----|------|
| 数据 + 方法 | `class` | `struct` + `impl` |
| 接口 | `class`（纯虚函数） | `trait` + `impl Trait for Type` |
| 构造函数 | `ClassName()` | `Type::new()`（关联函数） |
| 静态方法 | `static void func()` | 无 self 的 fn |
| this 指针 | `this` | `&self` / `&mut self` / `self` |

**核心记忆**：`impl Type` 给类型绑方法，`impl Trait for Type` 实现接口。
