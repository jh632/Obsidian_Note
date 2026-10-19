- `static_cast<目标类型>(表达式)` 类型转换
- ```cpp
double d = 3.14;
int i = static_cast<int>(d);                 // 数值转换，i = 3

void* p = &some_struct;
auto* s = static_cast<MyStruct*>(p);         // void* 转具体指针

const wifi_scan_result* r =
static_cast<const wifi_scan_result*>(cb->info);   // 转换时顺便带上 const
  ```