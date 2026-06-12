# -*- coding: utf-8 -*-
"""DaVinci Resolve menu script: import a readable Jianying timeline."""

from __future__ import print_function

import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


TOOL_ROOT = os.path.join(
    os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")),
    "Blackmagic Design", "DaVinci Resolve", "Support", "XiaoerTools",
)
CONFIG_FILE = os.path.join(TOOL_ROOT, "config.json")
CONVERTER = os.path.join(TOOL_ROOT, "jianying_to_resolve_xml.py")
DECRYPTOR = os.path.join(TOOL_ROOT, "jy-draftc", "jy-draftc.exe")
LOG_FILE = os.path.join(TOOL_ROOT, "jianying_to_resolve.log")


def message(title, body, error=False):
    ctypes.windll.user32.MessageBoxW(0, body, title, 0x10 if error else 0x40)


def log(body):
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + body + "\n")


def safe_name(value):
    value = re.sub(r'[\\/:*?"<>|]+', "_", value or "").strip(" .")
    return value[:80] or "Jianying Timeline"


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        raise RuntimeError("工具配置不存在，请重新运行安装程序。")
    with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    for key in ("python_exe", "draft_root"):
        if not config.get(key):
            raise RuntimeError("工具配置不完整：%s" % key)
    if not os.path.isfile(CONVERTER):
        raise RuntimeError("剪映导入组件不存在，请重新运行安装程序。")
    return config


def get_resolve():
    resolved = globals().get("resolve")
    if resolved:
        return resolved
    fusion_app = globals().get("fusion") or globals().get("fu")
    if fusion_app:
        try:
            resolved = fusion_app.GetResolve()
            if resolved:
                return resolved
        except Exception:
            pass
    module_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
    if module_path not in sys.path:
        sys.path.append(module_path)
    import DaVinciResolveScript as dvr_script
    return dvr_script.scriptapp("Resolve")


def run_converter(config, arguments):
    command = [config["python_exe"], CONVERTER] + arguments
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "剪映时间线转换失败。")
    return json.loads(process.stdout)


def choose_draft_folder(config):
    fusion_app = globals().get("fusion") or globals().get("fu")
    if not fusion_app:
        raise RuntimeError("当前 Resolve 脚本环境未提供文件夹选择接口。")
    return fusion_app.RequestDir(config["draft_root"])


def ask_options(config, draft_path):
    fusion_app = globals().get("fusion") or globals().get("fu")
    bmd_app = globals().get("bmd")
    if not fusion_app or not bmd_app:
        raise RuntimeError("当前 Resolve 脚本环境未提供原生 UI 接口。")

    ui = fusion_app.UIManager
    dispatcher = bmd_app.UIDispatcher(ui)
    window_id = "com.xiaoer.jianyingToResolve.options"
    old = ui.FindWindow(window_id)
    if old:
        old.Hide()
    draft_name = os.path.basename(os.path.normpath(draft_path))
    window = dispatcher.AddWindow(
        {
            "ID": window_id,
            "Geometry": [500, 260, 700, 250],
            "WindowTitle": "剪映 → DaVinci Resolve",
        },
        ui.VGroup({"Spacing": 10, "Margin": 18}, [
            ui.Label({"Text": "剪映草稿文件夹：", "Weight": 0}),
            ui.HGroup({"Weight": 0}, [
                ui.LineEdit({"ID": "DraftPath", "Text": draft_path, "Weight": 1}),
                ui.Button({"ID": "Browse", "Text": "浏览...", "Weight": 0}),
            ]),
            ui.Label({"Text": "已自动定位到剪映草稿目录，可点击浏览重新选择。", "Weight": 0}),
            ui.Label({"Text": "导入后的达芬奇时间线名称：", "Weight": 0}),
            ui.LineEdit({"ID": "TimelineName", "Text": safe_name(draft_name), "Weight": 0}),
            ui.Label({"ID": "Status", "Text": "准备导入", "Weight": 0}),
            ui.HGroup({"Weight": 0}, [
                ui.HGap(0, 1),
                ui.Button({"ID": "Cancel", "Text": "取消"}),
                ui.Button({"ID": "Start", "Text": "导入时间线"}),
            ]),
        ]),
    )
    result = {"draft": None, "name": None, "window": window}

    def close(_event):
        dispatcher.ExitLoop()

    def browse(_event):
        selected = fusion_app.RequestDir(config["draft_root"])
        if selected:
            window.Find("DraftPath").Text = selected

    def start(_event):
        result["draft"] = window.Find("DraftPath").Text.strip()
        result["name"] = safe_name(window.Find("TimelineName").Text)
        dispatcher.ExitLoop()

    window.On[window_id].Close = close
    window.On["Cancel"].Clicked = close
    window.On["Browse"].Clicked = browse
    window.On["Start"].Clicked = start
    window.Show()
    dispatcher.RunLoop()
    window.Hide()
    return result["draft"], result["name"]


def main():
    config = load_config()
    resolved = get_resolve()
    if not resolved:
        raise RuntimeError("无法连接 DaVinci Resolve。")
    project = resolved.GetProjectManager().GetCurrentProject()
    if not project:
        raise RuntimeError("请先在 DaVinci Resolve 中打开一个项目。")

    draft_path = choose_draft_folder(config)
    if not draft_path:
        return
    draft_path, timeline_name = ask_options(config, draft_path)
    if not draft_path:
        return
    if not os.path.isdir(draft_path):
        raise RuntimeError("剪映草稿文件夹不存在：%s" % draft_path)

    temp_dir = Path(tempfile.gettempdir()) / "XiaoerJianyingToResolve"
    temp_dir.mkdir(parents=True, exist_ok=True)
    xml_path = temp_dir / (safe_name(timeline_name) + ".xml")
    log("convert start: %s" % draft_path)
    report = run_converter(
        config,
        [
            "--draft", draft_path,
            "--output", str(xml_path),
            "--name", timeline_name,
            "--decryptor", DECRYPTOR,
        ],
    )

    media_pool = project.GetMediaPool()
    timeline = media_pool.ImportTimelineFromFile(
        str(xml_path),
        {"timelineName": timeline_name, "importSourceClips": True},
    )
    if not timeline:
        raise RuntimeError("DaVinci Resolve 未能导入生成的 XML 时间线。")
    project.SetCurrentTimeline(timeline)
    resolved.GetProjectManager().SaveProject()
    log("import done: " + json.dumps(report, ensure_ascii=False))

    warning = ""
    if report.get("missing_media"):
        warning = "\n\n有 %d 个素材路径不存在，需在达芬奇中重新链接。" % len(report["missing_media"])
    message(
        "剪映 → DaVinci Resolve",
        "导入完成。\n\n时间线：%s\n视频片段：%s\n音频片段：%s\n画布：%sx%s  %s fps%s"
        % (
            timeline_name,
            report.get("video_clips", 0),
            report.get("audio_clips", 0),
            report.get("width"), report.get("height"), report.get("fps"), warning,
        ),
    )


try:
    main()
except Exception as exc:
    log("ERROR: %s" % exc)
    message("剪映 → DaVinci Resolve：导入失败", str(exc), error=True)
