# 达芬奇时间线转剪映草稿 / Resolve Timeline to Jianying Draft

将 DaVinci Resolve 当前时间线一键转换为 Windows 剪映专业版可继续编辑的草稿。

Convert the current DaVinci Resolve timeline into an editable Windows Jianying Pro draft with one command.

## 功能 / Features

- 从 Resolve 的 `Workspace > Scripts > Utility` 菜单直接运行  
  Run directly from Resolve's `Workspace > Scripts > Utility` menu.
- 自动读取当前时间线，无需手动导出 XML  
  Read the current timeline automatically without manually exporting XML.
- 保留视频/音频轨道、剪辑点、源入点和出点  
  Preserve video/audio tracks, edits, source in points, and source out points.
- 支持基础缩放、位置、旋转和透明度  
  Transfer basic scale, position, rotation, and opacity settings.
- 自动读取横屏、竖屏时间线分辨率  
  Detect landscape and portrait timeline resolutions.
- 识别素材 90°/270° 旋转信息，使剪映选框贴合画面  
  Handle 90°/270° rotation metadata so selection bounds match the visible image.
- 将源文件同步到剪映素材库，并按文件去重  
  Populate Jianying's media library and deduplicate source files.
- 使用空剪映主轨，避免 Resolve V1 被磁吸后错位  
  Keep an empty Jianying main track to prevent magnetic-track offsets.
- 支持转换前重命名、运行进度和完成确认  
  Provide draft naming, progress UI, and completion confirmation.

## 界面预览 / Interface Preview

在 DaVinci Resolve 中运行脚本后，可以确认或修改剪映草稿名称，再开始转换。  
After launching the script in DaVinci Resolve, confirm or rename the Jianying draft before starting the conversion.

![DaVinci Resolve 转剪映草稿界面 / Resolve to Jianying conversion dialog](docs/images/resolve-to-jianying-dialog.png)

## 环境要求 / Requirements

- Windows 10/11
- DaVinci Resolve 20 or 21
- Windows 剪映专业版 / Jianying Pro for Windows
- Python 3.8+（推荐 3.11/3.12 / 3.11 or 3.12 recommended）

## 安装 / Installation

1. 从 [Releases](../../releases) 下载最新 ZIP。  
   Download the latest ZIP from [Releases](../../releases).
2. 解压整个 ZIP，不要只运行压缩包内的单个文件。  
   Extract the entire ZIP before running the installer.
3. 双击 `安装.cmd` 或 `Install.cmd`。  
   Double-click `安装.cmd` or `Install.cmd`.
4. 完全退出并重新启动 DaVinci Resolve。  
   Fully restart DaVinci Resolve.

## 使用说明 / Usage

1. 在 DaVinci Resolve 中打开需要转换的项目和时间线。  
   Open the target project and timeline in DaVinci Resolve.
2. 选择以下菜单：  
   Open this menu:

   ```text
   Workspace > Scripts > Utility > Current Timeline to Jianying
   ```

3. 输入生成后的剪映草稿名称，点击“开始转换”。  
   Enter the Jianying draft name and click Start Conversion.
4. 等待进度窗口完成。转换期间可以继续使用 Resolve。  
   Wait for the progress window; Resolve remains usable during conversion.
5. 转换完成后剪映会自动启动，在草稿列表中打开新项目。  
   Jianying starts automatically; open the new project from its draft list.

## 转换范围 / Conversion Scope

可以迁移 / Supported:

- 视频和音频轨道 / Video and audio tracks
- 时间线位置与剪辑点 / Timeline positions and edits
- 素材入点和出点 / Source in and out points
- 基础缩放、位置、旋转、透明度 / Basic scale, position, rotation, and opacity
- 横屏与竖屏画布 / Landscape and portrait canvases
- 素材库索引 / Media library entries

无法保证完整迁移 / Not fully transferable:

- Resolve 调色节点 / Resolve color nodes
- Fusion 合成 / Fusion compositions
- 第三方插件 / Third-party plugins
- 复杂转场和光流变速 / Complex transitions and optical-flow retiming
- Fairlight 音频特效 / Fairlight audio effects

视频内嵌音频会保留在视频片段中，可在剪映内按需使用“分离音频”。  
Embedded audio remains attached to video clips and can be detached inside Jianying when needed.

## 卸载 / Uninstallation

运行 `卸载.cmd` 或 `Uninstall.cmd`。卸载不会删除已生成的剪映草稿。  
Run `卸载.cmd` or `Uninstall.cmd`. Existing Jianying drafts will not be deleted.

## 开源依赖 / Open-source Dependency

本项目使用 [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)，许可证见 `THIRD_PARTY_LICENSES/`。  
This project uses [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft). Its license is included under `THIRD_PARTY_LICENSES/`.

## License

MIT
