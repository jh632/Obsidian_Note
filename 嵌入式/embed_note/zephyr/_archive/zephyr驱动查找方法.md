---
tags: [zephyr, 驱动, devicetree, kconfig, 工作流]
---

# Zephyr 驱动查找方法

> 核心原则：不靠记忆，靠固定查询路径。

---

## 标准查询流程

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

---

## 五步速查命令

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

---

## 关键认知

### Binding YAML = 硬件配置接口文档

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

### Kconfig 不要手猜名字

实际可能 `CONFIG_TMP11X=y` 而非 `CONFIG_TMP117=y`，必须看 Kconfig 源文件确认。

### 官方文档只作入口，开发时读源码

官方文档信息有时不全，直接看驱动源码更可靠。

---

## 目录认知

```
zephyr/
├── drivers/sensor/          ← 传感器驱动
├── dts/bindings/            ← 硬件 Binding 文档
├── include/zephyr/drivers/  ← Driver API 头文件
├── samples/                 ← 示例
└── tests/                   ← 测试代码
```

---

## GitHub 搜索（补充手段）

```
repo:zephyrproject-rtos/zephyr "invensense,mpu6050"
```

能直接找到 Binding、Driver、Sample、Board Overlay、Test，是最快理解驱动实际用法的方法。

---

## 推荐工具

安装 `ripgrep`（`rg`）代替 `grep -r`，搜索 Zephyr 源码效率更高。

```bash
sudo apt install ripgrep
```

---

## 实战案例：MPU6050

| 步骤 | 命令 | 结果 |
|------|------|------|
| 全局搜索 | `rg "mpu6050" $ZEPHYR_BASE` | `drivers/sensor/tdk/mpu6050/` + `dts/bindings/sensor/invensense,mpu6050.yaml` |
| 看 Binding | `cat dts/bindings/sensor/invensense,mpu6050.yaml` | `compatible: "invensense,mpu6050"` |
| 看 Kconfig | `cat drivers/sensor/tdk/mpu6050/Kconfig` | `CONFIG_MPU6050=y` |
| 看源码 | 优先看 `init()` → WHO_AM_I → 配置寄存器 → 注册 I2C → `sample_fetch()` |

DTS 写法：
```dts
mpu6050: mpu6050@68 {
    compatible = "invensense,mpu6050";
    reg = <0x68>;
};
```
