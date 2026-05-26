---
name: esp-idf-device-driver-style
description: Apply the user's ESP-IDF C device-driver style for GERB_GSI and related projects. Use when creating, reviewing, or editing dev_* drivers, BSP HAL wrappers, protocol-backed devices, main.c hardware demos, or AGENTS.md-style code rules in ESP-IDF C projects.
---

# ESP-IDF Device Driver Style

Use this skill when working on the user's ESP-IDF C driver code. Prefer small, direct changes that match the existing `dev_*`, `hal_*`, and protocol component style.

## First Steps

Read the project `AGENTS.md` before coding and say it was read. If the project is a coding workspace and the root has no `AGENTS.md`, create it only when the user asks or the active instructions require it.

Inspect the current module before deciding API shape. Preserve the local style even when another style would also work.

For implementation requests, make the smallest change that satisfies the stated requirement. Do not add adjacent features, refactors, or cleanup unless the change itself creates unused code.

## File Boundaries

In this project, `.c` files include only their matching `.h`:

```c
#include "dev_rtc.h"
```

Put needed system, ESP-IDF, BSP, HAL, protocol, and device includes in the header when the current module style requires them. Do not add extra includes in `.c` unless the user explicitly changes this rule.

Keep the public contract in `.h`: handle type, config/data structs, ops table, constants used by callers, and concise Doxygen comments.

Keep implementation details in `.c`: private struct, register maps, static helpers, logging tag, and bus/protocol logic.

## API Shape

Prefer `handle + ops`:

```c
typedef struct dev_xxx_s *dev_xxx_handle_t;

typedef struct {
    esp_err_t (*create)(const dev_xxx_config_t *config, dev_xxx_handle_t *out_handle);
    esp_err_t (*delete)(dev_xxx_handle_t handle);
    esp_err_t (*read)(dev_xxx_handle_t handle, dev_xxx_data_t *out);
    bool (*is_online)(dev_xxx_handle_t handle);
} dev_xxx_ops_t;

const dev_xxx_ops_t *dev_xxx_get_ops(void);
```

Define the real object only in `.c`:

```c
struct dev_xxx_s {
    ...
};
```

Expose only functions required by the current use case. Do not add future-facing APIs such as alarm, offset calibration, ioctl-style dispatch, SNTP sync, or complex configuration unless requested.

When public API is narrowed or renamed, update all call sites and do not leave obsolete public helpers "just in case".

## Configuration

`create(NULL, ...)` does not mean "use default config". Return `ESP_ERR_INVALID_ARG`.

Only field-level defaults are allowed when the header documents them, for example:

```c
uint8_t i2c_addr;     /* 0=default address */
uint32_t i2c_speed_hz;/* 0=default speed */
```

If the latest user instruction says no default for a field, remove that behavior.

## Validation

Keep checks minimal but necessary:

- `config == NULL`
- `out_handle == NULL`
- `handle == NULL`
- output pointer `== NULL`
- required bus/port handle `== NULL`
- actual bus/protocol call failures

Do not validate business policy in the driver unless requested. Examples to leave to upper layers:

- RTC date range beyond what raw register decoding requires
- SNTP/system-time policy
- file naming policy beyond a requested formatting helper
- application-level calibration decisions

Separate communication status from data validity. `is_online` means recent communication worked. A data struct may carry `valid` when the hardware reports data is not trustworthy:

```c
typedef struct {
    bool valid;
    ...
} dev_xxx_data_t;
```

For RTC-style OS/power-loss flags, prefer `ESP_OK + valid=false` when the I2C transaction succeeds but the chip says the time is invalid. Use an error return for communication or driver failures.

## Logging

Use lowercase, short log messages.

Error logs include `failed` and key-value fields:

```c
ESP_LOGE(TAG, "read time failed: err=%s", esp_err_to_name(ret));
ESP_LOGE(TAG, "i2c device add failed: addr=0x%02x err=%s", addr, esp_err_to_name(ret));
```

Success logs are sparse and only for key lifecycle events:

```c
ESP_LOGI(TAG, "rtc created addr=0x%02x", addr);
```

Prefer these field formats where applicable: `err=%s`, `timeout_ms=%lu`, `len=%u`, `expected=%u`, `got=%u`, `addr=0x%02x`.

## Comments

Use Chinese comments and Doxygen when documenting this codebase.

Header comments describe the external contract. Source comments describe implementation-specific details: register meanings, byte order, timing constraints, protocol frame quirks, and hardware assumptions.

Do not duplicate long explanations in both `.h` and `.c`. Keep one authoritative description, usually in `.h`; `.c` only adds implementation details.

## Register And Protocol Code

Put chip register definitions near the top of `.c`. Keep registers from the referenced vendor/Linux driver if the user wants them for learning or later use, but remove whole feature groups the user excludes.

Use clear comments on important bits:

```c
/* CTRL1 bit5: STOP=1 stops RTC, STOP=0 resumes. */
#define DEV_RTC_PCF85063_CTRL1_STOP BIT(5)
```

For I2C register devices, prefer the existing HAL operations:

```c
i2c->read_mem(handle->dev, reg, buf, len);
i2c->write_mem(handle->dev, reg, buf, len);
i2c->write_byte(handle->dev, reg, value);
```

Use a small `update_bits()` helper only when read-modify-write is repeated or maps directly to a familiar operation such as Linux `regmap_update_bits()`.

## Naming

Public and ops implementation functions keep the module prefix:

```c
dev_rtc_create()
dev_rtc_read_time()
dev_rtc_get_ops()
```

Small static helpers do not need the module prefix:

```c
bin_to_bcd()
bcd_to_bin()
update_bits()
```

Use names already established by nearby modules. Avoid introducing a new naming pattern unless the user asks.

## Resource Lifetime

Use `goto fail` cleanup in `create()` when resources are acquired in stages:

```c
ret = ops->device_add(...);
if (ret != ESP_OK) {
    goto fail;
}

fail:
    if (dev_added) {
        (void)ops->device_remove(handle->dev);
    }
    free(handle);
    return ret;
```

`delete(NULL)` may return `ESP_OK`.

Do not delete a handle inside an infinite demo loop and then reuse it. Create once, use repeatedly, delete only when the demo exits.

## Main Demos

When the user asks for a `main.c` test demo, write a real demo in `main.c`, not just a plan.

Reuse existing board/device initialization when possible. Do not initialize a shared I2C/SPI/UART bus twice if `dev_init_all()` already owns it. Add a narrow getter only when needed to access an existing shared resource.

Keep demos direct:

- create the device
- read or write once or in a simple loop
- log raw and formatted values needed for validation
- avoid extra UI, storage, networking, or synchronization unless requested

For RTC demos, upper layers may set test time when `valid=false`; the RTC driver should not silently perform SNTP or system-time policy.

## Verification

Run `git diff --check` after edits. Build only when requested or when the user has not said to avoid builds and the local ESP-IDF environment is available.

If `idf.py` is unavailable or the shell environment is broken, report that separately from source-code findings. Do not treat environment failure as code failure.
