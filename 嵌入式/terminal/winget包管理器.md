|命令|功能说明|常用示例|补充说明|
|---|---|---|---|
|**`search`**|搜索软件，找到它的 `ID`|`winget search vscode`|查找不确定名字的软件时使用。|
|**`show`**|查看软件详细信息|`winget show Microsoft.PowerToys`[](https://blog.csdn.net/qq_46619479/article/details/149408681)|安装前查看版本、介绍等。|
|**`install`**|安装软件|`winget install Microsoft.VisualStudioCode`[](https://blog.csdn.net/weixin_29228203/article/details/159364123)|最常用的安装命令。|
|**`list`**|列出电脑上已装的软件|`winget list`|可查看当前所有可识别的软件。|
|**`upgrade`**|更新软件|`winget upgrade --all`|一键更新所有可升级的软件。|
|**`uninstall`**|卸载软件|`winget uninstall "网易云音乐"`[](https://blog.csdn.net/qq_46619479/article/details/149408681)|也可以用 ID 来卸载。|
|**`export` / `import`**|导出/导入软件列表|`winget export -o apps.json`|重装系统后，一键恢复软件的好帮手。|
|**`source`**|管理软件源|`winget source list`|可查看当前使用的软件仓库。|
|**`--help`**|万能帮助命令|`winget install --help`|记不住参数时，随时查看官方说明。|
