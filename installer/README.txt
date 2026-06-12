DaVinci Resolve 当前时间线 → 剪映草稿
========================================

系统要求
--------
1. Windows 10/11
2. DaVinci Resolve 21（免费版或 Studio）
3. Windows 剪映专业版
4. Python 3.8 以上，推荐 Python 3.11/3.12
   安装 Python 时请勾选“Add Python to PATH”。
5. 首次安装 Python 依赖时需要联网。

安装
----
1. 解压整个 ZIP，不要只单独打开其中一个文件。
2. 双击“安装.cmd”或“Install.cmd”。
3. 安装成功后，完全退出并重新启动 DaVinci Resolve。

使用
----
1. 在 DaVinci Resolve 中打开目标时间线。
2. 选择：Workspace > Scripts > Utility > Current Timeline to Jianying
3. 修改剪映草稿名称，点击“开始转换”。
4. 等待进度窗口完成；剪映会自动启动。

转换范围
--------
- 保留视频和音频轨道、片段位置、源入点/出点。
- 保留基础缩放、位置、旋转和透明度。
- 会创建一条空的剪映主轨，避免达芬奇 V1 被剪映主轨磁吸而错位。
- 直接读取达芬奇当前时间线分辨率，支持 9:16 等竖屏时间线。
- 识别视频的 90°/270° 旋转元数据，使剪映选框贴合实际画面。
- 源素材会同步出现在剪映左侧素材库中，并按文件去重。
- 视频内嵌音频保持在视频片段中，可在剪映里按需“分离音频”。
- Resolve 调色节点、Fusion、第三方插件和复杂特效不会完整迁移。

卸载
----
双击“卸载.cmd”。卸载不会删除已经生成的剪映草稿。

开源依赖
--------
本工具内含 pyJianYingDraft 0.2.6：
https://github.com/GuanYixuan/pyJianYingDraft
其许可证副本位于 THIRD_PARTY_LICENSES 文件夹。
