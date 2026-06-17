---
date: 2026-06-16
tags: [低通滤波, rc-filter, embedded-c]
aliases: [rc-low-pass-filter, 一阶低通滤波, 软件低通滤波]
---

# RC 低通滤波器原理

## 概述
RC 低通滤波器是最基础的模拟滤波器，由一个电阻 R 和一个电容 C 组成。它允许低频信号通过、衰减高频信号，是理解所有高阶滤波器的基础。在嵌入式系统中，其一阶数字等效形式（一阶 IIR 低通滤波）因计算极轻量（一次乘加）、无需缓冲区，成为 ADC 采样的首选去噪手段。

## 核心概念
- **截止频率** fc = 1/(2πRC)：信号衰减 3dB（幅度降为原来的 0.707 倍）的频率点
- **-20dB/decade 滚降**：频率每增加 10 倍，增益下降 20dB
- **一阶 IIR 数字等效**：软件中 y[n] = α·x[n] + (1-α)·y[n-1]
- **α 的物理意义**：α = 采样周期 / (RC 时间常数)，决定滤波器的"惯性"大小

## 细节

### 一阶 RC 电路分析

最基本的 RC 低通电路：

```
输入 Vi ── R ──┬── 输出 Vo
               │
               C
               │
              GND
```

电容的阻抗 Zc = 1/(jωC)，输出电压是电容对地的分压：

Vo = Vi × Zc / (R + Zc) = Vi × 1/(1 + jωRC)

> 直观理解：低频时电容阻抗很大（近似开路），信号几乎无衰减通过；高频时电容阻抗很小（近似短路），信号被旁路到地。

### 传递函数

连续域（s 域）传递函数：

H(s) = Vo(s) / Vi(s) = 1 / (1 + sRC) = ωc / (s + ωc)

其中 ωc = 1/RC 是特征角频率。

令 s = jω 得到频率响应：

H(jω) = 1 / (1 + jωRC) = 1 / (1 + jω/ωc)

### 幅频特性

幅频特性（幅度 vs 频率）：

|H(jω)| = 1 / √(1 + (ω/ωc)²)

相频特性（相位 vs 频率）：

∠H(jω) = -arctan(ω/ωc)

| 频率 | 幅度（倍） | 幅度（dB） | 相位 |
|------|-----------|-----------|------|
| ω << ωc (DC) | 1 | 0 dB | 0° |
| ω = ωc (截止) | 0.707 | -3 dB | -45° |
| ω = 10 × ωc | 0.1 | -20 dB | ≈ -90° |
| ω >> ωc | ≈ ωc/ω | → -∞ dB | → -90° |

> 读图要点：在 Bode 图上，低频段（通带）增益约 0dB，高频段（阻带）以 -20dB/decade 的斜率下降。转折点就在 fc 处。

### 截止频率的计算

截止频率定义为增益下降 3dB 的频率点：

fc = 1 / (2πRC)

| R | C | fc |
|---|----|----|
| 1 kΩ | 1 μF | 159 Hz |
| 10 kΩ | 0.1 μF | 159 Hz |
| 10 kΩ | 1 μF | 15.9 Hz |
| 100 kΩ | 10 nF | 159 Hz |

时间常数 τ = RC，表示电容充放电到 63% 所需的时间。截止频率与时间常数的关系：

fc = 1 / (2πτ)

### 软件低通滤波（一阶 IIR）的实现

将模拟 RC 滤波离散化（后向欧拉法 s ≈ (1 - z⁻¹)/T），得到递推公式：

H(z) = T / (T + RC) / (1 - RC/(T + RC)·z⁻¹)

写成差分方程：

y[n] = α · x[n] + (1 - α) · y[n-1]

其中：
- α = T / (T + RC)
- T = 采样周期（秒）
- RC = 时间常数

**基本实现：**

```c
typedef struct {
    float alpha;  // 滤波系数 [0, 1]
    float out;    // 上次输出
} lpf1_t;

static inline void lpf1_init(lpf1_t *f, float alpha) {
    f->alpha = alpha > 1.0f ? 1.0f : (alpha < 0.0f ? 0.0f : alpha);
    f->out   = 0.0f;
}

static inline float lpf1_update(lpf1_t *f, float x) {
    f->out = f->alpha * x + (1.0f - f->alpha) * f->out;
    return f->out;
}
```

**从截止频率反算 alpha：**

```c
// 由 fc 和采样频率 fs 计算 alpha
static inline float lpf1_alpha_from_fc(float fc, float fs) {
    float tau = 1.0f / (2.0f * 3.14159265f * fc);
    float T   = 1.0f / fs;
    return T / (T + tau);  // alpha = T / (T + RC)
}
```

使用示例：
```c
// 采样率 1000 Hz，截止频率 50 Hz
float fs = 1000.0f;                          // 1 kHz 采样
float fc = 50.0f;                            // 截止 50 Hz
float alpha = lpf1_alpha_from_fc(fc, fs);    // alpha ≈ 0.239

lpf1_t filter;
lpf1_init(&filter, alpha);

// 每次 ADC 采样后调用
uint16_t adc_val = adc_read();
float filtered = lpf1_update(&filter, (float)adc_val);
```

**定点数实现（无 FPU 的 MCU，如 8 位机）：**

```c
// alpha 用 Q15 格式表示，alpha_q15 = alpha * 32768
static inline int16_t lpf1_q15_update(int32_t *out, int16_t x, int16_t alpha_q15) {
    *out = ((int32_t)alpha_q15 * x + (32768 - alpha_q15) * (*out)) >> 15;
    return (int16_t)(*out);
}
```

**alpha 取值的工程经验：**

| alpha | fc（fs=1kHz） | 特性 |
|-------|--------------|------|
| 0.5 | ~159 Hz | 弱滤波，响应快 |
| 0.2 | ~35 Hz | 适中 |
| 0.1 | ~16 Hz | 强平滑，明显滞后 |
| 0.01 | ~1.6 Hz | 极强滤波，响应很慢 |

alpha 越小，滤除高频噪声的能力越强，但对输入变化的响应也越慢（滞后大）。

### 软件 vs 硬件 RC 滤波的对比

| 特性 | 硬件 RC | 软件一阶 IIR |
|------|---------|-------------|
| 成本 | 需要 R + C 元件 | 一次乘加运算 |
| 灵活性 | 需更换元件改变 fc | 运行时修改 alpha |
| 抗混叠 | 可作为 ADC 前级抗混叠 | 不能替代抗混叠硬件 |
| 延迟 | 群延迟 ≈ RC | 取决于 alpha，类似等效 |
| 温漂 | R、C 值随温度变化 | 无温漂 |

> 两者数学本质完全相同：y[n] = α·x[n] + (1-α)·y[n-1] 就是 RC 滤波的离散形式。详细推导见 [[EWMA]]。

### 常见陷阱

1. **alpha 过小导致输出爬升慢**：首次采样时可用 `f->out = x` 跳过冷启动
2. **alpha 与 fc 不是线性关系**：当 α 很小时（如 0.01），fc ≈ α·fs / (2π)；当 α 较大时直接用公式
3. **Ts 必须远小于 RC**：采样定理要求 α < 1，即 T < RC。否则滤波器会不稳定
4. **不能替代硬件抗混叠**：软件滤波无法阻止高频信号通过采样折叠到低频

## 参考
- Horowitz & Hill,《The Art of Electronics》, 3rd ed., Ch.1
- Oppenheim & Schafer,《Discrete-Time Signal Processing》, 3rd ed., Ch.7
- AN-455: "Understanding and Designing EMI Filters" (TI Application Note)
- AN-733: "Software RC Filter" (Microchip Application Note)

## 相关笔记
- [[EWMA]] — 一阶 IIR 低通在嵌入式中的最简实现，本页的软件实现与之等价
- [[均值滤波]] — 另一种常见去噪手段，需要缓冲区
- [[消抖算法的选择]] — 软滤波的工程选型对比
