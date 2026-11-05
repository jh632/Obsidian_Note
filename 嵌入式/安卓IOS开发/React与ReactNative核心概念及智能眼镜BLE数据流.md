---
date: 2026-11-03
tags:
  - "#安卓IOS开发"
  - "#React/Reactnative"
aliases:
  - React 与 React Native 入门
  - RN 智能眼镜 BLE 数据流
---

# React 与 React Native 核心概念及智能眼镜 BLE 数据流

> 来源：[介绍React与React Native](https://chatgpt.com/c/6ae7fd22-db0c-83ee-9ba8-4be40c9aa8b0)，ChatGPT 回复，2026-11-02
> 相关笔记：[[RN智能眼镜配套APP学习路线]]、[[基于TS和RN的面向对象程序设计]]

## 学习视角

面向智能眼镜 APP，学习 React 和 React Native（RN）的目标，是读懂现有项目，并能独立完成界面、设备状态与蓝牙通信相关功能。已有的 ESP32 和 BLE 经验可以帮助理解 GATT、Characteristic、Notification 和设备协议；React 的状态更新方式、移动端应用生命周期以及 Android / iOS 原生接口需要结合 RN 项目学习。

## React 与 React Native

React 提供组件、状态和数据驱动界面等能力。React 常用于 Web 界面开发。React Native 使用 React 的组件模型和编程方式，结合 Android 与 iOS 的原生视图来构建移动应用。

| 内容 | React Web | React Native |
| --- | --- | --- |
| 运行环境 | 浏览器 | Android / iOS |
| 界面显示 | DOM | 原生视图组件 |
| 常用页面元素 | `div`、`span` | `View`、`Text` |
| 用户操作 | `onClick` | `onPress` |
| 布局与样式 | CSS | `StyleSheet` 与 Flexbox |
| 系统能力 | 浏览器 API | 原生模块与系统 API |

RN 页面常用 `View`、`Text`、`Image`、`TextInput`、`Pressable`、`ScrollView`、`FlatList` 和 `Modal`。这些组件构成应用界面，并处理用户操作。

## React 的核心概念

### 组件、Props 与 State

组件负责显示一部分界面。智能眼镜 APP 可以由设备页、设置页、电量显示和设备卡片等组件组成。Props 是父组件传给子组件的输入参数，子组件通过回调请求父组件更新数据；State 保存会变化的界面信息。

以下示例演示组件、Props 和本地状态更新。点击按钮会将页面中的 `connected` 更新为 `true`。

```tsx
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

function DeviceCard({ name, battery }: { name: string; battery: number }) {
    return (
        <View>
            <Text>{name}</Text>
            <Text>电量：{battery}%</Text>
        </View>
    );
}

function DevicePage() {
    const [device, setDevice] = useState({
        connected: false,
        battery: 85,
        name: "AI Glasses"
    });

    return (
        <View>
            <DeviceCard name={device.name} battery={device.battery} />
            <Text>{device.connected ? "已连接" : "未连接"}</Text>
            <Pressable
                onPress={() => setDevice(previous => ({
                    ...previous,
                    connected: true
                }))}
            >
                <Text>连接设备</Text>
            </Pressable>
            <Pressable
                onPress={() => setDevice(previous => ({
                    ...previous,
                    battery: 70
                }))}
            >
                <Text>更新电量</Text>
            </Pressable>
        </View>
    );
}
```

State 发生变化后，React 会重新执行组件的渲染逻辑，协调需要提交给原生视图的变化。示例使用函数回调基于前一份状态更新 `device`，并保留其他字段。这个模式适合显示 BLE 设备的连接状态、电量和固件信息。

### Hooks

| Hook | 主要用途 | 智能眼镜 APP 示例 |
| --- | --- | --- |
| `useState` | 保存组件状态 | 设备连接状态、电量 |
| `useEffect` | 管理副作用与订阅 | 注册 BLE 事件监听 |
| `useRef` | 在多次渲染间保存引用或可变值 | 保存设备引用、定时器句柄；修改 `current` 不会触发渲染 |
| `useMemo` | 缓存计算结果 | 计算设备列表显示内容 |
| `useCallback` | 缓存函数引用 | 给子组件传递稳定回调 |
| `useContext` | 在组件间共享数据 | 读取应用级设备状态 |

BLE 订阅需要在所属组件或连接管理者结束使用时释放。示例中，页面只订阅自身需要的设备事件：

```tsx
import { useEffect, useState } from "react";

interface BatteryDeviceManager {
    onBatteryChange(
        deviceId: string,
        listener: (battery: number) => void
    ): { remove(): void };
}

function useBattery(
    deviceManager: BatteryDeviceManager,
    deviceId: string
): number {
    const [battery, setBattery] = useState(0);

    useEffect(() => {
        const subscription = deviceManager.onBatteryChange(deviceId, setBattery);

        return () => {
            subscription.remove();
        };
    }, [deviceManager, deviceId]);

    return battery;
}
```

此处的 `BatteryDeviceManager` 是说明订阅方式的示例接口，`onBatteryChange()` 返回包含 `remove()` 的订阅对象。

`useEffect` 的依赖数组决定副作用重新建立的时机：

| 依赖数组 | 执行规则 |
| --- | --- |
| 未提供 | 每次组件提交渲染后执行 |
| `[]` | 组件首次提交后执行；组件卸载时清理 |
| `[deviceManager, deviceId]` | 首次提交后执行；依赖变化时清理上次订阅，并根据最新依赖重新订阅 |

组件卸载时，React 会调用 Effect 返回的清理函数。开发环境中的 React Strict Mode 可能额外执行初始化与清理。Effect 使用的响应式数据应列入依赖数组；异步操作需要处理依赖已变化或组件已卸载的情况。

示例中的页面级订阅在组件卸载或 `deviceId` 变化时清理。导航页面的显示状态与组件生命周期由导航配置决定。跨页面持续的 BLE 连接由设备连接管理者维护，页面通过共享状态读取连接信息。

## RN 应用的运行层次

```text
React 页面与 Hooks
        ↓
应用业务与共享状态
        ↓
设备管理、BLE 服务和协议处理
        ↓
RN BLE 库或 Native Module
        ↓
Android Bluetooth API / iOS CoreBluetooth
        ↓
智能眼镜 GATT 服务
```

| 层次 | 主要职责 |
| --- | --- |
| 页面与组件 | 显示设备信息、响应用户操作 |
| 设备业务 | 组织连接、设备控制和固件升级流程 |
| BLE 服务 | 扫描、连接、读写和订阅 Notification |
| 协议模块 | 编码命令、组装和解析设备数据 |
| 状态管理 | 向多个页面提供统一的设备状态 |
| 原生平台 | 执行蓝牙、权限和其他系统操作 |

RN 项目常用 TypeScript 编写业务代码。Android 原生工程可能包含 Kotlin、Java 与 Gradle；iOS 工程可能包含 Swift、Objective-C 与 Xcode 配置。Node.js 为开发工具提供运行环境，Metro 负责打包 JavaScript，Hermes 是 RN 应用常用的 JavaScript 引擎。遇到蓝牙权限、后台运行或系统行为问题时，需要沿调用路径判断问题属于业务代码、RN 库、原生模块还是操作系统。

## 手机与眼镜的 BLE 角色

| 智能眼镜 | 手机 APP |
| --- | --- |
| Peripheral | Central |
| GATT Server | GATT Client |
| 提供 Service 和 Characteristic | 发现 Service 和 Characteristic |
| 通过 Characteristic 接收 Write | 向 Characteristic 写入命令 |
| 发送 Notification | 订阅并接收 Notification |

## 从扫描到更新界面的完整数据流

```text
APP 启动
  ↓
检查蓝牙状态与权限
  ↓
扫描并筛选设备
  ↓
建立 GATT 连接并发现 Service / Characteristic
  ↓
订阅 Notification，准备接收设备数据
  ↓
接收字节片段 → 组装协议帧 → 校验并解析
  ↓
更新共享设备状态 → React 页面更新
```

完整流程可以按以下步骤阅读项目：

1. **准备蓝牙环境**：检查蓝牙开关、运行时权限和应用状态。
2. **扫描设备**：按设备名称、广播内容或厂商数据筛选眼镜。
3. **建立连接**：连接管理者保存连接对象，管理连接超时和异常断开。
4. **发现服务**：检查固件提供的 Service UUID、Characteristic UUID 和属性。
5. **订阅通知**：为设备上报数据的 Characteristic 注册 Notification 监听，并确认通知已启用。
6. **解析消息**：将通知提供的字节交给协议模块处理。按协议检查帧头、长度、类型与 CRC；数据不完整时先缓存片段并组装完整帧。
7. **更新设备状态**：把解析出的电量、固件信息或连接状态写入统一的设备状态。
8. **刷新界面**：页面读取状态并显示最新信息。
9. **发送设备命令**：将业务操作编码为协议数据，写入指定 Characteristic，并在需要时等待设备响应。
10. **清理连接资源**：断开时取消 Notification 监听、清除连接引用并发布断开状态。

常见的模块调用关系如下：

```text
DevicePage
    → DeviceManager
        → BleService
            → RN BLE Library / Native Module
                → Android BluetoothGatt / iOS CoreBluetooth

眼镜 Notification
    → BleService
        → FrameAssembler / ProtocolParser
            → Device Store
                → React 页面
```

例如，页面发起 `setPromptSpeed(3)` 时，`DeviceManager` 将业务请求交给协议模块编码，`BleService` 再把数据写入目标 Characteristic。设备返回的数据经过 Notification、协议解析与状态更新后显示在页面。页面无需直接维护 GATT 操作细节。

## 连接状态与异常处理

连接过程包含多个状态，可用明确的有限状态描述：

```text
Disconnected
  → Scanning
  → Connecting
  → DiscoveringServices
  → SubscribingNotifications
  → Ready
```

流程中也需要处理 `Disconnected`、`Error` 或重连状态。只有连接建立、服务发现完成、所需通知订阅准备就绪后，页面才适合显示设备可用。

需要结合项目处理蓝牙关闭、权限拒绝、扫描超时、连接超时、通知失败、意外断开、断线重连和应用切换到后台等情况。一次 BLE Write 或 Notification 可以只包含业务帧的一部分；协议层应依据设备定义处理分包和帧重组。

## 常见 RN 工程与依赖

| 名称 | 用途 |
| --- | --- |
| TypeScript | JavaScript 的静态类型扩展 |
| React | 组件和界面状态管理 |
| React Native | 跨平台移动应用框架 |
| React Navigation | 页面导航 |
| Zustand | 共享状态管理 |
| `react-native-ble-plx` | BLE 通信库，可提供扫描、连接、读写和通知订阅能力 |
| Axios | HTTP 请求 |
| AsyncStorage | 本地数据存储 |
| React Native Reanimated | 动画 |
| TanStack Query | 服务端数据管理 |
| Metro | JavaScript 打包工具 |
| Hermes | JavaScript 引擎 |
| Expo | RN 开发工具与平台 |

阅读现有项目时，可查看 `package.json` 与锁文件，确认当前 RN 版本、实际依赖、项目采用的 Expo 或 Community CLI 配置，再依据项目使用的库查阅接口。

## 代码目录与职责

目录布局可以按团队既有项目结构组织。一种常见示意如下：

```text
src/
├── components/       # 通用界面组件
├── screens/          # 页面
├── navigation/       # 页面导航
├── hooks/            # React Hooks
├── services/         # 设备业务流程
├── bluetooth/        # 扫描、连接与 BLE 操作
├── protocols/        # 命令编码和数据解析
├── stores/           # 多页面共享状态
├── types/            # TypeScript 类型
└── utils/            # 通用函数
```

理解项目时，重点找出每种资源和状态由谁维护：页面管理自己的显示状态，设备管理者维护连接生命周期，BLE 服务执行 GATT 操作，协议模块处理帧与命令，状态管理模块向页面提供设备信息。团队也可能采用 feature-based 目录，把设备功能涉及的页面、服务和状态放在同一功能目录内。

## 学习顺序与练习

1. **TypeScript 与 React**：掌握 JSX / TSX、函数组件、Props、State、Hooks、泛型和异步操作；目标是读懂现有页面及状态更新路径。
2. **React Native**：熟悉界面组件、Flexbox、`StyleSheet`、导航、共享状态与 Android / iOS 调试；练习完成一个设备页面。
3. **BLE 移动端开发**：掌握扫描、过滤、GATT 连接、服务发现、Characteristic 读写、Notification、MTU、分包和异常恢复；目标是完成设备连接与数据交互。
4. **原生工程与工程化**：阅读 Kotlin / Java、Swift、Native Module、运行时权限和构建配置；理解后台 BLE、OTA、日志和性能分析。

练习项目可以围绕智能眼镜管理 APP 组织：设备列表、连接详情、电量与固件信息、音量与亮度设置、提词器开始与暂停、滚动速度调节和 OTA 进度。验证内容包括模拟数据下的状态变化、真实设备的 GATT 通信，以及 Android / iOS 的权限、连接、通知和异常处理。

接手公司项目后，沿着 `App.tsx → Navigation → DeviceScreen → connectDevice() → BLE 服务 → GATT 初始化 → Notification 订阅 → Device Store → 界面更新` 阅读实际调用链。优先确认应用入口、连接对象持有者、Notify 解析位置、设备状态维护位置、断线处理方式与数据保存位置。

## 相关笔记

- [[RN智能眼镜配套APP学习路线]]
- [[基于TS和RN的面向对象程序设计]]
- [[01-蓝牙入门]]
- [[02-NimBLE-API基础]]
