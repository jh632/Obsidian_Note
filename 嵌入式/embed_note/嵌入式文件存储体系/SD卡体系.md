# SD卡体系 - 文件系统选型

SD卡上常见的文件系统主要是 **FAT 家族**和 **exFAT**，其余（NTFS/ext4/F2FS）属于手动格式化才能碰到的选项。

## FAT12 / FAT16 / FAT32

同一套设计的三种"位宽"版本，数字代表 **FAT 表里每个簇地址占多少位**：

| 类型 | 簇地址位宽 | 最大簇数 | 卷容量上限 | 备注 |
|---|---|---|---|---|
| FAT12 | 12 位 | 约 4084 簇 | 几 MB～32MB 级别 | 软盘时代产物，SD 卡上基本绝迹 |
| FAT16 | 16 位 | 约 65524 簇 | 约 2GB（非标准扩展可到 4GB） | 老式 ≤2GB 的 SD 卡；单簇最大通常 32KB |
| FAT32 | 名义 32 位，实际 28 位（高 4 位保留） | — | 理论更大，Windows 自带格式化工具人为限制 32GB | 第三方工具能格式化更大卷，只是资源管理器不让用 |

### 常见误解：单文件 4GB 上限是全家共享的

**FAT12/16/32 的单文件大小上限都一样：4GB − 1 字节（2³² − 1）**

- 目录项里记录文件大小的字段是 **32 位宽**，这是 FAT 家族共享的限制，不是"FAT32 专属"
- 很多人以为"FAT16 是 2GB、FAT32 是 4GB"——那个 2GB 说的是早期 DOS 对**卷容量**的限制，跟**单文件大小**是两回事

## exFAT

微软 2006 年专门给闪存/大容量存储设计的，解决 FAT 家族的两个老毛病：

- **去掉 4GB 单文件限制**，理论上到 EB 级别
- **用位图记录空闲簇状态**，不用像 FAT32 那样为分配空间扫描整个 FAT 表，大容量卡下写入分配效率更高
- 目录结构更灵活，没有 FAT16 那种固定根目录条目数限制

专利情况：以前有授权顾虑，不少开源/嵌入式项目刻意回避；微软 2019 年公开了规范细节并对合规实现的必要专利免费授权（Linux 支持时间线见下）。

### Linux 内核支持时间线

- 2019.08 微软公开 exFAT 规范
- **Linux 5.4（2019.11）**：先在 staging 里合入了一个基于三星旧代码快照的预览驱动
- **Linux 5.7（2020.04）**：三星持续维护的新驱动正式落在 `fs/exfat`（不走 staging），staging 旧版随后删除
- 更早只能靠 exfat-fuse，或 out-of-tree 的 exfat-nofuse 补丁

## SD协会官方对照

容量分级和文件系统是规范强绑定的：

| 卡类型 | 容量范围（官方定义） | 规定的文件系统 |
|---|---|---|
| SD (SDSC) | ≤2GB | FAT12/FAT16 |
| SDHC | >2GB–32GB | FAT32 |
| SDXC | >32GB–2TB | exFAT |
| SDUC | >2TB–128TB | exFAT |

- 边界是"大于上一档"的关系（SD 协会原文：more than 2GB up to 32GB……），市售最小 SDHC 卡才是 4GB
- **SDXC 的 2TB 上限不是 exFAT 本身的限制**，是 MBR 分区表的寻址极限：32 位 LBA × 512B 扇区 = 2³² × 512B = 2TB；更大容量的 SDUC 要换成 GPT/SFD 布局
- exFAT 分区在 MBR 里的类型码与 NTFS 相同（0x07），不能靠分区表区分两者

## 内部结构对比

### FAT家族的磁盘布局

```
MBR(可选) → DBR/BPB → [FAT32保留区: FSInfo扇区 + 备份DBR] → FAT#1 → FAT#2 → 数据区
（FAT12/16 的根目录紧跟FAT、大小固定；FAT32 的根目录是数据区里的普通簇链）
```

**FAT表**：每个簇一个表项，值为"文件的下一个簇号"，顺着链读就是文件内容：

| 表项值（FAT12/16/32） | 含义 |
|---|---|
| 0x000 | 空闲簇 |
| 0xFF7 / 0xFFF7 / 0x0FFFFFF7 | 坏簇标记 |
| ≥0xFF8 / ≥0xFFF8 / ≥0x0FFFFFF8 | 链尾 EOC（文件结束） |
| 其他 | 文件下一簇的簇号 |

- FAT[0] 存介质描述符；**FAT[1] 被 Windows 用作卷脏标志**（正常卸载位/上次 I/O 出错位），挂载时发现脏位就要扫盘修复——这是"直接拔卡后插电脑要 chkdsk"的来源
- **FAT32 为什么只用 28 位**：坏簇标记占掉了 `0x0FFFFFF7`，EOC 又占掉 `0x0FFFFFF8~0x0FFFFFFF`，所以可分配簇号必须小于 `0x0FFFFFF7` → 全卷最多约 2.68 亿簇（268,435,445）；高 4 位读写时必须原样保留
- FAT32 卷理论上限 ≈ 2.68 亿簇 × 32KB ≈ **8TB**，远超 Windows 格式化工具 32GB 的人为限制（对大 FAT32 卷 Windows 只是不给格式化，读写不受限）
- FAT32 另有 FSInfo 扇区缓存空闲簇数，避免每次分配都扫全表

**目录项**：32 字节定长，关键字段：

| 偏移 | 大小 | 字段 |
|---|---|---|
| 0 | 11 | 短文件名（8.3 格式） |
| 11 | 1 | 属性 |
| 20 | 2 | 首簇号高 16 位（仅 FAT32 用到） |
| 26 | 2 | 首簇号低 16 位 |
| 28 | 4 | **文件大小（32 位）← "4GB−1"限制的直接出处** |

**长文件名（LFN/VFAT 扩展）**：8.3 短名放不下时，在短名项前面倒序排若干 LFN 目录项（属性字节 = 0x0F），每项塞 13 个 UTF-16 字符，用校验和与对应短名绑定；长名最长 255 字符（约需 20 条目录项）。不支持 LFN 的老系统只会看到 `XXXXXX~1.EXE` 这样的短名。

**FAT12/16/32 的分界由簇数决定**：簇数 <4085 为 FAT12，<65525 为 FAT16，否则为 FAT32（微软 fatgen103 规范原文）——这就是"FAT16 最多 65524 簇、卷上限 2GB"这些数字的出处。

### exFAT的磁盘布局

```
引导区(主+备份各12扇区, 带校验和) → FAT → 簇堆(Cluster Heap)
                                        ├─ 分配位图(通常在2号簇)
                                        ├─ Up-case表(大小写转换)
                                        └─ 根目录及所有数据
```

- **空闲空间管理换了机制**：FAT 不再承担"哪些簇空闲"的职责，改用**分配位图**——每簇 1 个 bit，bit0 对应 2 号簇。找空簇扫位图即可，不用遍历整个 FAT 表，这就是大卡上分配快的结构性原因
- 根目录不再是固定区域，首簇号直接写在引导扇区字段里；也没有 `.` `..` 这两个特殊目录项
- **一个文件 = 一组条目集**（每条仍 32 字节）：`0x85` File 条目（属性/时间戳）+ `0xC0` Stream Extension（首簇号/长度/标志）+ N 条 `0xC1` File Name（每条 15 个 UTF-16 字符，名字最长 255）
- Stream 条目里有 **NoFatChain 标志**：文件连续分配时置位，完全不用写 FAT 链；只有碎片化了才建链 → 顺序写大文件的元数据开销更低
- **文件大小字段是 64 位 ← 去掉 4GB−1 限制的直接出处**；簇最大可到 32MB；最大簇数 2³²−11（规范建议不超过 2²⁴−2 以免 FAT 过大）
- TexFAT 是加事务安全语义的扩展（双 FAT 双位图），Windows CE 在用，其他场景基本见不到

一句话总结差异：**FAT 家族里 FAT 表身兼两职（记簇链 + 记空闲）；exFAT 把空闲管理拆给了位图、把 FAT 链降级成只为碎片文件服务，再把大小字段扩成 64 位。**

## 其他可选（非SD标准，手动格式化能选到）

- **NTFS**：Windows 原生，带日志（journaling）、权限、压缩。
	- 日志机制意味着更多写入次数，对闪存写放大/寿命不友好
	- 很多嵌入式设备、相机、车机读不了 NTFS，兼容性最差
	- 一般不建议拿来格式化 SD 卡
- **ext4**：Linux 原生，带日志。嵌入式 Linux 产品有时用来做数据分区，但 Windows/macOS 默认不认，不适合当通用可移动介质
- **F2FS**：三星做的，专门针对 NAND 闪存物理特性优化（减少写放大、更好的垃圾回收）。Android 和部分嵌入式 Linux 场景常见，裸机/MCU 环境比较少见

## 容易混淆：LittleFS/SPIFFS 不是给SD卡用的

两者是不同层面的东西：

- **LittleFS、SPIFFS**：给 MCU 片上 SPI Flash 芯片用的**原始闪存文件系统**，直接操作 page/sector 级别擦写，没有 FTL 这层
- **SD 卡内部自带控制器**，做磨损均衡和坏块管理，对外就是个**普通块设备**
- 所以 SD 卡上用的是 FAT/exFAT/ext4 这类**块设备文件系统**，跟 LittleFS/SPIFFS 不是一个层面

参见 [[VFS文件管理系统]]（VFS 下三种后端的分层图：SPIFFS/LittleFS 面向 Flash，FAT/exFAT 面向块设备）。

## 实践：MSC OTA 场景选型

固件镜像一般几 MB 到几十 MB，FAT32 的 4GB 单文件限制基本碰不到：

- 除非打算用 32GB 以上的 SDXC 卡，**FAT32 就够**
- 也省得在 FatFs 里开 exFAT 编译选项，增加代码体积

具体到 FatFs（ELM Chan）开 exFAT 的代价：

```c
#define FF_FS_EXFAT     1   // 总开关
#define FF_USE_LFN      2   // exFAT 强制要求 >= 1
#define FF_MAX_LFN      255 // 推荐值
#define FF_LFN_UNICODE  1   // 推荐值 >= 1
```

- 前置条件：必须开 LFN，推荐 `FF_LFN_UNICODE >= 1` + `FF_MAX_LFN == 255`；exFAT 需要 C99（内部用 64 位整型），放弃 C89 兼容
- RAM 代价可算出来：LFN 工作缓冲 `(FF_MAX_LFN+1)×2 = 512B`；开 exFAT 后再加 `(FF_MAX_LFN+44)/15×32 ≈ 608B`，合计约 **1.1KB**
- Zephyr 和 ESP-IDF 打包的 ffconf.h 默认都是 `FF_FS_EXFAT 0`（Zephyr 连 LFN 都默认关着）
- 商用注意：ChaN 在应用笔记里注明 FatFs 的 exFAT 是基于微软专利申请文档的独立实现，商业产品是否需要微软授权需自行确认——微软的免费授权面向"按公开规范的合规实现"，和 FatFs 这种独立实现不是一回事

## 参考资料

- Microsoft FAT Specification (fatgen103)：https://academy.cba.mit.edu/classes/networking_communications/SD/FAT.pdf
- Microsoft exFAT File System Specification：https://learn.microsoft.com/en-us/windows/win32/fileio/exfat-specification
- ChaN exFAT 笔记：https://elm-chan.org/docs/exfat_e.html
- FatFs 配置选项：https://elm-chan.org/fsw/ff/doc/config.html
- SD Association – Capacity 分级页：https://www.sdcard.org/developers/sd-standard-overview/capacity-sd-sdhc-sdxc-sduc/
- Phoronix: New exFAT driver lands with Linux 5.7：https://www.phoronix.com/news/New-exFAT-For-Linux-5.7
