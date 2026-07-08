# Cargo — Rust 包管理器与构建工具

## 1. 基础命令

```bash
# 创建新项目
cargo new my_project             # 二进制项目
cargo new my_lib --lib           # 库项目

# 构建
cargo build                      # 调试构建
cargo build --release            # 发布构建（启用优化）
cargo build --target <target>    # 交叉编译到指定目标

# 运行
cargo run                        # 构建并运行
cargo run -- arg1 arg2           # 向程序传递参数

# 检查（不生成二进制，快速验证编译）
cargo check

# 清理
cargo clean
```

---

## 2. Cargo.toml — 项目清单

```toml
[package]
name = "my_project"
version = "0.1.0"
edition = "2021"                 # Rust Edition：2015 / 2018 / 2021 / 2024
authors = ["name <email>"]
description = "..."              # crates.io 发布时必填
license = "MIT"
repository = "https://..."
readme = "README.md"

[dependencies]
# 来自 crates.io
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["full"] }

# git 仓库依赖
my_crate = { git = "https://github.com/user/repo.git", branch = "main" }
my_crate = { git = "https://github.com/user/repo.git", tag = "v1.0.0" }

# 本地路径依赖
my_crate = { path = "../my_crate" }

[dev-dependencies]              # 仅在测试、示例、bench 中可用
pretty_assertions = "1"

[build-dependencies]            # 构建脚本 (build.rs) 中可用
cc = "1"

[features]                      # 条件编译特性
default = ["std"]
std = []
serde_support = ["dep:serde"]

[profile.release]               # 覆盖发布配置
opt-level = 3                   # 优化级别 0-3 / "s" / "z"
lto = true                      # 链接时优化
codegen-units = 1               # 单代码生成单元，提升优化
strip = "symbols"               # 去除符号表，减小体积
```

---

## 3. 依赖管理

### 版本指定

| 写法 | 含义 |
|------|------|
| `"1.17"` | `^1.17`，兼容 1.17.x ~ <2.0.0 |
| `"^1.17"` | 同上 |
| `"~1.17"` | 兼容 1.17.x ~ <1.18.0 |
| `"=1.17"` | 精确匹配 1.17 |
| `">=1.17, <2"` | 范围指定 |
| `"*"` | 任意版本（不推荐） |

### 更新依赖

```bash
cargo update                    # 更新 Cargo.lock 中所有兼容版本
cargo update -p crate_name      # 仅更新指定 crate
cargo outdated                  # 查看可更新的依赖（需要 cargo-outdated）
```

### 依赖树

```bash
cargo tree                      # 显示依赖树
cargo tree -i crate_name        # 反向：谁依赖了这个 crate
cargo tree -e features          # 查看 features 如何开启
```

---

## 4. 测试与文档

```bash
# 测试
cargo test                      # 运行所有测试
cargo test test_name            # 运行名称匹配的测试
cargo test -- --nocapture       # 显示 println 输出
cargo test -- --test-threads=1 # 单线程执行

# 仅运行文档测试
cargo test --doc

# 文档
cargo doc                       # 生成文档 (target/doc/)
cargo doc --open                # 生成并打开
cargo doc --no-deps             # 仅生成自身文档，不含依赖文档

# 示例
cargo run --example example_name  # 运行 examples/ 中的示例
```

---

## 5. 发布与包管理

```bash
# 发布前检查
cargo package                   # 验证并生成 .crate 包
cargo publish --dry-run         # 模拟发布

# 发布到 crates.io
cargo login                     # 登录（输入 API token）
cargo publish                   # 发布当前版本

# 安装/卸载二进制 crate
cargo install <crate_name>      # 安装（到 ~/.cargo/bin/）
cargo install --list            # 列出已安装
cargo uninstall <crate_name>    # 卸载
```

### 版本号语义 (SemVer)

**主版本.次版本.补丁** (如 `1.24.7`)：
- **补丁**：向后兼容的 bug 修复
- **次版本**：向后兼容的新功能
- **主版本**：不兼容的 API 变更

**预发布标记**：`1.0.0-alpha.1`、`1.0.0-beta.2`、`1.0.0-rc.1`

---

## 6. Workspace — 多包项目管理

```toml
# 顶层 Cargo.toml
[workspace]
members = [
    "crates/core",
    "crates/cli",
    "crates/web",
]
resolver = "2"                  # 特性解析器 v2
```

```bash
cargo build --workspace         # 构建整个 workspace
cargo test -p <crate_name>      # 测试 workspace 中的特定 crate
```

工作区规则：
- 根级 `Cargo.lock` 统一管理所有依赖版本
- 各子包的 `Cargo.toml` 用 `path =` 引用兄弟包
- 只有根级可以包含 `[workspace]`；子包依赖共享

---

## 7. 构建脚本 (build.rs)

```rust
// build.rs — 在编译前运行，用于生成代码、链接系统库等
fn main() {
    // 在编译时设置环境变量
    println!("cargo:rustc-link-lib=ssl");
    println!("cargo:rerun-if-changed=src/protos/");

    // 生成 Rust 源码
    prost_build::compile_protos(&["src/protos/data.proto"],
                                &["src/protos/"]).unwrap();
}
```

常用指令：
- `cargo:rerun-if-changed=PATH` — 仅当文件变更时才重新运行 build.rs
- `cargo:rustc-link-lib=LIB` — 链接系统库
- `cargo:rustc-link-search=DIR` — 添加链接搜索路径
- `cargo:rustc-env=VAR=VALUE` — 编译时设置环境变量（可用 `env!()` 访问）

---

## 8. 配置文件 — `.cargo/config.toml`

位置：项目根 `.cargo/config.toml` 或全局 `~/.cargo/config.toml`

```toml
# 替换依赖源（加速国内下载，推荐使用镜像）
[source.crates-io]
replace-with = "rsproxy"

[source.rsproxy]
registry = "https://rsproxy.cn/crates.io-index"

# 设置默认 target
[build]
target = "thumbv7em-none-eabihf"
rustflags = ["-C", "link-arg=-Tmemory.x"]

# 设置镜像（中科大）
[source.ustc]
registry = "https://mirrors.ustc.edu.cn/crates.io-index"

# 设置环境变量
[env]
RUST_LOG = "debug"
```

### 国内镜像配置

创建 `~/.cargo/config.toml`（或项目 `.cargo/config.toml`）：

```toml
[source.crates-io]
replace-with = "rsproxy"

[source.rsproxy]
registry = "https://rsproxy.cn/crates.io-index"

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[registries.rsproxy]
index = "https://rsproxy.cn/crates.io-index"
```

---

## 9. 常用技巧

### 条件编译特性 (Features)

```toml
[features]
default = ["std"]
std = []
# 开启一个特性会自动开启它依赖的特性
alloc = ["dep:allocator"]
```

```rust
// 在代码中使用
#[cfg(feature = "std")]
fn use_std() { ... }

#[cfg(not(feature = "std"))]
fn no_std() { ... }
```

### 减小二进制体积

```toml
[profile.release]
opt-level = "z"      # 按大小优化
lto = true           # 链接时优化
codegen-units = 1    # 单代码生成单元
strip = true         # 去除符号
panic = "abort"      # 去除 panic 展开代码
```

### no_std 嵌入式项目

```toml
[package]
name = "firmware"

[dependencies]
cortex-m = "0.7"
cortex-m-rt = "0.7"
panic-halt = "0.2"   # 或 panic-abort

[build]
# cross.toml 或 .cargo/config.toml 中指定
target = "thumbv7em-none-eabihf"
```

---

## 10. 常用工具与扩展

```bash
# 安装常用工具
cargo install cargo-edit         # cargo add / rm / upgrade
cargo install cargo-watch        # 文件变更时自动重新运行
cargo install cargo-expand       # 展开宏（查看宏展开结果）
cargo install cargo-udeps        # 检测未使用的依赖
cargo install cargo-audit        # 检查依赖安全漏洞
cargo install cargo-fmt          # 格式化（通常 rustup 自带）
cargo install cargo-clippy       # 代码检查（通常 rustup 自带）

# 用法
cargo add serde                  # 添加依赖
cargo rm serde                   # 移除依赖
cargo watch -x check             # 修改后自动 cargo check
cargo expand                     # 展开宏
cargo udeps                      # 找出未使用的依赖
cargo audit                      # 安全检查
cargo fmt                        # 格式化代码
cargo clippy                     # 代码 lint
```

---

## 11. Cargo 环境变量

| 变量 | 说明 |
|------|------|
| `CARGO_MANIFEST_DIR` | 当前包的目录路径 |
| `CARGO_PKG_VERSION` | 包版本号 |
| `CARGO_PKG_NAME` | 包名 |
| `CARGO_CFG_TARGET_ARCH` | 目标架构 (如 x86_64) |
| `OUT_DIR` | build.rs 输出目录（编译时生成的文件放这里） |

代码中使用：
```rust
let version = env!("CARGO_PKG_VERSION");
let dir = env!("CARGO_MANIFEST_DIR");
```

---

## 12. 快速参考卡片

| 场景 | 命令 |
|------|------|
| 新建项目 | `cargo new name` |
| 新建库 | `cargo new lib_name --lib` |
| 快速检查 | `cargo check` |
| 构建 | `cargo build --release` |
| 运行 | `cargo run -- args` |
| 测试 | `cargo test` |
| 生成 doc | `cargo doc --open` |
| 添加依赖 | `cargo add cratename` |
| 升级依赖 | `cargo update` |
| 查看依赖树 | `cargo tree` |
| 发布 | `cargo publish` |
| 安装工具 | `cargo install name` |
| 代码检查 | `cargo clippy` |
| 格式化 | `cargo fmt` |
