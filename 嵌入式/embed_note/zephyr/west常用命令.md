---
date: 2026-08-14
tags:
  - "#命令"
aliases: []
---

# west常用命令

```bash
#获取板子列表
west boards
#烧录esp板子
west flash --esp-device /dev/ttyACM0
#编译esp项目(运行在主cpu)
west build -b esp32s3_devkitc/esp32s3/procpu -p
```