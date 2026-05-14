## 1初始化流程
```
硬件初始化
  ↓
LVGL 核心初始化
  ↓
显示设备 display 初始化
  ↓
输入设备 input 初始化
  ↓
定时器 / tick / task handler 初始化
```
## 2 必须配置 LV_COLOR_DEPTH
### 1 LV_COLOR_DEPTH
```c
#define LV_COLOR_DEPTH 16
```

| 值    | 含义       | 常见场景                   |
| ---- | -------- | ---------------------- |
| `1`  | 单色       | 墨水屏、黑白屏                |
| `8`  | 256 色    | 少见                     |
| `16` | RGB565   | MCU 小屏幕最常见             |
| `24` | RGB888   | Linux framebuffer、PC   |
| `32` | ARGB8888 | 带 alpha 的 GUI、PC、Linux |
|      |          |                        |
### 2 LV_COLOR_16_SWAP
```c
#define LV_COLOR_16_SWAP 0/1
```

## 3 必须配置：内存管理
### 1 使用固定内存块
```c
#define LV_MEM_CUSTOM 0
#define LV_MEM_SIZE (64U * 1024U)
```

### 2 使用系统malloc/calloc
```c
#define LV_MEM_CUSTOM 1
#define LV_MEM_CUSTOM_ALLOC   malloc
#define LV_MEM_CUSTOM_FREE    free
#define LV_MEM_CUSTOM_REALLOC realloc
```

## 4 必须配置：显示缓冲区

为flush_cb分配一块内存 40可以修改,取决于内存大小,相当于一次刷新几行
```c
static lv_color_t buf1[MY_DISP_HOR_RES * 40];

static lv_disp_draw_buf_t draw_buf;

lv_disp_draw_buf_init(
    &draw_buf,
    buf1,
    NULL,
    MY_DISP_HOR_RES * 40
);
```

绑定到display_driver
```c
static lv_disp_drv_t disp_drv;

lv_disp_drv_init(&disp_drv);

disp_drv.hor_res = MY_DISP_HOR_RES;
disp_drv.ver_res = MY_DISP_VER_RES;
disp_drv.flush_cb = my_disp_flush;
disp_drv.draw_buf = &draw_buf;

lv_disp_drv_register(&disp_drv);
```