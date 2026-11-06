/*
# Zephyr Sensor API 架构图

把 Zephyr Sensor API 的架构画进当前 Excalidraw 绘图。

- 左列（旧版同步）：Fetch and Get —— `sensor_sample_fetch()` 阻塞读入驱动私有数据，`sensor_channel_get()` 取缓存值，得到驱动已经换算好的 `sensor_value`，应用侧不需要解码。
- 右列（新式异步）：Read and Decode —— `SENSOR_DT_READ_IODEV` 定义读取端点，`sensor_read()` 基于 RTIO 异步读取编码数据，再按「需要解码？」判定：解码得到 q31 定点物理量，或把编码数据直接搬走（存储 / 转发 / 稍后解码）。
- 事件在两条路径上形式不同：同步路径用 `sensor_trigger_set()` 回调，异步路径用 `SENSOR_DT_STREAM_IODEV` 流式事件入队。
- 两列下方是公共层：`struct sensor_driver_api` → I2C / SPI 总线 → 芯片寄存器（或 emulator）。
- 图顶部是配置通道：`sensor_attr_get()` / `sensor_attr_set()`。

打开一个 Excalidraw 绘图（空白或已有内容均可）后运行本脚本；绘图里已有内容时，新图绘制在现有内容右侧的空白区域。

```javascript
*/

// ============================================================
// 样式常量
// ============================================================

const FONT_FAMILY = 2; // Helvetica：含中文字形
const TEXT_COLOR = "#1e1e1e";
const BOX_STROKE = "#343a40";
const ARROW_COLOR = "#495057";
const ROUGHNESS = 0;
const STROKE_WIDTH = 2;

const FONT_SIZE = {
  title: 32,
  section: 20,
  node: 16,
  small: 14,
};

const FILL = {
  frameL: "#e7f5ff", // 左列外框（同步）
  frameR: "#ebfbee", // 右列外框（异步）
  plain: "#ffffff", // 普通步骤
  result: "#fff3bf", // 数据产物
  decide: "#ffd8a8", // 判定
  decode: "#b2f2bb", // 解码结果
  skip: "#e9ecef", // 不解码分支
  event: "#e5dbff", // 事件
  layer: "#d0ebff", // 驱动接口层
  hw: "#f1f3f5", // 总线 / 芯片
  attr: "#f3f0ff", // 配置
};

const STROKE = {
  frameL: "#1971c2",
  frameR: "#2f9e44",
  layer: "#1971c2",
  hw: "#868e96",
  event: "#7048e8",
  result: "#e67700",
  decide: "#e8590c",
  decode: "#2f9e44",
  skip: "#868e96",
  attr: "#7048e8",
};

// ============================================================
// 布局常量（画布坐标，单位 px）
// ============================================================

const CANVAS_WIDTH = 1520; // 两列加间距的总宽度，用于标题与配置条居中

const TITLE = "Zephyr Sensor API 架构";
const TITLE_Y = 0;

const ATTR_TEXT =
  "配置：sensor_attr_get() / sensor_attr_set()（采样率 · 量程 · 过采样）";
const ATTR_BOX = { x: 430, y: 60, w: 660, h: 48 };

/** 两条路径的外框 */
const FRAMES = [
  { id: "frameL", x: 0, y: 140, w: 620, h: 880, fill: FILL.frameL, stroke: STROKE.frameL },
  { id: "frameR", x: 760, y: 140, w: 760, h: 1140, fill: FILL.frameR, stroke: STROKE.frameR },
];

/** 外框内的列标题（无边框文本） */
const SECTION_TITLES = [
  { x: 30, y: 165, text: "旧版同步：Fetch and Get" },
  { x: 790, y: 165, text: "新式异步：Read and Decode（RTIO）" },
];

/** 节点：矩形 / 菱形，带居中文本 */
const NODES = [
  // ---- 左列：Fetch and Get ----
  {
    id: "a1", x: 60, y: 250, w: 500, h: 100, fill: FILL.plain, stroke: BOX_STROKE,
    text: "sensor_sample_fetch()\n阻塞读取，存入驱动私有数据",
  },
  {
    id: "a2", x: 60, y: 450, w: 500, h: 100, fill: FILL.plain, stroke: BOX_STROKE,
    text: "sensor_channel_get()\n从驱动缓存取值（不再访问总线）",
  },
  {
    id: "a3", x: 60, y: 650, w: 500, h: 100, fill: FILL.result, stroke: STROKE.result,
    text: "sensor_value\n已换算的物理量，应用不需要解码",
  },
  {
    id: "a4", x: 60, y: 850, w: 500, h: 100, fill: FILL.event, stroke: STROKE.event,
    text: "事件：sensor_trigger_set()\n回调运行在线程上下文",
  },

  // ---- 右列：Read and Decode ----
  {
    id: "b1", x: 810, y: 250, w: 640, h: 100, fill: FILL.plain, stroke: BOX_STROKE,
    text: "SENSOR_DT_READ_IODEV\n定义读取端点（设备 + 通道列表）",
  },
  {
    id: "b2", x: 810, y: 450, w: 640, h: 100, fill: FILL.plain, stroke: BOX_STROKE,
    text: "sensor_read() / sensor_read_async_mempool()\n基于 RTIO 的异步读取",
  },
  {
    id: "b3", x: 810, y: 650, w: 640, h: 100, fill: FILL.result, stroke: STROKE.result,
    text: "编码数据（原始帧）\n含时间戳 / 通道列表 / 移位值的通用头",
  },
  {
    id: "d", x: 1030, y: 800, w: 200, h: 120, fill: FILL.decide, stroke: STROKE.decide,
    shape: "diamond", text: "需要解码？",
  },
  {
    id: "e2", x: 810, y: 970, w: 310, h: 110, fill: FILL.skip, stroke: STROKE.skip,
    text: "编码数据直接搬走\n（存储 / 转发 / 稍后解码）",
  },
  {
    id: "e1", x: 1145, y: 970, w: 310, h: 110, fill: FILL.decode, stroke: STROKE.decode,
    text: "sensor_get_decoder() + decode()\n→ q31 定点（物理量）",
  },
  {
    id: "b4", x: 810, y: 1130, w: 640, h: 100, fill: FILL.event, stroke: STROKE.event,
    text: "事件：SENSOR_DT_STREAM_IODEV\n触发事件与数据一起进入完成队列（流式）",
  },

  // ---- 公共层 ----
  {
    id: "drv", x: 430, y: 1440, w: 660, h: 130, fill: FILL.layer, stroke: STROKE.layer,
    text:
      "struct sensor_driver_api\nsample_fetch · channel_get · attr_set · attr_get\ntrigger_set · get_decoder · submit",
  },
  {
    id: "bus", x: 560, y: 1620, w: 400, h: 80, fill: FILL.hw, stroke: STROKE.hw,
    text: "I2C / SPI 总线",
  },
  {
    id: "chip", x: 560, y: 1780, w: 400, h: 80, fill: FILL.hw, stroke: STROKE.hw,
    text: "芯片寄存器（或 emulator）",
  },
];

/** 箭头：连接节点，可带分支标签 */
const EDGES = [
  { from: "a1", to: "a2" },
  { from: "a2", to: "a3" },
  { from: "b1", to: "b2" },
  { from: "b2", to: "b3" },
  { from: "b3", to: "d" },
  { from: "d", to: "e2", fromSide: "left", label: "否" },
  { from: "d", to: "e1", fromSide: "right", label: "是" },
  { from: "frameL", to: "drv", fromSide: "bottom", toSide: "top" },
  { from: "frameR", to: "drv", fromSide: "bottom", toSide: "top" },
  { from: "drv", to: "bus", fromSide: "bottom", toSide: "top" },
  { from: "bus", to: "chip", fromSide: "bottom", toSide: "top" },
];

// ============================================================
// 绘制函数
// ============================================================

/**
 * 把 ea.style 设成节点基准样式
 * @param {string} fill 填充色
 * @param {string} stroke 描边色
 */
function useNodeStyle(fill, stroke) {
  ea.style.fontFamily = FONT_FAMILY;
  ea.style.fontSize = FONT_SIZE.node;
  ea.style.strokeColor = TEXT_COLOR;
  ea.style.backgroundColor = fill;
  ea.style.fillStyle = "solid";
  ea.style.strokeWidth = STROKE_WIDTH;
  ea.style.roughness = ROUGHNESS;
  ea.style.strokeStyle = "solid";
  ea.style.strokeSharpness = "round";
}

/**
 * 画一个纯矩形外框
 * @param {object} frame 外框定义 {x, y, w, h, fill, stroke}
 * @param {number} dx 水平偏移
 * @returns {string} 元素 id
 */
function addFrame(frame, dx) {
  useNodeStyle(frame.fill, frame.stroke);
  return ea.addRect(frame.x + dx, frame.y, frame.w, frame.h);
}

/**
 * 画一个带边框文本的节点（矩形或菱形）
 * @param {object} node 节点定义 {x, y, w, h, text, fill, stroke, shape}
 * @param {number} dx 水平偏移
 * @returns {string} 节点（容器）元素的 id
 */
function addNode(node, dx) {
  useNodeStyle(node.fill, node.stroke);
  const id = ea.addText(node.x + dx, node.y, node.text, {
    box: node.shape ?? "rectangle",
    width: node.w,
    height: node.h,
    boxPadding: 12,
    boxStrokeColor: node.stroke,
    textAlign: "center",
    textVerticalAlign: "middle",
  });
  // 固定容器的实际宽高，保证布局坐标与箭头锚点一致
  const el = ea.getElement(id);
  el.width = node.w;
  el.height = node.h;
  return id;
}

/**
 * 画一段无边框文本
 * @param {{x: number, y: number, text: string}} item 文本定义
 * @param {number} dx 水平偏移
 * @param {number} fontSize 字号
 * @param {string} align 水平对齐方式
 * @returns {string} 文本元素 id
 */
function addCaption(item, dx, fontSize, align = "left") {
  ea.style.fontFamily = FONT_FAMILY;
  ea.style.fontSize = fontSize;
  ea.style.strokeColor = TEXT_COLOR;
  ea.style.backgroundColor = "transparent";
  ea.style.fillStyle = "solid";
  ea.style.strokeWidth = STROKE_WIDTH;
  ea.style.roughness = ROUGHNESS;
  return ea.addText(item.x + dx, item.y, item.text, { textAlign: align });
}

/**
 * 画居中标题
 * @param {string} text 标题文字
 * @param {number} y 纵坐标
 * @param {number} fontSize 字号
 * @param {number} canvasWidth 画布总宽度（用于居中计算）
 * @param {number} dx 水平偏移
 * @returns {string} 文本元素 id
 */
function addCenteredTitle(text, y, fontSize, canvasWidth, dx) {
  ea.style.fontFamily = FONT_FAMILY;
  ea.style.fontSize = fontSize;
  ea.style.strokeColor = TEXT_COLOR;
  const width = ea.measureText(text).width;
  return ea.addText((canvasWidth - width) / 2 + dx, y, text, {
    textAlign: "center",
  });
}

/**
 * 用箭头连接两个节点；带 label 时在箭头中部加标签
 * @param {object} ids 节点 id 对照表 {name: elementId}
 * @param {object} edge 连线定义 {from, to, fromSide, toSide, label}
 */
function addEdge(ids, edge) {
  ea.style.fontFamily = FONT_FAMILY;
  ea.style.fontSize = FONT_SIZE.small;
  ea.style.strokeColor = ARROW_COLOR;
  ea.style.strokeWidth = STROKE_WIDTH;
  ea.style.roughness = ROUGHNESS;

  const arrowId = ea.connectObjects(
    ids[edge.from],
    edge.fromSide ?? null,
    ids[edge.to],
    edge.toSide ?? null,
    { numberOfPoints: 0, endArrowHead: "arrow" }
  );

  if (edge.label) {
    ea.addLabelToLine(arrowId, edge.label);
  }
  return arrowId;
}

/**
 * 绘制整张架构图
 * @param {number} dx 水平偏移（避开绘图里已有内容）
 */
function drawDiagram(dx) {
  const ids = {};

  for (const frame of FRAMES) {
    ids[frame.id] = addFrame(frame, dx);
  }
  for (const section of SECTION_TITLES) {
    addCaption(section, dx, FONT_SIZE.section);
  }
  for (const node of NODES) {
    ids[node.id] = addNode(node, dx);
  }
  addNode(
    {
      id: "attr",
      x: ATTR_BOX.x,
      y: ATTR_BOX.y,
      w: ATTR_BOX.w,
      h: ATTR_BOX.h,
      fill: FILL.attr,
      stroke: STROKE.attr,
      text: ATTR_TEXT,
    },
    dx
  );
  for (const edge of EDGES) {
    addEdge(ids, edge);
  }
  addCenteredTitle(TITLE, TITLE_Y, FONT_SIZE.title, CANVAS_WIDTH, dx);
}

/**
 * 计算新图的水平偏移：绘图里已有内容时放到现有内容右侧
 * @returns {number} 水平偏移量，空绘图时为 0
 */
function computeOffset() {
  const existing = ea.getViewElements();
  if (existing.length === 0) {
    return 0;
  }
  const box = ea.getBoundingBox(existing);
  return box.topX + box.width + 200;
}

// ============================================================
// 主流程
// ============================================================

const view = ea.setView("auto");
if (!view) {
  new ea.obsidian.Notice("请先打开一个 Excalidraw 绘图，再运行本脚本");
  return;
}

ea.clear();
drawDiagram(computeOffset());
await ea.addElementsToView(false, true);

new ea.obsidian.Notice("Zephyr Sensor API 架构图已绘制完成");
