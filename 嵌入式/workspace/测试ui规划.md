# PSA 出厂质检 UI 方案（简化版）

## 设计原则

- **独立运行**：不依赖现有 EEZ Studio UI，质检固件单独编译（通过 sdkconfig 宏切换）
- **两页轮播**：Page1 传感器数据，Page2 传感器数据+通信状态，每 5 秒自动翻页
- **纯数据展示**：每行显示传感器名称 + 实时读值 + 通过/失败图标
- **零交互**：不需要按键，完全自动运行

---

## 一、UI 布局

### Page 1 — 传感器数据（上）

```
┌──────────────────────────┐
│  PSA 出厂质检            │  ← 标题栏（固定）
├──────────────────────────┤
│ I2C Bus     ✓           │
│ SPI Bus     ✓           │
│ BME280      ✓  25.3C    │
│                  45.2%   │
│                  1013hPa │
│ MPU6050     ✓  ax:0.02  │
│                  ay:0.01 │
│                  az:0.98 │
│ TMP117      ✓  32.5C    │
│ GH3220      ✓  HR:72    │
│                  SpO2:98 │
│              PPG:12534   │
│                  -3421   │
│                   8967   │
│ MAX30009    ✓  Z:5.2kΩ  │
│                  ADC:1234│
├──────────────────────────┤
│       ◉ ○               │  ← 页码指示器
│     Page 1/2            │
└──────────────────────────┘
```

### Page 2 — 传感器数据（下）+ 通信 + 结果

```
┌──────────────────────────┐
│  PSA 出厂质检            │  ← 标题栏（固定）
├──────────────────────────┤
│ AXP2101     ✓  Bat:85%  │
│                V:3.92V   │
│                  Chg:CC  │
│                  28.1C   │
│ RTC         ✓  2026-5-27│
│                   10:30  │
│ OLED        ✓           │
│ Button      ✓           │
│ USB CDC     ✓  Connected│
│ BLE         ✓  Adv      │
├──────────────────────────┤
│  通过: 11  失败: 0      │  ← 汇总行
│       ◉ ○               │
│     Page 2/2            │
└──────────────────────────┘
```

---

## 二、数据结构

```c
typedef enum {
    QC_NOT_RUN = 0,
    QC_PASS,
    QC_FAIL,
    QC_SKIPPED,
} qc_result_t;

typedef struct {
    qc_result_t result;
    char value[32];     // 展示值，如 "25.3C"
    char detail[64];    // 额外信息行2，如 "hum:45.2% 1013hPa"
    char detail2[64];   // 额外信息行3
} qc_item_t;

typedef struct {
    qc_item_t i2c_bus;
    qc_item_t spi_bus;
    qc_item_t bme280;
    qc_item_t mpu6050;
    qc_item_t tmp117;
    qc_item_t gh3220;
    qc_item_t max30009;
    qc_item_t axp2101;
    qc_item_t rtc;
    qc_item_t oled;
    qc_item_t button;
    qc_item_t usb;
    qc_item_t ble;

    uint8_t page;           // 当前页码 0/1
    uint8_t pass_count;
    uint8_t fail_count;
} qc_report_t;
```

---

## 三、页面分配

| Page 1 | Page 2 |
|--------|--------|
| I2C Bus | AXP2101 |
| SPI Bus | RTC |
| BME280 | OLED |
| MPU6050 | Button |
| TMP117 | USB CDC |
| GH3220 | BLE |
| MAX30009 | 汇总结果 |

---

## 四、采集与判定规则

### 4.1 非接触式传感器（上电即可判）

| 传感器 | 通过条件 | 展示值 |
|--------|---------|--------|
| **I2C Bus** | `i2c_bus_status == ESP_OK` | `OK` / `FAIL` |
| **SPI Bus** | `spi_bus_status == ESP_OK` | `OK` / `FAIL` |
| **BME280** | `bme280_status == true && valid == true` | `temp`, `hum%`, `hPa` |
| **MPU6050** | `mpu6050_status == MPU6050_OK` | `ax/ay/az` 原始值 |
| **TMP117** | `tmp117_status == TMP117_OK && tmp_valid == true` | `skin_temp` |
| **AXP2101** | `read_status == OK` | 电量%, 电压V, 充电状态, 电池温度 |
| **RTC** | `valid == true && year >= 2025` | 日期 时间 |
| **OLED** | `DISP_Driver.check_status() == DISP_OK` | `OK` / `FAIL` |
| **Button** | 按键中断触发 | `PRESSED` / `—` |

### 4.2 接触式传感器（需手指触摸）

| 传感器 | 通过条件 | 展示值 |
|--------|---------|--------|
| **GH3220** | `gh3220_status == GH3220_OK && wear_status == true && hr > 0` | HR, SpO2, PPG 6通道生数据 |
| **MAX30009** | `max30009_status == MAX30009_OK && eda_wear_status == true` | 阻抗 kΩ, 原始 ADC |

> 接触式传感器若未被触摸，显示 `WAIT` 而非 `FAIL`，操作员看到后放手指。

### 4.3 通信通道

| 通道 | 通过条件 | 展示值 |
|------|---------|--------|
| **USB CDC** | `tud_cdc_connected()` | `Connected` / `—` |
| **BLE** | BLE 正在广播 | `Adv` / `Connected` / `—` |

---

### 4.4 生数据来源

| 传感器 | 生数据 | 数据来源 | 读取方式 |
|--------|--------|---------|---------|
| **AXP2101 电压** | `uint16_t raw_adc` | 寄存器 0x34(高) + 0x35(低) | `i2c_ops->read_mem(handle, 0x34, buf, 2)`, 公式: `VBAT(mV) = ADC_COUNT * 1.1 / 4096 * (VBAT_ADC_RANGE)` |
| **GH3220 PPG** | `uint32_t ppg_val[6]` | `PPG_DoubleBuffer_t` 中 `PPG_SampleBlock_t.ppg_val` | 通过 `ppg_swap_and_get()` 获取。6 通道: 2 LED × 3 波长 (绿/红/红外), 或按 Goodix 定义的通道布局 |
| **MAX30009 EDA** | `int32_t eda_val` | `EDA_DoubleBuffer_t` 中 `EDA_SampleBlock_t.eda_val` | 通过 `eda_swap_and_get()` 获取。20-bit 有符号 ADC, 再经 `max30009_adc_to_ohms()` 转为阻抗 |

> GH3220 和 MAX30009 的生数据依赖双缓冲采集任务在运行。质检模式下需要启动对应的 sensor task（但不是通过通信协议触发，而是本地直接启动）。

## 五、实现方案

### 5.1 编译切换

`sdkconfig` 中定义 `CONFIG_QC_MODE=y`，编译时在 `main.c` 中：

```c
#ifdef CONFIG_QC_MODE
    qc_ui_start();  // 进入质检UI，不启动正常采集
#else
    // 正常启动流程
#endif
```

### 5.2 新增文件

```
components/application/qc_ui/
    CMakeLists.txt
    qc_ui.h
    qc_ui.c
```

### 5.3 qc_ui 核心逻辑

```c
void qc_ui_start(void)
{
    // 1. 复用现有的 drivers_init() 初始化所有传感器
    // 2. 创建 LVGL 两页 label 控件
    // 3. 创建定时器, 每 500ms:
    //    - 采集所有传感器最新数据到 qc_report_t
    //    - 更新当前页 label 文本
    //    - 判定 pass/fail
    // 4. 创建 5 秒翻页定时器
}
```

**关键点**：
- 创建精简的数据采集任务：GH3220 process task + MAX30009 read task，不进双缓冲完整链路
- GH3220 PPG 生数据通过 hook 回掉直读（或读 `s_sensor_value` + `ppg_get_read_buffer()`）
- MAX30009 EDA 生数据通过 ops 的 `read_impedance()` 直接轮询
- BME280/TMP117/MPU6050/AXP2101/RTC 读值直接通过各自的 ops 接口轮询
- 不启动通信栈（USB CDC + BLE 初始化可跳过，或只检查连接状态）
- LVGL tick 用 `lv_timer_handler()` 在同一个 FreeRTOS task 中驱动

### 5.4 页数扩展到 3 页

如果 2 页放不下（字体不能太小），可以扩展到 3 页：

| Page 1 | Page 2 | Page 3 |
|--------|--------|--------|
| I2C Bus | GH3220 | USB CDC |
| SPI Bus | MAX30009 | BLE |
| BME280 | AXP2101 | 汇总结果 |
| MPU6050 | RTC | |
| TMP117 | OLED + Button | |

---

## 六、改动清单

| 文件 | 改动 |
|------|------|
| `components/application/qc_ui/qc_ui.h` | **新增** — 质检 UI API |
| `components/application/qc_ui/qc_ui.c` | **新增** — 两页轮播实现 |
| `components/application/qc_ui/CMakeLists.txt` | **新增** |
| `components/application/CMakeLists.txt` | 添加 qc_ui 子目录 |
| `main/main.c` | 添加 `#ifdef CONFIG_QC_MODE` 分支 |
| `sdkconfig` | 添加 `CONFIG_QC_MODE` 宏（或 sdkconfig 独立文件） |

**不修改**：所有现有驱动代码、EEZ UI、通信协议。
