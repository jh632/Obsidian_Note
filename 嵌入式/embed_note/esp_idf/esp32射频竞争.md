好，从底层开始讲整个原理。

---

## 一、ESP32 硬件限制：单射频

ESP32 只有一个 **2.4GHz 射频前端**。WiFi（AP + STA）和蓝牙（BT + BLE）共用：

```
         ┌─────────────┐
         │  单射频硬件  │ ← 同一时刻只能干一件事
         └──────┬──────┘
        ┌───────┴───────┐
        ▼               ▼
     WiFi (AP+STA)    BLE
```

所以 ESP-IDF 用 **时分复用（TDM）** 来调度——分时间片，轮流用。

---

## 二、AP 靠 Beacon 宣告"我还活着"

AP 模式最关键的事情：**每 100ms 发一次 Beacon 帧**。

```
时间轴： |Beacon|          |Beacon|          |Beacon|          |Beacon|
         0ms             100ms            200ms            300ms
```

手机连上 AP 后会监听这些 Beacon。如果连续 **5-10 个 Beacon 收不到**（0.5-1s），手机的 WiFi 子系统就认为 AP 挂了，启动"智能切换网络"——这就是你看到的现象。

---

## 三、扫描时射频离开 AP 信道

你配网时设备工作在这种模式：**APSTA**（AP + STA 共存）

```
信道1  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (扫描 Probe Request)
信道2  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
信道3  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
信道4  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
信道5  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
信道6  ░░░░░░░░░░░░░░░░░░░░░░ ← AP 在这里！但射频没空发 Beacon
信道7  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  ...
信道13 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

- ESP32 配置在**信道 6** 当 AP
- `esp_wifi_scan_start` 让 STA 逐个信道发 Probe Request
- 扫描到信道 1、2、3、4、5、7、8…13 时，**射频物理上切走了**
- 信道 6 上没有射频，****Beacon **发不出去****
- 手机收不到 Beacon → 以为 AP 断了 → 自动切到你家的 WiFi

---

## 四、蓝牙让情况更糟

蓝牙共存时分复用，把一个信道的时间再分一半给 BLE：

```
无蓝牙时：     |信道1 scan|信道2 scan|...|信道6 dwell|信道7 scan|...
              120ms      120ms         30ms(发Beacon) 120ms
总耗时 ≈ 13 × 120ms = 1.5s  

有蓝牙时：     |WiFi|BLE|WiFi|BLE|WiFi|BLE|...
              时间片交替，WiFi 实际占用率更低
总耗时 ≈ 5s   ← 你实测 4.9s
```

5s 内射频绝大部分时间都不在信道 6，手机当然切网。

---

## 五、怎么修？`home_chan_dwell_time`

扫描器每扫完一个非 AP 信道，允许你设置一个"回主页信道停留时间"，让 AP 喘口气发 Beacon：

```
加了 dwell time 后：
     |信道1 scan|← 回信道6发Beacon →|信道2 scan|← 回信道6发Beacon →|...
     ≈120ms       home_chan_dwell      ≈120ms       home_chan_dwell
```

这个字段叫 **`home_chan_dwell_time`**，`wifi_scan_config_t` 里有（你用的 v5.3.4 支持）：

```c
typedef struct {
    ...
    uint8_t home_chan_dwell_time;   // 默认 30ms，范围 30-150ms
    wifi_scan_channel_bitmap_t channel_bitmap;  // 可以指定只扫哪些信道
} wifi_scan_config_t;
```

**默认 30ms 太短**——只够发 1/3 个 Beacon（Beacon 本身就需要 ~1ms 但 WiFi 调度有开销），手机大概率收不到。

设成 **150ms** 的好处：
- 每个非 AP 信道扫完后，回来停 150ms
- 这段时间 AP 可以正常发 **1 个完整的 Beacon** + 响应手机的数据
- 手机不断收到 Beacon → 不会触发智能切换
- 代价：150ms × 13 信道 ≈ **多 2s**，总耗时 ~7s

要不要试一下？改一行配置的事：

```c
wifi_scan_config_t scan_cfg = {
    ...
    .home_chan_dwell_time = 150,
};
```