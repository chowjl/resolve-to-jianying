# 达芬奇与剪映时间线互转 / DaVinci Resolve and Jianying Timeline Bridge

在 DaVinci Resolve 与 Windows 剪映专业版之间双向迁移可编辑时间线。

Transfer editable timelines in both directions between DaVinci Resolve and Jianying Pro for Windows.

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
- 从 Resolve 菜单直接导入剪映草稿，支持剪映 10.8 加密草稿<br>
  Import Jianying drafts directly from Resolve, including encrypted Jianying 10.8 drafts.
- 打开反向脚本时自动定位到剪映草稿根目录<br>
  Open the folder picker directly at Jianying's draft root.

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

### DaVinci Resolve → 剪映 / Resolve → Jianying

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

### 剪映 → DaVinci Resolve / Jianying → Resolve

1. 在 DaVinci Resolve 中打开用于接收时间线的项目。<br>
   Open the destination project in DaVinci Resolve.
2. 选择以下菜单：<br>
   Open this menu:

   ```text
   Workspace > Scripts > Utility > Jianying Timeline to Resolve
   ```

3. 文件夹选择器会自动打开剪映草稿根目录，选择需要导入的草稿文件夹。<br>
   The folder picker opens at Jianying's draft root automatically; select the draft folder to import.
4. 确认或修改时间线名称，点击“导入时间线”。<br>
   Confirm or rename the timeline, then click Import Timeline.
5. 脚本会解密本机草稿副本并导入 Resolve，不会修改原始剪映草稿。<br>
   The script decrypts a temporary local copy and imports it into Resolve without modifying the original draft.

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

加密草稿读取使用 MIT 许可的 [jy-draftc](https://github.com/wenshui330/jy-draftc)，仅调用本机剪映安装目录中的 `videoeditor.dll`。<br>
Encrypted draft reading uses the MIT-licensed [jy-draftc](https://github.com/wenshui330/jy-draftc) helper and calls only the local Jianying installation's `videoeditor.dll`.

## License

MIT
