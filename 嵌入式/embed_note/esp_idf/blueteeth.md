### 1.api_espidf
```c
init_nvs();

/* 只做 BLE 时，先释放 Classic 内存；只做 Classic 时，先释放 BLE 内存 */
ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));
// 或：ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_BLE));

esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
ESP_ERROR_CHECK(esp_bt_controller_init(&amp;bt_cfg));
ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));          "cm">// 或 ESP_BT_MODE_CLASSIC_BT / ESP_BT_MODE_BTDM

ESP_ERROR_CHECK(esp_bluedroid_init());
ESP_ERROR_CHECK(esp_bluedroid_enable());

/* 然后根据业务注册回调 */

typedef void (*esp_gap_ble_cb_t)(esp_gap_ble_cb_event_t event,
                                 esp_ble_gap_cb_param_t *param);
                               
  
typedef void (*esp_gatts_cb_t)(esp_gatts_cb_event_t event,
                               esp_gatt_if_t gatts_if,
                               esp_ble_gatts_cb_param_t *param);                                
ESP_ERROR_CHECK(esp_ble_gap_register_callback(gap_cb));
ESP_ERROR_CHECK(esp_ble_gatts_register_callback(gatts_cb));
ESP_ERROR_CHECK(esp_ble_gatts_app_register(APP_ID));
// 或 GATTC / SPP / BT GAP 等 API
```