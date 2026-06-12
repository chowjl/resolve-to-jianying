# Resolve to Jianying

将 DaVinci Resolve 当前时间线一键转换为 Windows 剪映专业版可继续编辑的草稿。

## 功能

- 从 Resolve 的 `Workspace > Scripts > Utility` 菜单直接运行
- 自动读取当前时间线，不需要手动导出 XML
- 保留视频/音频轨道、剪辑点、源入点和出点
- 支持基础缩放、位置、旋转和透明度
- 自动读取横屏、竖屏时间线分辨率
- 识别素材 90°/270° 旋转信息，使剪映选框贴合画面
- 将源文件同步到剪映素材库，并按文件去重
- 使用空剪映主轨，避免 Resolve V1 被磁吸后错位
- 支持转换前重命名、运行进度和完成确认

## 环境要求

- Windows 10/11
- DaVinci Resolve 20 或 21
- Windows 剪映专业版
- Python 3.8+，推荐 Python 3.11/3.12

## 安装

1. 从 [Releases](../../releases) 下载最新 ZIP。
2. 解压整个 ZIP。
3. 双击 `安装.cmd` 或 `Install.cmd`。
4. 完全退出并重新启动 DaVinci Resolve。

## 使用

打开目标时间线，选择：

```text
Workspace > Scripts > Utility > Current Timeline to Jianying
```

输入剪映草稿名称并开始转换。完成后剪映会自动启动。

## 转换限制

以下内容无法保证完整迁移：

- Resolve 调色节点
- Fusion 合成
- 第三方插件
- 复杂转场和光流变速
- Fairlight 音频特效

视频内嵌音频会保留在视频片段中，可在剪映内按需使用“分离音频”。

## 卸载

运行安装包中的 `卸载.cmd` 或 `Uninstall.cmd`。卸载不会删除已生成的剪映草稿。

## 开源依赖

本项目使用 [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)，其许可证见 `THIRD_PARTY_LICENSES/`。

## License

MIT
