#!/usr/bin/env python3
"""Generate professional Chinese resume PDF for 蒋瀚 — modest tone edition."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os

FONT_DIR = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Hei", os.path.join(FONT_DIR, "simhei.ttf")))
pdfmetrics.registerFont(TTFont("Sun", os.path.join(FONT_DIR, "simsun.ttc"), subfontIndex=0))

# ── Colors ──
C_DARK   = HexColor("#1a1a2e")
C_BLUE   = HexColor("#1B3A5C")
C_GRAY   = HexColor("#555555")
C_LGRAY  = HexColor("#888888")
C_ACCENT = HexColor("#2C5F8A")
C_LINE   = HexColor("#CCCCCC")
WHITE    = white

# ── Styles (all SimSun body, SimHei headings) ──
S = {
    "name": ParagraphStyle("N", fontName="Hei", fontSize=22, textColor=C_DARK, spaceAfter=2*mm, alignment=TA_CENTER),
    "contact": ParagraphStyle("C", fontName="Sun", fontSize=8.5, textColor=C_GRAY, spaceAfter=1*mm, alignment=TA_CENTER),
    "intent": ParagraphStyle("I", fontName="Sun", fontSize=9, textColor=C_DARK, spaceAfter=3*mm, alignment=TA_CENTER),
    "section": ParagraphStyle("S", fontName="Hei", fontSize=11, textColor=C_BLUE, spaceBefore=3.5*mm, spaceAfter=0.5*mm),
    "body": ParagraphStyle("B", fontName="Sun", fontSize=8.5, textColor=C_DARK, leading=14.5, spaceAfter=0.3*mm),
    "body_bold": ParagraphStyle("BB", fontName="Hei", fontSize=8.5, textColor=C_DARK, leading=14.5),
    "bullet": ParagraphStyle("BL", fontName="Sun", fontSize=8, textColor=C_DARK, leading=13.5,
                              leftIndent=8, firstLineIndent=0, spaceAfter=0.2*mm),
    "bullet_bold": ParagraphStyle("BLB", fontName="Hei", fontSize=8, textColor=C_DARK, leading=13.5,
                              leftIndent=8, firstLineIndent=0, spaceAfter=0.2*mm),
    "meta": ParagraphStyle("M", fontName="Sun", fontSize=7.5, textColor=C_LGRAY, spaceAfter=0.3*mm),
    "project_title": ParagraphStyle("PT", fontName="Hei", fontSize=9.5, textColor=C_DARK, spaceAfter=0.5*mm),
    "project_meta": ParagraphStyle("PM", fontName="Sun", fontSize=7.5, textColor=C_LGRAY, spaceAfter=0.3*mm),
}

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_LINE, spaceBefore=0.5*mm, spaceAfter=1.5*mm)

def sec(title):
    return [Paragraph(title, S["section"]), hr()]

def bul(text):
    return Paragraph(f"• {text}", S["bullet"])

def buls(items):
    return [bul(t) for t in items]

def proj(title, meta, desc, points):
    """Project block: title line + description + bullets."""
    r = []
    # Title + meta on same line via table
    tbl = Table([
        [Paragraph(f"<b>{title}</b>", S["project_title"]),
         Paragraph(meta, ParagraphStyle("R", fontName="Sun", fontSize=7.5, textColor=C_LGRAY, alignment=TA_RIGHT))]
    ], colWidths=[9*cm, 8*cm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    r.append(tbl)
    if desc:
        r.append(Paragraph(desc, S["body"]))
        r.append(Spacer(1, 0.5*mm))
    r.extend(buls(points))
    r.append(Spacer(1, 1.5*mm))
    return r

# ═══════════════════ GENERATE ═══════════════════
def build():
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "蒋瀚_嵌入式软件工程师_简历.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=1.2*cm, bottomMargin=1.2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)

    S = ParagraphStyle
    story = []

    # ── HEADER ──
    story.append(Paragraph("蒋 瀚", S("N", fontName="Hei", fontSize=22, textColor=C_DARK,
                                        spaceAfter=1.5*mm, alignment=TA_CENTER)))
    story.append(Paragraph("男 · 15858531984 · 1626748192@qq.com", S("C", fontName="Sun", fontSize=8.5,
                                        textColor=C_GRAY, spaceAfter=0.5*mm, alignment=TA_CENTER)))
    story.append(Spacer(1, 1*mm))

    # ── EDUCATION ──
    story.extend(sec("教育经历"))
    story.append(Paragraph("<b>温州理工学院</b>　|　电子信息工程　|　本科　|　2024.09 - 2027.06", S("B", fontName="Hei", fontSize=8.5)))

    # ── INTERNSHIP ──
    story.extend(sec("实习经历"))
    story.append(Paragraph("<b>埃特博兰（Etteplan）</b>　|　嵌入式软件实习生　|　2026.04 - 2026.06", S("B", fontName="Hei", fontSize=8.5)))
    story.append(Paragraph("参与 ESP32-S3 平台上工业采集与可穿戴设备固件的开发与调试工作。", S("meta")))
    story.append(Spacer(1, 0.3*mm))
    story.extend(buls([
        "搭建 ESP-NOW 通信测试框架，基于 RTT 测量延迟和丢包率，与 HTTP 方式对比为方案选型提供参考",
        "参考 GBN 滑动窗口机制实现了 ESP-NOW 上的可靠传输组件，处理序号管理和超时重传",
        "参与了双端时间戳同步的验证，基于 ESP-NOW 时间戳交换评估同步精度",
        "按 handle/ops 风格封装了力传感器、ADS1015、RTC、电池、LCD 等设备驱动接口",
        "完成力传感器 Modbus RTU 读取，配置 UART/RS485 通信、解析保持寄存器数据并换算为 kN 单位",
        "参与了 PSA 项目 WebSocket 客户端的开发与调试，包括连接状态机维护和 JSON 协议解析",
        "移植 CO5300 显示驱动并适配 LVGL，对接 BME280 环境传感器数据到 UI 刷新流程",
        "参与驱动层重构，把 7 个旧单例驱动逐步改造成统一的 ops+handle 风格",
        "配合完成 GH3220 传感器驱动的部分适配工作，接入 PPG/HR 数据",
        "实现了 HTTP OTA 流程，参与调试 USB 挂载 U 盘的 OTA 升级方案",
        "配合实现 AP 配网页面和 WebSocket 自动重连功能",
    ]))

    # ── PROJECTS ──
    story.extend(sec("项目经历"))

    # P1: PSA
    story.extend(proj(
        "腕带式多道生理信号采集系统（PSA）",
        "ESP32-S3 / ESP-IDF / LVGL / WebSocket",
        "设备集成 PPG、EDA、IMU、环境温湿度气压等多颗传感器，支持蓝牙、USB 和 WebSocket 数据传输，配备 OLED 彩屏显示。",
        [
            "配合完成 GH3220 生理信号 SoC 的 SPI 通信适配和部分算法配置调试",
            "参与 MAX30009 生物阻抗传感器的驱动调试和 EDA 数据读取验证",
            "参与 MPU6050 六轴 IMU 和 BME280 环境传感器的驱动适配",
            "参与 WebSocket 客户端的开发，完成 JSON 协议解析与数据推送的编码调试",
            "配合实现 OTA 升级流程（HTTP OTA + USB U 盘 OTA）的本地验证",
            "参与 LVGL UI 的适配工作，移植 CO5300 QSPI 显示驱动并接入传感器数据刷新",
            "配合调试 AP 配网模式和 WebSocket 自动重连功能",
            "参与驱动层重构方案讨论，按统一风格修改了部分旧驱动的接口",
            "调试了 RTC 时钟同步、SD 卡存储和 AXP2101 电源管理的部分功能",
        ]
    ))

    # P2: GERB
    story.extend(proj(
        "轨道交通隔振器测量系统（GERB）",
        "ESP32-S3 / ESP-IDF / Modbus RTU / ESP-NOW",
        "用于轨道交通场景的隔振器状态测量，实时采集力和位移传感器数据，在主机上显示结果。",
        [
            "搭建 ESP-NOW 通信测试环境，评估延迟和不同距离下的丢包率",
            "参考 GBN 滑动窗口机制实现基础可靠传输功能，处理序号、ACK 和超时重试",
            "参与双端时间戳同步方案验证，评估基于 ESP-NOW 的对时精度",
            "完成了力传感器的 Modbus RTU 驱动封装，实现 RS485 通信和数据解析",
            "封装了 ADS1015 弹簧测距的 I2C 驱动，处理原始 ADC 读取和零点校准",
            "封装了 RTC、电池、LCD、SD 卡等驱动的统一接口",
        ]
    ))

    # P3: STM32
    story.extend(proj(
        "STM32 四轴飞控实验项目",
        "STM32 / MPU6050 / NRF24L01 / PID",
        "",
        [
            "搭建了四轴飞行器实验平台，调试 NRF24L01 无线通信链路",
            "通过 MPU6050 采集姿态数据，配合卡尔曼滤波做姿态角估算",
            "实现基础 PID 姿态控制，完成低空手动飞行验证",
            "封装了传感器和通信模块的外设访问接口",
        ]
    ))

    # ── SKILLS ──
    story.extend(sec("专业技能"))
    skills = [
        ("嵌入式",     "C 语言、ESP-IDF、FreeRTOS，了解常用数据结构和状态机"),
        ("通信协议",   "UART、I2C、SPI、Modbus RTU、ESP-NOW、WebSocket、HTTP"),
        ("驱动开发",   "GH3220、MAX30009、MPU6050、BME280、ADS1015 等传感器调试"),
        ("工程工具",   "LVGL、Git、cmake，能使用示波器和逻辑分析仪辅助排查"),
        ("其他",       "可阅读英文芯片手册，使用 AI 辅助工具提升开发效率"),
    ]
    data = []
    for cat, desc in skills:
        data.append([Paragraph(f"<b>{cat}</b>", S("B", fontName="Hei", fontSize=8)), Paragraph(desc, S("B", fontName="Sun", fontSize=8))])
    t = Table(data, colWidths=[2*cm, 15*cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 2*mm),
        ("TOPPADDING", (0,0), (-1,-1), 0.3*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 0.8*mm),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, HexColor("#EEEEEE")),
    ]))
    story.append(t)

    # ── AWARDS ──
    story.extend(sec("获奖情况"))
    story.extend(buls([
        "全球人工智能算法大赛 浙江省二等奖",
        "蓝桥杯程序设计大赛 浙江省二等奖",
    ]))

    # ── ABOUT ──
    story.extend(sec("自我评价"))
    story.append(Paragraph(
        "对嵌入式开发有兴趣，实践中主要接触过 RTOS、通信协议、传感器驱动和可穿戴设备固件方向。"
        "能结合芯片手册和实际调试现象定位问题，习惯关注代码的可维护性和模块化组织。",
        S("B", fontName="Sun", fontSize=8.5, leading=15)
    ))

    doc.build(story)
    print(f"OK: {out}")

if __name__ == "__main__":
    build()
