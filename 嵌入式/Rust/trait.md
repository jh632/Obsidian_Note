# Trait

**如果说 `impl` 是"怎么做"，那么 `trait` 就是"应该会做什么"。**

## 为什么需要 Trait

假设有两种动物：

```rust
struct Dog;
struct Cat;
```

直接给它们各自实现 `speak`：

```rust
impl Dog {
    fn speak(&self) {
        println!("wang");
    }
}
impl Cat {
    fn speak(&self) {
        println!("miao");
    }
}
```

虽然都叫 `speak`，但 **Rust 并不知道它们有什么共同点**。无法写一个统一的函数：

```rust
fn make_sound(animal: ???) {
    animal.speak();
}
```

Dog？Cat？都不对。这时候就需要 **Trait**。

---

## Trait 本质是什么

Trait 可以理解为 **一种能力（Capability）**：

```rust
trait Animal {
    fn speak(&self);
}
```

这句话没有写任何代码，只是规定：

> **谁说自己是 Animal，就必须会 `speak()`。**

类似现实中的接口：

```
接口：会飞
-------
fly()

谁实现？
鸟、飞机、超人
```

它们长得完全不同，但都有 `fly()`。这就是 Trait。

---

## 实现 Trait

```rust
impl Animal for Dog {
    fn speak(&self) {
        println!("wang");
    }
}

impl Animal for Cat {
    fn speak(&self) {
        println!("miao");
    }
}
```

结构关系：

```
Animal
   │
   ├──── Dog
   │
   └──── Cat
```

Dog 和 Cat 都属于 Animal —— 不是因为继承，而是因为 **它们都实现了 Animal Trait**。

---

## Trait 最大的作用 —— 多态

有了 Trait，可以写泛型函数：

```rust
fn make_sound<T: Animal>(animal: &T) {
    animal.speak();
}
```

调用：

```rust
let dog = Dog;
let cat = Cat;
make_sound(&dog);
make_sound(&cat);
```

输出：

```
wang
miao
```

`T: Animal` 意思是：

> **T 可以是任何类型，只要它实现了 Animal Trait。**

对比 C++：

```cpp
class Animal {
public:
    virtual void speak() = 0;
};
```

Trait 很大程度上承担了 **接口 + 抽象类** 的职责。

---

## Rust 为什么不用继承

Rust 故意没有 `class Dog : public Animal` 这种语法，因为继承会带来问题：

```
Animal
  ↓
Dog
  ↓
PoliceDog
  ↓
SpecialPoliceDog
```

层数越来越深。Rust 认为：

> **不要问"是什么"，而要问"会什么"。**

例如 Dog 会叫、会跑、会游泳，这些能力可以用 Trait 表示：

```rust
trait Speak {}
trait Run {}
trait Swim {}

impl Speak for Dog {}
impl Run for Dog {}
impl Swim for Dog {}
```

结构：

```
Dog
 ├── Speak
 ├── Run
 └── Swim
```

这比继承灵活得多。

---

## Trait 类比 Java 接口

如果你学过 Java：

```java
// Java
interface Animal {
    void speak();
}
class Dog implements Animal {
    public void speak() { ... }
}
```

```rust
// Rust
trait Animal {
    fn speak(&self);
}
impl Animal for Dog {
    fn speak(&self) { ... }
}
```

几乎一一对应。

---

## 标准库到处都是 Trait

你每天都在用：

### Debug —— 打印

```rust
#[derive(Debug)]
struct Person {
    name: String,
}

println!("{:?}", person);
```

`Debug` 就是 Trait，展开后类似 `impl Debug for Person { ... }`。

### PartialEq —— 比较

```rust
#[derive(PartialEq)]
struct Point {
    x: i32,
}

// 没有这个 Trait，point1 == point2 编译会报错
```

### Clone —— 克隆

```rust
#[derive(Clone)]
// 展开就是 impl Clone for Type
```

---

## 总结

| 概念 | 作用 | 类比 |
|------|------|------|
| `struct` | 定义数据 | C 的 `struct` |
| `impl Type` | 给类型添加方法 | C++ 成员函数 |
| `trait` | 定义一组行为规范（能力） | Java `interface` / C++ 抽象接口 |
| `impl Trait for Type` | 让某个类型具备这种能力 | `implements` / 实现接口 |

一句话记忆：

```
struct：我有什么（数据）
impl：我能做什么（方法）
trait：别人要求我必须会什么（能力/接口）
```

对于有 C 和嵌入式开发背景的人，先把 **Trait 当作"接口"** 来理解即可。等学到泛型（`T: Trait`）、`dyn Trait` 和标准库中的 `Read`、`Write`、`Iterator` 等 Trait 后，会发现 Rust 大部分抽象能力都是围绕 Trait 构建的。
