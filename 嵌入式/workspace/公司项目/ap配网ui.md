# ESP32 SoftAP + HTTP 网页配网方案设计

## 1. 目录结构
在项目中新建 `wifi_prov` 组件，结构设计如下：
```text
components/wifi_prov/
├── CMakeLists.txt
├── wifi_prov.c                 # SoftAP、HTTP 服务器、配网状态机核心逻辑
├── wifi_prov.h                 # 对外接口：wifi_prov_enter / wifi_prov_exit
├── provision/
│   └── index.html              # 配网页（内置于 SPIFFS 镜像中）
└── spiffs_image/               # SPIFFS 镜像构建中间目录
```

## 2. 业务交互流程
```text
 [长按按键触发]
        │
        ▼
 wifi_ws_deinit()               # 释放原有网络资源
        │
        ▼
 启动 SoftAP                    # 热点名称: "PSA-<serial>"
        │
        ▼
 启动 HTTPD (Port: 80)
        │
        ▼
 用户连接 SoftAP
        │
        ▼
 浏览器访问 192.168.4.1
        │
        ▼
 加载配网页 (index.html)
        │
        ▼
 用户选择 WiFi 并输入密码
        │
        ▼
 点击 "连接" 按钮
        │
        ▼
 POST /api/configure            # 提交配置
        │
        ▼
 写入 NVS 存储 -> 切换 STA 模式 -> 连接目标 WiFi
        │
  ┌─────┴─────┐
  │连接成功    │连接失败
  ▼           ▼
返回成功提示   返回错误提示 -> 停留在网页
  │
  ▼
延时 1 秒
  │
  ▼
关闭 SoftAP -> 进入正常运行模式
```

## 3. HTTP API 接口设计
| API              | 方法   | 前端用途         | 返回内容                                                     | 后续如何拓展                                                      |
| ---------------- | ---- | ------------ | -------------------------------------------------------- | ----------------------------------------------------------- |
| `/`              | GET  | 加载配网页        | `index.html` (HTML)                                      | 无，已固定。如要改页面内容，改 `provision/index.html` 重新编译                 |
| `/api/device`    | GET  | 读取设备序列号/固件版本 | `{"serial":"...","fw_ver":"...","product":"..."}`        | 加字段：在 `prov_get_device_handler` 中 `cJSON_AddStringToObject` |
| `/api/scan`      | GET  | 扫描附近 WiFi    | `[{"ssid":"...","rssi":-50}]`                            | 加字段（如 authmode、channel）：在扫描循环中<br>`cJSON_AddNumberToObject` |
| `/api/configure` | POST | 提交 WiFi 密码   | `{"success":true,"message":"..."}`                       | 加参数：在 JSON 解析中<br>`cJSON_GetObjectItem(body, "新字段")`        |
| `/api/status`    | GET  | 轮询连接结果       | `{"status":"connecting\|success\|fail","message":"..."}` | 加状态字段：在<br>`cJSON_AddStringToObject` 中加                     |
|                  |      |              |                                                          |                                                             |
## 4. 前端配网页面设计（中文）

网页整体采用单页应用（SPA）设计，包含以下核心视觉模块与功能：

*   **[标题栏]**：PSA 设备配网 + `[动态读取设备序列号/版本号]`
*   **[WiFi 列表区]**：
    *   展示扫描到的 SSID 列表，支持点击直接选中。
    *   提供 **[重新扫描]** 按钮，点击触发列表刷新。
*   **[表单输入区]**：
    *   **密码输入框**：始终保持可见。
    *   **[连接] 按钮**：点击锁定输入并提交数据。
*   **[状态提示区]**：动态显示当前配网进度（`连接中...` / `配网成功` / `连接失败，请重试`）。
*   **[页脚]**：设备和固件基础信息展示。


