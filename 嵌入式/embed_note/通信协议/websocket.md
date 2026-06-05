---
date: 2026-06-01
tags: [websocket, esp-idf, 通信协议, tcp, tls, networking]
aliases: [WebSocket, RFC 6455]
---

# WebSocket

## 概述

WebSocket 是一种基于 TCP 的全双工通信协议（RFC 6455），通过 HTTP Upgrade 握手建立连接后，客户端和服务器可以在同一条连接上双向、低延迟地发送消息帧。对嵌入式设备而言，它比 HTTP 轮询省带宽、比 raw TCP 更标准化，适合实时数据推送场景（设备状态上报、远程调试终端、OTA 进度推送等）。

## 核心概念

### 协议分层：它不在 HTTP 之上

常见误区是"WebSocket 基于 HTTP"，实际上 HTTP 只参与握手：

```
应用层       WebSocket 帧（opcode + payload）
               ↓
会话层       HTTP Upgrade 握手（一次性，连接建立后退出）
               ↓
传输层       TCP（全双工流）
               ↓
安全层       TLS（wss:// 时在 TCP 之上）
```

- **握手阶段**：客户端发 HTTP GET + `Upgrade: websocket`，服务器 101 响应，之后协议切换为 WebSocket 帧
- **数据传输阶段**：HTTP 完全不参与，双方直接交换 WebSocket 帧
- **关闭阶段**：任一方发 Close 帧（opcode 0x8），对方回 Close 帧，TCP 关闭

### WebSocket 帧结构

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------+ - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+
```

关键字段：
这段**2到14字节**的固定头部包含了关键的元数据。

- **FIN (1 bit)**：**最后一帧标志**。1表示这一帧是整个消息的最后一片；0表示后面还有分片[](https://blog.csdn.net/ababab12345/article/details/103759223)。就像快递分多个包裹寄送，这个标志告诉你这是不是最后一个。
    
- **RSV1, RSV2, RSV3 (各1 bit)**：**扩展保留位**。为WebSocket扩展预留，没有扩展时必须是0，否则连接会被中断[](https://www.ctyun.cn/developer/article/569526444462149)。
    
- **Opcode (4 bits)**：**操作码**，用来告诉接收方这个包裹里装的是什么[](https://blog.csdn.net/ababab12345/article/details/103759223)。具体类型如下表所示：
    
- **MASK (1 bit)**：**掩码标志**。1表示有效载荷被掩码，0则没有[](https://www.ctyun.cn/developer/article/569526444462149)。**从客户端发给服务器的数据帧，这个位必须为1**，以保证网络安全[](https://cloud.tencent.com.cn/developer/article/1402600?from=15425)。
    
- **Payload len (7 bits / 7+16 bits / 7+64 bits)**：**有效载荷长度**。根据其值指示Payload Data的长度[](https://www.ctyun.cn/developer/article/569526444462149)[](https://blog.csdn.net/ababab12345/article/details/103759223)：
    
    - **0-125**：长度直接为这个值。
        
    - **126**：长度由随后的2个字节（16位）表示。
        
    - **127**：长度由随后的8个字节（64位）表示，支持超大数据的传输。
        
- **Extended payload length (16 or 64 bits)**：当Payload len为126或127时，这个字段用来指定真正的有效载荷长度[](https://www.ctyun.cn/developer/article/569526444462149)。
    
- **Masking-key (32 bits)**：**掩码密钥**。仅当MASK位为1时才存在。接收方会用这个密钥对Payload Data进行异或运算，以还原原始数据[](https://www.ctyun.cn/developer/article/569526444462149)[](https://cloud.tencent.com.cn/developer/article/1402600?from=15425)。

### Opcode 一览

| Opcode | 类型 | 说明 |
|--------|------|------|
| 0x0 | Continuation | 分片消息的后续帧 |
| 0x1 | Text | UTF-8 文本数据 |
| 0x2 | Binary | 二进制数据 |
| 0x8 | Close | 关闭连接 |
| 0x9 | Ping | 心跳请求 |
| 0xA | Pong | 心跳响应 |

Ping/Pong 用于 keep-alive：收到 Ping 必须回 Pong，但应用层一般不直接操作——ESP-IDF 客户端会自动处理。

### 握手过程

客户端请求：
```http
GET /path HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

服务器响应：
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

- `Sec-WebSocket-Key` 是客户端随机生成的 base64 串，服务器用固定 GUID `258EAFA5-E914-47DA-95CA-C5AB0DC85B11` 拼接后 SHA-1 再 base64 得到 `Sec-WebSocket-Accept`——这是握手安全的根基
- `Sec-WebSocket-Protocol` 可选，用于协商子协议（如 MQTT over WebSocket）

### 关闭码（Close Code）

| 码 | 含义 |
|----|------|
| 1000 | 正常关闭 |
| 1001 | 端点离开（如页面跳转） |
| 1002 | 协议错误 |
| 1003 | 收到不支持的数据类型 |
| 1006 | 连接异常关闭（不会在帧中发送） |
| 1007 | 数据格式不符（如收到非 UTF-8 却声称 text） |
| 1008 | 策略违反 |
| 1009 | 消息过大 |
| 1011 | 服务器内部错误 |
| 3000-4999 | 应用程序自定义 |

## ESP-IDF WebSocket Client

### 架构

```
 应用层
    ↓ init / start / send / close / destroy
 ESP WebSocket Client (esp_websocket_client)
    ↓ event loop + internal task
 esp_transport (TCP / TLS)
    ↓
 mbedTLS (wss://) / lwIP socket (ws://)
```

客户端内部创建独立 RTOS 任务，通过 event loop 向应用层派发事件。多个 client handle 可共存。

### 配置结构 `esp_websocket_client_config_t`

```c
typedef struct {
    const char *uri;                   // 完整 URI（ws:// 或 wss://），设置后覆盖 host/port/path
    const char *host;                  // 域名或 IP
    int port;                          // 端口（ws 默认 80，wss 默认 443）
    const char *path;                  // HTTP 路径，默认 "/"
    const char *username;              // Basic Auth 用户名
    const char *password;              // Basic Auth 密码
    const char *subprotocol;           // 请求的子协议
    const char *user_agent;            // 自定义 User-Agent
    const char *headers;               // 附加 HTTP 头，每行以 CRLF 结尾

    // TLS
    const char *cert_pem;              // 服务器证书（PEM 格式）
    size_t cert_len;                   // 证书长度（DER 时用）
    const char *client_cert;           // 客户端证书（mTLS）
    size_t client_cert_len;
    const char *client_key;            // 客户端私钥
    size_t client_key_len;
    bool use_global_ca_store;          // 使用全局 CA 存储
    bool skip_cert_common_name_check;  // 跳过 CN 校验

    // 重连
    bool disable_auto_reconnect;       // 禁止自动重连
    int reconnect_timeout_ms;          // 重连间隔（默认 10s）
    int network_timeout_ms;            // 网络操作超时（默认 10s）

    // 心跳
    size_t ping_interval_sec;          // Ping 间隔（默认 10s）
    int pingpong_timeout_sec;          // Pong 超时断连
    bool disable_pingpong_discon;      // Pong 超时不自动断连

    // 任务
    const char *task_name;
    int task_prio;
    int task_stack;
    int task_core_id;                  // 绑核

    // 其他
    int buffer_size;                   // 接收缓冲区大小
    bool keep_alive_enable;            // TCP keep-alive
    int keep_alive_idle;
    int keep_alive_interval;
    int keep_alive_count;
    void *user_context;                // 透传用户数据到事件回调
} esp_websocket_client_config_t;
```

### 状态机与事件

```
  init → [BEGIN] → [BEFORE_CONNECT] → [CONNECTED]  ⇄  [DATA]
                         ↑                  ↓            ↓
                         └── 重连 ←── [DISCONNECTED] / [ERROR] / [CLOSED] → [FINISH]
```

事件类型 `esp_websocket_event_id_t`：

| 事件 | 触发条件 |
|------|----------|
| `WEBSOCKET_EVENT_CONNECTED` | 连接建立，握手完成，可收发数据 |
| `WEBSOCKET_EVENT_DATA` | 收到数据帧（可能是分片帧） |
| `WEBSOCKET_EVENT_DISCONNECTED` | 传输层断开 |
| `WEBSOCKET_EVENT_CLOSED` | 正常关闭 |
| `WEBSOCKET_EVENT_ERROR` | 传输或协议错误 |
| `WEBSOCKET_EVENT_ANY` | 通配符，监听所有事件 |

数据事件结构 `esp_websocket_event_data_t`：
```c
typedef struct {
    const char *data_ptr;              // 载荷指针
    int data_len;                      // 本次事件数据长度
    bool fin;                          // FIN 标志（分片结束时为 true）
    uint8_t op_code;                   // 帧 opcode
    esp_websocket_client_handle_t client; // 客户端句柄
    void *user_context;                // 用户上下文
    int payload_len;                   // 完整消息总长（跨分片）
    int payload_offset;                // 当前分片在完整消息中的偏移
    int close_status_code;             // 服务器关闭码
    esp_websocket_error_codes_t error_handle; // 错误详情（仅 ERROR 事件有效）
} esp_websocket_event_data_t;
```

### 生命周期与 API

一个完整的客户端生命周期：

```c
// 1. 初始化
esp_websocket_client_config_t cfg = {
    .uri = "ws://echo.websocket.org",
    // 其他配置...
};
esp_websocket_client_handle_t client = esp_websocket_client_init(&cfg);

// 2. 注册事件回调
esp_websocket_register_events(client, WEBSOCKET_EVENT_ANY, event_handler, NULL);

// 2.5 可选：追加 HTTP 头（必须在 start 之前）
esp_websocket_client_append_header(client, "Authorization", "Bearer xxx");

// 3. 启动连接
esp_websocket_client_start(client);

// 4. 收发数据（在事件回调中进行）
esp_websocket_client_send_text(client, data, len, portMAX_DELAY);
esp_websocket_client_send_bin(client, data, len, portMAX_DELAY);

// 5. 关闭（干净关闭：发 Close 帧 → 等服务器回 Close → 等 TCP 关闭）
esp_websocket_client_close(client, pdMS_TO_TICKS(3000));

// 6. 销毁
esp_websocket_client_destroy(client);
```

### 发送 API 全貌

| 函数 | Opcode | FIN | 用途 |
|------|--------|-----|------|
| `send_text` | 0x1 | 自动置位 | 发送完整文本帧 |
| `send_text_partial` | 0x1 | 不置位 | 文本分片的起始帧 |
| `send_bin` | 0x2 | 自动置位 | 发送完整二进制帧 |
| `send_bin_partial` | 0x2 | 不置位 | 二进制分片的起始帧 |
| `send_cont_msg` | 0x0 | 不置位 | 分片中的延续帧 |
| `send_fin` | — | 独立 FIN 帧 | 标记分片结束 |
| `send_with_opcode` | 自定义 | 最后一帧置位 | 完全控制 |

分片发送模式：
```c
esp_websocket_client_send_bin_partial(client, chunk1, len1, timeout);
esp_websocket_client_send_cont_msg(client, chunk2, len2, timeout);
esp_websocket_client_send_cont_msg(client, chunk3, len3, timeout);
esp_websocket_client_send_fin(client);  // 收尾
```
接收端的 `payload_len` 和 `payload_offset` 可用来拼装完整消息。

### 事件回调模板

```c
static void websocket_event_handler(void *handler_args, esp_event_base_t base,
                                     int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    esp_websocket_client_handle_t client = data->client;

    switch (event_id) {
    case WEBSOCKET_EVENT_CONNECTED:
        ESP_LOGI(TAG, "Connected");
        break;
    case WEBSOCKET_EVENT_DATA:
        ESP_LOGI(TAG, "Received %d bytes (opcode=%d, fin=%d)",
                 data->data_len, data->op_code, data->fin);
        // data->data_ptr 和 data->data_len 用于处理数据
        break;
    case WEBSOCKET_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "Disconnected");
        break;
    case WEBSOCKET_EVENT_CLOSED:
        ESP_LOGI(TAG, "Closed, server code=%d", data->close_status_code);
        break;
    case WEBSOCKET_EVENT_ERROR:
        ESP_LOGE(TAG, "Error: type=%d, handshake_status=%d",
                 data->error_handle.esp_ws_handshake_status_code);
        break;
    }
}
```

### TLS 配置要点

- **wss://** 时必须提供 `cert_pem`，否则 TLS 默认不验证证书（不安全）
- 提取服务器证书：
  ```bash
  echo "" | openssl s_client -showcerts -connect example.com:443 \
      | sed -n "1,/Root/d; /BEGIN/,/END/p" \
      | openssl x509 -outform PEM > server.pem
  ```
- 也可用 `use_global_ca_store = true` + `crt_bundle_attach` 启用 CA bundle

### 心跳机制设计

WebSocket 连接有三个层次的心跳/保活，层次不同、互不冲突：

```
应用层心跳   ← 你自定义的消息帧，检测"对端应用是否卡死"
    ↓
WebSocket Ping/Pong  ← RFC 6455 协议层，对端自动回复，不经过应用层
    ↓
TCP keep-alive  ← 操作系统/LwIP 层，只有 ACK 包，检测"网线拔了没有"
```

#### 各层对比

| 机制 | 配置 | 检测范围 | 对端要求 | 功耗 |
|------|------|----------|----------|------|
| TCP keep-alive | `keep_alive_enable` + idle/interval/count | 网络层死连接（拔网线、NAT 超时） | 不需要对端配合 | 极低 |
| WebSocket Ping/Pong | `ping_interval_sec` / `pingpong_timeout_sec` | TCP 通道活性 | RFC 6455 强制支持，自动回复 | 低 |
| 应用层心跳 | 自定义 task 定时 send | TCP 通道 + 对端应用逻辑活性 | 需要对端显式回复 | 取决于设计 |

#### 应用层心跳 vs IDF Ping：选哪个？

**核心差异**：WebSocket Ping/Pong 由协议栈自动处理——对端收到 Ping 后，在协议栈层直接回 Pong，**不会送到对端应用层**。因此它只能证明"TCP 还通着"，不能证明"对端应用程序没卡死"。

如果你自己实现了应用层心跳（比如每 5s 发一条 JSON ping，超时无回复主动断连+重连），那你的心跳**已经覆盖了 WebSocket Ping 的检测范围**，IDF 的 `ping_interval_sec` 是冗余的。可以关掉：

```c
esp_websocket_client_config_t cfg = {
    .uri = "ws://server/ws",
    .ping_interval_sec = 0,          // 关闭协议层 ping
    .disable_pingpong_discon = true,  // 不因 pong 超时断连
};
```

#### 建议保留 TCP keep-alive

即使你有关闭 WebSocket Ping/Pong 和应用心跳，也建议保留 TCP keep-alive——它不占应用带宽（只有裸 ACK），能兜底检测拔网线、Wi-Fi 漫游丢连接、NAT 表过期这类**根本没有对端参与的场景**：

```c
.keep_alive_enable = true,
.keep_alive_idle = 5,
.keep_alive_interval = 5,
.keep_alive_count = 3,
```

#### 组合建议

| 场景 | 推荐配置 |
|------|----------|
| 纯设备端需要保持通路 | TCP keep-alive + WebSocket Ping/Pong（全自动，零代码） |
| 需要确认对端业务正常 | TCP keep-alive + 应用层心跳（关 IDF Ping） |
| 省电/低流量设备 | 仅 TCP keep-alive，定期查 `is_connected` |

### 实用技巧

- **重连超时调整**：在 `WEBSOCKET_EVENT_DISCONNECTED` 事件中调用 `esp_websocket_client_set_reconnect_timeout()` 可动态调整重连间隔
- **互斥 TLS 方式**：`cert_pem` 和 `use_global_ca_store` + `crt_bundle_attach` 二选一
- **不能从事件回调中调用 stop/close/destroy**，会死锁——应在回调外触发
- **错误排查**：ERROR 事件中的 `error_handle` 结构提供了 TLS 错误码、握手 HTTP 状态码、socket errno 三层信息

## 参考

- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [ESP WebSocket Client 官方文档](https://docs.espressif.com/projects/esp-protocols/esp_websocket_client/docs/latest/)
- [esp-protocols GitHub](https://github.com/espressif/esp-protocols)

## 相关笔记

- [[modbus]]
- [[can总线]]
- [[ESP WebSocket Client API]]
