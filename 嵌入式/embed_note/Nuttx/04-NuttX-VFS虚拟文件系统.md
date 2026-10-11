---
tags: [embed_note, NuttX, VFS, filesystem]
date: 2026-10-11
aliases: [NuttX VFS, NuttX虚拟文件系统, FatFs挂载, SPIFFS挂载, 文件系统分层]
---

# NuttX VFS 虚拟文件系统：统一接入 FAT、SPIFFS 和 LittleFS

前置笔记：[[01-NuttX-环境配置和编译烧录流程]]、[[02-NuttX-基础API]]、[[03-NuttX-字符设备驱动编写]]。

先给结论：**可以通过 VFS 把 FAT/VFAT、SPIFFS、LittleFS、ROMFS 等文件系统接入同一套 open/read/write/close 接口。**

但 VFS 并不是把所有文件系统变成完全相同的实现。它统一的是：

- 路径查找；
- 文件描述符；
- 文件和目录操作入口；
- 挂载点到具体文件系统的分发。

每种文件系统仍然保留自己的存储模型、容量限制、掉电保护能力、目录语义和配置要求。

---

## 1. VFS 到底解决什么问题

如果没有 VFS，应用需要分别调用不同的 API：

~~~text
FAT      → fat_open()、fat_read()
SPIFFS   → spiffs_open()、spiffs_read()
LittleFS → lfs_file_open()、lfs_file_read()
~~~

这样应用会直接依赖底层文件系统，换存储介质时必须修改大量代码。

有 VFS 后，应用只看统一接口：

~~~c
int fd = open("/data/config.txt", O_RDONLY);
read(fd, buffer, sizeof(buffer));
close(fd);
~~~

路径前缀决定请求由哪个挂载实例处理：

~~~text
open("/sdcard/a.txt")  → /sdcard → FAT
open("/spiffs/a.txt")  → /spiffs → SPIFFS
open("/data/a.txt")    → /data   → LittleFS
~~~

所以 VFS 的核心价值可以概括成一句话：

> 应用依赖路径和文件操作协议，文件系统负责实现协议，存储驱动负责访问介质。

---

## 2. NuttX 中的完整分层

把一条文件访问路径拆开，可以看到下面几层：

~~~text
应用层
  open/read/write/fstat/opendir/fsync
          │
          ▼
NuttX VFS
  路径解析、挂载点匹配、文件描述符管理
          │
          ├── /dev/ttyS0     → 字符设备驱动
          ├── /dev/mmcsd0    → 块设备驱动
          ├── /sdcard        → VFAT/FAT 文件系统
          ├── /spiffs        → SPIFFS 文件系统
          ├── /data          → LittleFS 文件系统
          └── /proc          → ProcFS 伪文件系统
          │
          ▼
文件系统或设备的操作表
          │
          ├── FAT → 块设备按扇区读写
          ├── SPIFFS/LittleFS → MTD 的读、写、擦除
          └── 字符设备 → file_operations
          │
          ▼
底层驱动
  SD/MMC、eMMC、NOR Flash、NAND Flash、RAM disk
~~~

这几层不要混淆：

| 层 | 负责什么 | 例子 |
| --- | --- | --- |
| VFS | 统一 API、路径和文件描述符 | open、read、mount |
| 文件系统 | 目录、文件名、空间分配、元数据 | FAT、SPIFFS、LittleFS |
| 块设备 | 按固定扇区读写 | SD/MMC、RAM disk |
| MTD | 面向 Flash 的读、写、擦除 | NOR、NAND、QSPI Flash |
| 字符设备 | 面向字节流或控制操作 | UART、GPIO、传感器 |

文件系统通常不会直接操作 GPIO 或 SPI 控制器。它依赖已经注册好的块设备或 MTD 设备。

---

## 3. 字符设备和挂载文件系统的区别

第 03 篇写的是字符设备驱动。它的节点类似：

~~~text
/dev/hello
~~~

访问它时，VFS 找到驱动的 file_operations：

~~~text
open("/dev/hello")
      ↓
hello_open()
      ↓
read("/dev/hello")
      ↓
hello_read()
~~~

挂载文件系统则是另一条路径：

~~~text
/data/config.txt
      ↓
VFS 找到 /data 挂载点
      ↓
LittleFS 的 mountpoint operations
      ↓
LittleFS 在 Flash 上查找 config.txt
      ↓
底层 MTD 驱动读 Flash
~~~

两者都使用 open/read/write，但实现入口不同：

| 访问对象 | VFS 找到的对象 | 主要操作表 |
| --- | --- | --- |
| /dev/hello | 设备 inode | struct file_operations |
| /sdcard/a.txt | 挂载点和文件 inode | 文件系统 mountpoint operations |
| /proc/meminfo | 伪文件系统节点 | ProcFS 的文件操作 |
| socket | socket 对象 | 网络 socket 接口 |

因此，register_driver("/dev/hello", ...) 是注册设备节点；mount(...) 是把一个文件系统实例接入路径树。两者都进入 VFS，但生命周期和内部协议不同。

---

## 4. VFS 中最重要的几个对象

### 4.1 路径

路径是应用选择对象的方式：

~~~text
/
├── dev/
│   ├── console
│   ├── ttyS0
│   └── mmcsd0
├── proc/
├── sdcard/
├── spiffs/
└── data/
~~~

VFS 先根据最长匹配原则找到挂载点，再把剩余路径交给对应的文件系统：

~~~text
请求：/data/config/device.json
挂载点：/data
交给 LittleFS：config/device.json
~~~

### 4.2 inode

在 NuttX 中，inode 是 VFS 里的节点对象，可以表示设备节点、目录、普通文件或伪文件系统节点。它保存节点名称、父子关系、操作表和私有数据等信息。

第 03 篇中：

~~~c
register_driver("/dev/hello", &g_hello_fops, 0666, &g_hello);
~~~

最后的 g_hello 会作为设备 inode 的私有数据，驱动可以从 filep->f_inode->i_private 取出。

### 4.3 struct file

应用调用 open() 后得到文件描述符 fd。fd 只是当前任务组文件表中的一个索引，真正保存打开状态的是 VFS 的 struct file。

struct file 通常关联：

- 当前 inode；
- 当前文件偏移量 f_pos；
- 本次打开的私有数据 f_priv；
- 打开标志；
- 文件系统或设备的操作入口。

所以 read(fd, ...) 最终会沿着下面的链路进入实现：

~~~text
fd
 ↓
struct file
 ↓
inode / mountpoint
 ↓
read callback
~~~

### 4.4 挂载点

挂载点把某个文件系统实例绑定到路径，例如：

~~~text
/dev/mmcsd0  ──mount -t vfat────> /sdcard
/dev/mtd0    ──mount -t spiffs──> /spiffs
/dev/mtd1    ──mount -t littlefs─> /data
~~~

挂载后，/sdcard 和 /spiffs 只是路径入口；实际文件名、目录结构和数据布局由各自文件系统管理。

---

## 5. FAT、SPIFFS、LittleFS 如何接入

### 5.1 FAT/FatFs：通常位于块设备之上

这里有一个容易混淆的名称：**FatFs** 通常指 Elm-Chan 的独立 FAT 文件系统库；而 NuttX 当前 `fs/fat`、`CONFIG_FS_FAT` 对应的是 NuttX 自己集成的 FAT/VFAT 实现。两者都可以提供 FAT 文件系统能力，但不是同一套源码或配置项。本篇说“FAT/VFAT”时，默认指 NuttX 内置实现；如果项目移植了外部 FatFs，需要按该移植层提供的块设备和挂载接口接入 VFS。

FAT 适合 SD 卡、eMMC、U 盘和 RAM disk 等块设备。块设备提供固定大小的扇区读写，FAT 负责：

- 分配簇；
- 管理 FAT 表；
- 管理目录项；
- 维护文件大小和起始簇；
- 把文件偏移转换为扇区访问。

典型链路：

~~~text
应用 open("/sdcard/log.txt")
        ↓
NuttX VFS
        ↓
VFAT/FAT
        ↓
/dev/mmcsd0 块设备
        ↓
SD/MMC 控制器
~~~

NSH 中的典型挂载命令：

~~~text
nsh> mkdir /sdcard
nsh> mount -t vfat /dev/mmcsd0 /sdcard
nsh> ls /sdcard
~~~

实际设备名可能是 /dev/mmcsd0、/dev/mmcsd0p1 或其他名称，由板级驱动和分区配置决定。

如果使用 RAM disk 练习，可以先创建或启用 /dev/ram0，格式化并挂载：

~~~text
nsh> mkfatfs /dev/ram0
nsh> mkdir /ramdisk
nsh> mount -t vfat /dev/ram0 /ramdisk
nsh> echo hello > /ramdisk/test.txt
nsh> cat /ramdisk/test.txt
~~~

命令是否存在取决于 mkfatfs、RAM disk 和 FAT 配置。

### 5.2 SPIFFS：面向 Flash 的日志结构文件系统

SPIFFS 适合 NOR Flash 这类需要擦除、不能像 RAM 一样任意覆盖的介质。它需要处理：

- 擦除块；
- 页面和对象；
- 空间回收；
- 磨损分散；
- Flash 上的文件和目录映射。

典型链路：

~~~text
应用 open("/spiffs/config.json")
        ↓
NuttX VFS
        ↓
SPIFFS
        ↓
/dev/mtd0
        ↓
NOR Flash 驱动
~~~

典型挂载形式：

~~~text
nsh> mkdir /spiffs
nsh> mount -t spiffs /dev/mtd0 /spiffs
nsh> ls /spiffs
~~~

这里的 /dev/mtd0 只是示例。真实项目可能使用分区后的 MTD 节点，或者由板级初始化代码直接传入 MTD 设备对象。

SPIFFS 的容量、文件名长度、缓存大小、页大小等参数需要与生成镜像的工具保持一致。使用 ESP-IDF 的 spiffsgen.py 或 mkspiffs 生成镜像时，不能只看挂载命令，还要核对 NuttX 的 SPIFFS 配置。

### 5.3 LittleFS：强调掉电安全和 Flash 友好性

LittleFS 同样面向 Flash，但重点是：

- 掉电时尽量保持文件系统可恢复；
- 通过复制和日志机制更新元数据；
- 适配小型 MCU 的 RAM 和 Flash；
- 进行磨损均衡。

典型链路：

~~~text
应用 open("/data/settings.bin")
        ↓
NuttX VFS
        ↓
LittleFS
        ↓
MTD 接口
        ↓
NOR/NAND/其他 Flash 设备
~~~

典型挂载形式：

~~~text
nsh> mkdir /data
nsh> mount -t littlefs /dev/mtd1 /data
~~~

LittleFS 的写入需要注意提交时机。为了保证数据已经提交到介质，重要写入后应调用：

~~~c
int fd = open("/data/settings.bin", O_WRONLY | O_CREAT, 0666);
write(fd, data, data_length);
fsync(fd);
close(fd);
~~~

是否需要显式 fsync、文件何时提交，以及配置项的具体语义，应以当前 NuttX 版本文档和配置为准。

### 5.4 对比表

| 文件系统 | 常见介质 | 上层设备接口 | 主要优势 | 主要注意点 |
| --- | --- | --- | --- | --- |
| FAT/VFAT | SD、eMMC、U 盘、RAM disk | 块设备 | 兼容 Windows/Linux，生态成熟 | 对突然掉电和 Flash 磨损不友好 |
| SPIFFS | NOR Flash | MTD | 适合小型 Flash，镜像工具较多 | 空间回收、配置匹配和性能要评估 |
| LittleFS | NOR/NAND Flash，也可配置到其他设备 | MTD | 掉电安全、磨损均衡 | 写入提交、块大小和缓存配置重要 |
| ROMFS | 固件内只读区域 | 块设备或镜像 | 简单、只读、占用少 | 不能在线修改 |
| ProcFS | 内存和内核状态 | 无真实存储介质 | 以文件方式暴露运行状态 | 不是持久化文件系统 |
| tmpfs | RAM | 内存 | 临时文件、速度快 | 重启或掉电丢失 |

统一接入不等于可以随便互换。例如，FAT 擅长跨平台交换文件，LittleFS 更适合设备配置和 Flash 持久化；把 SD 卡上的大量数据和 NOR Flash 上的小配置使用同一套选型标准，容易得到不合适的结果。

---

## 6. 从挂载到读写：一条完整调用链

以读取 /sdcard/log.txt 为例：

~~~text
1. 应用调用 open("/sdcard/log.txt", O_RDONLY)
2. VFS 解析路径并匹配 /sdcard 挂载点
3. VFS 调用 FAT 文件系统的 open 逻辑
4. FAT 查询目录项，找到文件起始簇和大小
5. VFS 创建 struct file，保存当前偏移量
6. 应用调用 read(fd, buffer, 128)
7. FAT 把文件偏移转换成逻辑扇区
8. FAT 请求 /dev/mmcsd0 读取扇区
9. SD/MMC 驱动访问控制器和卡
10. 数据逐层返回给应用
11. close(fd) 释放文件和文件系统内部资源
~~~

写入时方向相反：

~~~text
应用 write()
  ↓
VFS / FAT
  ↓
块设备 write sector
  ↓
SD/MMC 控制器
~~~

对 SPIFFS/LittleFS 来说，底层还要在合适的时机执行 Flash 擦除、写入和垃圾回收；因此一次 write() 的代价可能比普通 RAM 或 SD 块写入更复杂。

---

## 7. 统一 API 的具体用法

### 7.1 POSIX 文件描述符接口

~~~c
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>

static int save_config(const char *path, const void *data, size_t length)
{
  int fd;
  ssize_t written;

  fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
  if (fd < 0)
    {
      printf("open failed: %d\n", errno);
      return -1;
    }

  written = write(fd, data, length);
  if (written != (ssize_t)length)
    {
      close(fd);
      return -1;
    }

  if (fsync(fd) < 0)
    {
      close(fd);
      return -1;
    }

  close(fd);
  return 0;
}
~~~

同一个函数可以接收：

~~~c
save_config("/sdcard/config.ini", data, length);
save_config("/spiffs/config.ini", data, length);
save_config("/data/config.ini", data, length);
~~~

代码不需要调用 FAT、SPIFFS 或 LittleFS 专用的文件 API。

### 7.2 stdio 接口

~~~c
FILE *fp = fopen("/data/log.txt", "a");
if (fp != NULL)
  {
    fputs("boot ok\n", fp);
    fflush(fp);
    fclose(fp);
  }
~~~

stdio 通过 FILE 提供缓冲；底层最终仍然要经过 VFS。需要精确控制短读、偏移、同步和错误码时，优先使用 fd 接口。

### 7.3 目录接口

~~~c
#include <dirent.h>

DIR *dir = opendir("/sdcard");
if (dir != NULL)
  {
    struct dirent *entry;

    while ((entry = readdir(dir)) != NULL)
      {
        printf("%s\n", entry->d_name);
      }

    closedir(dir);
  }
~~~

目录操作同样由挂载点对应的文件系统实现。某些只读或简化文件系统对重命名、权限、时间戳等功能支持有限。

---

## 8. mount、umount 和自动挂载

### 8.1 手动挂载

手动挂载适合调试和固定介质：

~~~text
nsh> mkdir /sdcard
nsh> mount -t vfat /dev/mmcsd0 /sdcard
nsh> ls /sdcard
nsh> umount /sdcard
~~~

卸载前应确保：

- 没有任务继续使用该挂载点下的文件；
- 所有文件都已经 close；
- 重要写入已经 fsync；
- 没有工作线程正在执行目录扫描或写入。

如果仍有打开文件或正在使用的目录，umount 可能失败，或者强制卸载后造成后续访问错误。

### 8.2 自动挂载

可插拔 SD 卡、USB 存储等介质适合使用自动挂载：

~~~text
介质插入
   ↓
块设备出现
   ↓
识别文件系统
   ↓
挂载到 /var/mnt/sdcard0
   ↓
应用开始访问
   ↓
介质拔出
   ↓
停止访问并卸载
~~~

自动挂载并不替代应用的错误处理。应用仍要面对：

- 介质尚未插入；
- 挂载尚未完成；
- 文件系统损坏；
- 介质被拔出；
- 路径短暂不可用。

应用不要把可移动介质的路径当作永久存在。

---

## 9. Kconfig 需要关注什么

不同 NuttX 版本和板卡菜单名称可能略有差异，通常可以在 menuconfig 中搜索这些符号：

| 配置 | 作用 |
| --- | --- |
| DISABLE_MOUNTPOINT | 禁止挂载点；需要文件系统时不能启用 |
| FS_FAT | 启用 FAT/VFAT |
| FS_SPIFFS | 启用 SPIFFS |
| FS_LITTLEFS | 启用 LittleFS |
| FS_ROMFS | 启用 ROMFS |
| FS_PROCFS | 启用 ProcFS |
| FS_AUTOMOUNTER | 启用自动挂载机制 |
| FS_LARGEFILE | 支持更大的文件 |
| MTD 相关配置 | 启用对应的 MTD 子系统和 Flash 驱动；具体符号按 NuttX 版本、芯片和板卡确认 |
| 块设备相关配置 | 启用对应的块设备驱动和介质支持；具体符号按 NuttX 版本、芯片和板卡确认 |
| CONFIG_NFILE_DESCRIPTORS | 配置文件描述符数量 |
| CONFIG_NFILE_STREAMS | 配置 stdio 流数量 |

配置不是越多越好。嵌入式系统应按实际介质选择文件系统，避免同时启用多个用不到的文件系统来浪费 Flash 和 RAM。

---

## 10. 如何判断一条路径由谁处理

遇到文件访问异常时，不要先怀疑应用 API，先把路径拆开：

~~~text
请求路径：/data/log/boot.txt

1. /data 是否是挂载点
2. /data 对应什么文件系统
3. 该文件系统需要块设备还是 MTD
4. 底层设备节点是否存在
5. 文件系统是否已经 mount
6. 目录 /data/log 是否存在
7. 应用是否有足够的 fd、RAM 和栈
~~~

常用 NSH 检查：

~~~text
nsh> mount
nsh> ls /dev
nsh> ls /data
nsh> df
nsh> free
~~~

具体命令是否启用取决于板卡配置。也可以在代码里使用 stat、statfs/statvfs、access 和 errno 定位问题。

---

## 11. 常见错误和原因

### open 返回 ENOENT

常见原因：

- 挂载点没有创建；
- 文件系统没有 mount；
- 路径拼写错误；
- 父目录不存在；
- 底层设备节点名称不对。

先确认挂载点和目录，再检查文件路径。

### mount 返回 ENODEV

通常表示底层设备不存在或设备类型不匹配。例如：

- 把块设备拿去给只接受 MTD 的文件系统；
- MTD 节点没有注册；
- SD/MMC 驱动没有初始化；
- 设备节点路径写错。

### mount 返回 EINVAL

可能是：

- 文件系统类型字符串不正确；
- Flash 几何参数不匹配；
- 镜像格式与配置不一致；
- 挂载参数或设备节点不符合当前版本要求。

### write 成功但重启后数据消失

可能是：

- 实际挂载的是 tmpfs 或 RAM disk；
- 写入后没有 fsync；
- 设备掉电前缓存没有提交；
- 使用了只在模拟器中存在的存储设备；
- 文件系统或底层 Flash 驱动没有正确完成写入。

### 文件系统变成只读或无法继续写

重点检查：

- FAT 是否损坏；
- SPIFFS/LittleFS 是否空间不足；
- Flash 是否达到擦写寿命；
- 是否在卸载、拔卡或掉电时仍有写操作；
- 底层驱动是否正确报告擦除和写入错误。

### 同样的文件名在不同目录表现不同

这是正常现象：

~~~text
/sdcard/config.ini  → FAT 的目录和大小限制
/spiffs/config.ini  → SPIFFS 的对象和 Flash 参数
/data/config.ini    → LittleFS 的块、缓存和提交规则
~~~

VFS 统一了调用方式，但不会消除底层文件系统的差异。

---

## 12. 持久化数据的选型

| 需求 | 推荐方向 | 原因 |
| --- | --- | --- |
| 与电脑交换大量文件 | FAT/VFAT + SD/eMMC | 兼容性好，容量大 |
| 保存少量设备配置到 NOR Flash | LittleFS 或 SPIFFS | 适配 Flash，支持磨损管理 |
| 需要较强掉电恢复 | LittleFS | 设计上强调写入一致性 |
| 固定资源、固件内置网页 | ROMFS | 只读、简单、无需写入 |
| 临时缓存、运行日志 | tmpfs 或 RAM disk | 访问快，但断电丢失 |
| 暴露内核状态和调试信息 | ProcFS | 数据由内核实时生成 |

选型时至少评估：

1. 介质类型：块设备还是 MTD。
2. 容量和文件数量。
3. 写入频率和单次写入大小。
4. 是否需要跨平台读取。
5. 掉电时能否接受最近写入丢失。
6. 擦写寿命和磨损均衡。
7. RAM、Flash 和文件描述符预算。
8. 是否需要权限、时间戳、重命名和目录操作。

---

## 13. 和第 03 篇字符驱动的关系

可以把两篇笔记放在同一张图里理解：

~~~text
/dev/hello
  └── register_driver()
      └── file_operations
          ├── hello_open()
          ├── hello_read()
          ├── hello_write()
          └── hello_ioctl()

/data/config.txt
  └── mount("...", "/data", "littlefs", ...)
      └── mountpoint operations
          ├── 文件系统 open
          ├── 文件系统 read
          ├── 文件系统 write
          └── 底层 MTD read/write/erase
~~~

共同点：

- 都通过 VFS 暴露路径；
- 都能被 open/read/write/close 访问；
- 都使用文件描述符和 struct file；
- 都需要处理并发、错误和资源生命周期。

不同点：

- 字符驱动通常代表实时设备或控制接口；
- 文件系统负责持久化的文件、目录和空间管理；
- 字符驱动一般由 register_driver() 注册；
- 文件系统通常由 mount() 建立挂载点；
- 文件系统还需要底层块设备或 MTD 设备。

这也是为什么写一个传感器字符驱动和接入 LittleFS 是两类不同的工作：前者主要实现设备操作表，后者要同时处理挂载、文件系统配置和存储介质适配。

---

## 14. 复习路线

建议按下面顺序复习：

~~~text
1. 先在 sim:nsh 中确认 /dev/console 和基本文件 API
2. 阅读第 03 篇，理解 register_driver() 和字符设备
3. 用 RAM disk + FAT 练习 mount、ls、写文件、卸载
4. 再阅读 SPIFFS/LittleFS 的 Flash 和 MTD 约束
5. 在真实板卡上注册 SD/MMC 或 MTD 设备
6. 让应用只使用 /data、/sdcard 等路径，不直接调用文件系统私有 API
7. 最后再分析掉电、拔卡、空间不足和并发写入
~~~

最小实验的目标不是一次把所有文件系统都启用，而是看清楚下面这条链：

~~~text
路径
  → VFS 挂载点
  → 文件系统实现
  → 块设备或 MTD
  → 具体存储介质
~~~

---

## 参考资料

- [NuttX File System Documentation](https://nuttx.apache.org/docs/latest/components/filesystem/index.html)
- [NuttX FAT/VFAT](https://nuttx.apache.org/docs/latest/components/filesystem/fat.html)
- [NuttX SPIFFS](https://nuttx.apache.org/docs/latest/components/filesystem/spiffs.html)
- [NuttX LittleFS](https://nuttx.apache.org/docs/latest/components/filesystem/littlefs.html)
- [NuttX File Descriptors](https://nuttx.apache.org/docs/latest/components/filesystem/file_descriptors.html)
- [NuttX File System Interfaces](https://nuttx.apache.org/docs/latest/reference/user/10_filesystem.html)
- [NuttX 源码中的 fs/vfs](https://github.com/apache/nuttx/tree/master/fs)
- [NuttX 源码中的 FAT](https://github.com/apache/nuttx/tree/master/fs/fat)
- [NuttX 源码中的 SPIFFS](https://github.com/apache/nuttx/tree/master/fs/spiffs)
- [NuttX 源码中的 LittleFS](https://github.com/apache/nuttx/tree/master/fs/littlefs)

## 相关笔记

- [[01-NuttX-环境配置和编译烧录流程]]
- [[02-NuttX-基础API]]
- [[03-NuttX-字符设备驱动编写]]
- [[嵌入式文件存储体系/VFS文件管理系统API]]
- [[嵌入式文件存储体系/SD卡体系]]

