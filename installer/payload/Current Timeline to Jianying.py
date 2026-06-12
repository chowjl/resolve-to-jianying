# -*- coding: utf-8 -*-
"""DaVinci Resolve menu script: export current timeline to a Jianying draft."""

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
CONVERTER = os.path.join(TOOL_ROOT, "xml_to_jianying_draft.py")
WORKER = os.path.join(TOOL_ROOT, "resolve_to_jianying_worker.py")
LOG_FILE = os.path.join(TOOL_ROOT, "resolve_to_jianying.log")


def message(title, body, error=False):
    ctypes.windll.user32.MessageBoxW(0, body, title, 0x10 if error else 0x40)


def log(body):
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + body + "\n")


def safe_name(value):
    value = re.sub(r'[\\/:*?"<>|]+', "_", value or "").strip(" .")
    return value[:80] or "Resolve Timeline"


def load_config():
    if not os.path.isfile(CONFIG_FILE):
        raise RuntimeError("工具配置不存在，请重新运行安装程序。")
    with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    required = ("python_exe", "jianying_exe", "draft_root")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError("工具配置不完整：%s" % ", ".join(missing))
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


def ask_name(default_name):
    fusion_app = globals().get("fusion") or globals().get("fu")
    bmd_app = globals().get("bmd")
    if not fusion_app or not bmd_app:
        raise RuntimeError("当前 Resolve 脚本环境未提供原生 UI 接口。")

    ui = fusion_app.UIManager
    dispatcher = bmd_app.UIDispatcher(ui)
    window_id = "com.xiaoer.resolveToJianying.options"
    old = ui.FindWindow(window_id)
    if old:
        old.Hide()

    window = dispatcher.AddWindow(
        {
            "ID": window_id,
            "Geometry": [560, 300, 560, 180],
            "WindowTitle": "DaVinci Resolve → 剪映",
        },
        ui.VGroup({"Spacing": 10, "Margin": 18}, [
            ui.Label({"Text": "剪映草稿名称：", "Weight": 0}),
            ui.LineEdit({"ID": "DraftName", "Text": default_name, "Weight": 0}),
            ui.Label({"Text": "将保留空的剪映主轨，达芬奇视频轨会放入普通副轨。", "Weight": 0}),
            ui.HGroup({"Weight": 0}, [
                ui.HGap(0, 1),
                ui.Button({"ID": "Cancel", "Text": "取消"}),
                ui.Button({"ID": "Start", "Text": "开始转换"}),
            ]),
        ]),
    )
    result = {"name": None}

    def close(_event):
        dispatcher.ExitLoop()

    def start(_event):
        result["name"] = safe_name(window.Find("DraftName").Text)
        dispatcher.ExitLoop()

    window.On[window_id].Close = close
    window.On["Cancel"].Clicked = close
    window.On["Start"].Clicked = start
    window.Show()
    dispatcher.RunLoop()
    window.Hide()
    return result["name"]


def main():
    config = load_config()
    resolved = get_resolve()
    if not resolved:
        raise RuntimeError("无法连接 DaVinci Resolve。")
    project = resolved.GetProjectManager().GetCurrentProject()
    if not project:
        raise RuntimeError("当前没有打开的达芬奇项目。")
    timeline = project.GetCurrentTimeline()
    if not timeline:
        raise RuntimeError("当前没有打开的时间线。")

    settings = timeline.GetSetting() or {}
    width = settings.get("timelineResolutionWidth") or project.GetSetting("timelineResolutionWidth")
    height = settings.get("timelineResolutionHeight") or project.GetSetting("timelineResolutionHeight")
    try:
        width, height = int(float(width)), int(float(height))
    except (TypeError, ValueError):
        width, height = 0, 0

    default_name = "%s-达芬奇导入-%s" % (safe_name(timeline.GetName()), time.strftime("%m%d-%H%M%S"))
    draft_name = ask_name(default_name)
    if not draft_name:
        return

    temp_dir = Path(tempfile.gettempdir()) / "XiaoerResolveToJianying"
    temp_dir.mkdir(parents=True, exist_ok=True)
    xml_path = temp_dir / (draft_name + ".xml")
    log("export start: %s" % timeline.GetName())
    if not timeline.Export(str(xml_path), resolved.EXPORT_FCP_7_XML):
        raise RuntimeError("达芬奇导出 FCP 7 XML 失败。")

    command = [
        config["python_exe"], WORKER,
        "--xml", str(xml_path),
        "--converter", CONVERTER,
        "--draft-root", config["draft_root"],
        "--name", draft_name,
        "--jianying", config["jianying_exe"],
        "--log", LOG_FILE,
    ]
    if width > 0 and height > 0:
        command.extend(["--width", str(width), "--height", str(height)])
        log("timeline resolution: %sx%s" % (width, height))
    subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


try:
    main()
except Exception as exc:
    log("ERROR: %s" % exc)
    message("达芬奇 → 剪映：转换失败", str(exc), error=True)
