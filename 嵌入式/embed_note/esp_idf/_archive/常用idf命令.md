`idf.py save-defconfig` :保存sdkconfig的更改到sdkconfig.defaults

`idf.py merge-bin` :合并打包固件为merged-binary.bin

`esptool.py -p COM24 --chip esp32s3 chip_id`:探查芯片信息,mac地址,型号,晶振,chipid

`esptool.py -p COM24 flash_id` :探查flash信息,flash厂家和大小

`esptool.py -p COM24 erase_flash` :擦除flash

```
esptool.py -p COM24 erase_region 0x10000 0x200000
```

| 参数       | 含义   |
| -------- | ---- |
| 0x10000  | 起始地址 |
| 0x200000 | 长度   |
`esptool.py -p COM24 write_flash 0x0 merged-binary.bin` :烧录

`idf.py -p COM24 monitor` :监视设备