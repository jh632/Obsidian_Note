ESP-IDF 提供了两种主要的自定义方式，你可以根据需求的复杂程度来选择：

| 特性       | **方式一：钩子 (Hooks)**                                                                                                                                                                                | **方式二：完全覆盖 (Override)**                                                                                                                                                                                                                                                                                        |     |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| **核心思路** | 在标准启动加载程序的初始化流程前后，插入自定义代码（钩子函数）。                                                                                                                                                                  | 提供一个完全自定义的 `bootloader_start.c` 来替换默认实现。                                                                                                                                                                                                                                                                       |     |
| **适用场景** | **轻量级扩展**，例如：  <br>- 硬件初始化或自检  <br>- 显示自定义启动Logo  <br>- 记录启动过程中的特定日志                                                                                                                              | **深度定制**，例如：  <br>- 实现完全不同的启动选择逻辑（如多镜像选择）[](http://blog.zhaosn.top/ESP32-examples/04.custom_bootloader/)  <br>- 增加新的安全检查  <br>- 添加专有的固件更新机制                                                                                                                                                                    |     |
| **实现难度** | **较低**，仅需实现几个接口函数。                                                                                                                                                                                | **较高**，需要完全理解启动加载程序的职责并自行实现。                                                                                                                                                                                                                                                                                   |     |
| **官方示例** | [custom_bootloader/bootloader_hooks](https://github.com/espressif/esp-idf/tree/master/examples/custom_bootloader/bootloader_hooks)[](http://blog.zhaosn.top/ESP32-examples/04.custom_bootloader/) | [custom_bootloader/bootloader_override](https://github.com/espressif/esp-idf/tree/master/examples/custom_bootloader/bootloader_override)[](http://blog.zhaosn.top/ESP32-examples/04.custom_bootloader/)[](https://docs.espressif.com/projects/esp-idf/en/v5.3.1/esp32s3/esp-idf-en-v5.3.1-esp32s3.pdf#460#333) |     |

hook.c
```c
#include "esp_log.h"

/* Function used to tell the linker to include this file
 * with all its symbols.
 */
void bootloader_hooks_include(void){
}


void bootloader_before_init(void) {
    /* Keep in mind that a lot of functions cannot be called from here
     * as system initialization has not been performed yet, including
     * BSS, SPI flash, or memory protection.
     */
    ESP_LOGI("HOOK", "This hook is called BEFORE bootloader initialization");
}

void bootloader_after_init(void) {
    ESP_LOGI("HOOK", "This hook is called AFTER bootloader initialization");
}
```

bootloader_start.c

```c
/*
 * SPDX-FileCopyrightText: 2015-2021 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <stdbool.h>
#include <sys/reent.h>
#include "sdkconfig.h"
#include "esp_log.h"
#include "bootloader_init.h"
#include "bootloader_utility.h"
#include "bootloader_common.h"

static const char* TAG = "boot";

static int select_partition_number(bootloader_state_t *bs);

/*
 * We arrive here after the ROM bootloader finished loading this second stage bootloader from flash.
 * The hardware is mostly uninitialized, flash cache is down and the app CPU is in reset.
 * We do have a stack, so we can do the initialization in C.
 */
/*
 * 只读存储器引导程序已完成从闪存加载第二阶段引导程序，随后程序运行至此。
 * 此时硬件基本未完成初始化，闪存缓存处于关闭状态，应用处理器也处于复位状态。
 * 当前已配置好栈空间，因此可使用C语言完成后续初始化工作。
 */
void __attribute__((noreturn)) call_start_cpu0(void)
{
    // 1. Hardware initialization
    if (bootloader_init() != ESP_OK) {
        bootloader_reset();
    }

#ifdef CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP
// If this boot is a wake up from the deep sleep then go to the short way,
// try to load the application which worked before deep sleep.
// It skips a lot of checks due to it was done before (while first boot).
// 如果本次开机是从深度休眠状态唤醒，则执行简易启动流程，
// 尝试加载深度休眠前正在运行的应用程序。
// 由于首次开机时已完成大量检测工作，本次将跳过相关检测步骤。
    bootloader_utility_load_boot_image_from_deep_sleep();
    // If it is not successful try to load an application as usual.
#endif

    // 2. Select the number of boot partition
    bootloader_state_t bs = {0};
    int boot_index = select_partition_number(&bs);
    if (boot_index == INVALID_INDEX) {
        bootloader_reset();
    }

    // 2.1 Print a custom message!
    esp_rom_printf("[%s] %s\n", TAG, CONFIG_EXAMPLE_BOOTLOADER_WELCOME_MESSAGE);

    // 3. Load the app image for booting
    bootloader_utility_load_boot_image(&bs, boot_index);
}

// Select the number of boot partition
static int select_partition_number(bootloader_state_t *bs)
{
    // 1. Load partition table
    if (!bootloader_utility_load_partition_table(bs)) {
        ESP_LOGE(TAG, "load partition table error!");
        return INVALID_INDEX;
    }

    // 2. Select the number of boot partition
    return bootloader_utility_get_selected_boot_partition(bs);
}

#if CONFIG_LIBC_NEWLIB
// Return global reent struct if any newlib functions are linked to bootloader
struct _reent *__getreent(void)
{
    return _GLOBAL_REENT;
}
#endif
```