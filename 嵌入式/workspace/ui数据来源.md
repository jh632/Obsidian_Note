QC UI 11 项测试 — 数据来源总结

Page 0 — 传感器（6 项）

项: BME280
判定依据: get_data.bme280_valid
数据来源: get_data.temp/hum/pressure（env_sensors_task 1Hz I2C 读取）
更新方式: 后台任务
────────────────────────────────────────
项: MPU6050
判定依据: get_data.mpu_valid
数据来源: g_IMU_DB write buffer 最新 sample → accel[3] gyro[3] 原始 int16 LSB
更新方式: mpu6050_read_task 25Hz → ring buffer
────────────────────────────────────────
项: TMP117
判定依据: get_data.tmp_valid
数据来源: get_data.skin_temp（env_sensors_task 1Hz I2C 读取）
更新方式: 后台任务
────────────────────────────────────────
项: GH3220
判定依据: get_data.ppg_valid
数据来源: g_PPG_DB write buffer 最新 sample → ppg_val[0..2] 原始 uint32 ADC
更新方式: GH3220 FIFO 中断 → gh_demo_hook → ring buffer
────────────────────────────────────────
项: MAX30009
判定依据: get_data.eda_valid
数据来源: g_EDA_DB write buffer 最新 sample → eda_val 原始 int32 ADC
更新方式: max30009_read_task 50Hz → ring buffer
────────────────────────────────────────
项: SPO2
判定依据: is_online() + read()
数据来源: dev_spo2_data_t.red_count/ir_count（直接 SPI+PCNT 读取）
更新方式: 每次 QC 轮询时直接读

Page 1 — 电源/外设（5 项）

项: AXP2101
判定依据: bd.read_status
数据来源: axp2101_get_ops()->get_data() → 电量/电压/充电状态/温度（直接 I2C）
更新方式: 每次 QC 轮询时直接读
────────────────────────────────────────
项: RTC
判定依据: read_time() == OK && rt.valid
数据来源: dev_rtc_get_ops()->read_time() → 年月日时分（直接 I2C）
更新方式: 每次 QC 轮询时直接读
────────────────────────────────────────
项: OLED
判定依据: check_status()
数据来源: 返回 DISP_OK 或失败
更新方式: 每次 QC 轮询时直接查
────────────────────────────────────────
项: USB
判定依据: phy_connected 标志
数据来源: usb_get_ops()->get_status() → 物理连接状态
更新方式: 每次 QC 轮询时直接查
────────────────────────────────────────
项: BLE
判定依据: is_connected()
数据来源: ble_get_ops()->is_connected() → 连接/广播状态
更新方式: 每次 QC 轮询时直接查

数据获取模式

- 直接读取（6 项）：AXP2101、RTC、OLED、SPO2、USB、BLE — 每次 collect_sensors() 直接调用驱动接口
- 共享内存（2 项）：BME280、TMP117 — 读取 get_data 全局结构体，由 env_sensors_task 1Hz 写入
- Ring buffer peek（3 项）：MPU6050、GH3220、MAX30009 — 拿 mutex → 读 write buffer 最新 sample → 释放 mutex，不消费数据**