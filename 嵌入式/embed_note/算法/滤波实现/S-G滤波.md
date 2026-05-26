---
date: 2026-05-26
tags: [滤波, S-G滤波, embedded-c]
aliases: [savitzky-golay, SG-smoothing, Savitzky-Golay]
---

# S-G 滤波

## 概述
Savitzky-Golay 滤波，对滑动窗口内样本做最小二乘多项式拟合，取中心点值。既能平滑噪声又能保留峰值/边缘特征，广泛用于光谱和传感器信号。

## 公式

对窗口内样本拟合 $p$ 阶多项式 $f(i) = \sum_{j=0}^{p}a_j i^j$，最小二乘目标：

$$\min_{a_0,\dots,a_p}\sum_{i=-M}^{M}\left[x_{k+i} - \sum_{j=0}^{p}a_j\,i^j\right]^2$$

取中心点 $i=0$ 处拟合值 $y_k = a_0$，等价于卷积：

$$y_k = \sum_{i=-M}^{M} c_i\, x_{k+i}$$

卷积核 $c_i$ 由最小二乘解的矩阵形式离线求出：
$$\mathbf{c} = (\mathbf{J}^T\mathbf{J})^{-1}\mathbf{J}^T\,\mathbf{e}_0$$

其中 $\mathbf{J}$ 为 Vandermonde 矩阵，$\mathbf{e}_0$ 取第 0 行。

## 预计算卷积核实现
```c
// 5 点 2 阶 S-G 平滑核（查表法，避免运行时拟合）
// 来源：对 [-2,-1,0,1,2] 做 2 阶最小二乘拟合的中心系数
static const float sg5_c2[5] = {-3.0f/35, 12.0f/35, 17.0f/35, 12.0f/35, -3.0f/35};

typedef struct {
    float buf[5];
    int   idx;
} sg5_filter_t;

static inline void sg5_init(sg5_filter_t *f) {
    f->idx = 0;
    memset(f->buf, 0, sizeof(f->buf));
}

static inline float sg5_update(sg5_filter_t *f, float x) {
    f->buf[f->idx] = x;
    f->idx = (f->idx + 1) % 5;

    float out = 0;
    for (int i = 0; i < 5; i++)
        out += f->buf[(f->idx + i) % 5] * sg5_c2[i];
    return out;
}
```

## 常用核速查
| 窗口 | 阶数 | 中心系数 | 滤波核 |
|------|------|---------|--------|
| 5 | 2 | 17/35 | [-3, 12, 17, 12, -3] / 35 |
| 7 | 2 | 7/21 | [-2, 3, 6, 7, 6, 3, -2] / 21 |
| 5 | 3 | 同 2 阶 | 奇数阶与低一偶数阶相同 |

> 阶数 >= 窗口大小则退化为无平滑的插值。一般窗口 ≥ 2*阶数+1。

## 要点
- 核可离线计算好存表，运行时仅做卷积，与均值滤波开销相当
- 相比均值/高斯滤波，最大优势是保峰保边（多项式拟合不削峰）
- 代价：对高频噪声抑制不如高斯滤波，阶数过高会拟合噪声
- 需要对称窗口，实时系统中存在 (N-1)/2 个采样点延迟

## 相关笔记
- [[消抖算法的选择]]
- [[高斯滤波]]
