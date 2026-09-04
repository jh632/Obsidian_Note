---
tags: [zephyr, devicetree, 设备树, 驱动, binding, kconfig, dts, 工作流]
date: 2026-09-01
aliases: [设备树, 驱动查找, devicetree, dts]
---

# Zephyr 设备树与驱动开发

> 2026-09-01 由原《设备树》与《zephyr驱动查找方法》两篇合并重组。
> 主线：**先理解设备树（如何描述硬件）→ 再学会查找/配置驱动（如何利用设备树）**。

---

## 1. 设备树概述

设备树（Device Tree）是一种描述硬件配置的数据结构，用于将硬件信息与驱动代码分离。在 Zephyr 中，设备树用于描述：

- 外设地址和寄存器映射
- 中断配置
- 时钟配置
- 引脚复用（pinmux）
- 设备间的连接关系

---

## 2. 三根设备树

### 2.1 dtsi：SoC 芯片描述树

- 本质：SoC 的"硬件户口簿"——外设、寄存器地址定义，**默认全关**。
- 来源：一般来自芯片厂商，冷门芯片需要自己写

### 2.2 dts：板子定义

定义**原理图上设备的连接**。

**示例：**

```c
#include <espressif/esp32s3/esp32s3_wroom_n8.dtsi>  // Espressif 提供

/ {
    model = "My Company Board v1.0";
    compatible = "mycompany,myboard";
    // ...
};

&i2c0 {
    status = "okay";
    pinctrl-0 = <&i2c0_myboard>;   // 用自己定义的引脚
};

&pinctrl {
    i2c0_myboard: i2c0_myboard {
        group1 {
            pinmux = <I2C0_SDA_GPIO14>, <I2C0_SCL_GPIO15>;  // 你们的接法
        };
    };
};
```

### 2.3 overlay：工程级补丁修改

- overlay 是**对已有设备树进行追加或修改的工程级补丁**

---

## 3. bindings.yaml：设备树节点的"类型定义"

`bindings.yaml` 是 **Zephyr Device Tree 体系里非常关键的一层**，可以理解为：

> **设备树节点的"类型定义文件"或者"设备树接口协议"。**

| Zephyr Device Tree | C 语言 |
| --- | --- |
| `.dts/.overlay` | 变量实例 |
| `compatible` | 类型名 |
| `bindings.yaml` | struct 定义 + 类型检查 |
| driver | 操作函数 |

例如 `bosch,bme280.yaml`：

```yaml
description: Bosch BME280 temperature sensor

compatible: "bosch,bme280"

include:
  - name: sensor-device.yaml

properties:

  reg:
    type: int
    required: true

  int-gpios:
    type: phandle-array
    required: false

  sampling-frequency:
    type: int
    required: false
```

---

## 4. 设备树语法

设备树（Device Tree，DTS）的语法其实不复杂，核心就是**节点（node）+ 属性（property）**的树状结构。

### 4.1 基本结构

```devicetree
/dts-v1/;              // 版本声明，通常放在文件最开头

/ {                     // 根节点
    node-name {          // 子节点
        property = value;
    };
};
```

### 4.2 节点语法

```devicetree
label: node-name@unit-address {
    ...
};
```

- `label:`：可选，给节点起个别名，方便用 `&label` 引用
- `node-name`：节点名
- `@unit-address`：可选，通常对应 `reg` 属性里的地址（比如 `uart@40002000`）

### 4.3 属性（property）的几种写法

```devicetree
// 字符串
label = "IO1 LED";

// 单个整数（cell），必须用尖括号
reg = <0x40002000>;

// 多个整数（数组）
gpios = <&gpio0 1 GPIO_ACTIVE_LOW>;

// 字符串数组
compatible = "vendor,chip", "generic,chip";

// 布尔属性：出现即为 true，不出现为 false
wakeup-source;

// 字节数组
mac-address = [00 11 22 33 44 55];

// phandle 引用（指向另一个节点）
clocks = <&clk_hse>;
```

### 4.4 引用节点：`&`

```devicetree
&gpio0 {
    status = "okay";
};

&{/soc/uart@40002000} {
    status = "okay";
};
```

两种写法：`&label`（用标签引用）或 `&{/full/path}`（用完整路径引用），常用于**覆盖（overlay）已有节点**，而不是新建。

### 4.5 一些"约定俗成"的关键属性

| 属性 | 作用 |
| --- | --- |
| `compatible` | 指定驱动匹配用的字符串，决定用哪个驱动处理这个节点 |
| `reg` | 寄存器地址/大小，或 I2C/SPI 设备地址 |
| `status` | `"okay"` / `"disabled"`，控制节点是否生效 |
| `#address-cells` / `#size-cells` | 定义子节点 `reg` 属性里地址和大小各占几个 cell（整数） |
| `interrupts` | 中断号及触发方式 |
| `clocks` / `clock-names` | 时钟源引用 |
| `pinctrl-0` / `pinctrl-names` | 引脚复用配置 |

### 4.6 预处理宏（C 风格）

设备树文件常配合 C 预处理器使用，所以能看到 `#include`、宏定义等：

```devicetree
#include <zephyr/dt-bindings/gpio/gpio.h>   // 引入 GPIO_ACTIVE_LOW 等宏
#include "board.dtsi"                       // 引入其他设备树片段

#define LED_PIN 1
gpios = <&gpio0 LED_PIN GPIO_ACTIVE_LOW>;
```

### 4.7 注释

支持 C 风格注释：

```devicetree
// 单行注释
/* 多行
   注释 */
```

### 4.8 文件类型后缀

| 后缀 | 含义 |
| --- | --- |
| `.dts` | 主设备树源文件 |
| `.dtsi` | 可被 `#include` 的"设备树片段"（复用/共享部分，类似头文件） |
| `.dtb` | 编译后的二进制设备树（Device Tree Blob） |
| `.overlay` | 覆盖文件，用于在不改动主 dts 的情况下增删/修改节点属性（Zephyr 里很常见） |

---

## 5. 驱动查找方法

> 核心原则：**不靠记忆，靠固定查询路径。**

### 5.1 标准查询流程

```
拿到新硬件
    ↓
Zephyr 是否支持？  → rg "芯片型号" $ZEPHYR_BASE
    ↓
找到 Binding       → find dts/bindings -iname "*芯片型号*"
    ↓
确认 compatible    → cat binding.yaml
    ↓
写 DTS            → compatible + reg
    ↓
找到 Kconfig       → cat drivers/.../Kconfig
    ↓
配置 prj.conf      → CONFIG_XXX=y
    ↓
查看 Sample        → rg "芯片型号" $ZEPHYR_BASE/samples
    ↓
理解 Driver API    → 查 include/zephyr/drivers/
    ↓
必要时读源码       → 从 init() 和 sample_fetch() 看起
```

### 5.2 五步速查命令

```bash
# 1. 全局搜索：确认是否支持
rg "mpu6050" $ZEPHYR_BASE

# 2. 查 Devicetree Binding → 获取 compatible 字符串
find $ZEPHYR_BASE/dts/bindings -iname "*mpu6050*"

# 3. 查 Driver 源码位置
find $ZEPHYR_BASE/drivers -iname "*mpu6050*"

# 4. 查 Kconfig → 确认 CONFIG 名
rg 'config MPU6050' $ZEPHYR_BASE

# 5. 查 Sample → 看实际用法
rg 'mpu6050' $ZEPHYR_BASE/samples
```

### 5.3 关键认知

**Binding YAML = 硬件配置接口文档**

```yaml
compatible: "bosch,bme280"
include: i2c-device.yaml          # 自动继承 I2C 标准属性（如 reg）
properties:
  int-gpios:
    type: phandle-array
    required: false                # 驱动特有属性
```

- `compatible` → 匹配哪个驱动
- `include` → 自动拥有总线标准属性
- `properties` → 驱动特有配置项

**Kconfig 不要手猜名字**

实际可能 `CONFIG_TMP11X=y` 而非 `CONFIG_TMP117=y`，必须看 Kconfig 源文件确认。

**官方文档只作入口，开发时读源码**

官方文档信息有时不全，直接看驱动源码更可靠。

### 5.4 目录认知

```
zephyr/
├── drivers/sensor/          ← 传感器驱动
├── dts/bindings/            ← 硬件 Binding 文档
├── include/zephyr/drivers/  ← Driver API 头文件
├── samples/                 ← 示例
└── tests/                   ← 测试代码
```

### 5.5 GitHub 搜索（补充手段）

```
repo:zephyrproject-rtos/zephyr "invensense,mpu6050"
```

能直接找到 Binding、Driver、Sample、Board Overlay、Test，是最快理解驱动实际用法的方法。

### 5.6 推荐工具

安装 `ripgrep`（`rg`）代替 `grep -r`，搜索 Zephyr 源码效率更高。

```bash
sudo apt install ripgrep
```

### 5.7 实战案例：MPU6050

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| 全局搜索 | `rg "mpu6050" $ZEPHYR_BASE` | `drivers/sensor/tdk/mpu6050/` + `dts/bindings/sensor/invensense,mpu6050.yaml` |
| 看 Binding | `cat dts/bindings/sensor/invensense,mpu6050.yaml` | `compatible: "invensense,mpu6050"` |
| 看 Kconfig | `cat drivers/sensor/tdk/mpu6050/Kconfig` | `CONFIG_MPU6050=y` |
| 看源码 | 优先看 `init()` → WHO_AM_I → 配置寄存器 → 注册 I2C → `sample_fetch()` | |

DTS 写法：

```dts
mpu6050: mpu6050@68 {
    compatible = "invensense,mpu6050";
    reg = <0x68>;
};
```
