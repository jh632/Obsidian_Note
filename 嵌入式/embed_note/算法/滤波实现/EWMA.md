---
date: 2026-05-26
tags: [滤波, EWMA, embedded-c]
aliases: [exponential-weighted-moving-average, 指数加权移动平均]
---

# EWMA

## 概述
指数加权移动平均，1 次乘加即可更新，是嵌入式最轻量的低通滤波器。等效于窗口无限长的均值滤波，但近期样本权重大。

## 公式

$$y_k = \alpha\, x_k + (1 - \alpha)\, y_{k-1}$$

展开递推形式：
$$y_k = \alpha\sum_{i=0}^{k}(1-\alpha)^i\,x_{k-i}$$

权重随距离指数衰减，等效窗口 $N \approx \dfrac{2}{\alpha} - 1$。

## 实现
```c
typedef struct {
    float alpha;  // 平滑系数 (0, 1]
    float out;
} ewma_t;

static inline void ewma_init(ewma_t *e, float alpha) {
    e->alpha = alpha;
    e->out   = 0;
}

static inline float ewma_update(ewma_t *e, float x) {
    e->out = e->alpha * x + (1 - e->alpha) * e->out;
    return e->out;
}
```

## 定点整数版（省 FPU）
```c
// alpha = 1/4，用移位实现
static inline int16_t ewma_q2_update(int16_t *out, int16_t x) {
    *out = x / 4 + (*out) - (*out) / 4;
    return *out;
}
```

## alpha 选取
| alpha | 等效窗口 N | 特性 |
|-------|-----------|------|
| 0.1 | ~20 | 强平滑，大滞后 |
| 0.2 | ~10 | 适中 |
| 0.5 | ~3 | 弱平滑，响应快 |

等效窗口 N ≈ 2/alpha - 1

## 与卡尔曼的关系
EWMA 是卡尔曼滤波在"静态模型 + 常量增益"下的特例：
- EWMA 的 alpha 对应卡尔曼增益 K
- 卡尔曼的 K 自适应调整，EWMA 的 alpha 固定

## 要点
- 最简单的低通滤波，1 次乘加，无缓冲区
- alpha 越小越平滑，但延迟越大
- 首次输出从 0 起步，可用首值初始化：`e->out = x` 跳过冷启动

## 相关笔记
- [[消抖算法的选择]]
- [[均值滤波]]
- [[卡尔曼滤波]]
