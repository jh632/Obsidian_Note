---
date: 2026-11-02
tags:
  - "#安卓IOS开发"
  - "#客户端APP学习路线"
aliases:
  - RN 智能眼镜 APP 学习路线
  - 安卓 iOS 开发学习路线
---

# RN 智能眼镜配套 APP 学习路线

## 学习目标

以维护现有 React Native（RN）项目为目标，逐步具备阅读项目代码、定位问题、修改功能和独立交付业务模块的能力。学习内容围绕智能眼镜配套 APP 展开，重点包括设备管理、BLE 通信、设备配置和状态同步，并结合 AI 辅助开发。

建议按照以下顺序学习，同时从第一周开始阅读和运行现有项目：

```text
TypeScript → React → React Native → BLE → Android / iOS 原生机制 → 项目架构 → 业务模块交付
```

每天投入约 1～2 小时，并结合工作任务练习。

## RN 应用的运行结构

RN 应用由界面、业务代码、RN 运行环境和 Android / iOS 原生能力共同组成。

| 部分 | 常见技术 | 用途 |
| --- | --- | --- |
| 界面 | React | 页面、组件和交互 |
| 业务代码 | TypeScript | 设备管理、状态和业务规则 |
| RN 运行环境 | React Native、Hermes | 执行 JavaScript 并连接原生功能 |
| 原生能力 | Android 的 Kotlin / Java，iOS 的 Swift / Objective-C | 蓝牙、权限和系统服务 |

调用原生功能时，代码通常沿着这条路径运行：

```text
TypeScript → React Native → Native Module → Android API / iOS API
```

例如，APP 在 TypeScript 中发起 BLE 操作，最终会由 Android 的 Bluetooth API 或 iOS 的 CoreBluetooth 完成系统层操作。了解这条路径有助于判断问题来自 RN 业务代码、原生模块还是操作系统。

## 第一阶段：TypeScript 与 React

建议用 5～7 天建立基础，并同步阅读项目中的实际代码。

### TypeScript

优先掌握以下内容：

| 内容 | 用途 | 与 C/C++ 的联系 |
| --- | --- | --- |
| 基本类型 | 表达数字、文本和布尔值 | int、float、char |
| interface、type | 描述对象和业务状态 | struct 等数据描述方式 |
| class | 定义对象及其行为 | class |
| 泛型 | 编写可复用的类型化代码 | template |
| Promise、async、await | 组织异步操作 | 异步任务与流程 |
| 箭头函数 | 编写回调和短函数 | Lambda |
| import、export | 管理模块 | 模块化 |
| 联合类型、类型收窄 | 表达并判断有限状态 | 多种类型与条件判断 |

设备信息可以先用接口描述：

```typescript
interface GlassesDevice {
    id: string;
    name: string;
    macAddress: string;
    connected: boolean;
    battery: number;
    firmwareVersion: string;
}

type ConnectionState =
    | "disconnected"
    | "scanning"
    | "connecting"
    | "connected"
    | "disconnecting"
    | "error";
```

### React

重点理解函数组件、Props、State、useState、useEffect、useRef、useMemo、useCallback、Context 和自定义 Hook。

BLE 开发需要特别理解 useEffect 的副作用和清理过程：

```typescript
useEffect(() => {
    const subscription = startListening();

    return () => {
        subscription.remove();
    };
}, []);
```

页面进入时可以开始页面所需的监听，页面离开时释放监听。设备连接通常要跨页面维持，因此连接对象和连接流程应由设备管理模块持有，避免跟随某个页面的生命周期结束。

## 第二阶段：React Native

建议用 5～7 天熟悉 RN 的界面组件、布局方式和系统接口。

RN 使用 View、Text、Image 等原生组件描述界面，没有 Web 页面里的 DOM。学习时关注：

| 模块 | 需要掌握的内容 | 在眼镜 APP 中的用途 |
| --- | --- | --- |
| Core Components | View、Text、Image、按钮 | 设备列表和设置页面 |
| StyleSheet | Flexbox 布局 | 适配不同屏幕 |
| Navigation | 页面路由和参数传递 | 设备页、设置页之间切换 |
| Platform | Android / iOS 差异判断 | 处理平台行为差异 |
| AppState | 前台、后台和过渡状态 | 应用切换时同步设备状态 |
| Permissions | 运行时权限 | 请求蓝牙相关权限 |
| Native Modules | 原生模块调用 | 使用平台 API |
| Linking | 外部链接和系统页面跳转 | 打开系统设置 |

AppState 对智能眼镜 APP 很重要。用户切换到其他应用后，需要结合产品需求和系统规则判断连接是否继续、Notify 是否继续接收、界面更新是否需要暂停，以及用户返回时如何同步设备状态。

## 第三阶段：BLE 移动端开发

这是与智能眼镜业务联系最紧密的部分，建议用 1～2 周学习，并持续结合项目练习。已有的 ESP32 BLE 经验可以用于理解 GATT Server；手机 APP 侧需要补充 GATT Client 的操作。

### 手机与眼镜的职责

| 眼镜（Peripheral） | 手机 APP（Central） |
| --- | --- |
| GATT Server | GATT Client |
| 提供 Service | 发现 Service |
| 提供 Characteristic | 读取或写入 Characteristic |
| 接收 Write Callback | 写入数据 |
| 发送 Notify | 订阅并接收 Notification |
| 上报连接事件 | 管理连接状态 |

常见交互流程如下：

```text
扫描设备
  ↓
连接设备
  ↓
发现 GATT Services 和 Characteristics
  ↓
订阅 TX Notify
  ↓
向 RX 写入数据并接收设备通知
```

典型自定义服务会使用一个 RX Characteristic 接收 APP 写入的数据，使用一个 TX Characteristic 向 APP 发送 Notify。Notify 订阅一般还需要配置 CCCD，BLE 库可能会代为处理。

### RN BLE 库与工程问题

react-native-ble-plx 是可供了解的 RN BLE 客户端库。项目实际使用的库需要从 package.json 和原生目录确认。常见库会提供扫描、连接、Service Discovery、读取、写入、Notify 订阅和连接状态监听等能力。Characteristic 的数据参数可能要求 Base64 编码，应以项目所用库的接口说明为准。

从示例进入产品功能时，需要继续检查连接对象由谁管理、异步错误如何传递、监听器何时释放、超时如何处理，以及 Android 和 iOS 的行为差异。

| 现象 | 需要检查的内容 |
| --- | --- |
| 扫描不到设备 | 扫描条件、权限和广播内容 |
| 连接失败 | 超时、连接状态和重试流程 |
| 连接成功但无法通信 | Service Discovery、UUID 和 Characteristic 属性 |
| 数据不完整 | ATT MTU、分包和协议帧重组 |
| 收不到 Notify | CCCD、订阅状态和连接状态 |
| 切换到后台后断连 | Android / iOS 后台运行规则 |
| 设备意外断开 | 断线检测、状态恢复和重连 |
| OTA 失败 | 分包、流控、CRC 和重试 |

不要假定一次 BLE Write 一定对应一条完整业务消息。协议帧可能包含帧头、类型、长度、数据和 CRC；当数据长度超过当前 ATT MTU 可以承载的范围时，需要分包发送并在接收端重组。

### 连接状态管理

连接流程可以表示为有限状态：

```text
DISCONNECTED → SCANNING → CONNECTING → CONNECTED
                                     ↓
                              RECONNECTING / ERROR
```

建议在 GATT 初始化和所需 Notify 订阅完成后再把设备标记为 CONNECTED。在 RN 项目中，应找到现有的设备管理位置，再按已有结构维护扫描、连接、GATT、协议和设备状态；新增模块时应保持改动范围清楚。

## 第四阶段：Android 与 iOS 原生机制

前两周同步建立基础，之后根据实际故障深入。学习目标是阅读原生代码，并判断问题属于 RN、Android 还是 iOS。

### Android

Android 项目常见语言为 Kotlin，也可能包含 Java 代码。建议关注：

| 内容 | 用途 |
| --- | --- |
| Activity、Service、Lifecycle | 理解应用入口、服务和生命周期 |
| BluetoothGatt | 理解 BLE 连接和 GATT 操作 |
| Runtime Permission | 理解运行时权限申请 |
| Intent | 理解组件间通信和页面跳转 |
| Gradle | 理解项目构建和依赖配置 |
| Logcat | 查看运行日志和定位故障 |

Android BLE 权限要求会随 Android 版本、目标 SDK 和扫描用途变化。Android 11 及以前的设备可能涉及位置权限；Android 12 及以后增加了 BLUETOOTH_SCAN、BLUETOOTH_CONNECT 等运行时权限。排查时需要同时核对系统版本和项目配置。

### iOS

iOS 常见语言为 Swift。建议关注：

| 内容 | 用途 |
| --- | --- |
| App Lifecycle | 理解应用生命周期 |
| UIViewController、SwiftUI | 阅读界面实现 |
| CoreBluetooth、Delegate | 理解 BLE 操作和异步回调 |
| Info.plist | 检查权限描述和应用配置 |
| Background Modes | 了解后台运行能力 |
| Xcode | 构建、调试和签名 |

CBCentralManager 的状态和扫描结果通过 Delegate 回调通知。排查 iOS 扫描问题时，应检查蓝牙状态、Info.plist 权限描述、扫描条件、广播内容和系统后台限制。

iOS 原生编译通常需要 macOS 和 Xcode；Windows 环境无法直接完成完整的本地 iOS 构建。

## 接手现有 RN 项目

### 1. 检查项目结构和依赖

先确认项目目录、依赖、脚本和平台工程：

```text
tree -L 2
cat package.json
cat tsconfig.json
ls android/
ls ios/
```

优先查看以下文件和目录：

| 文件或目录 | 需要确认的内容 |
| --- | --- |
| package.json | 依赖、脚本和 RN 版本 |
| app.json | 应用配置 |
| tsconfig.json | TypeScript 配置 |
| metro.config.js | Metro 配置 |
| babel.config.js | Babel 配置 |
| android/、ios/ | 原生工程和平台设置 |
| Podfile | iOS 原生依赖 |
| yarn.lock、pnpm-lock.yaml 或 package-lock.json | 锁定的依赖版本 |

确认项目使用 Expo Managed、Expo Prebuild 还是 React Native Community CLI（Bare）。这会影响原生目录的维护方式和能否直接修改原生代码。

### 2. 运行项目

接手后先完成依赖安装、Android 环境配置、Android 编译、真机安装和启动，并查看运行日志、入口文件与主页面。有 macOS 时，再补充 iOS 构建和真机运行。

### 3. 理解现有架构

沿着实际代码调用关系，找出应用入口、页面导航、全局状态、蓝牙初始化、连接对象持有者、Notify 数据处理、设备信息更新、断线恢复和设备信息存储位置。

一条常见的连接调用路径如下：

```text
App.tsx → Navigation → DeviceScreen → connectDevice()
        → BLE 管理模块 → GATT 初始化 → Notify 订阅
        → Device Store → 页面显示连接状态
```

阅读时可以尝试回答这些问题：

- APP 从哪里启动，页面如何组织？
- 路由和全局状态分别由什么模块管理？
- 蓝牙连接在哪里初始化，由谁持有连接对象？
- Notify 数据在哪里解析，设备信息在哪里更新？
- 断线后谁负责状态恢复和重连？
- APP 如何保存设备信息？

### 4. 完成一个小功能

从设备连接流程开始追踪 UI、业务函数、BLE 管理模块、GATT 操作、状态更新和界面刷新。理解调用路径后，可以选择一个小范围功能练习，例如增加连接超时、显示设备 RSSI、展示固件版本或增加断线提示。

## 使用 AI 辅助开发

让 AI 先基于现有代码解释目录、依赖和调用关系，再提供明确的修改范围与接口约束。审查方案时，重点检查状态管理、异步操作、监听器释放、错误处理、超时和平台差异。每次围绕一个独立功能修改，并在 Android 与 iOS 真机上验证关键场景。

可以给 AI 提供以下项目约束：

```text
1. 遵循现有项目结构和编码方式。
2. 修改前确认现有依赖，不替换无关依赖。
3. 将改动限制在需求涉及的模块。
4. 明确管理 BLE 连接的对象及其生命周期。
5. 为每个监听器提供对应的释放操作。
6. 为异步操作处理错误和超时。
7. 检查 Android 与 iOS 的行为差异。
8. 完成后说明修改文件和调用关系。
9. 给出需要执行的真机验证场景。
```

## 六周学习计划

| 周次 | 学习内容 | 阶段成果 |
| --- | --- | --- |
| 第 1 周 | TypeScript、React Hooks | 阅读现有业务代码并理解组件状态 |
| 第 2 周 | RN 组件、导航和状态管理 | 独立修改一个页面 |
| 第 3 周 | BLE GATT、RN BLE 库 | 跑通扫描、连接和服务发现 |
| 第 4 周 | BLE 协议、状态管理和异常处理 | 完成一项设备控制功能 |
| 第 5 周 | Android、iOS 原生机制 | 定位一个双端行为差异 |
| 第 6 周 | OTA、后台运行、测试和项目整理 | 独立交付一个完整功能 |

## 学习资料

优先查阅以下官方文档和项目资料：

- TypeScript 官方文档
- React Learn
- React Native 官方文档
- Android Developers 的 BLE 文档
- Apple CoreBluetooth 文档
- react-native-ble-plx 项目文档
- 项目当前使用的 BLE 库、导航库和状态管理库文档

## 发展方向

现有嵌入式经验可以与移动端开发结合，逐步覆盖固件、通信协议、Android / iOS 客户端和跨端联调。理解硬件、设备状态和协议细节，有助于完整负责智能硬件的软件功能，并利用 AI 提升日常开发效率。
