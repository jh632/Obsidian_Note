  ### 构建与基础

  - [x] 1. 构建系统搭建 — `CMakeLists.txt`, `idf_component.yml`, `sdkconfig` ✅ 2026-06-01
  - [x] 2. NVS 配置模块 — `wifi_ws_config.h/c` (SSID/密码/服务器URL 读写) ✅ 2026-06-01
  - [x] 3. WiFi STA 连接管理 — `wifi_ws.c` (esp_netif + esp_wifi 事件驱动) ✅ 2026-06-01

  ### 通信层

  - [x] 4. WebSocket 客户端 — `esp_websocket_client` (URL 拼接 + 事件处理) ✅ 2026-06-02
  - [x] 5. cJSON 协议编解码 — `wifi_ws_protocol.h/c` (全部消息的 build/parse) ✅ 2026-06-01

  ### 业务逻辑

  - [x] 6. 设备连接状态机 — `DISCONNECTED → WIFI_CONNECTING → ... → COLLECTING` ✅ 2026-06-02
  - [x] 7. 命令接收与分发 — JSON 解析 → cmd 路由 → 业务处理 → JSON 响应 ✅ 2026-06-03
  - [x] 8. 传感器数据打包 — `wifi_ws_data.h/c` (双缓冲非破坏读取 + cJSON 打包) ✅ 2026-06-03

  ### 运行保障

  - [ ] 9. 心跳与定时器 — 30s ping + 指数退避重连 (1s→60s)
  - [x] 10. 集成到 main.c — `wifi_ws_init()` 接入 + 编译验证 ✅ 2026-06-03
  ws_config:配置wifi和url到nvs中
  ws_protocal:解析上位机下放的命令和下位机请求json文件的组装
  wifi_ws:初始化wifi_sta和websocket_client,实现连接状态机和命令接收与分发
  ws_data: