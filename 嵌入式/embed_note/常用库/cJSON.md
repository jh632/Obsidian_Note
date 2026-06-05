---
date: 2026-06-01
tags: [cjson, json, c-library]
aliases: [cJSON]
---

# cJSON

## 概述
cJSON 是 C 语言超轻量 JSON 解析库，仅 `cJSON.h` + `cJSON.c` 两个文件，广泛用于嵌入式。核心数据结构 `cJSON` 是一个多叉树节点，链表连接兄弟，`child` 指向子节点。

## JSON 语法规则

> JSON（JavaScript Object Notation）是纯文本、语言无关的数据交换格式。ECMA-404 / RFC 8259。

### 数据类型

| 类型 | 示例 | 说明 |
|---|---|---|
| `object` | `{"key":"val"}` | 无序键值对，键必须是双引号字符串 |
| `array` | `[1, 2, 3]` | 有序列表 |
| `string` | `"hello"` | Unicode，转义用 `\`，必须双引号 |
| `number` | `3.14`, `-2`, `1e10` | 整数/浮点/科学计数法，十进制 |
| `boolean` | `true` / `false` | 必须小写 |
| `null` | `null` | 必须小写 |

### 语法要点

```json
{
    "name": "esp32",               // 注释不支持（标准 JSON 无注释）
    "freq": 240,                   // 数字：无前导零、无 NaN/Infinity
    "active": true,                // 布尔：仅 true/false，小写
    "features": ["wifi", "bt"],    // 数组尾部不能有逗号
    "meta": {                      // 嵌套对象
        "ver": "1.0"
    },                             // 最后一个元素后面不能有逗号
    "note": "line1\nline2",        // 换行符用 \n，不能字面换行
    "quote": "say \"hello\""       // 双引号转义 \"
}
```

### 严格规则

- **键必须用双引号** — `{key:1}` ❌，`{"key":1}` ✅
- **尾巴逗号非法** — `[1,2,]` ❌，`{"a":1,}` ❌
- **结束符** — 一个完整 JSON 文本的根必须是 object 或 array
- **编码** — 默认 UTF-8（RFC 8259 强制）。可带 BOM（EF BB BF），但 cJSON 对 BOM 处理因版本而异
- **数字范围** — JSON 标准无范围限制；cJSON 用 `double` 存储（IEEE 754），大整数可能丢精度

### 常见错误

| 错误写法 | 正确写法 | 原因 |
|---|---|---|
| `{name: "x"}` | `{"name": "x"}` | 键未加双引号 |
| `[1,2,]` | `[1,2]` | 尾部逗号 |
| `{"a": true,}` | `{"a": true}` | 对象尾部逗号 |
| `{"a": .5}` | `{"a": 0.5}` | 数字不能省略前导 0 |
| `{"a": 01}` | `{"a": 1}` | 数字不能有前导 0 |
| `{"a": NaN}` | ❌ 无效 JSON | NaN/Infinity 不合法 |
| `{"a": undefined}` | `{"a": null}` | undefined 不是 JSON 类型 |
| 字符串内字面换行 | `"line\nline"` | 换行必须用 `\n` |

## 核心数据结构

```c
typedef struct cJSON {
    struct cJSON *next, *prev;   // 兄弟链表
    struct cJSON *child;         // 首个子节点（对象/数组）
    int type;                     // 节点类型
    char *valuestring;           // 字符串值
    double valuedouble;          // 数字值
    char *string;                // 键名
} cJSON;
```

节点类型：`cJSON_Object` | `cJSON_Array` | `cJSON_String` | `cJSON_Number` | `cJSON_True` | `cJSON_False` | `cJSON_NULL` | `cJSON_Raw` | `cJSON_Invalid`

## API 速查

### 解析

```c
// 解析 JSON 字符串，返回根节点（用完需 cJSON_Delete）
cJSON *cJSON_Parse(const char *value);

// 带选项解析：可指定是否在末尾继续解析
cJSON *cJSON_ParseWithOpts(const char *value, const char **return_parse_end, cJSON_bool require_null_terminated);

// 释放 cJSON 树
void cJSON_Delete(cJSON *item);
```

### 创建

```c
cJSON *cJSON_CreateObject(void);                          // {}
cJSON *cJSON_CreateArray(void);                           // []
cJSON *cJSON_CreateString(const char *string);            // "str"
cJSON *cJSON_CreateNumber(double num);                    // 1.23
cJSON *cJSON_CreateBool(cJSON_bool b);                    // true/false
cJSON *cJSON_CreateNull(void);                            // null
cJSON *cJSON_CreateRaw(const char *raw);                  // 原始 JSON 片段
cJSON *cJSON_CreateIntArray(const int *nums, int count);  // [1,2,3]
cJSON *cJSON_CreateFloatArray(const float *nums, int count);
cJSON *cJSON_CreateDoubleArray(const double *nums, int count);
cJSON *cJSON_CreateStringArray(const char **strings, int count);
```

### 对象操作

```c
// 添加/替换/删除字段
void cJSON_AddItemToObject(cJSON *obj, const char *key, cJSON *item);
void cJSON_AddItemToObjectCS(cJSON *obj, const char *key, cJSON *item); // key 不拷贝，指针直接引用
void cJSON_ReplaceItemInObject(cJSON *obj, const char *key, cJSON *newitem);
void cJSON_ReplaceItemInObjectCaseSensitive(cJSON *obj, const char *key, cJSON *newitem);
void cJSON_DeleteItemFromObject(cJSON *obj, const char *key);           // 按 key 删除
void cJSON_DeleteItemFromObjectCaseSensitive(cJSON *obj, const char *key);

// 查找字段（返回节点指针，失败返回 NULL）
cJSON *cJSON_GetObjectItem(const cJSON *obj, const char *key);
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON *obj, const char *key);
cJSON_bool cJSON_HasObjectItem(const cJSON *obj, const char *key);

// 便捷取值
char    *cJSON_GetStringValue(const cJSON *item);
double   cJSON_GetNumberValue(const cJSON *item);
```

### 数组操作

```c
void cJSON_AddItemToArray(cJSON *array, cJSON *item);
void cJSON_ReplaceItemInArray(cJSON *array, int which, cJSON *newitem);
void cJSON_DeleteItemFromArray(cJSON *array, int which);
int  cJSON_GetArraySize(const cJSON *array);
cJSON *cJSON_GetArrayItem(const cJSON *array, int index);
```

### 序列化

```c
// 格式化输出（带缩进换行，用完 free）
char *cJSON_Print(const cJSON *item);

// 紧凑输出（无多余空格换行）
char *cJSON_PrintUnformatted(const cJSON *item);

// 带预分配 buffer 的打印（减少 malloc）
cJSON_bool cJSON_PrintPreallocated(cJSON *item, char *buf, int len, cJSON_bool fmt);

// 获取预分配所需 buffer 大小
int cJSON_GetPrintBufferSize(const cJSON *item, cJSON_bool fmt);
```

### 杂项

```c
cJSON *cJSON_Duplicate(const cJSON *item, cJSON_bool recurse);  // 深拷贝
int cJSON_Compare(const cJSON *a, const cJSON *b, cJSON_bool case_sensitive);
cJSON *cJSON_ParseWithLength(const char *value, size_t buffer_length); // 非 \0 结尾解析
```

## 典型用法

### 解析

```c
const char *json_str = "{\"name\":\"esp32\",\"id\":1,\"sensors\":[25.5,30.0]}";
cJSON *root = cJSON_Parse(json_str);
if (!root) {
    const char *err = cJSON_GetErrorPtr();  // 获取错误位置
    return;
}

cJSON *name = cJSON_GetObjectItem(root, "name");
printf("name: %s\n", name->valuestring);           // "esp32"
printf("id: %.0f\n", cJSON_GetNumberValue(cJSON_GetObjectItem(root, "id"))); // 1

cJSON *sensors = cJSON_GetObjectItem(root, "sensors");
cJSON *first = cJSON_GetArrayItem(sensors, 0);
printf("sensor[0]: %.1f\n", first->valuedouble);   // 25.5

cJSON_Delete(root);
```

### 构建

```c
cJSON *root = cJSON_CreateObject();
cJSON_AddStringToObject(root, "name", "esp32");
cJSON_AddNumberToObject(root, "id", 1);

cJSON *arr = cJSON_AddArrayToObject(root, "sensors");
cJSON_AddItemToArray(arr, cJSON_CreateNumber(25.5));
cJSON_AddItemToArray(arr, cJSON_CreateNumber(30.0));

char *str = cJSON_PrintUnformatted(root);  // {"name":"esp32","id":1,"sensors":[25.5,30]}
cJSON_Delete(root);
free(str);
```

### 遍历数组/对象

```c
// 遍历数组
cJSON_ArrayForEach(item, array) {
    printf("%.1f\n", item->valuedouble);
}

// 遍历对象子节点（需手动遍历 child 链表）
cJSON *child = obj->child;
while (child) {
    printf("key=%s\n", child->string);
    child = child->next;
}
```

## 注意事项

1. **cJSON_Print / cJSON_PrintUnformatted 返回的 `char*`** 需要调用者 `free()`，否则内存泄漏。
2. **`AddXxxToObject` 系列是宏**，内部调用 `cJSON_CreateXxx` + `cJSON_AddItemToObject`，更简洁。
3. **cJSON_AddItemToObject 会接管 item 所有权**，不要重复释放。
4. **删除数组元素** 用 `cJSON_DeleteItemFromArray(arr, idx)`。
5. **CaseSensitive 版本** 默认即区分大小写，带 `CaseSensitive` 后缀的版本只是语义更明确。
6. **cJSON_Parse** 失败时可用 `cJSON_GetErrorPtr()` 定位错误。

## 参考

- [GitHub - DaveGamble/cJSON](https://github.com/DaveGamble/cJSON)
- cJSON.h 源码注释
