---
tags: [embed_note, NuttX, driver, GPIO, LED]
date: 2026-10-11
aliases: [NuttX字符设备驱动, NuttX LED驱动, register_driver, GPIO LED]
---

# NuttX 字符设备驱动编写：用 `/dev/led0` 控制板载 LED

前置笔记：[[01-NuttX-环境配置和编译烧录流程]]、[[02-NuttX-基础API]]。

这篇笔记把最小字符设备驱动做成一个真正能控制硬件的 LED 驱动。驱动注册后生成 `/dev/led0`，应用通过标准文件接口控制 LED：

~~~text
应用程序
   │ open/read/write/ioctl
   ▼
NuttX VFS
   │ 根据路径找到 inode 和 file_operations
   ▼
/dev/led0 字符设备驱动
   │ 互斥保护设备状态
   ▼
board_userled() / 板级 GPIO 实现
   ▼
板载 LED 和 GPIO 引脚
~~~

这个例子使用 NuttX 通用的 `board_userled()` 板级接口。LED 的具体 GPIO、有效电平和时钟初始化由目标板的 board 支持代码处理，因此同一份驱动逻辑可以用于多个提供 User LED 接口的开发板。若某块板没有这个接口，只需要替换硬件适配函数，不需要重写 VFS 部分。

> [!important] 运行条件
> 这不再是 `sim:nsh` 中的纯内存演示。要看到 LED 亮灭，必须使用带板载 User LED、并实现 `board_userled_initialize()` / `board_userled()` 的 NuttX 板卡配置。没有真实 LED 的模拟器只能用于检查代码结构，不能产生物理灯光。
>
> `board_userled_initialize()` 和 `board_userled()` 只会在目标配置提供 `CONFIG_ARCH_HAVE_LEDS` 时声明。这个符号不是所有 NuttX 板卡都会提供，因此编译前要先检查目标板的 `include/nuttx/board.h` 和生成的 `.config`。没有该接口时，应按第 7 节改用目标板自己的 GPIO 适配层。

---

## 1. 先记住四个核心对象

### 1.1 设备节点

~~~text
/dev/led0
~~~

这是应用看到的路径。`open("/dev/led0", ...)` 时，NuttX VFS 根据路径找到 LED 驱动的 inode。

### 1.2 `struct file_operations`

它是一组回调函数，描述驱动支持哪些文件操作：

| 成员 | 作用 |
| --- | --- |
| `open` | 保存当前设备实例，初始化本次打开的文件状态 |
| `close` | 释放本次打开的状态 |
| `read` | 读取当前 LED 状态，示例返回 `0\n` 或 `1\n` |
| `write` | 写入字符 `0` 或 `1`，关闭或点亮 LED |
| `ioctl` | 执行设置、读取、翻转等控制命令 |
| `seek` | LED 不是普通可定位文件，通常填 `NULL` |
| `poll` | 只有需要等待状态变化时才实现 |

当前 NuttX 的操作表顺序是 `open、close、read、write、seek、ioctl、mmap、truncate、poll...`，初始化时必须按当前版本的 `struct file_operations` 定义填写。

### 1.3 设备级私有数据与打开级私有数据

`register_driver()` 的最后一个参数会保存到 inode 的 `i_private`。驱动在 `open()` 中取出它，再放进 `filep->f_priv`：

~~~c
static int led_open(FAR struct file *filep)
{
  FAR struct inode *inode = filep->f_inode;
  FAR struct led_dev_s *priv = inode->i_private;

  filep->f_priv = priv;
  filep->f_pos = 0;
  return 0;
}
~~~

`i_private` 通常保存一个物理 LED 实例的状态，多个 fd 会共享它；`f_priv` 属于当前打开的文件。若每次 `open()` 都需要独立上下文，应在 `open()` 中单独分配，在 `close()` 中释放。

### 1.4 文件描述符

~~~text
fd  ──> struct file ──> inode ──> file_operations
                         └──────> i_private
~~~

应用只持有整数 `fd`，驱动通过 `filep` 找到当前 LED 实例和文件偏移。

---

## 2. LED 驱动的生命周期

~~~text
初始化板级 LED
      ↓
初始化 led_dev_s 和互斥锁
      ↓
register_driver("/dev/led0", &g_led_fops, 0666, &g_led)
      ↓
应用 open/write/read/ioctl/close
      ↓
unregister_driver("/dev/led0")
~~~

固定板载 LED 通常在板级初始化阶段注册，并一直保留 `/dev/led0`。为了便于教学，下面的 `main()` 在命令中注册、使用、注销一次；正式项目应把注册函数放到板级初始化或专门的驱动初始化入口，不能让即将退出的应用栈变量作为 `i_private`。

---

## 3. 完整 LED 字符驱动

### 3.1 文件结构

~~~text
apps/examples/led_driver/
├── Kconfig
├── Make.defs
├── Makefile
└── led_driver_main.c
~~~

教学阶段可以把驱动和测试命令放在一个源文件里。正式项目可以把驱动实现、公共 ioctl 头文件和测试应用拆开。

### 3.2 驱动完整源码

保存为 `led_driver_main.c`：

~~~c
#include <nuttx/config.h>
#include <nuttx/board.h>
#include <nuttx/fs/fs.h>
#include <nuttx/mutex.h>

#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#ifndef CONFIG_ARCH_HAVE_LEDS
#  error "This example requires CONFIG_ARCH_HAVE_LEDS and board_userled()"
#endif

#define LED_DEV_PATH "/dev/led0"

/* 目标板的第一个 User LED。多 LED 板卡可以为不同实例使用不同索引。 */
#define LED_INDEX 0

/* SET 使用 arg 直接传 0/1；GET 使用 arg 指向 int。 */
#define LEDIOC_SET    _IO('L', 0)
#define LEDIOC_GET    _IOR('L', 1, int)
#define LEDIOC_TOGGLE _IO('L', 2)

struct led_dev_s
{
  mutex_t lock;
  int     index;
  bool    state;
};

static struct led_dev_s g_led;

static void led_hw_set(FAR struct led_dev_s *priv, bool on)
{
  /* 板级实现负责 GPIO 配置、有效电平和实际输出。 */
  board_userled(priv->index, on);
  priv->state = on;
}

static int led_open(FAR struct file *filep)
{
  FAR struct inode *inode = filep->f_inode;
  FAR struct led_dev_s *priv = inode->i_private;

  filep->f_priv = priv;
  filep->f_pos = 0;
  return 0;
}

static int led_close(FAR struct file *filep)
{
  filep->f_priv = NULL;
  return 0;
}

static ssize_t led_read(FAR struct file *filep, FAR char *buffer,
                        size_t buflen)
{
  FAR struct led_dev_s *priv = filep->f_priv;
  char output[2];
  size_t count;
  int ret;

  if (buffer == NULL && buflen > 0)
    {
      return -EINVAL;
    }

  if (buflen == 0)
    {
      return 0;
    }

  /* 把 LED 状态当作一个两字节的只读快照："0\n" 或 "1\n"。 */
  if (filep->f_pos > 0)
    {
      return 0;
    }

  ret = nxmutex_lock(&priv->lock);
  if (ret < 0)
    {
      return ret;
    }

  output[0] = priv->state ? '1' : '0';
  output[1] = '\n';
  count = buflen < sizeof(output) ? buflen : sizeof(output);
  memcpy(buffer, output, count);
  filep->f_pos += count;

  nxmutex_unlock(&priv->lock);
  return (ssize_t)count;
}

static ssize_t led_write(FAR struct file *filep, FAR const char *buffer,
                         size_t buflen)
{
  FAR struct led_dev_s *priv = filep->f_priv;
  bool on;
  size_t i;
  int ret;

  if (buffer == NULL && buflen > 0)
    {
      return -EINVAL;
    }

  if (buflen == 0)
    {
      return 0;
    }

  if (buffer[0] == '1')
    {
      on = true;
    }
  else if (buffer[0] == '0')
    {
      on = false;
    }
  else
    {
      return -EINVAL;
    }

  /* 允许 echo 产生的换行和常见空白，但不接受多余命令。 */
  for (i = 1; i < buflen; i++)
    {
      if (buffer[i] != ' ' && buffer[i] != '\t' &&
          buffer[i] != '\r' && buffer[i] != '\n')
        {
          return -EINVAL;
        }
    }

  ret = nxmutex_lock(&priv->lock);
  if (ret < 0)
    {
      return ret;
    }

  led_hw_set(priv, on);
  filep->f_pos = 0;

  nxmutex_unlock(&priv->lock);
  return (ssize_t)buflen;
}

static int led_ioctl(FAR struct file *filep, int cmd, unsigned long arg)
{
  FAR struct led_dev_s *priv = filep->f_priv;
  FAR int *statep;
  bool on;
  int ret;

  switch (cmd)
    {
      case LEDIOC_SET:
        if (arg > 1)
          {
            return -EINVAL;
          }

        ret = nxmutex_lock(&priv->lock);
        if (ret < 0)
          {
            return ret;
          }

        led_hw_set(priv, arg != 0);
        filep->f_pos = 0;
        nxmutex_unlock(&priv->lock);
        return 0;

      case LEDIOC_GET:
        if (arg == 0)
          {
            return -EINVAL;
          }

        statep = (FAR int *)(uintptr_t)arg;
        ret = nxmutex_lock(&priv->lock);
        if (ret < 0)
          {
            return ret;
          }

        *statep = priv->state ? 1 : 0;
        nxmutex_unlock(&priv->lock);
        return 0;

      case LEDIOC_TOGGLE:
        ret = nxmutex_lock(&priv->lock);
        if (ret < 0)
          {
            return ret;
          }

        on = !priv->state;
        led_hw_set(priv, on);
        filep->f_pos = 0;
        nxmutex_unlock(&priv->lock);
        return 0;

      default:
        return -ENOTTY;
    }
}

/* 顺序必须与当前 NuttX 的 struct file_operations 定义一致。 */
static const struct file_operations g_led_fops =
{
  led_open,       /* open      */
  led_close,      /* close     */
  led_read,       /* read      */
  led_write,      /* write     */
  NULL,           /* seek      */
  led_ioctl,      /* ioctl     */
  NULL,           /* mmap      */
  NULL,           /* truncate  */
  NULL            /* poll      */
};

static int led_register(void)
{
  uint32_t available;
  int ret;

  available = board_userled_initialize();
  if ((available & (1u << LED_INDEX)) == 0)
    {
      return -ENODEV;
    }

  memset(&g_led, 0, sizeof(g_led));
  g_led.index = LED_INDEX;

  ret = nxmutex_init(&g_led.lock);
  if (ret < 0)
    {
      return ret;
    }

  ret = nxmutex_lock(&g_led.lock);
  if (ret == 0)
    {
      led_hw_set(&g_led, false);
      nxmutex_unlock(&g_led.lock);
    }

  if (ret < 0)
    {
      nxmutex_destroy(&g_led.lock);
      return ret;
    }

  ret = register_driver(LED_DEV_PATH, &g_led_fops, 0666, &g_led);
  if (ret < 0)
    {
      nxmutex_destroy(&g_led.lock);
    }

  return ret;
}

int main(int argc, FAR char *argv[])
{
  char buffer[4];
  int state;
  int fd;
  int ret;
  ssize_t nread;

  ret = led_register();
  if (ret < 0)
    {
      printf("LED register failed: %d\n", ret);
      return 1;
    }

  fd = open(LED_DEV_PATH, O_RDWR);
  if (fd < 0)
    {
      printf("open failed: %d\n", errno);
      unregister_driver(LED_DEV_PATH);
      nxmutex_destroy(&g_led.lock);
      return 1;
    }

  /* 写入 1 点亮，再读取状态。 */
  ret = (int)write(fd, "1\n", 2);
  printf("write returned: %d\n", ret);

  nread = read(fd, buffer, sizeof(buffer) - 1);
  if (nread > 0)
    {
      buffer[nread] = '\0';
      printf("LED state: %s", buffer);
    }

  ret = ioctl(fd, LEDIOC_GET, (unsigned long)(uintptr_t)&state);
  if (ret == 0)
    {
      printf("ioctl get: %d\n", state);
    }

  ioctl(fd, LEDIOC_TOGGLE, 0);
  printf("LED toggled\n");

  close(fd);
  ret = unregister_driver(LED_DEV_PATH);
  if (ret < 0)
    {
      printf("unregister_driver failed: %d\n", ret);
    }

  nxmutex_destroy(&g_led.lock);
  return ret < 0 ? 1 : 0;
}
~~~

### 3.3 逐段理解实现

#### `board_userled()` 是硬件适配层

驱动不直接写某个芯片的 GPIO 寄存器，而是调用：

~~~c
board_userled(priv->index, on);
~~~

板级代码负责把 `index` 映射到实际 GPIO，并处理高电平点亮、低电平点亮、端口复用和时钟。这样 LED 驱动的 VFS 部分不会被某个 MCU 型号绑死。

如果目标板没有实现 User LED 接口，可以把 `led_hw_set()` 改成该芯片的 GPIO API，例如在初始化时配置输出模式，在设置状态时调用 GPIO 写函数。`led_open/read/write/ioctl` 和 `register_driver()` 的结构不需要改变。

#### `read()` 为什么返回 `0\n` 或 `1\n`

LED 状态不是连续字节流，返回一个短文本快照便于用 NSH 查看：

~~~text
nsh> cat /dev/led0
1
~~~

通过 `f_pos` 让一次打开只读出一份快照，读完后返回 0。写入新状态会把当前 fd 的 `f_pos` 清零。

#### `write()` 为什么接受 `echo 1 > /dev/led0`

`echo` 通常会附加换行，所以驱动接受首字符 `0` 或 `1`，并允许后面跟空格、制表符或换行。其他字符返回 `-EINVAL`，避免把不明确的字符串误当成控制命令。

#### `ioctl()` 适合做什么

本例提供三个控制命令：

| 命令 | 作用 |
| --- | --- |
| `LEDIOC_SET` | `arg` 为 0 关闭，为 1 点亮 |
| `LEDIOC_GET` | `arg` 指向 `int`，返回当前状态 |
| `LEDIOC_TOGGLE` | 翻转当前状态 |

`LEDIOC_GET` 的指针参数在 FLAT 构建中可以直接示例化；在 PROTECTED/KERNEL 构建中，驱动必须遵循当前 NuttX 的用户空间拷贝和地址检查规则，不能默认直接解引用用户指针。

#### 为什么要加锁

`write()`、`read()` 和 `ioctl()` 都会访问 `state`，并且硬件写入和状态更新必须保持一致。多个任务同时操作时使用 `mutex_t` 保护临界区。中断上下文不能调用会睡眠的 mutex；LED 这种简单输出通常不需要在中断里直接操作。

---

## 4. 驱动支持多实例吗

支持。上面的示例只注册了一个 `/dev/led0`，只是因为很多开发板只有一个 User LED。NuttX 不限制一个驱动只能对应一个设备。

多实例的关键是：复用同一份 `file_operations`，为每个 LED 保存不同的设备结构体，并注册到不同路径：

~~~c
static struct led_dev_s g_led0;
static struct led_dev_s g_led1;

led_register_instance("/dev/led0", &g_led0, 0);
led_register_instance("/dev/led1", &g_led1, 1);
~~~

`register_driver()` 的最后一个参数分别保存到两个 inode 的 `i_private`，所以相同的 `led_read()` 可以通过 `filep->f_priv` 找到当前实例。每个实例应有自己的状态和锁；如果多个 LED 共享 I2C、SPI 或 GPIO 扩展器，还要遵守共享总线的互斥规则。

多设备实例和同一设备多次 `open()` 是两个概念：

| 场景 | 典型状态 |
| --- | --- |
| 两个物理 LED | 每个 inode 的 `i_private` 指向一份 `led_dev_s` |
| 多个任务打开 `/dev/led0` | 设备状态在 `led_dev_s` 中共享，文件偏移在各自 `struct file` 中独立 |
| 每次打开都要有独立模式 | 在 `open()` 中分配打开级结构，`close()` 中释放 |

---

## 5. 加入 NuttX Apps

### 5.1 Kconfig

`apps/examples/led_driver/Kconfig`：

~~~kconfig
config EXAMPLES_LED_DRIVER
    bool "NuttX GPIO LED character driver"
    default n
    help
      Build the /dev/led0 GPIO LED character driver example.
      The selected board must provide CONFIG_ARCH_HAVE_LEDS,
      board_userled_initialize(), and board_userled().
~~~

这个示例依赖具体板级 User LED 实现；不同 NuttX 版本的 Kconfig 依赖写法可能不同，应以当前 `apps/examples` 中相邻示例为准。即使 Kconfig 菜单中能看到该选项，也必须确认目标配置提供 `CONFIG_ARCH_HAVE_LEDS` 和对应的 `board_userled` API。

### 5.2 Make.defs

~~~makefile
ifeq ($(CONFIG_EXAMPLES_LED_DRIVER),y)
CONFIGURED_APPS += $(APPDIR)/examples/led_driver
endif
~~~

### 5.3 Makefile

~~~makefile
include $(APPDIR)/Make.defs

PROGNAME  = led_driver
PRIORITY  = 100
STACKSIZE = 3072
MODULE    = $(CONFIG_EXAMPLES_LED_DRIVER)
MAINSRC   = led_driver_main.c

include $(APPDIR)/Application.mk
~~~

---

## 6. 配置、编译和运行

先选择目标板的 NuttX 配置，再启用板载 LED 支持和这个示例：

~~~bash
cd nuttx
./tools/configure.sh -l <board>:<config>
make menuconfig
~~~

在 menuconfig 中找到：

~~~text
Application Configuration
  → Examples
    → NuttX GPIO LED character driver
~~~

同时确认目标板提供 User LED 支持。菜单名称和配置符号会随架构、板卡及 NuttX 版本变化，不能直接把某块板的 GPIO 配置复制到另一块板。

编译并启动：

~~~bash
make -j
~~~

进入 NSH 后执行：

~~~text
nsh> led_driver
write returned: 2
LED state: 1
ioctl get: 1
LED toggled
nsh> cat /dev/led0
0
nsh> echo 1 > /dev/led0
nsh> cat /dev/led0
1
~~~

教学程序退出时会注销 `/dev/led0`，因此退出后节点消失是预期行为。若希望节点长期存在，应在板级初始化中调用注册函数，并由系统生命周期负责注销；不要在长期运行的驱动中使用应用栈上的私有数据。

---

## 7. 如果不使用 `board_userled()`

真实项目中更常见的是把某个 GPIO 定义在板级 `board.h`，再由驱动调用芯片 GPIO API。适配层可以保持下面这种形状：

~~~c
static void led_hw_set(FAR struct led_dev_s *priv, bool on)
{
  bool level = on; /* 如果硬件低电平点亮，这里改为 !on。 */

  gpio_write(priv->gpio, level);
  priv->state = on;
}
~~~

实际的 `gpio_config()`、`gpio_write()` 函数和 GPIO 编码是架构相关的，必须参考目标芯片和同一板卡已有驱动。不要把某个 STM32、ESP32 或 RP2040 的 GPIO 宏直接当成所有 NuttX 板卡的通用 API。

无论底层是 `board_userled()` 还是直接 GPIO，分层关系都相同：

~~~text
write("1") / ioctl(SET)
        ↓
led_write() / led_ioctl()
        ↓
led_hw_set()
        ↓
GPIO 控制器
        ↓
LED 引脚
~~~

---

## 8. 常见错误定位

### `register_driver()` 返回 `-EEXIST`

同一路径已经注册。检查是否重复执行初始化，或板级代码已经注册了同名节点。

### `led_register()` 返回 `-ENODEV`

通常表示 `LED_INDEX` 超出板级 User LED 位图，或者目标板没有启用 User LED 支持。先查看目标板 `board.h` 中的 LED 索引和 NuttX 配置。

### `open("/dev/led0")` 返回 `ENOENT`

检查注册函数是否执行成功、`/dev` 是否可用、路径是否拼写正确，以及应用是否真的编译进固件。

### 写入成功但灯不亮

依次检查：

- LED 是否是低电平点亮；
- `LED_INDEX` 是否对应正确的物理灯；
- 板级 GPIO 是否已经配置成输出；
- 该 GPIO 是否被其他外设复用；
- 调用的是不是目标板实际使用的 LED 接口。

### `ioctl()` 返回 `-ENOTTY`

应用和驱动使用的 ioctl 宏不一致，或命令没有在 `switch` 中处理。应把命令定义放在驱动和应用共享的公共头文件中。

### 多任务同时控制时状态异常

检查设备状态、GPIO 写入和共享总线访问是否有明确的锁。不要用 `volatile` 代替互斥和内存同步。

---

## 9. 驱动编写检查清单

~~~text
[ ] 设备节点路径唯一，注册和注销成对
[ ] i_private 指向的设备对象生命周期足够长
[ ] file_operations 顺序与当前 NuttX 头文件一致
[ ] open/read/write/ioctl 返回值符合约定
[ ] GPIO 初始化、有效电平和资源释放明确
[ ] 多任务访问设备状态时有锁
[ ] ioctl 参数经过检查，用户指针符合构建模式要求
[ ] 多实例使用独立的设备结构体和路径
[ ] 错误路径会释放 mutex、GPIO、IRQ 和总线资源
[ ] 在目标板上验证亮、灭、查询、翻转和异常输入
~~~

最值得记住的一句话是：**NuttX 字符驱动首先是一个实现了 VFS 文件操作协议的对象，然后才是对 GPIO、I2C、SPI 或寄存器的封装。**

---

## 参考资料

- [NuttX Driver Documentation](https://nuttx.apache.org/docs/latest/components/drivers/index.html)
- [NuttX Board API](https://github.com/apache/nuttx/blob/master/include/nuttx/board.h)
- [register_driver() 声明](https://github.com/apache/nuttx/blob/master/include/nuttx/fs/fs.h)
- [struct file_operations 定义](https://github.com/apache/nuttx/blob/master/include/nuttx/fs/fs.h)
- [NuttX Apps Custom Apps How-to](https://nuttx.apache.org/docs/latest/guides/build/customapps.html)
- [NuttX 源码仓库](https://github.com/apache/nuttx)

## 相关笔记

- [[01-NuttX-环境配置和编译烧录流程]]
- [[02-NuttX-基础API]]
- [[04-NuttX-VFS虚拟文件系统]]
- [[嵌入式文件存储体系/VFS文件管理系统]]
- [[Zephyr/03-Zephyr-设备树与驱动开发]]
