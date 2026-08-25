---
date: 2026-08-21
tags:
  - "#VFS"
aliases: []
---

# VFS文件管理系统API

> 涵盖应用层 POSIX / stdio API、VFS 抽象层设计、Linux 内核核心对象，以及 ESP-IDF 中的具体实践。

---

## 一、VFS 本质

**VFS（Virtual File System）不是一套固定的 API，而是一种抽象层设计。**

其核心价值：**让不同文件系统可以共享同一套文件操作接口**，应用程序无需关心底层是 FAT32、ext4 还是 LittleFS。

```
                    应用程序
                       │
        ┌──────────────┴──────────────┐
        │       文件系统 API          │
        │ open/read/write/stat/...    │
        └──────────────┬──────────────┘
                       │
                 VFS / FSAL
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      ext4           FAT32         LittleFS
        │              │              │
      Block          Block           Flash
      Device         Device
```

---

## 二、应用层 API（你实际编程用的）

### 1. POSIX 文件描述符接口（底层，基于 `fd`）

| 类别 | 核心 API |
|------|----------|
| 打开/创建 | `open()`, `openat()`, `creat()` |
| 关闭 | `close()` |
| 读取 | `read()`, `pread()`, `readv()` |
| 写入 | `write()`, `pwrite()`, `writev()` |
| 定位 | `lseek()` |
| 属性 | `stat()`, `fstat()`, `lstat()` |
| 删除 | `unlink()`, `unlinkat()` |
| 重命名 | `rename()`, `renameat()` |
| 目录操作 | `opendir()`, `readdir()`, `closedir()`, `mkdir()`, `rmdir()` |
| 文件系统信息 | `statfs()`, `statvfs()` |
| 控制 | `ioctl()`, `fcntl()` |
| 权限 | `chmod()`, `fchmod()`, `chown()`, `fchown()`, `umask()` |
| 链接 | `link()`, `symlink()` |

**示例：**
```c
int fd = open("/tmp/test.txt", O_RDWR | O_CREAT, 0644);
write(fd, buf, len);
lseek(fd, 0, SEEK_SET);
read(fd, buf, len);
close(fd);
```

**特殊说明：**
- `pread()` / `pwrite()`：在指定 offset 读写，**不改变当前文件偏移量**。
- `lseek(fd, 0, SEEK_END)`：获取文件大小。

---

### 2. 标准 I/O 接口（带缓冲，基于 `FILE*`）

| 功能 | API |
|------|-----|
| 打开 | `fopen()` |
| 关闭 | `fclose()` |
| 读取 | `fread()` |
| 写入 | `fwrite()` |
| 定位 | `fseek()` |
| 获取位置 | `ftell()` |
| 刷新缓冲区 | `fflush()` |
| 结束判断 | `feof()` |

**关系：** stdio 是在 POSIX `open/read/write` 之上提供的封装，两者最终都落到 VFS。

```
       应用
         │
   ┌─────┴─────┐
   │           │
stdio API  POSIX API
(FILE*)     (fd)
   │           │
   └─────┬─────┘
         ▼
        VFS
```

---

### 3. 目录与文件管理

| 操作 | API |
|------|-----|
| 打开目录 | `opendir()` |
| 读取目录项 | `readdir()` → `struct dirent` |
| 关闭目录 | `closedir()` |
| 创建目录 | `mkdir()` |
| 删除空目录 | `rmdir()` |
| 判断文件存在 | `access()` |
| 获取文件大小/属性 | `stat()` |
| 删除文件 | `unlink()` |
| 重命名 | `rename()` |

**示例：**
```c
DIR *dir = opendir("/sdcard/OTA");
struct dirent *ent;
while ((ent = readdir(dir)) != NULL) {
    printf("%s\n", ent->d_name);
}
closedir(dir);

struct stat st;
if (stat("/sdcard/OTA/app.bin", &st) == 0) {
    printf("size=%ld\n", st.st_size);
}
```

---

### 4. 文件系统容量查询

```c
struct statvfs fs;
if (statvfs("/sdcard", &fs) == 0) {
    uint64_t total = fs.f_blocks * fs.f_frsize;
    uint64_t free  = fs.f_bfree * fs.f_frsize;
}
```

> `stat()` 获取**单个文件**信息；`statvfs()` 获取**整个文件系统**信息。

---

## 三、ESP-IDF 中的 VFS 实践

### 1. SD 卡 + FatFs 挂载

```c
esp_vfs_fat_sdmmc_mount("/sdcard", ...);
```

将 FatFs 挂载到 `/sdcard`，之后所有 `fopen("/sdcard/...")` 自动交由 FatFs 处理。

### 2. OTA 典型流程

```
/sdcard
   ▼
opendir("/sdcard/OTA")
   ▼
readdir() 遍历，找到 app_v1.2.bin
   ▼
stat() 获取大小
   ▼
fopen() 或 open()
   ▼
fread() / read() 分块读取 → esp_ota_write()
   ▼
fclose() / close()
   ▼
unlink() （可选删除已升级文件）
```

**实际用到的 API：** `opendir`, `readdir`, `stat`, `fopen`, `fread`, `fclose`, `unlink`, `mkdir`, `access`。

### 3. 路径说明

ESP-IDF 中 VFS 将不同设备挂载到不同路径前缀：
- `/sdcard` → SD 卡 FatFs
- `/spiffs` → SPIFFS
- `/littlefs` → LittleFS

应用层**不需要关心底层**，统一使用 POSIX/stdio 接口。

---

## 四、VFS 架构核心（Linux 视角）

### 1. 关键内核对象

| 对象 | 表示什么 |
|------|----------|
| `super_block` | 一个已挂载的文件系统实例 |
| `inode` | 一个文件/目录的元数据（大小、权限、时间等） |
| `dentry` | 路径名与 inode 的关联（目录项缓存） |
| `file` | 一次 `open()` 产生的打开实例（包含当前 offset） |
| `file_operations` | 具体文件系统的操作函数表（read/write/ioctl...） |

### 2. 调用链示例

```c
fd = open("/home/a.txt", O_RDONLY);
```

背后流程：
```
"/home/a.txt"
      │
      ▼
    dentry   （路径解析缓存）
      │
      ▼
    inode    （文件元数据）
      │
      ▼
    file     （打开实例，含 offset）
      │
      ▼
     fd       （返回给用户）
```

`read(fd, buf, size)` 最终通过：
```
fd → struct file → file->f_op → 具体文件系统的 read()
```

### 3. 为什么 VFS 重要？

> **VFS 的价值不是提供 `open()`，而是让不同文件系统可以共享同一套文件操作接口。**

这样，应用层可以这样写：
```c
open("/sdcard/ota.bin", O_RDONLY);   // 实际是 FAT32
open("/flash/config.json", O_RDWR);  // 实际是 LittleFS
```

底层不同，但上层 API 完全一致。

---


## 五、总结：API 分类速查表

| 类别 | 核心 API |
|------|----------|
| **文件打开关闭** | `open`, `openat`, `creat`, `close` |
| **文件读写** | `read`, `write`, `pread`, `pwrite`, `readv`, `writev` |
| **文件定位** | `lseek` |
| **文件属性** | `stat`, `fstat`, `lstat` |
| **文件删除/重命名** | `unlink`, `rename` |
| **目录操作** | `opendir`, `readdir`, `closedir`, `mkdir`, `rmdir` |
| **文件系统信息** | `statfs`, `statvfs` |
| **控制与权限** | `ioctl`, `fcntl`, `chmod`, `chown` |
| **链接** | `link`, `symlink` |
| **标准 I/O（缓冲）** | `fopen`, `fclose`, `fread`, `fwrite`, `fseek`, `ftell`, `fflush` |

---
