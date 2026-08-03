# 专业技能

## 编程语言与基础

- 精通 C/C++，对链接过程的底层机制有深入理解，清楚 Linker 的符号决议与地址重定位过程，精通 ELF 格式、链接脚本，熟练掌握 ARM 汇编，能看懂上下文切换代码，熟练使用 Python 开发主机测试及调试脚本
- 精通 Cortex-M 内核，特权级与非特权级，熟悉 AAPCS，调用约定时现场保存与恢复，异常进入与异常返回流程，硬件自动入栈出栈，Tail Chaining，中断晚到等

## MCU 与启动

- 熟练使用 STM32、GD32、F1、F4、H5、H7 系列 MCU，精通 MCU bring up，Reset_Handler 到 main 的完整启动过程及 .data .bss 段的加载过程，能用 C 写简单文件系统

## RTOS 与调度

- 精通实时操作系统编程，善于识别并解决 Race Condition，熟悉锁的实现原理、CAS 原子指令，熟悉基于优先级的抢占式调度和 Round-Robin 轮转调度算法，会评估 WCET，熟练使用 FreeRTOS、ThreadX、RT-Thread，会对接移植到其他芯片平台

## 开发工具与构建

- 精通基于 VScode、CMake、Ninja、ARM GNU Toolchain、OpenOCD、clang-format 等工具链的嵌入式开发环境，精通单目标与面向 target 的构建组织，单元测试等多任务的构建方式
- 熟练应用 GoogleTest 进行 Host 端单元测试，在 Docker 容器化环境中开发，了解 CI/CD 流程

## Bootloader 与 OTA

- 精通 Bootloader 及 A/B 双分区 IAP/OTA 升级方案，自动回滚，异常处理，实现 MCUboot

## 软件架构与设计模式

- 精通模块化设计，虚函数、多态实现硬件抽象层，在应用层屏蔽底层硬件差异，提高代码可移植性
- 熟悉嵌入式数据结构：表、环、队列等缓冲区等数据结构，熟悉使用状态机模式、层次状态机、队列状态机，熟悉使用策略模式、观察者模式、发布订阅模式，注重模块解耦、分层、抽象，注重代码质量与代码复用

## 外设与通信

- 熟练使用 UART、TIM、DMA、ADC、DAC、I2C、SPI 等外设及 RS485、CAN、Modbus 等协议
- 熟练掌握基于 Protocol Buffer、RPC 的嵌入式多设备通讯协议设计
- 熟悉计算机网络体系结构、TCP/IP 协议栈，懂得常用协议的原理，了解 Socket 编程

## 电机控制

- 熟悉自动控制及运动控制相关理论，熟悉 FOC 电机控制原理、Clarke/Park 变换、SVPWM 调制原理、电流环速度闭环控制、PID 控制、积分分离和积分抗饱和算法，熟悉步进电机驱动

## 版本控制与协作

- 熟练使用 Git 进行团队协作开发，熟悉 Git Workflow，熟悉使用 repo 进行多仓库管理

## Linux 与 GUI

- 熟练使用 Linux 进行日常开发，会使用 Qt 开发收发程序，移植过 LVGL

## 硬件基础

- 熟悉电路基础知识，能看懂原理图，会使用立创 EDA 绘制 PCB、焊接贴片元件，会使用示波器、逻辑分析仪、信号发生器等常用工具

## 机械结构

- 会使用 SolidWorks 进行零件和装配体建模，懂得结构设计、传动相关知识，有实际项目零件加工打样经验
