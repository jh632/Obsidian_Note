---
date: 2026-11-02
tags:
  - 安卓IOS开发
  - TypeScript
  - React-Native
aliases:
  - TypeScript 面向对象设计
  - RN 面向对象设计
---

# 基于 TypeScript 和 RN 的面向对象程序设计

## 核心思路

TypeScript 提供 class、interface、继承、泛型和访问控制等面向对象能力。React Native 项目通常会把这些能力与函数组件、Hooks 和状态管理一起使用：类适合管理有生命周期的服务对象，类型适合描述数据，组件负责显示和交互。

以智能眼镜 APP 为例，可以按职责组织代码：

~~~text
React 页面与 Hooks
        ↓
设备业务服务
        ↓
BLE 通信接口 → BLE 库或原生模块
        ↓
设备协议编码与解析
~~~

页面显示数据并接收用户操作；业务服务组织设备连接和命令；BLE 通信模块执行扫描、连接和读写；协议模块解释设备传来的字节数据。项目已有结构应优先沿用，无需为了使用面向对象语法增加没有实际职责的类。

## TypeScript 的面向对象基础

### 类与对象

class 用来描述带有数据和行为的对象，new 用来创建实例。

~~~typescript
class DeviceConnection {
    private connected = false;

    constructor(readonly deviceId: string) {}

    connect(): void {
        this.connected = true;
    }

    disconnect(): void {
        this.connected = false;
    }

    isConnected(): boolean {
        return this.connected;
    }
}

const connection = new DeviceConnection("glasses-001");
connection.connect();
~~~

| C++ 概念 | TypeScript 写法 |
| --- | --- |
| 类 | class |
| 构造函数 | constructor |
| 成员变量 | 属性 |
| 成员函数 | 方法 |
| 对象实例 | new ClassName() |
| 空指针值 | null |
| 字符串 | string |

TypeScript 的类型检查发生在编译阶段。接口和类型标注编译为 JavaScript 后会被擦除，运行时仍需要对来自 BLE、存储或网络的数据进行必要校验。

### 封装与访问控制

TypeScript 提供三种常用访问修饰符：

| 修饰符 | 访问范围 |
| --- | --- |
| public | 所有调用方都可以访问；默认访问级别 |
| protected | 当前类及其子类可以访问 |
| private | 仅当前类可以访问，主要由 TypeScript 编译器检查 |

例如，设备地址通常不需要允许业务代码随意改写：

~~~typescript
class BluetoothDevice {
    private connected = false;

    constructor(
        readonly name: string,
        private readonly macAddress: string
    ) {}

    getAddress(): string {
        return this.macAddress;
    }

    setConnected(value: boolean): void {
        this.connected = value;
    }
}
~~~

TypeScript 的 private 是编译器访问限制。JavaScript 原生私有字段使用 # 声明，在运行时也无法通过对象外部直接访问。封装的目的在于规定状态如何变化，例如让连接状态通过连接流程更新，而不是允许各页面任意写入。

### 继承与方法重写

extends 用于继承类，子类构造函数通过 super() 调用父类构造函数。override 可以让编译器检查重写的方法是否存在于父类中。

~~~typescript
class Device {
    constructor(readonly name: string) {}

    connect(): void {
        console.log("Connecting to", this.name);
    }
}

class BleDevice extends Device {
    override connect(): void {
        console.log("Connecting over BLE", this.name);
    }
}
~~~

继承适用于子类确实可以遵循父类行为的情况。若设备之间只是共用一部分能力，组合独立对象往往更容易维护。

### 接口、多态与结构化类型

interface 可以描述对象需要具备的属性和方法。实现对象只要具有兼容的结构，就可以传给需要该接口的函数；无需显式声明 implements 才能满足类型检查。

~~~typescript
interface DeviceTransport {
    connect(deviceId: string): Promise<void>;
    disconnect(): Promise<void>;
}

class BleTransport implements DeviceTransport {
    async connect(deviceId: string): Promise<void> {
        console.log("Connect BLE device:", deviceId);
    }

    async disconnect(): Promise<void> {
        console.log("Disconnect BLE device");
    }
}

class MockTransport implements DeviceTransport {
    async connect(deviceId: string): Promise<void> {
        console.log("Connect test device:", deviceId);
    }

    async disconnect(): Promise<void> {
        console.log("Disconnect test device");
    }
}

async function openDevice(
    transport: DeviceTransport,
    deviceId: string
): Promise<void> {
    await transport.connect(deviceId);
}
~~~

openDevice() 依赖 DeviceTransport 描述的操作，不需要知道传入对象如何完成连接。不同实现可以提供 BLE 通信或测试行为，这体现了多态。

| 能力 | interface | class |
| --- | --- | --- |
| 描述对象结构 | 可以 | 可以 |
| 规定需要实现的方法 | 可以 | 可以通过抽象成员规定 |
| 提供方法实现 | 否 | 可以 |
| 创建运行时实例 | 否 | 可以 |
| 被类实现 | 类使用 implements | 不适用 |
| 扩展其他定义 | 使用 extends | 使用 extends |

interface 主要用于编译期类型检查，不会保留为 JavaScript 运行时对象。class 会生成可创建实例的运行时代码。

### 泛型

泛型让类型定义可以接收其他类型，同时保留检查能力：

~~~typescript
interface ApiResult<T> {
    code: number;
    message: string;
    data: T;
}

interface DeviceInfo {
    id: string;
    name: string;
    macAddress: string;
}

const result: ApiResult<DeviceInfo> = {
    code: 0,
    message: "success",
    data: {
        id: "glasses-001",
        name: "AI Glasses",
        macAddress: "AA:BB:CC:DD"
    }
};
~~~

泛型常用于网络响应、设备消息、缓存和状态管理。泛型只约束编译期代码；数据来自外部时，运行时数据仍可能不符合声明的类型。

## 智能眼镜 APP 的职责划分

假设 APP 需要扫描眼镜、连接设备、读取电量、发送控制命令和处理设备断开事件。可以先把数据、通信、协议和业务职责分开。

### 数据类型

设备信息通常只是数据，可以使用 interface 或 type 表达，无需为每个数据对象都创建一个类：

~~~typescript
interface DeviceInfo {
    id: string;
    name: string;
    rssi: number;
    battery?: number;
}
~~~

### BLE 通信接口

通信接口描述上层业务需要的操作。具体实现再调用项目实际使用的 BLE 库：

~~~typescript
interface BleTransport {
    connect(deviceId: string): Promise<void>;
    disconnect(deviceId: string): Promise<void>;
    write(data: Uint8Array): Promise<void>;
    subscribe(
        deviceId: string,
        listener: (data: Uint8Array) => void
    ): () => void;
}
~~~

subscribe() 返回释放函数，让调用方能够明确取消监听。实际项目中的接口应根据 BLE 库和设备协议调整，避免保留项目不会使用的操作。

### 协议模块

协议模块负责把业务命令编码为字节数据，并依据设备协议解释收到的数据。假设设备协议规定命令 0x01 用于设置音量：

~~~typescript
class ProtocolEncoder {
    setVolume(volume: number): Uint8Array {
        if (!Number.isInteger(volume) || volume < 0 || volume > 100) {
            throw new Error("Volume must be an integer from 0 to 100");
        }

        return new Uint8Array([0x01, volume]);
    }
}
~~~

真实协议还可能包含帧头、长度、命令编号、校验值、分包和请求响应匹配。协议格式应依据设备固件定义；一次 BLE Notification 不一定正好包含一条完整业务消息。下面的解析方法只示意数据已经按真实协议完成组帧后的解析。

~~~typescript
class ProtocolParser {
    parseBattery(frame: Uint8Array): number | null {
        if (frame.length === 0) {
            throw new Error("Empty device frame");
        }

        if (frame[0] !== 0x01) {
            return null;
        }

        if (frame.length !== 2 || frame[1] > 100) {
            throw new Error("Invalid battery frame");
        }

        return frame[1];
    }
}
~~~

BLE 通知回调提供的是字节片段。若设备协议允许一帧跨越多个通知，业务层需要先组帧，再把完整帧交给解析器。组帧规则应依据设备协议实现：

~~~typescript
interface FrameAssembler {
    push(chunk: Uint8Array): Uint8Array[];
}
~~~

### 设备业务服务与依赖注入

设备服务把传输和协议模块组合起来，集中实现设备业务操作：

~~~typescript
class DeviceService {
    constructor(
        private readonly transport: BleTransport,
        private readonly encoder: ProtocolEncoder,
        private readonly parser: ProtocolParser,
        private readonly frameAssembler: FrameAssembler
    ) {}

    async connect(deviceId: string): Promise<void> {
        await this.transport.connect(deviceId);
    }

    async disconnect(deviceId: string): Promise<void> {
        await this.transport.disconnect(deviceId);
    }

    async setVolume(volume: number): Promise<void> {
        const command = this.encoder.setVolume(volume);
        await this.transport.write(command);
    }

    subscribeBattery(
        deviceId: string,
        listener: (battery: number) => void
    ): () => void {
        return this.transport.subscribe(deviceId, data => {
            for (const frame of this.frameAssembler.push(data)) {
                const battery = this.parser.parseBattery(frame);

                if (battery !== null) {
                    listener(battery);
                }
            }
        });
    }
}
~~~

构造函数接收所需依赖，这种方式称为依赖注入。业务服务可以与 BLE 库的具体类型隔离，测试时也可以传入模拟实现。若项目只有一种实现且没有测试或替换需要，接口和注入层应保持简单。

### 通知订阅和资源释放

DeviceService 可以通过 BleTransport 收到字节数据，再交给协议模块处理。React 页面不应直接负责解码 BLE 数据，也不应让每个页面分别管理同一条设备连接。

事件订阅需要有明确的释放位置：设备连接管理者可以在连接结束时释放连接级监听，页面 Hook 则释放自己创建的页面级订阅。不同监听的生命周期由各自的所有者管理。

## React 与面向对象代码如何配合

React Native 页面通常使用函数组件。组件读取状态并返回界面，设备连接和命令流程由业务服务处理。

~~~tsx
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

function BatteryView({ battery }: { battery: number }) {
    return (
        <View>
            <Text>电量：{battery}%</Text>
        </View>
    );
}
~~~

Hooks 用于管理界面状态和 React 生命周期相关的订阅。下面的例子在 deviceId 变化或组件卸载时取消订阅：

~~~tsx
function useBattery(
    deviceService: DeviceService,
    deviceId: string
): number {
    const [battery, setBattery] = useState(0);

    useEffect(() => {
        const unsubscribe = deviceService.subscribeBattery(
            deviceId,
            setBattery
        );

        return unsubscribe;
    }, [deviceService, deviceId]);

    return battery;
}
~~~

此例假定 DeviceService.subscribeBattery() 会返回取消订阅的函数。Hook 负责把业务事件接到组件状态；BLE 连接仍由独立的设备连接管理者负责。不要在组件每次渲染时创建新的 DeviceService，应由应用组合入口或项目既有的依赖管理方式持有稳定实例。

| React 概念 | 在页面中的用途 |
| --- | --- |
| Props | 向子组件传递数据和回调 |
| useState | 保存当前组件需要展示的状态 |
| useEffect | 建立外部订阅并在依赖变化时清理 |
| Context 或状态管理库 | 在多个页面之间共享状态 |
| 组件组合 | 将界面组织成可复用部分 |

Hooks 与类的成员变量、方法和构造函数有不同的运行规则。它们用于处理 React 组件的状态和副作用，不能视作传统对象成员的直接替代品。

## 常用设计原则

### 单一职责

一个类或模块应围绕明确的职责组织。扫描与连接、协议编码与解析、设备业务、OTA 和界面状态分别由相应模块处理，避免一个 DeviceManager 同时承担所有工作。

### 依赖倒置

设备业务面向 BleTransport 这样的抽象操作编写，再由应用组合入口选择具体实现。这样更换 BLE 库或进行单元测试时，业务代码受到的影响会更小。

### 组合优于继承

不同设备可能共享连接能力，却拥有不同协议和功能。通过组合传输对象、协议处理器和业务服务来表达差异，通常比不断增加 BleDevice、SmartWatch、SmartRing 等继承层级更清楚。

### 按需要增加抽象

接口、工厂和依赖注入适合解决具体边界问题，例如隔离 BLE 库、替换测试实现或集中创建长生命周期对象。单纯把每个函数包装成类会增加理解成本。

## 建议的目录组织

先以现有项目结构为准。新模块可以参考以下职责划分：

~~~text
src/
├── components/       # 通用界面组件
├── screens/          # 页面
├── hooks/            # React Hooks
├── models/           # 数据类型
├── services/         # 设备业务和固件升级业务
├── bluetooth/        # BLE 库封装、扫描和连接
├── protocol/         # 命令编码、数据解析
├── stores/           # 跨页面共享的界面状态
└── utils/            # 通用函数
~~~

目录名称只是组织方式，代码边界应由调用关系和资源所有权决定：

| 模块 | 主要职责 |
| --- | --- |
| screens、components | 显示数据并收集用户操作 |
| hooks | 连接 React 生命周期与业务状态 |
| services | 编排设备业务流程 |
| bluetooth | 扫描、连接、读写和通知订阅 |
| protocol | 命令编码和设备消息解析 |
| stores | 保存多个页面共享的界面状态 |
| models | 描述设备和消息的数据类型 |

## 嵌入式经验与 RN 的联系

| 嵌入式开发经验 | RN 项目中可关联的内容 |
| --- | --- |
| 驱动接口 | BLE 通信接口与原生 API |
| 通信协议 | Protocol Encoder、Parser 和消息匹配 |
| 业务模块 | Device Service |
| 全局设备状态 | Store 或 Context |
| 事件通知 | BLE Notify 和订阅回调 |
| 模块接口 | TypeScript interface |
| 资源释放 | 连接管理者和 Hook 的取消订阅逻辑 |

已有的协议、设备和状态管理经验可以帮助理解移动端设备业务；需要补充 React 的状态更新方式、原生权限和应用生命周期规则。

## 学习顺序

1. 掌握 TypeScript 的类型、类、接口、泛型和异步操作。
2. 理解封装、继承、多态、组合、依赖注入和单一职责。
3. 学习 React 函数组件、Props、State、Hooks 和组件组合。
4. 阅读现有 RN 项目的导航、状态管理和原生模块。
5. 追踪一条 BLE 扫描、连接、Notify 和命令发送流程。
6. 根据项目需要学习错误处理、连接恢复和测试。

智能眼镜 APP 的重点在于明确设备连接的所有者、业务服务的边界、协议数据的处理位置，以及多个页面如何读取一致的设备状态。面向对象语法服务于这些边界设计；界面继续按 React 组件和 Hooks 的方式组织。
