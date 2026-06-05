## 1 PSA项目问题

### 1.1 驱动格式混乱

| 维度   | 模式 A（dev_* ops/句柄）                           | 模式 B（外部单例）                                          |
| ---- | -------------------------------------------- | --------------------------------------------------- |
| 使用者  | bme280、spo2、rtc、sdcard                       | MPU6050、TMP117、MAX30009、GH3220、AXP2101、OLED、PCF8563 |
| 生命周期 | `create(config, &handle)` / `delete(handle)` | `init(bus)` / `deinit()`                            |
| 状态存储 | 堆分配的不透明句柄                                    | `.c` 文件内 `static` 全局变量                              |
| 错误类型 | `esp_err_t`                                  | 每个驱动自定义枚举                                           |
| 多实例  | 支持                                           | 不支持（单例）                                             |

### 1.2发现的具体问题
  
  1. 两种模式并存：调用者必须知道每个驱动用的是哪种模式，没有统一抽象
  2. RTC 驱动重复：pcf8563.c（旧单例）和 dev_rtc.c（新模式）同时存在，功能重叠
  3. 错误类型不一致：模式 B 驱动各自定义了 mpu6050_status_t、axp2101_status_t 等
  4. 引脚散落各处：SPI 引脚硬编码在 hal_spi.h，AXP2101 引脚在 axp2101.h，I2C 引脚在 drivers_init.c
  5. AXP2101 自建 FreeRTOS 任务：init() 内部 xTaskCreate 轮询电池，生命周期不可控
  6. GH3220 臃肿：供应商演示代码占据驱动代码主体
## 2 重构方案
### 2.1 目录重组
  
 将分散的驱动目录扁平化为统一结构：
components/device/
  │
  ├── CMakeLists.txt                          # 组件构建脚本
  │
  ├── include/                          
  │   ├── dev_bme280.h                       
  │   ├── dev_spo2.h                     
  │   ├── dev_rtc.h                         
  │   ├── dev_sdcard.h                   
  │   ├── dev_mpu6050.h      
  │   ├── dev_tmp117.h               
  │   ├── dev_max30009.h                
  │   ├── dev_gh3220.h                     
  │   ├── dev_axp2101.h              
  │   ├── dev_oled.h              
  │   ├── dev_key.h                          
  │   └── dev_init.h                       
  │
  ├── src/                                    # === 实现文件 ===
  │   │
  │   ├── dev_bme280.c                    
  │   ├── dev_spo2.c                
  │   ├── dev_rtc.c                
  │   ├── dev_sdcard.c                    
  │   ├── dev_mpu6050.c             
  │   ├── dev_tmp117.c                 
  │   ├── dev_max30009.c        
  │   ├── dev_axp2101.c            
  │   ├── dev_oled.c           
  │   ├── dev_key.c                   
  │   ├── dev_init.c                  
  │   └── dev_gh3220/                       
  │       ├── dev_gh3220.c                  
  │       ├── dev_gh3220_hook.h               # [重构] 
  │       │
  │       └── arithmetic                        
  │           ├── algo-lib/                   # 闭源算法库 
  │           ├── demo_kernel_code/           # 开源内核层
  │           └── demo_algo_code/             # 开源算法调用层


### 2.2 驱动统一改造
每个旧单例驱动按 GERB 模式重写：

| 旧 API | 新 API |
| --- | --- |
| MPU6050_Driver.init(bus) | dev_mpu6050_get_ops()->create(&cfg, &handle) |
| MPU6050_Driver.read(&sample) | dev_mpu6050_get_ops()->read(handle, &data) |
| MPU6050_Driver.deinit() | dev_mpu6050_get_ops()->delete(handle) |
| 自定义 mpu6050_status_t | esp_err_t |
每个驱动改造要点：
  - 将 static 全局变量封装进堆分配的不透明句柄结构体
  - init(bus) → create(config, &handle)，引入配置结构体
  - 自定义错误枚举 → esp_err_t
  - 新增 NULL-safe 的 delete()
  - 新增 get_ops() 返回 static const ops 表

涉及的驱动（共 7 个）： MPU6050、TMP117、MAX30009、GH3220、AXP2101、OLED、PCF8563

### 2.3 集中板级驱动到dev_init.c

创建 dev_init.c，作为所有引脚定义和初始化顺序的唯一文件：
```c
// 所有引脚定义集中在此，不再散落各处
  #define I2C_SDA_PIN 15
  #define I2C_SCL_PIN 14
  #define SPI_MOSI_PIN 1

  // ...

  // 文件级静态句柄（s_ 前缀，GERB 约定）
  static dev_bme280_handle_t s_bme280;
  static dev_mpu6050_handle_t s_mpu6050;
  // ...

  esp_err_t dev_init_all(void) {
      // 1. 初始化 I2C 总线
      // 2. 初始化电源管理 (AXP2101)
      // 3. 初始化显示 (OLED)
      // 4. 按依赖顺序初始化各传感器
      // ...
  }

  // 句柄访问器
  dev_bme280_handle_t dev_init_get_bme280(void) { return s_bme280; }
```
### 2.4 更新调用方

更新 drivers_init.c、drivers_data/ 及应用层代码，统一使用：
  - dev_xxx_get_ops()->action(handle, ...) API
  - dev_init_get_xxx() 获取句柄
  - 一致的 esp_err_t 返回值
## 3 各部件实现

### 3.1 dev_bme280
  状态：已是模式 A，无需改造，仅需迁移目录。

  目录: components/device/include/dev_bme280.h
        components/device/src/dev_bme280.c

  API 不变：
  ```c
  typedef struct {
    i2c_master_bus_handle_t bus_handle;
    uint8_t                 i2c_addr;
} dev_bme280_config_t;

typedef struct {
    float temperature; /* 摄氏度 */
    float pressure;    /* 帕斯卡 */
    float humidity;    /* %RH */
    bool  valid;
} dev_bme280_data_t;

typedef struct dev_bme280_s *dev_bme280_handle_t;

/* 驱动操作接口 */

typedef struct {

    esp_err_t (*create)(const dev_bme280_config_t *config, dev_bme280_handle_t *ret_handle);
    esp_err_t (*delete)(dev_bme280_handle_t handle);
    esp_err_t (*read)(dev_bme280_handle_t handle, dev_bme280_data_t *data);
    bool (*is_online)(dev_bme280_handle_t handle);

} dev_bme280_ops_t;

const dev_bme280_ops_t *dev_bme280_get_ops(void);
  ```

### 3.2 dev_spo2
状态：已是模式 A，无需改造，仅需迁移目录。

目录: components/device/include/dev_bme280.h  
components/device/src/dev_bme280.c
```c
typedef struct {
    hal_spi_config_t *spi_config;       /* 共享 SPI 总线配置 */
    gpio_num_t        cs_pin;           /* TS9517 串行锁存片选 */
    gpio_num_t        red_pin;          /* RED_CS，高电平打开红光窗口 */
    gpio_num_t        ir_pin;           /* IR_CS，高电平打开红外窗口 */
    gpio_num_t        out_pin;          /* OUT 频率输出到 MCU */
    uint8_t           red_code;         /* 红光 LED 电流码，0..127 */
    uint8_t           ir_code;          /* 红外 LED 电流码，0..127 */
    uint32_t          sample_window_us; /* 每个 LED 的计频窗口 */
} dev_spo2_config_t;

#define DEV_SPO2_INIT_CONFIG(_spi_config)                                                        \

    (dev_spo2_config_t) {                                                                        \

        .spi_config       = (_spi_config),                                                       \
        .cs_pin           = DEV_SPO2_DEFAULT_CS_PIN,                                             \
        .red_pin          = DEV_SPO2_DEFAULT_RED_PIN,                                            \
        .ir_pin           = DEV_SPO2_DEFAULT_IR_PIN,                                             \
        .out_pin          = DEV_SPO2_DEFAULT_OUT_PIN,                                            \
        .red_code         = DEV_SPO2_DEFAULT_RED_CODE,                                           \
        .ir_code          = DEV_SPO2_DEFAULT_IR_CODE,                                            \
        .sample_window_us = DEV_SPO2_DEFAULT_SAMPLE_WINDOW_US,                                   \
    }

typedef struct {
    uint32_t red_count;   /* 红光窗口内采到的脉冲数 */
    uint32_t ir_count;    /* 红外窗口内采到的脉冲数 */
    uint32_t red_freq_hz; /* 红光脉冲数换算出的频率 */
    uint32_t ir_freq_hz;  /* 红外脉冲数换算出的频率 */
    bool     valid;       /* 红光和红外窗口都成功采样后为真 */
} dev_spo2_data_t;  

typedef struct dev_spo2_s *dev_spo2_handle_t;

typedef struct {
    esp_err_t (*create)(const dev_spo2_config_t *config, dev_spo2_handle_t *ret_handle);
    esp_err_t (*delete)(dev_spo2_handle_t handle);
    esp_err_t (*read)(dev_spo2_handle_t handle, dev_spo2_data_t *data);
    /* 不重建设备，直接更新红光和红外两个电流寄存器。 */
    esp_err_t (*set_led_code)(dev_spo2_handle_t handle, uint8_t red_code, uint8_t ir_code);
    bool (*is_online)(dev_spo2_handle_t handle);
} dev_spo2_ops_t;

const dev_spo2_ops_t *dev_spo2_get_ops(void);
```

### 3.3 dev_RTC

状态：已是模式 A，仅需迁移目录 + 删除 pcf8563。
目录: 
components/device/include/dev_rtc.h
components/device/src/dev_rtc.c
删除: driver_rtc/pcf8563.h, driver_rtc/pcf8563.c

```c
typedef struct dev_rtc_s *dev_rtc_handle_t;

typedef struct {
    i2c_master_bus_handle_t bus_handle;  
    uint8_t                 i2c_addr;    
    uint32_t                i2c_speed_hz;
} dev_rtc_config_t;

typedef struct {
    bool     valid;
    uint16_t year;
    uint8_t  month;
    uint8_t  day;
    uint8_t  hour;
    uint8_t  minute;
    uint8_t  second;
    uint8_t  weekday;
} dev_rtc_time_t;

typedef struct {
    esp_err_t (*create)(const dev_rtc_config_t *config, dev_rtc_handle_t *out_handle);
    esp_err_t (*delete)(dev_rtc_handle_t handle);
    esp_err_t (*read_time)(dev_rtc_handle_t handle, dev_rtc_time_t *out_time);
    esp_err_t (*set_time)(dev_rtc_handle_t handle, const dev_rtc_time_t *time);
    bool (*is_online)(dev_rtc_handle_t handle);
    esp_err_t (*sync_to_system)(dev_rtc_handle_t handle);
} dev_rtc_ops_t;

const dev_rtc_ops_t *dev_rtc_get_ops(void);
```

### 3.4 dev_battery
GERB项目已有重构后文件可复用
原psa轮询打印电量留给上层实现
```c
/* AXP2101 充电状态值，对应 dev_battery_data_t.charge_state。 */
#define DEV_BATTERY_PRE_CHARGE   0X01
#define DEV_BATTERY_CC_CHARGE    0X02
#define DEV_BATTERY_CV_CHARGE    0X03
#define DEV_BATTERY_CHARGE_DONE  0X04
#define DEV_BATTERY_NOT_CHARGING 0X05

typedef enum {
    DEV_BATTERY_CHG_CURR_0MA    = 0x00,
    DEV_BATTERY_CHG_CURR_100MA  = 0x04,
    DEV_BATTERY_CHG_CURR_125MA  = 0x05,
    DEV_BATTERY_CHG_CURR_150MA  = 0x06,
    DEV_BATTERY_CHG_CURR_175MA  = 0x07,
    DEV_BATTERY_CHG_CURR_200MA  = 0x08,
    DEV_BATTERY_CHG_CURR_300MA  = 0x09,
    DEV_BATTERY_CHG_CURR_400MA  = 0x0A,
    DEV_BATTERY_CHG_CURR_500MA  = 0x0B,
    DEV_BATTERY_CHG_CURR_600MA  = 0x0C,
    DEV_BATTERY_CHG_CURR_700MA  = 0x0D,
    DEV_BATTERY_CHG_CURR_800MA  = 0x0E,
    DEV_BATTERY_CHG_CURR_900MA  = 0x0F,
    DEV_BATTERY_CHG_CURR_1000MA = 0x10,
    DEV_BATTERY_CHG_CURR_INVALID
} dev_battery_charge_current_t;

#define BATTERY_STATUS_TASK_DELAY_MS 2000

typedef struct {
    bool    charge_status;
    uint8_t reg01;
    uint8_t charge_direction;
    uint8_t charge_state;
    uint8_t battery_level;
    float   battery_temperature;
} dev_battery_data_t;

typedef struct dev_battery_s *dev_battery_handle_t;

typedef struct {
    i2c_master_bus_handle_t      i2c_bus;
    uint32_t                     i2c_speed_hz;
    dev_battery_charge_current_t charge_speed;
} dev_battery_config_t;

typedef struct {
    esp_err_t (*create)(dev_battery_handle_t *handle, const dev_battery_config_t *config);
    esp_err_t (*delete)(dev_battery_handle_t handle);
    esp_err_t (*set_charge_current)(dev_battery_handle_t         handle,
                                    dev_battery_charge_current_t current);
    esp_err_t (*power_off)(dev_battery_handle_t handle);
    esp_err_t (*get_data)(dev_battery_handle_t handle, dev_battery_data_t *data);
    esp_err_t (*is_online)(dev_battery_handle_t handle, bool *online);
} dev_battery_ops_t;

const dev_battery_ops_t *dev_battery_get_ops(void);
```

### 3.5 **dev_imu**(需重构)

 状态：模式 B → 模式 A，核心改造对象。

```c
typedef struct dev_mpu6050_s *dev_mpu6050_handle_t;

typedef struct {
  i2c_master_bus_handle_t bus_handle;    // 必须
  uint8_t                 i2c_addr;       // 0 = 0x68
  uint32_t                i2c_speed_hz;   // 0 = 400000
  uint8_t                 accel_range;    // 0 = ±2g (保持现有配置)
  uint8_t                 gyro_range;     // 0 = ±250°/s
  uint8_t                 dlpf_cfg;       // 0 = 3 (44Hz/42Hz)
  uint8_t                 sample_rate_div;// 0 = 9 (100Hz)
} dev_mpu6050_config_t;

typedef struct {
  int16_t raw_ax, raw_ay, raw_az;
  int16_t raw_gx, raw_gy, raw_gz;
  float   pitch, roll, yaw;
} dev_mpu6050_data_t;

typedef struct {
  esp_err_t (*create)(const dev_mpu6050_config_t *config, dev_mpu6050_handle_t *ret_handle);
  esp_err_t (*delete)(dev_mpu6050_handle_t handle);
  esp_err_t (*read)(dev_mpu6050_handle_t handle, dev_mpu6050_data_t *data);
  bool      (*is_online)(dev_mpu6050_handle_t handle);
} dev_mpu6050_ops_t;
```

### 3.6 **dev_tmp117**(需重构)
精密温度传感器（I2C）
```c
  typedef struct dev_tmp117_s *dev_tmp117_handle_t;

  typedef struct {
      i2c_master_bus_handle_t bus_handle;
      uint8_t                 i2c_addr;       // 0 = 0x48
      uint32_t                i2c_speed_hz;   // 0 = 400000
  } dev_tmp117_config_t;

  typedef struct {
      float temperature;   // 摄氏度
      bool  valid;
  } dev_tmp117_data_t;

  typedef struct {
      esp_err_t (*create)(const dev_tmp117_config_t *config, dev_tmp117_handle_t *ret_handle);
      esp_err_t (*delete)(dev_tmp117_handle_t handle);
      esp_err_t (*read)(dev_tmp117_handle_t handle, dev_tmp117_data_t *data);
      bool      (*is_online)(dev_tmp117_handle_t handle);
  } dev_tmp117_ops_t;
```
重构要点:
 - s_ctx → 堆分配的 struct dev_tmp117_s {   i2c_master_dev_handle_t dev; bool online; 
  }
  - TMP117_Driver.init(bus) → dev_tmp117_get_ops()->create(&cfg, &handle)
  - TMP117_Driver.check_status() → dev_tmp117_get_ops()->is_online(handle)
  - tmp117_status_t → esp_err_t
  ### 3.7 **dev_max3009**(需重构)
  ```c
typedef struct dev_max30009_s *dev_max30009_handle_t;

typedef struct {
  hal_spi_config_t *spi_config;
  gpio_num_t        cs_pin;      // 0 = 18
  gpio_num_t        int_pin;     // 0 = 17
} dev_max30009_config_t;

typedef struct {
  int32_t  *adc_buf;      // 调用方提供的缓冲区
  uint16_t  buf_size;     // 缓冲区容量
  uint16_t  out_count;    // 实际读出样本数
  float     ohms;         // 最新一个样本的阻抗值 (Ω)
  float     conductivity_us; // 电导率 (µS)
  bool      valid;
  bool      lead_off;     // 电极脱落
} dev_max30009_data_t;

typedef struct {
  esp_err_t (*create)(const dev_max30009_config_t *config, dev_max30009_handle_t *ret_handle);
  esp_err_t (*delete)(dev_max30009_handle_t handle);
  esp_err_t (*read)(dev_max30009_handle_t handle, dev_max30009_data_t *data);
  bool      (*is_online)(dev_max30009_handle_t handle);
  esp_err_t (*flush_fifo)(dev_max30009_handle_t handle);
} dev_max30009_ops_t;

// 工具函数保留（不依赖 handle）
float max30009_adc_to_ohms(int32_t adc_val, float bioz_gain, float imag_apk);
float max30009_ohms_to_conductivity_us(float ohms);
  ```
  ### 3.8 **dev_lcd**(需重构)
  只做板级驱动封装,完成qspi屏幕驱动提供lvgl适配所需api(C05300)
  ```c
#include "esp_lcd_types.h"

typedef struct dev_lcd_s *dev_lcd_handle_t; 

 //定位坐标原点
  typedef enum {
    DEV_LCD_ORIENTATION_TOP_LEFT_X_RIGHT_Y_DOWN = 0,
    DEV_LCD_ORIENTATION_TOP_RIGHT_X_LEFT_Y_DOWN,
    DEV_LCD_ORIENTATION_BOTTOM_LEFT_X_RIGHT_Y_UP,
    DEV_LCD_ORIENTATION_BOTTOM_RIGHT_X_LEFT_Y_UP,
    DEV_LCD_ORIENTATION_TOP_LEFT_X_DOWN_Y_RIGHT,
    DEV_LCD_ORIENTATION_TOP_RIGHT_X_DOWN_Y_LEFT,
    DEV_LCD_ORIENTATION_BOTTOM_LEFT_X_UP_Y_RIGHT,
    DEV_LCD_ORIENTATION_BOTTOM_RIGHT_X_UP_Y_LEFT,
    DEV_LCD_ORIENTATION_COUNT,
} dev_lcd_orientation_t;
  
  /* ===== 配置结构体 ===== */
typedef struct {
    int                     width;              // 屏幕宽度
    int                     height;             // 屏幕高度
    spi_host_device_t       spi_host;           // SPI 主机外设
    int                     sclk_pin;           // 时钟引脚
    int                     data0_pin;          // IO0
    int                     data1_pin;          // IO1
    int                     data2_pin;          // IO2
    int                     data3_pin;          // IO3
    int                     cs_pin;             // 片选引脚
    int                     dc_pin;             // 命令/数据选择引脚（-1 表示使用 9 位 QSPI 模式）
    int                     rst_pin;            // 复位引脚
    int                     bl_pin;             // 背光引脚
    int                     clock_speed_hz;     // 时钟频率（Hz）
    int                     max_transfer_sz;    // 单次最大传输字节数
    dev_lcd_orientation_t   orientation;        // 显示方向
    bool                    color_inverted;     // 颜色反转
    lcd_rgb_element_order_t rgb_ele_order;      // RGB 元素顺序
} dev_lcd_config_t;

typedef struct {
    esp_err_t (*create)(const dev_lcd_config_t *config, dev_lcd_handle_t *out_handle);
    esp_err_t (*delete)(dev_lcd_handle_t handle);
    esp_err_t (*flush)(dev_lcd_handle_t handle,
                       int              x_start,
                       int              y_start,
                       int              x_end,
                       int              y_end,
                       const void      *color_data);
    esp_err_t (*set_backlight)(dev_lcd_handle_t handle, uint8_t brightness);
} dev_lcd_ops_t;

const dev_lcd_ops_t *dev_lcd_get_ops(void);
  ```
### 3.9 dev_sdcard
状态：已是模式 A，仅需迁移目录。

目录: components/device/include/dev_sdcard.h
	components/device/src/dev_sdcard.c

API 不变。

### 3.10 **dev_key**(需重构)
- 业务逻辑混杂在代码中
- 取消multi_button的依赖,同GERB项目的按键驱动
- 业务逻辑留给上层
### 3.11 **dev_gh3220**(需重构)
现有架构分层:
driver_gh3220/
├── algo-lib/                          # [闭源]6个.a静态库+模型权重
│   ├── HR/HRV/SPO2/ECG/NADT/COMMON    # 算法库
│   └── algo_params/                   # 12个权重/配置文件
│
├── demo_kernel_code/                  # [开源SDK] 汇顶内核层
│   ├── driver/                        # SPI/I2C底层接口抽象
│   │   ├── gh_drv_interface.c         # 总线读写 + 延时 + 复位
│   │   └── gh_drv_control.c           # 寄存器控制
│   ├── kernel/                        # 数据协议 + 状态机
│   │   ├── gh_demo.c                  # 主状态机 (1774行, 佩戴测在此)
│   │   ├── gh_demo_protocol.c         # 内部协议解析
│   │   └── gh_demo_reg_array.c        # 寄存器配置表
│   └── module/                        # 传感器模块 (ECG/AGC)
│
├── demo_algo_code/                    # [开源SDK] 算法调用层
│   ├── goodix_algo_call/src/          # 各算法调用封装 (HR/SPO2/ECG/...)
│   └── goodix_algo_application/src/
│       └── gh3x2x_demo_algo_hook.c    # ★ 算法结果回调 → s_sensor_value
│
└── driver_user/                       # [项目代码] BSP适配层
├── gh3220.h                       # 对外接口
└── gh3220.c                       # SPI/GPIO/中断适配 + 佩戴采样控制

### 3.11 dev_init - 板级唯一初始化
dev_init.h

```c
#include "hal_i2c.h"
#include "hal_spi.h"
#include "dev_bme280.h"
#include "dev_spo2.h"
#include "dev_rtc.h"
#include "dev_mpu6050.h"
#include "dev_tmp117.h"
#include "dev_max30009.h"
#include "dev_axp2101.h"
#include "dev_oled.h"
#include "dev_sdcard.h"
#include "dev_key.h"

esp_err_t dev_init_all(void);
esp_err_t dev_deinit_all(void);

/* 句柄访问器 — 上层通过这些函数获取设备实例 */
dev_bme280_handle_t   dev_init_get_bme280(void);
dev_spo2_handle_t     dev_init_get_spo2(void);
dev_rtc_handle_t      dev_init_get_rtc(void);
dev_mpu6050_handle_t  dev_init_get_mpu6050(void);
dev_tmp117_handle_t   dev_init_get_tmp117(void);
dev_max30009_handle_t dev_init_get_max30009(void);
dev_axp2101_handle_t  dev_init_get_axp2101(void);
dev_oled_handle_t     dev_init_get_oled(void);
dev_sdcard_handle_t   dev_init_get_sdcard(void);
dev_key_handle_t      dev_init_get_key_power(void);


```
dev_init.c
```c
// 所有引脚定义集中在此
#define PSA_I2C_SDA_PIN   GPIO_NUM_15
#define PSA_I2C_SCL_PIN   GPIO_NUM_14
#define PSA_SPI_MOSI_PIN  GPIO_NUM_1
#define PSA_SPI_MISO_PIN  GPIO_NUM_3
#define PSA_SPI_SCLK_PIN  GPIO_NUM_2
//...

// 文件级静态句柄
static i2c_master_bus_handle_t  s_i2c_bus;
static hal_spi_config_t         s_spi_conf;
static dev_bme280_handle_t      s_bme280;
static dev_mpu6050_handle_t     s_mpu6050;
// ...

esp_err_t dev_init_all(void) {
  // 1. I2C 总线
  hal_i2c_config_t i2c_conf = { .port = HAL_I2C_PORT_0, .sda_io = PSA_I2C_SDA_PIN, .scl_io = PSA_I2C_SCL_PIN };
  hal_i2c_get_ops()->bus_init(&i2c_conf, &s_i2c_bus);

  // 2. SPI 总线
  s_spi_conf = HAL_SPI_INIT_CONFIG(HAL_SPI_PORT_0, PSA_SPI_MOSI_PIN, PSA_SPI_MISO_PIN, PSA_SPI_SCLK_PIN);
  hal_spi_get_ops()->bus_init(&s_spi_conf);

  // 3. 电源 (AXP2101) — 先使能显示供电
  dev_axp2101_config_t axp_cfg = { .bus_handle = s_i2c_bus };
  dev_axp2101_get_ops()->create(&axp_cfg, &s_axp2101);
  dev_axp2101_get_ops()->enable_display_power(s_axp2101);
  vTaskDelay(pdMS_TO_TICKS(500));

  // 4. 显示 (OLED)
  dev_oled_config_t oled_cfg = { 0 };  // 全 0 = 使用默认引脚
  dev_oled_get_ops()->create(&oled_cfg, &s_oled);

  // 5. 环境传感器 (BME280)
  dev_bme280_config_t bme_cfg = { .bus_handle = s_i2c_bus };
  dev_bme280_get_ops()->create(&bme_cfg, &s_bme280);

  // 6. RTC
  dev_rtc_config_t rtc_cfg = { .bus_handle = s_i2c_bus };
  dev_rtc_get_ops()->create(&rtc_cfg, &s_rtc);

  // 7. IMU (MPU6050)
  dev_mpu6050_config_t mpu_cfg = { .bus_handle = s_i2c_bus };
  dev_mpu6050_get_ops()->create(&mpu_cfg, &s_mpu6050);

  // 8. 温度 (TMP117)
  dev_tmp117_config_t tmp_cfg = { .bus_handle = s_i2c_bus };
  dev_tmp117_get_ops()->create(&tmp_cfg, &s_tmp117);

  // 9. EDA (MAX30009)
  dev_max30009_config_t max_cfg = { .spi_config = &s_spi_conf };
  dev_max30009_get_ops()->create(&max_cfg, &s_max30009);

  // 10. SPO2
  dev_spo2_config_t spo2_cfg = { .spi_config = &s_spi_conf };
  dev_spo2_get_ops()->create(&spo2_cfg, &s_spo2);

  // 11. 按键
  dev_key_config_t key_cfg = { .gpio_num = GPIO_NUM_45, .active_level = 1 };
  dev_key_get_ops()->create(&key_cfg, &s_key_power);

  return ESP_OK;
}
```