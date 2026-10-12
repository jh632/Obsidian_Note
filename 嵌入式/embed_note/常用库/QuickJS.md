---
date: 2026-10-12
tags: [embed_note, 常用库, JavaScript, 脚本引擎]
aliases: [QuickJS 学习笔记, JavaScript 嵌入式引擎]
---

# QuickJS：轻量 JavaScript 引擎与嵌入式集成

> 学习目标：理解 JavaScript 如何在 C 程序中运行，能够执行脚本、绑定 C 函数，并把脚本任务接入 RTOS 事件循环。
> 本笔记以 Fabrice Bellard 的原版 QuickJS 为对象；QuickJS-NG 是另一个分支，集成时不要混用两者的头文件、库和字节码。

## 1. QuickJS 到底是什么

**QuickJS 是用 C 实现的 JavaScript 引擎，可以嵌入其他程序，让程序执行 JavaScript 脚本。**“模拟 JavaScript 引擎”可以理解为用软件实现语言执行机制，但它实际执行 JavaScript，不是模拟浏览器或 CPU。

JavaScript 是语言，QuickJS 是实现这门语言的引擎，宿主程序则负责提供硬件和系统能力。

| 层次 | 负责什么 | 嵌入式例子 |
| --- | --- | --- |
| JavaScript 脚本 | 业务规则、状态判断、流程编排 | 温度超过阈值时打开风扇 |
| QuickJS 引擎 | 解析代码、执行字节码、管理 JS 对象 | 执行 `if (temp > 30) ...` |
| C/C++ 宿主 | 暴露 API、调度事件、管理资源 | 提供 `readTemperature()`、`setFan()` |
| RTOS / 驱动 | 实际操作设备 | I²C 读传感器、GPIO 控制风扇 |

引擎内建 `Object`、`Array`、`JSON`、`Promise` 等语言对象，但 **DOM、GPIO、网络、`setTimeout()` 都属于宿主能力**。`qjs` 命令行工具会额外提供辅助功能；直接调用 `JS_NewContext()` 不会自动得到这些功能，也不能直接运行任意 Node.js 项目。

官方文档的 2026-06-04 版本说明支持大部分 ES2025 特性；具体语法支持以实际使用的版本为准。学习时先关注函数、对象、模块、Promise 和 C API。

## 2. 为什么嵌入式项目会用它

可以把经常变化的业务规则放进脚本，例如按键动作、传感器阈值、设备联动和 UI 逻辑。驱动、协议栈和资源管理仍由固件负责。

```text
传感器 / 按键 / 网络回调
          │ 复制事件数据到队列
          ▼
       JS 专用任务
          │ 调用脚本处理函数
          ▼
  JavaScript：判断业务条件
          │ 调用宿主暴露的 C 函数
          ▼
     驱动或设备工作任务
```

收益是业务逻辑更容易修改；代价是引擎代码体积、对象堆内存、解释执行开销和集成复杂度。脚本更新是否需要重刷固件，取决于宿主是否支持独立存储和加载脚本。

**“轻量”不代表适合所有 MCU。**先在 PC 学习接口，再在目标板测量 Flash、空闲 RAM、任务栈和最坏执行时间。硬实时控制、ISR 和高频采样处理优先用 C/C++；脚本适合较低频的业务编排。

## 3. 执行原理：源码 → 字节码 → 解释执行

```text
JavaScript 源码
      │ 词法 / 语法分析，直接生成并优化字节码
      ▼
QuickJS 字节码（栈式虚拟机指令）
      │ 解释器逐条执行
      ▼
结果、异常，或对宿主 C 函数的调用
```

原版 QuickJS 使用字节码解释器，没有 JIT。CPU 运行的是编译后的 QuickJS C 代码，解释器根据字节码完成加法、属性访问、函数调用等操作。

`qjsc` 可以将 JS 编译成包含字节码的 C 文件，再与引擎一起编译成程序。**这不等于把每条 JS 语句直接翻译成机器码**；程序仍需要解释器执行字节码。满足构建条件时可裁掉运行时源码编译器，是否真正节省空间要看链接结果。

## 4. 三个核心概念

| 概念 | 可以怎样理解 | 注意事项 |
| --- | --- | --- |
| `JSRuntime` | 管理对象堆、GC 和执行资源的运行时 | 一个运行时不能被多个线程同时使用 |
| `JSContext` | 一个 JS 执行环境（Realm） | 有自己的全局对象和内建对象 |
| `JSValue` | 一个 JS 值的 C 侧表示 | 可表示数字、字符串、对象、函数等 |

一个 `JSRuntime` 可以包含多个 `JSContext`，同一运行时中的上下文可以共享对象。不同运行时之间不能直接传递 JS 对象，应使用序列化数据等方式通信。多个 Context 也不等于进程级隔离。

典型生命周期：

```text
JS_NewRuntime()
  → 设置内存、栈和中断限制
  → JS_NewContext()
  → 注册宿主函数
  → JS_Eval() / JS_Call()
  → 处理事件与 Promise jobs
  → 释放宿主持有的 JSValue
  → JS_FreeContext()
  → JS_FreeRuntime()
```

## 5. 第一步：在 PC 上运行脚本

先从 [官方发布页](https://bellard.org/quickjs/) 下载原版源码。在 Linux 或 Windows 的 WSL 中，安装 C 编译器和 `make`，进入解压后的源码目录：

```bash
# 在 Linux / WSL 终端执行，不是在 PowerShell 中执行
make
./qjs -e 'print(20 + 22)'
./qjs hello.js
```

`hello.js`：

```javascript
function shouldStartFan(temperature, threshold) {
    return temperature > threshold;
}

print(shouldStartFan(32, 30)); // true
```

这里的 `print()` 由 `qjs` 工具提供。下一节自己创建宿主程序时，需要自行注册输出或其他系统函数。

## 6. 最小 C 宿主：JS 调用 C，C 读取结果

这个例子把 C 函数注册为全局 `hostAdd()`，执行 `hostAdd(20, 22)`，然后把结果转成 C 字符串输出。

```c
#include <stdio.h>
#include "quickjs.h"

static void dump_exception(JSContext *ctx)
{
    JSValue exception = JS_GetException(ctx);
    const char *message = JS_ToCString(ctx, exception);
    fprintf(stderr, "JS exception: %s\n",
            message ? message : "<cannot convert exception to string>");
    if (message) {
        JS_FreeCString(ctx, message);
    } else {
        // 异常对象转字符串也可能抛异常，清理这个新的异常。
        JSValue secondary = JS_GetException(ctx);
        JS_FreeValue(ctx, secondary);
    }
    JS_FreeValue(ctx, exception);
}

static JSValue js_host_add(JSContext *ctx, JSValueConst this_val,
                           int argc, JSValueConst *argv)
{
    (void)this_val;
    if (argc < 2)
        return JS_ThrowTypeError(ctx, "hostAdd requires two arguments");

    double a, b;
    if (JS_ToFloat64(ctx, &a, argv[0]) < 0 ||
        JS_ToFloat64(ctx, &b, argv[1]) < 0)
        return JS_EXCEPTION;

    return JS_NewFloat64(ctx, a + b);
}

int main(void)
{
    int status = 1;
    JSRuntime *rt = JS_NewRuntime();
    if (!rt)
        return 1;

    JSContext *ctx = JS_NewContext(rt);
    if (!ctx) {
        JS_FreeRuntime(rt);
        return 1;
    }

    JSValue global = JS_GetGlobalObject(ctx);
    JSValue fn = JS_NewCFunction(ctx, js_host_add, "hostAdd", 2);
    if (JS_IsException(fn)) {
        JS_FreeValue(ctx, global);
        dump_exception(ctx);
        goto cleanup;
    }

    // JS_SetPropertyStr 接管 fn；即使设置失败，也不要再次释放 fn。
    int rc = JS_SetPropertyStr(ctx, global, "hostAdd", fn);
    JS_FreeValue(ctx, global);
    if (rc < 0) {
        dump_exception(ctx);
        goto cleanup;
    }

    const char script[] = "hostAdd(20, 22)";
    JSValue result = JS_Eval(ctx, script, sizeof(script) - 1,
                             "demo.js", JS_EVAL_TYPE_GLOBAL);
    if (JS_IsException(result)) {
        dump_exception(ctx);
    } else {
        const char *text = JS_ToCString(ctx, result);
        if (text) {
            printf("%s\n", text); // 预期输出：42
            JS_FreeCString(ctx, text);
            status = 0;
        } else {
            dump_exception(ctx);
        }
    }
    JS_FreeValue(ctx, result);

cleanup:
    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);
    return status;
}
```

编译时包含对应版本的 `quickjs.h`，链接同版本的 QuickJS 库；构建宏和系统库依照该版本的 Makefile。上例是 PC 宿主示例，移植到 ESP-IDF / Zephyr 时还要处理工具链、平台依赖和组件构建。

调用链：`JS_Eval()` → JS 执行 `hostAdd()` → `js_host_add()` → `JS_NewFloat64()` → C 获取返回值。

`JS_NewCFunction(..., 2)` 中的 `2` 是函数的声明参数个数，不会自动校验传入参数；要在回调中检查 `argc`。`JS_ToFloat64()` 会按 JS 规则做类型转换；若硬件 API 必须接收数字，应先用 `JS_IsNumber()` 等函数严格校验，再检查数值范围。

## 7. 最容易出错的部分：JSValue 所有权

QuickJS 使用**引用计数 + 循环引用回收**。有 GC 并不意味着 C 侧拿到的值可以不释放。

| 场景 | 所有权规则 | 正确动作 |
| --- | --- | --- |
| `JS_Eval()`、`JS_Call()`、`JS_GetPropertyStr()` 返回值 | 通常是调用方持有的新引用 | 用完 `JS_FreeValue()` |
| C 回调的 `argv`、`this_val` | 借用引用 | 不要直接释放 |
| 要长期保存借用值 | 需要自己的引用 | `JS_DupValue()`，结束时释放 |
| `JS_SetPropertyStr()` 的 value 参数 | 接管传入值 | 不再释放这个引用；失败也会消耗 |
| `JS_ToCString()` 返回字符串 | 引擎分配的字符串 | `JS_FreeCString()`，不要 `free()` |
| `JS_GetException()` 返回异常值 | 调用方持有 | 记录后 `JS_FreeValue()` |

其他 API 是否接管所有权，要查对应接口，不能一概套用。

```c
// 想保存一个 JS 回调：不能只做 callback = argv[0]。
JSValue callback = JS_DupValue(ctx, argv[0]);

// 后续在同一个运行时所属的 JS 任务中调用它。
JSValue result = JS_Call(ctx, callback, JS_UNDEFINED, 0, NULL);
if (JS_IsException(result))
    dump_exception(ctx);
JS_FreeValue(ctx, result);

// 取消订阅 / 销毁时：
JS_FreeValue(ctx, callback);
```

真实订阅接口还需要检查 `JS_IsFunction()`；替换旧回调时先释放旧引用。所有回调引用应在 Context 销毁前清理。

## 8. 异常：返回值和异常对象是两回事

`JS_EXCEPTION` 是“发生异常”的标记，真正的异常对象保存在 Context 中。C 必须先检查 `JS_IsException()`，再用 `JS_GetException()` 取出并处理。

脚本抛异常、数值转换失败、内存分配失败都可能进入这条路径。调试时可进一步读取异常对象的 `stack` 属性；读取属性本身也可能失败，因此也要检查异常。

需要制造 C 侧异常时，可返回 `JS_ThrowTypeError()`、`JS_ThrowRangeError()` 等接口的结果。对硬件操作，则先定义好错误语义，例如参数错误抛异常，异步设备失败 reject Promise。

## 9. Promise 不会自己驱动事件循环

```javascript
Promise.resolve(42).then(value => hostAdd(value, 1));
```

`JS_Eval()` 返回并不意味着所有 `.then()` 都执行完了。裸引擎提供 Promise job 队列，宿主需要调用 `JS_ExecutePendingJob()` 推进它。

```c
// 一次只处理有限个 job，避免微任务不断生成而占住 JS 任务。
for (int i = 0; i < 16; ++i) {
    JSContext *job_ctx = NULL;
    int rc = JS_ExecutePendingJob(rt, &job_ctx);
    if (rc == 0)
        break; // 当前没有 job
    if (rc < 0) {
        dump_exception(job_ctx);
        break;
    }
}
```

`16` 只是演示批次上限，还要配合单次执行超时和 RTOS 调度。事件循环要同时处理硬件事件与 jobs；队列没有硬件事件时，也不能把仍有 jobs 的 JS 任务永久阻塞。`JS_IsJobPending()` 可用于判断是否还有待执行的 job。

**Promise job 队列不包含完整的硬件 I/O 和定时器管理。**`setTimeout()`、网络完成事件和异步传感器读取，都需要宿主实现。完整应用还应通过 `JS_SetHostPromiseRejectionTracker()` 记录未处理的 Promise rejection。

## 10. 嵌入式集成时的约束

### 10.1 一个运行时交给一个任务使用

推荐使用专用 JS 任务持有 Runtime、Context 和全部 JSValue。驱动回调、其他 RTOS 任务和 ISR 通过队列发送普通 C 数据，由 JS 任务统一调用脚本。

不要从 ISR 执行 JS；不要把一个 `JSValue` 当成普通消息跨运行时传递。异步队列中的字符串和缓冲区还要明确由谁复制、谁释放。

### 10.2 限制内存、栈和执行时间

| API | 作用 | 边界 |
| --- | --- | --- |
| `JS_SetMemoryLimit()` | 限制 Runtime 经引擎分配器分配的内存 | 不覆盖宿主自行分配的所有缓冲区 |
| `JS_SetMaxStackSize()` | 设置引擎使用的系统栈上限 | 不会扩大 RTOS 任务实际栈 |
| `JS_SetInterruptHandler()` | 定期检查是否应该停止执行 | 用宿主单调时钟判断截止时间 |
| `JS_NewRuntime2()` | 接入自定义分配器 | 可用于分配统计、平台内存适配 |
| `JS_ComputeMemoryUsage()` | 获取运行时内存统计 | 配合测量堆峰值和任务栈水位 |

中断回调返回非零会请求引擎中断。宿主需要自行维护每轮执行的截止时间，它不是一个自动启动的超时定时器。若 C 绑定函数内部阻塞，JS 中断回调也不能直接打断这个 C 函数，因此硬件绑定应短小，耗时操作尽量异步化。

引用计数通常能及时回收对象，但循环引用回收和解释执行仍有开销，不能据此承诺硬实时性能。

### 10.3 宿主 API 要窄而明确

优先提供 `setLed(bool)`、`readTemperature()` 这样的能力，明确参数范围、错误返回和是否异步。直接开放任意内存地址、文件路径或全部系统调用，会让资源管理和权限控制变得困难。

字节码格式与 QuickJS 版本绑定，不能作为跨版本通用格式；官方说明字节码执行前没有安全校验，不应加载不可信字节码。更新脚本或字节码时，应同时记录引擎版本和宿主 API 版本。

## 11. 源码阅读顺序

| 文件 | 重点看什么 |
| --- | --- |
| `quickjs.h` | 对外 API、JSValue、回调签名 |
| `examples/hello.c` | 官方 JS 模块与 C 函数绑定示例 |
| `qjs.c` | 命令行工具如何创建和运行引擎 |
| `quickjs-libc.c` / `.h` | 标准模块、I/O 和事件循环的参考实现；不是 MCU 必需组件 |
| `quickjs.c` | 编译器、解释器、对象模型和 GC |
| `qjsc.c` | JS 到内嵌字节码 C 文件的编译工具 |

先掌握 API 和生命周期，再从 `JS_Eval()`、`JS_Call()`、`JS_ExecutePendingJob()` 的实现追踪执行路径，最后深入虚拟机指令和 GC。

## 12. 分阶段练习

- [ ] 在 PC 用 `qjs` 运行函数、对象、JSON 和模块，分清 JS 语言能力与宿主 API。
- [ ] 编译最小 C 宿主，得到 `42`；把脚本改成 `throw new Error('test')` 验证异常路径。
- [ ] 绑定模拟的 `setLed()`，让 JS 根据温度决定 LED 状态；加入参数校验。
- [ ] 保存并调用一个 JS 回调，反复注册和注销，检查引用是否正确释放。
- [ ] 执行 Promise 示例，观察有无 `JS_ExecutePendingJob()` 时的差异。
- [ ] 实现超时中断，用 `while (true) {}` 验证脚本可被终止。
- [ ] 选 ESP-IDF 或 Zephyr 集成，采用事件队列 → JS 任务 → C 绑定的结构。
- [ ] 测量加载脚本、处理事件和回收对象时的内存峰值、栈水位和耗时，再决定是否用于实际项目。

## 参考

- [QuickJS 官方主页与源码下载](https://bellard.org/quickjs/)
- [QuickJS 官方文档](https://bellard.org/quickjs/quickjs.html)：重点看 C API、Memory handling、Execution timeout and interrupts、Internals。
- [原版 QuickJS 源码仓库](https://github.com/bellard/quickjs)
- [MDN JavaScript 指南](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Guide)

## 相关笔记

- [[cJSON]]：只解析和生成 JSON；QuickJS 则能执行 JS 逻辑，且有内建 `JSON` 对象。
- [[嵌入式设计模式-事件总线]]：将驱动事件交给脚本任务的组织方式。
- [[任务和协程]]：理解脚本任务、异步 job 与 RTOS 调度的区别。
- [[嵌入式内存优化实战]]：评估引擎和业务脚本的资源开销。
- [[01-ESP-IDF-项目结构与构建工具]]
- [[02-Zephyr-项目结构与构建配置]]
