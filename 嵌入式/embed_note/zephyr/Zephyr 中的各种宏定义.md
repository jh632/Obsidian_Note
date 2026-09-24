---
date: 2026-09-18
tags: [embed_note, zephyr]
aliases: [zephyr宏定义, Zephyr 各种宏定义]
---

# Zephyr 中的各种宏定义

> 按类别组织的 Zephyr 常用宏速查，对照 Zephyr main 分支（4.x）源码核对。
> 大纲先行，后续学习中逐条补充。

## 线程与定时器

- [x] `K_THREAD_DEFINE(name, stack_size, entry, p1, p2, p3, prio, options, delay)` — 静态定义线程和它的线程栈 ✅ 2026-09-20
	- `name` 是 `k_tid_t`，其他文件可用 `extern const k_tid_t <name>;` 引用
	- `delay` 为 0 时启动后立即可被调度，非 0 表示延时启动（毫秒）
- [ ] `K_KERNEL_THREAD_DEFINE(...)` — 参数相同，线程只能运行在内核模式，不能进入用户模式
- [x] `K_THREAD_STACK_DEFINE(name, size)` — 单独定义线程栈数组，配合 `k_thread_create()` 使用 ✅ 2026-09-20
- [ ] `K_TIMER_DEFINE(name, expiry_fn, stop_fn)` — 静态定义 `struct k_timer`
- [ ] `K_TIMER_OBSERVER_DEFINE(name, init, start, stop, expiry)` — 静态定义 `struct k_timer_observer`，需 `CONFIG_TIMER_OBSERVER`

## 同步原语

- [ ] `K_SEM_DEFINE(name, initial_count, count_limit)` — 静态定义 `struct k_sem`
	- 编译期检查：`count_limit` 非 0、`initial_count` 不超过 `count_limit`、`count_limit` 不超过 `K_SEM_MAX_LIMIT`
- [ ] `K_MUTEX_DEFINE(name)` — 静态定义 `struct k_mutex`，初始无持有者
- [ ] `K_CONDVAR_DEFINE(name)` — 静态定义 `struct k_condvar`
- [ ] `K_EVENT_DEFINE(name)` — 静态定义 `struct k_event`

## 数据传递

- [ ] `K_MSGQ_DEFINE(q_name, q_msg_size, q_max_msgs, q_align)` — 静态定义 `struct k_msgq` 和消息 ring buffer
	- `q_align` 填 1 即可，ring buffer 不要求对齐
	- 不能加 `static` 关键字，需要文件内可见改用 `K_MSGQ_DEFINE_STATIC`
- [ ] `K_MSGQ_DEFINE_TYPE(q_name, q_msg_type, q_max_msgs)` — 按消息类型自动取 `sizeof` 和 `__alignof`
- [ ] `K_FIFO_DEFINE(name)` / `K_LIFO_DEFINE(name)` — 静态定义 `struct k_fifo` / `struct k_lifo`，队列里存放指针
- [ ] `K_STACK_DEFINE(name, stack_num_entries)` — 静态定义 `struct k_stack` 和存放 `stack_data_t` 值的数组
- [ ] `K_PIPE_DEFINE(name, pipe_buffer_size, pipe_align)` — 静态定义 `struct k_pipe` 和 ring buffer
- [ ] `K_MBOX_DEFINE(name)` — 静态定义 `struct k_mbox`
- [ ] `K_QUEUE_DEFINE(name)` — 静态定义 `struct k_queue`

## 内存管理

- [x] `K_MEM_SLAB_DEFINE(name, slab_block_size, slab_num_blocks, slab_align)` — 静态定义固定块内存池和 buffer ✅ 2026-09-20
	- 编译期检查：块大小必须是 `slab_align` 的倍数、`slab_align` 必须是 2 的幂
	- 不能加 `static` 关键字，需要文件内可见改用 `K_MEM_SLAB_DEFINE_STATIC`
	- buffer 变量名 `_k_mem_slab_buf_<name>`，段标签 `k_mem_slab_buf_<name>`，尺寸与对齐经 `WB_UP` 取整
- [ ] `K_MEM_SLAB_DEFINE_TYPE(name, type, slab_num_blocks)` — 块大小与对齐取自 `sizeof(type)`、`__alignof(type)`
- [ ] `K_MEM_SLAB_DEFINE_IN_SECT(name, in_section, ...)` — 把 buffer 放进 `in_section` 指定的内存段
- [ ] `K_HEAP_DEFINE(name, bytes)` — 静态定义 `struct k_heap` 和 `bytes` 大小的内存区域，段标签 `kheap_buf_<name>`
- [ ] `K_HEAP_DEFINE_NOCACHE(name, bytes)` — 同上，内存区域在非缓存内存

## 工作项

- [ ] `K_WORK_DEFINE(work, work_handler)` — 静态定义 `struct k_work`，可加 `static` 前缀限制在本文件
- [ ] `K_WORK_DELAYABLE_DEFINE(work, work_handler)` — 静态定义 `struct k_work_delayable`
- [ ] `K_WORK_USER_DEFINE(work, work_handler)` — 静态定义 `struct k_work_user`

## 命名变体

- [ ] 无后缀 — 外部链接，其他文件用 `extern struct k_xxx <name>;` 访问
- [ ] `_STATIC` — 只在定义它的文件内可见，只有 `K_MSGQ_DEFINE` 和 `K_MEM_SLAB_DEFINE` 两族有
- [ ] `_TYPE` — 用 `sizeof(type)` 和 `__alignof(type)` 代替手写的块大小与对齐
- [ ] `_IN_SECT` — 通过 `in_section` 参数指定存储所在的内存段，只有 `K_MEM_SLAB_DEFINE` 有

## 定义宏展开结构

以 `K_MEM_SLAB_DEFINE(my_slab, 64, 10, 4)` 为例，宏体展开出三个部分：

- [ ] 编译期检查 — `BUILD_ASSERT` 两条，检查块大小是对齐值的倍数、对齐值是 2 的幂
- [ ] 存储 — buffer 数组 `_k_mem_slab_buf_my_slab`，经 `WB_UP` 取整，放在 noinit 段（启动阶段不清零）
- [ ] 对象 — `STRUCT_SECTION_ITERABLE(k_mem_slab, my_slab) = Z_MEM_SLAB_INITIALIZER(...)`，放进段名 `_k_mem_slab` 的可迭代段
	- 不需要额外 buffer 的宏（`K_SEM_DEFINE`、`K_MUTEX_DEFINE`、`K_TIMER_DEFINE`、`K_FIFO_DEFINE`）宏体只有一条 `STRUCT_SECTION_ITERABLE`
	- `K_THREAD_DEFINE` 展开出 `K_THREAD_STACK_DEFINE` 和线程对象两部分
	- `K_WORK_DEFINE` 不经过可迭代段，直接定义 `struct k_work` 并赋初始值

## 初始化与注册

- [ ] `SYS_INIT(init_fn, level, prio)` — 注册启动时自动调用的初始化函数，按 level、prio 的顺序执行
	- level 取值：`EARLY`、`PRE_KERNEL_1`、`PRE_KERNEL_2`、`POST_KERNEL`、`APPLICATION`、`SMP`
	- `prio` 必须是数字或宏定义的形式，不能是表达式
- [ ] `SYS_INIT_NAMED(name, init_fn, level, prio)` — 同一文件注册多个初始化函数时使用
- [ ] `DEVICE_DT_DEFINE(node_id, init_fn, pm, data, config, level, prio, api, ...)` — 由设备树节点创建 `struct device`
	- level 只接受 `PRE_KERNEL_1`、`PRE_KERNEL_2`、`POST_KERNEL`
	- 内部经 `Z_INIT_ENTRY_SECTION` 排进 `.z_init_<level>_P_<prio>_SUB_<sub>` 段
- [ ] `DEVICE_DT_INST_DEFINE(inst, ...)` — 参数与上一行相同，节点取自 `DT_DRV_INST(inst)`
- [ ] `DEVICE_DT_GET(node_id)` — 取得设备对象指针，使用前用 `device_is_ready()` 检查
- [ ] `LOG_MODULE_REGISTER(module_name[, level])` — 注册日志模块，每个模块只在一个文件里调用一次
- [ ] `LOG_MODULE_DECLARE(module_name[, level])` — 多文件模块的其他文件引用已经注册过的模块

## 段与存储位置

- [ ] `__noinit` — `__in_section_unique(noinit)`，放进 noinit 段，启动阶段不清零
- [ ] `__noinit_named(name)` — 同上，段名里带上 `name`，每个变量单独成段
- [ ] `__aligned(n)` — 变量按 n 字节对齐
- [ ] `__in_section(sec, subsec, name)` — 放进指定名字的段
- [ ] `__in_section_unique(seg)` / `__in_section_unique_named(seg, name)` — 每个使用处单独成段，段名用 `__COUNTER__` 或指定名字区分
- [ ] `__nocache` — `CONFIG_NOCACHE_MEMORY` 开启时为 `__in_section_unique(_NOCACHE_SECTION_NAME)`，放进非缓存内存段
- [ ] `WB_UP(x)` / `WB_DN(x)` — 按字长（`sizeof(void *)`）向上/向下取整
- [ ] `STRUCT_SECTION_ITERABLE(type, name)` — 把对象放进以类型名命名的可迭代段（段名带下划线前缀），用 `STRUCT_SECTION_FOREACH` 遍历

## 编译期工具

- [ ] `BUILD_ASSERT(cond[, msg])` — 编译期断言，`cond` 不成立时编译报错
- [ ] `ARRAY_SIZE(array)` — 数组的元素个数
- [ ] `CONTAINER_OF(ptr, type, member)` — 由结构体成员的指针得到外层结构体的指针
- [ ] `ROUND_UP(x, align)` / `ROUND_DOWN(x, align)` — 向上/向下取整到 `align` 的倍数
- [ ] `POINTER_TO_UINT(x)` / `UINT_TO_POINTER(x)` — 指针与整数之间的转换
- [ ] `BIT(n)` / `BIT_MASK(n)` / `GENMASK(h, l)` — 位操作
