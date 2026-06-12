达芬奇时间线转剪映草稿 / Resolve Timeline to Jianying Draft
============================================================

简介 / Overview
---------------
将 DaVinci Resolve 当前时间线转换成 Windows 剪映专业版可继续编辑的草稿。
Convert the current DaVinci Resolve timeline into an editable Windows Jianying Pro draft.

系统要求 / Requirements
-----------------------
1. Windows 10/11
2. DaVinci Resolve 20 或 21 / DaVinci Resolve 20 or 21
3. Windows 剪映专业版 / Jianying Pro for Windows
4. Python 3.8+，推荐 3.11/3.12 / Python 3.8+, preferably 3.11/3.12
5. 首次安装依赖时需要联网 / Internet access is required during first installation

安装 / Installation
-------------------
1. 解压整个 ZIP，不要只运行压缩包内的单个文件。
   Extract the entire ZIP before running the installer.
2. 双击“安装.cmd”或“Install.cmd”。
   Double-click Install.cmd or 安装.cmd.
3. 安装完成后，完全退出并重新启动 DaVinci Resolve。
   Fully restart DaVinci Resolve after installation.

使用 / Usage
------------
1. 在 DaVinci Resolve 中打开目标项目和时间线。
   Open the target project and timeline in DaVinci Resolve.
2. 选择：Workspace > Scripts > Utility > Current Timeline to Jianying
3. 输入剪映草稿名称并点击“开始转换”。
   Enter the Jianying draft name and click Start Conversion.
4. 等待进度窗口完成；转换期间可以继续使用 Resolve。
   Wait for the progress window; Resolve remains usable.
5. 转换完成后剪映会自动启动。
   Jianying starts automatically when conversion finishes.

支持内容 / Supported Content
----------------------------
- 视频和音频轨道 / Video and audio tracks
- 时间位置、剪辑点、素材入点与出点 / Timeline edits and source ranges
- 基础缩放、位置、旋转与透明度 / Basic transforms and opacity
- 横屏、竖屏时间线 / Landscape and portrait timelines
- 素材库同步与去重 / Media library population and deduplication
- 空剪映主轨防止第一轨磁吸错位 / Empty main track to prevent magnetic offsets

限制 / Limitations
------------------
Resolve 调色节点、Fusion、第三方插件、复杂转场、光流变速及 Fairlight 特效
无法保证完整迁移。

Resolve color nodes, Fusion compositions, third-party plugins, complex transitions,
optical-flow retiming, and Fairlight effects are not guaranteed to transfer.

卸载 / Uninstallation
---------------------
双击“卸载.cmd”或“Uninstall.cmd”。卸载不会删除已生成的剪映草稿。
Double-click Uninstall.cmd or 卸载.cmd. Existing Jianying drafts are preserved.

开源依赖 / Open-source Dependency
---------------------------------
pyJianYingDraft 0.2.6
https://github.com/GuanYixuan/pyJianYingDraft
许可证位于 THIRD_PARTY_LICENSES 文件夹。
Its license is included in THIRD_PARTY_LICENSES.
