---
date: 2026-06-18
tags: [how-to, wsl2, usb, esp32, esp-idf]
aliases: [WSL2 USB passthrough, WSL2 USB透传]
updated: 2026-06-18
---

# WSL2 USB 透传 — ESP32 烧录指南

## 概述

WSL2 运行在 Hyper-V 虚拟机中，无法直接访问 Windows 主机的 USB 设备。通过 [usbipd-win](https://github.com/dorssel/usbipd-win)（微软官方推荐的开源项目），可以将 USB 设备通过 USB/IP 协议透传到 WSL2，实现在 Linux 环境下烧录和调试 ESP32。

> 本笔记基于 Microsoft 官方文档和 usbipd-win 项目 README 整理，适用于 ESP-IDF 开发场景。

---

## 先决条件

| 项目 | 要求 |
|------|------|
| Windows 版本 | Windows 10 (x64/ARM64) 或 Windows 11，Build 1809+ |
| WSL 版本 | WSL 2（非 WSL 1） |
| WSL 内核 | ≥ 5.10.60.1（运行 `uname -r` 查看） |
| usbipd-win | v5.0.0+（推荐最新版） |

---

## 一、首次安装

### 1. 更新 WSL 内核

确保内核支持 USB/IP（新版 WSL 内核已内置 USB/IP 模块）：

**PowerShell（管理员）：**

```powershell
wsl --update
wsl --shutdown
```

> 如果内核版本低于 5.10.60.1，更新后会自动升级。

### 2. Windows 端安装 usbipd-win

**PowerShell（管理员）：**

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

> 使用 `--interactive` 避免自动重启。安装完成后无需手动重启。

安装内容：
- 服务 `usbipd`（USBIP Device Host）—— 开机自启
- 命令行工具 `usbipd` —— 加入 PATH
- 防火墙规则 `usbipd` —— 允许本地子网连接

### 3. WSL 端安装 USB/IP 工具

```bash
sudo apt update
sudo apt install -y linux-tools-generic hwdata usbutils
```

#### 修复 usbip 命令路径问题

WSL 内核版本（如 `6.x.x-microsoft`）可能与 `linux-tools-generic` 包中的版本不匹配，导致 `/usr/bin/usbip` 脚本报错。

**推荐方案：用 `update-alternatives` 注册正确路径**

```bash
sudo update-alternatives --install /usr/bin/usbip usbip \
  /usr/lib/linux-tools/*-generic/usbip 20
```

> 这比直接复制二进制更优雅，且能随包更新自动切换。

**备选方案：直接复制（如果 update-alternatives 不可用）**

```bash
sudo cp /usr/lib/linux-tools/*-generic/usbip /usr/local/bin/usbip
```

验证：

```bash
usbip version          # 应正常输出版本号
```

---

## 二、绑定设备（只需做一次）

`usbipd bind` 将设备标记为可共享，**绑定状态在 Windows 重启后依然有效**，无需重复执行。

**PowerShell（管理员）：**

```bash
# 查看所有 USB 设备，找到 ESP32 对应的 BUSID
usbipd list

# 绑定设备（只需一次，重启后仍有效）
usbipd bind --busid <BUSID>
```

> **bind 需要管理员权限。** bind 后设备状态变为 `Shared`。

---

## 三、每次使用流程

### Step 1 — Attach 设备到 WSL

**PowerShell（普通权限即可）：**

```powershell
usbipd attach --wsl --busid <BUSID>
```

> **attach 不需要管理员权限**（只有 bind 需要）。

#### 可选：auto-attach 模式（推荐）

如果设备会频繁断开重连（如 ESP32 进入下载模式时 USB 会重新枚举），使用 `--auto-attach` 可自动重连：

```powershell
usbipd attach --wsl --busid <BUSID> --auto-attach
```

该命令会保持前台运行，设备断开后重新插入时自动重新 attach，无需手动干预。

> 按 `Ctrl+C` 退出 auto-attach 模式。

### Step 2 — WSL 确认设备

```bash
lsusb                        # 应看到 303a:1001 Espressif
ls /dev/ttyACM*              # 应看到 /dev/ttyACM0
```

### Step 3 — 权限处理

#### 方案 A：手动设置权限（简单但临时）

```bash
sudo chmod 666 /dev/ttyACM0
```

#### 方案 B：加入 dialout 组（推荐，需启用 systemd）

```bash
# 首次执行（需重启 WSL 生效）
sudo usermod -aG dialout $USER
```

重启 WSL 后，当前用户的串口设备权限自动生效，无需每次 chmod。

#### 方案 C：udev 规则（需启用 systemd）

> **重要：** WSL2 默认不运行 systemd，udev 规则**不会自动生效**。需要先启用 systemd。

**启用 systemd：** 编辑 `/etc/wsl.conf`：

```ini
[boot]
systemd=true
```

然后重启 WSL：

```powershell
wsl --shutdown
```

**添加 udev 规则：**

```bash
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", MODE="0666"' | \
  sudo tee /etc/udev/rules.d/99-esp32.rules
sudo udevadm control --reload-rules
```

> 如果 `udevadm control --reload-rules` 报 "No such file or directory" 错误，改用：
> `sudo service udev restart`

### Step 4 — 烧录

```bash
cd ~/projects/your_project
source ~/.espressif/tools/activate_idf_v5.3.5.sh  # 按实际版本调整
idf.py -p /dev/ttyACM0 flash
```

### Step 5 — 监视串口

```bash
idf.py -p /dev/ttyACM0 monitor
```

按 `Ctrl+]` 退出 monitor。

### Step 6 — 断开设备（可选）

**PowerShell：**

```powershell
usbipd detach --busid <BUSID>
```

> 如果只是暂时不用，可以不 detach。设备物理断开时会自动从 WSL 中移除。
> 重新使用时只需再次 `usbipd attach --wsl --busid <BUSID>`（bind 还在）。

---

## 四、完整快捷流程

```
# ===== Windows（首次绑定，之后无需重复）=====
usbipd bind --busid <BUSID>

# ===== Windows（每次使用）=====
usbipd attach --wsl --busid <BUSID>

# ===== WSL =====
sudo chmod 666 /dev/ttyACM0
cd ~/projects/your_project
source ~/.espressif/tools/activate_idf_v5.3.5.sh
idf.py -p /dev/ttyACM0 flash monitor
```

---

## 五、常见问题

### Q: `lsusb` 看不到设备

1. 确认 Windows 端已 attach：

```powershell
usbipd list           # 状态应为 Attached
```

2. 如果状态是 `Shared`，重新 attach：

```powershell
usbipd attach --wsl --busid <BUSID>
```

3. WSL 端检查内核模块：

```bash
sudo modprobe vhci-hcd
lsmod | grep vhci     # 应有 vhci_hcd 和 usbip_core
```

如果 `modprobe` 失败，说明内核缺少 USB/IP 模块，运行 `wsl --update` 更新内核。

### Q: `idf.py flash` 提示 "Path not readable" 或权限拒绝

```bash
sudo chmod 666 /dev/ttyACM0
```

更好的长期方案是加入 `dialout` 组或启用 systemd + udev 规则（见"权限处理"部分）。

### Q: 设备重新插拔后不可用

1. 重新插拔后 BUSID 可能变化，先查看：

```powershell
usbipd list
```

2. 重新 attach（bind 仍在，不需要重新 bind）：

```powershell
usbipd attach --wsl --busid <新BUSID>
```

> 推荐使用 `--auto-attach` 模式，避免手动处理重连。

### Q: `usbipd attach` 报 "Device busy (exported)"

```powershell
usbipd detach --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

### Q: ESP32 进入下载模式后设备断开

ESP32 在烧录时会自动复位并重新枚举 USB 设备，这会导致 attach 断开。解决方法：

- 使用 `usbipd attach --wsl --busid <BUSID> --auto-attach`，设备重新枚举后自动重连
- 或者在烧录前按住 ESP32 的 **BOOT** 按键，烧录完成后再松开

### Q: `idf.py flash` 烧录超时或卡住

尝试降低波特率：

```bash
idf.py -p /dev/ttyACM0 -b 115200 flash
```

### Q: udev 规则不生效

WSL2 默认不运行 systemd，所以 udev 不会自动执行。需要：

1. 在 `/etc/wsl.conf` 中启用 systemd
2. 重启 WSL（`wsl --shutdown`）
3. 确认 udev 正在运行：`systemctl status udev`

---

## 六、原理简述

```
┌──────────────┐   USB/IP 协议   ┌──────────────┐
│  Windows 主机  │ ◄────────────► │   WSL2 虚拟机  │
│  (USB Host)   │                │  (VHCI 客户端) │
│               │                │               │
│  usbipd-win   │  TCP 3240      │  vhci-hcd     │
│  (USB Server) │ ──────────────►│  (USB/IP Client)│
└──────────────┘                └──────────────┘
```

- **usbipd-win** 在 Windows 侧作为 USB 服务器，将物理 USB 设备通过网络协议共享
- **WSL2 内核** 的 `vhci-hcd` 模块作为 USB/IP 客户端接收设备
- 设备一旦 attach 到 WSL，Windows 侧将无法使用该设备
- bind 是 Windows 侧的权限操作（标记设备可共享），attach 是建立实际连接

---

## 参考

- [Microsoft 官方文档 - Connect USB devices to WSL](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)
- [usbipd-win GitHub 仓库](https://github.com/dorssel/usbipd-win)
- [usbipd-win WSL 支持 Wiki](https://github.com/dorssel/usbipd-win/wiki/WSL-support)
- [WSL2 Linux Kernel 源码](https://github.com/microsoft/WSL2-Linux-Kernel)

## 相关笔记

无