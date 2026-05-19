| API | Brief | 常见用途 | 备注 |
|---|---|---|---|
| `nvs_flash_init()` | 初始化默认 `nvs` 分区 | 系统启动时初始化 NVS | 一般全局只做一次 |
| `nvs_flash_erase()` | 擦除默认 `nvs` 分区 | `nvs` 空间异常或版本不兼容时恢复 | 常配合 `nvs_flash_init()` 使用 |
| `nvs_open()` | 打开默认 `nvs` 分区中的命名空间 | 后续读写某组配置 | 返回 `nvs_handle_t` |
| `nvs_open_from_partition()` | 打开指定 NVS 分区中的命名空间 | 项目里有多个 NVS 分区时使用 | 平时不如 `nvs_open()` 常用 |
| `nvs_close()` | 关闭已打开的 `handle` | 一次读写完成后释放句柄 | `open` 成功后通常都要 `close` |
| `nvs_set_u8()` | 写入 `uint8_t` 值 | 保存标志位、状态位 | 写后需 `nvs_commit()` |
| `nvs_set_u16()` | 写入 `uint16_t` 值 | 保存较小范围数值 | 写后需 `nvs_commit()` |
| `nvs_set_u32()` | 写入 `uint32_t` 值 | 保存计数、长度、CRC、版本号 | 很常用 |
| `nvs_set_u64()` | 写入 `uint64_t` 值 | 保存时间戳、长整型计数 | 写后需 `nvs_commit()` |
| `nvs_set_i8()` | 写入 `int8_t` 值 | 保存小范围有符号状态 | 写后需 `nvs_commit()` |
| `nvs_set_i16()` | 写入 `int16_t` 值 | 保存小范围有符号参数 | 写后需 `nvs_commit()` |
| `nvs_set_i32()` | 写入 `int32_t` 值 | 保存普通有符号配置值 | 写后需 `nvs_commit()` |
| `nvs_set_i64()` | 写入 `int64_t` 值 | 保存大范围有符号数值 | 写后需 `nvs_commit()` |
| `nvs_set_str()` | 写入字符串 | 保存设备名、服务器地址、版本字符串 | 适合文本配置 |
| `nvs_set_blob()` | 写入二进制数据块 | 保存结构体、校准参数、原始 buffer | 适合复杂数据 |
| `nvs_commit()` | 提交写入到 flash | 所有 `set/erase` 之后持久化保存 | 不调用可能掉电丢失 |
| `nvs_get_u8()` | 读取 `uint8_t` 值 | 读取标志位、状态位 | 常用来判断配置是否存在/有效 |
| `nvs_get_u16()` | 读取 `uint16_t` 值 | 读取短整型配置 | 读取失败常看返回值 |
| `nvs_get_u32()` | 读取 `uint32_t` 值 | 读取长度、CRC、计数、版本号 | 很常用 |
| `nvs_get_u64()` | 读取 `uint64_t` 值 | 读取时间戳等大整数 | 读取失败需处理默认值 |
| `nvs_get_i8()` | 读取 `int8_t` 值 | 读取小范围有符号配置 | 同类接口之一 |
| `nvs_get_i16()` | 读取 `int16_t` 值 | 读取短整型有符号参数 | 同类接口之一 |
| `nvs_get_i32()` | 读取 `int32_t` 值 | 读取普通有符号配置值 | 常见 |
| `nvs_get_i64()` | 读取 `int64_t` 值 | 读取大范围有符号数值 | 同类接口之一 |
| `nvs_get_str()` | 读取字符串 | 读取文本配置 | 常先读长度，再正式读取 |
| `nvs_get_blob()` | 读取二进制数据块 | 读取结构体、校准参数、二进制数据 | 常先读长度，再正式读取 |
| `nvs_erase_key()` | 删除一个 key | 清除某个配置项 | 删除后需 `nvs_commit()` |
| `nvs_erase_all()` | 删除当前命名空间全部 key | 恢复某组配置默认值 | 删除后需 `nvs_commit()` |
| `nvs_get_stats()` | 获取 NVS 分区使用情况 | 排查空间不足、统计已用条目 | 调试时有用 |
| `nvs_get_used_entry_count()` | 获取当前命名空间已用条目数 | 看当前 namespace 占用情况 | 调试辅助 |
| `nvs_find_key()` | 查询 key 是否存在及类型 | 在不直接读取值时做存在性判断 | 相对不如 `nvs_get_xxx()` 常用 |

| 常见返回值 | Brief | 常见场景 | 备注 |
|---|---|---|---|
| `ESP_OK` | 操作成功 | 读写/打开/提交正常完成 | 最常见成功返回 |
| `ESP_ERR_NVS_NOT_FOUND` | key 或 namespace 不存在 | 第一次启动、配置尚未写入 | 常按“使用默认值”处理 |
| `ESP_ERR_NVS_INVALID_LENGTH` | 读取缓冲区长度不够 | `nvs_get_str()` / `nvs_get_blob()` | 常先查长度再读 |
| `ESP_ERR_NVS_NO_FREE_PAGES` | NVS 分区无可用页 | 分区满、分区表变化 | 常擦除后重新初始化 |
| `ESP_ERR_NVS_NEW_VERSION_FOUND` | NVS 数据版本不兼容 | 升级后旧数据格式不兼容 | 常擦除后重新初始化 |
| `ESP_ERR_INVALID_ARG` | 参数非法 | 空指针、长度非法等 | 基础参数检查错误 |