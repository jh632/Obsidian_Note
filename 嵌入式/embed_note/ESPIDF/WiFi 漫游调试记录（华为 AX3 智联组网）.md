---
tags: [embed_note, ESPIDF]
---

# WiFi 漫游调试记录（华为 AX3 智联组网）

环境：ESP-IDF v5.3.4 / ESP32-S3，AP 为两台华为 AX3 智联组网（同一 SSID `HJ-PSW`，两个节点都在 2.4GHz 信道 1）。

## 1. 问题现象

设备每次连接（含重启后）都连到固定的一台节点，即使那台信号更差。连接建立后也不会因信号变差切换到另一台。

## 2. 根因

两个机制叠加，都与信号强度无关。

**选台顺序固定。** `components/wifi_ws/wifi_ws.c` 的 `wifi_config_t wifi_cfg = {0}` 只填了 SSID 和密码，其余字段取零值，对应 ESP-IDF 的默认行为（`docs/en/api-guides/wifi.rst` 的字段说明）：

- `scan_method = 0 = WIFI_FAST_SCAN`：扫到第一个同 SSID 的 AP 就停止扫描并连接
- `channel = 0`：从信道 1 开始按 1~N 顺序扫描
- `sort_method = 0 = WIFI_CONNECT_AP_BY_SIGNAL`：该排序只在 `WIFI_ALL_CHANNEL_SCAN` 下参与选择，FAST_SCAN 下不起作用

**连接记忆。** 驱动默认 `WIFI_STORAGE_FLASH`，会把连接成功的 BSSID 记为 profile 写入 NVS，重启后优先连回该节点（启动日志里的 `prof:N` 是 profile 索引）。实测中 NVS 记录的正是那个弱节点，所以重启不改变结果。

连接建立后，STA 默认不会主动换节点，漫游需要 802.11k/v 引导或者额外的漫游逻辑。

## 3. 改动

### 3.1 STA 配置（components/wifi_ws/wifi_ws.c）

```c
/* 智联组网的各节点 SSID 相同，FAST_SCAN 只连扫描顺序里第一个匹配的节点，
 * 与该节点信号强弱无关；全信道扫描后按 RSSI 排序才能连上最强的节点 */
wifi_cfg.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
wifi_cfg.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;
/* 低于该 RSSI 的节点直接排除，避免连上远处的节点 */
wifi_cfg.sta.threshold.rssi = -80;
/* 802.11k/v：声明 RRM 与 BTM 能力，路由器可用 BTM 请求引导设备切换节点 */
wifi_cfg.sta.rm_enabled  = 1;
wifi_cfg.sta.btm_enabled = 1;
```

`esp_wifi_init()` 之后追加：

```c
/* 清除 NVS 中残留的 WiFi 状态：驱动会把上次连接的 BSSID 记为 profile，
 * 重启后优先连回它，即使该节点信号已变差 */
esp_wifi_restore();
/* 状态只留在 RAM，驱动不再把本次连接的 BSSID 写回 NVS */
esp_wifi_set_storage(WIFI_STORAGE_RAM);
```

### 3.2 断开处理

`WIFI_EVENT_STA_DISCONNECTED` 分支中，漫游引起的断开跳过应用层的 10 秒重连：

```c
if (evt->reason == WIFI_REASON_ROAMING ||              /* 207 */
    evt->reason == WIFI_REASON_BSS_TRANSITION_DISASSOC /* 12 */) {
    break;   /* 由 roaming app 和驱动自行重连 */
}
```

原因：roaming app 在断开事件里自己会调用 `esp_wifi_connect()`（`roaming_app.c:198`，经 `wifi_default.c` 挂在默认事件处理器上），应用层再调用会打断正在进行的节点切换。

### 3.3 配置项（sdkconfig.defaults）

```
CONFIG_IDF_EXPERIMENTAL_FEATURES=y
CONFIG_ESP_WIFI_11KV_SUPPORT=y
CONFIG_ESP_WIFI_RRM_SUPPORT=y
CONFIG_ESP_WIFI_WNM_SUPPORT=y
CONFIG_ESP_WIFI_SCAN_CACHE=y
CONFIG_ESP_WIFI_ENABLE_ROAMING_APP=y
CONFIG_ESP_WIFI_ROAMING_LOW_RSSI_THRESHOLD=-70
CONFIG_ESP_WIFI_ROAMING_PERIODIC_SCAN_THRESHOLD=-60
CONFIG_ESP_WIFI_ROAMING_PERIODIC_RRM_MONITORING=n
```

`ESP_WIFI_ENABLE_ROAMING_APP` 打开后由 `esp_wifi_init()` 自动初始化（`wifi_init.c:450`），应用侧不需要调用 API。它的行为：

- 低 RSSI 触发：当前节点 RSSI 跌破阈值时扫描并找更好的节点。连接时刻若 RSSI 已经低于配置阈值，触发阈值会被下调为"当前 RSSI − 5dB"（`ROAMING_LOW_RSSI_OFFSET`），避免刚连上就切换
- 周期扫描：每 30 秒（`ROAMING_SCAN_MONITOR_INTERVAL`）扫描一次，当前 RSSI 低于 `PERIODIC_SCAN_THRESHOLD` 且候选强出 `SCAN_ROAM_RSSI_DIFF`（默认 15dB）时发起切换
- 切换方式：先发 802.11v 的 BTM 查询让路由器引导；BTM 连续失败 2 次后主动断开并直连候选节点（legacy roaming，`roaming_app.c` 的 `trigger_legacy_roam`）

三个 RSSI 阈值的层次：

| 阈值 | 取值 | 含义 |
|------|------|------|
| `threshold.rssi` | -80 | 连接时的最低要求，低于此值的节点不参与连接 |
| `ROAMING_LOW_RSSI_THRESHOLD` | -70 | 已连接状态下信号跌破此值就找更好的节点 |
| `ROAMING_PERIODIC_SCAN_THRESHOLD` | -60 | 周期扫描在此值以下才判断是否值得切换 |

### 3.4 关闭 802.11k 周期请求

华为 AX3 的中国官网规格只标注 802.11v（AX3 Pro 为 802.11k/v），实测周期发送的 802.11k 邻居报告请求没有响应，每 30 秒产生一条 `E ROAM: No data received for neighbor report`。关闭 `ROAMING_PERIODIC_RRM_MONITORING` 后该日志消失，BTM 引导路径不受影响（`trigger_network_assisted_roam` 里两者独立）。

## 4. 实测对照（2026-09-20，设备 SN-PSW-W-HJ013）

两个节点的 BSSID：`62:52:7b:56:23:20` 与 `e2:ec:8d:d9:08:b8`。

只开漫游、未清 profile 的版本（先连弱节点，0.7 秒后漫游到强节点）：

```
I (5082) wifi:connected with HJ-PSW, aid = 1, channel 1, BW20, bssid = 62:52:7b:56:23:20
I (5083) wifi:security: WPA2-PSK, phy: bgn, rssi: -69
W (5770) wifi_ws: STA 断开连接，原因: 207
I (5787) wifi_ws: 节点漫游切换中，等待驱动重连
I (8228) wifi:connected with HJ-PSW, aid = 3, channel 1, BW20, bssid = e2:ec:8d:d9:08:b8
I (8229) wifi:security: WPA2-PSK, phy: bgn, rssi: -58
```

加上 `esp_wifi_restore()` + `WIFI_STORAGE_RAM` 之后（启动直接连扫描选出的节点）：

```
I (4169) wifi:connected with HJ-PSW, aid = 3, channel 1, BW20, bssid = e2:ec:8d:d9:08:b8
I (4170) wifi:security: WPA2-PSK, phy: bgn, rssi = -65
I (5354) wifi_ws: register success (code=1)
```

启动日志里的 profile 索引从 `prof:6` 变为 `prof:1`，对应旧记录被清除、按本次扫描结果重新建立。

漫游运行时的日志（`ROAM:` 前缀）：

- `ROAM: Issued Scan` / `ROAM: Could not find a better AP with the threshold set to N`：周期扫描与候选比较结果
- `ROAM: Disconnecting and connecting to <BSSID> on account of better rssi`：legacy 方式切换
- `ROAM: roaming_app_rssi_low_handler:bss rssi is=<RSSI>`：低 RSSI 触发

原始串口日志：`logs/20260920_161530_roam_before_nvs_clear.log`（清 profile 前的对照）、`logs/20260920_163805_roam_final.log`（最终版本）。

## 5. 路由器侧要求（华为官方文档）

- 两台路由器必须是智联组网。华为官方明确只有智联支持"自动切换到信号更好的路由器"，Wi-Fi 中继和普通有线桥接不支持
- 「更多功能 > 应用 > 辅助功能 > 快速漫游」保持开启（《华为路由器漫游环境使用建议》）
- Web 界面若有「组网信道模式」（更多功能 > Wi-Fi 设置 > Wi-Fi 高级），选「同信道部署」，官方说明为"提升 Wi-Fi 设备移动漫游体验"；异信道部署会让客户端跨信道切换
- 两台之间的回程优先用网线（官方给出的稳定性顺序：有线 > PLC > Wi-Fi）

## 6. 调试手法与注意点

- 抓串口日志：`build/serial_capture.py <串口> <秒数> <输出文件>`。复位与抓取放在同一条命令里，中间的时间间隙会漏掉启动日志
- 设备复位用 `python -m esptool --chip esp32s3 -p <串口> --before default_reset --after hard_reset run`。不要用 `USBJTAGSerialReset` 的 DTR/RTS 序列（`serial_capture.py` 的 `--reset` 参数），那会把芯片带进下载模式
- 想用调高 `ROAMING_LOW_RSSI_THRESHOLD` 的方式强制触发低 RSSI 漫游不成立：连接时刻 RSSI 已低于阈值时，roaming app 会把触发阈值下调为"当前 RSSI − 5dB"
- 判断节点选择是否按信号进行，看启动日志里 `wifi:connected with ... bssid = ...` 与紧随其后的 `wifi:security: ... rssi = ...`
- 配置改动后必须删除生成的 `sdkconfig` 再构建，否则旧值残留（defaults 只在生成 sdkconfig 时生效）

## 7. 与本次改动无关的既有现象

- PPG `late read(BACKLOG)` 积压：日志里从 9 月 16 日起大量存在（单份日志最多 2887 次）。成因是 GH3220 FIFO 读取要跨 3 次 SPI 事务，而 SPI2 与 TF 卡、MAX30009、SPO2 共用一把互斥锁，被占住时 FIFO 积压超过双缓冲容量（`gh_demo_hook.c` 的告警注释）
- GH3220 初始化偶发失败（`GH3220 initialization failed!`），同一固件换一次启动可能就正常
