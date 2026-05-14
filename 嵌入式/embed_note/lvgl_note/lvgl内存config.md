## 1 使用的内存类型

| 类型                  | 作用                           | 常见配置                                                    |
| ------------------- | ---------------------------- | ------------------------------------------------------- |
| LVGL heap           | LVGL 内部对象、样式、动画、事件、图片缓存等动态分配 | `LV_MEM_SIZE` / `CONFIG_LV_MEM_SIZE_KILOBYTES`          |
| display draw buffer | 屏幕刷新绘图缓冲区                    | `buffer_size` / `draw_buf`                              |
| FreeRTOS task stack | LVGL task / UI task 的栈空间     | `uxTaskGetStackHighWaterMark()` / `xTaskCreate()` stack |
| 图片/字体资源             | bin、C array、字体 bitmap 等      | 编译进 flash / RAM / PSRAM                                 |
| DMA buffer          | SPI/LCD 刷屏 DMA 使用的缓冲区        | `buff_dma = true`                                       |
## 2 
