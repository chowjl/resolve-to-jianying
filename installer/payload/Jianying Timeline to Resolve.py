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


def srt_time(frame, fps):
    milliseconds = int(round(frame * 1000.0 / fps))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, milliseconds)


def write_srt(path, subtitles, fps):
    lines = []
    for index, item in enumerate(subtitles, 1):
        lines.extend([
            str(index),
            "%s --> %s" % (srt_time(item["start_frame"], fps), srt_time(item["end_frame"], fps)),
            item["text"],
            "",
        ])
    Path(path).write_text("\n".join(lines), encoding="utf-8-sig")


def unique_timeline_name(project, requested):
    existing = set()
    for index in range(1, int(project.GetTimelineCount() or 0) + 1):
        timeline = project.GetTimelineByIndex(index)
        if timeline:
            existing.add(timeline.GetName())
    if requested not in existing:
        return requested
    number = 2
    while "%s (%d)" % (requested, number) in existing:
        number += 1
    return "%s (%d)" % (requested, number)


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
            "Geometry": [460, 190, 760, 360],
            "WindowTitle": "剪映 → DaVinci Resolve",
        },
        ui.VGroup({"Spacing": 8, "Margin": 18}, [
            ui.Label({"Text": "剪映草稿文件夹：", "Weight": 0}),
            ui.HGroup({"Weight": 0}, [
                ui.LineEdit({"ID": "DraftPath", "Text": draft_path, "Weight": 1}),
                ui.Button({"ID": "Browse", "Text": "浏览...", "Weight": 0, "MinimumSize": [110, 32]}),
                ui.HGap(12, 0),
            ]),
            ui.Label({"Text": "已自动定位到剪映草稿目录，可点击浏览重新选择。", "Weight": 0}),
            ui.Label({"Text": "导入后的达芬奇时间线名称：", "Weight": 0}),
            ui.LineEdit({"ID": "TimelineName", "Text": safe_name(draft_name), "Weight": 0}),
            ui.Label({"ID": "Status", "Text": "准备导入", "Weight": 0}),
            ui.VGap(4),
            ui.HGroup({"Weight": 0}, [
                ui.HGap(0, 1),
                ui.Button({"ID": "Cancel", "Text": "取消", "MinimumSize": [130, 34]}),
                ui.Button({"ID": "Start", "Text": "导入时间线", "MinimumSize": [150, 34]}),
                ui.HGap(0, 1),
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

    log("convert start: %s" % draft_path)
    plan = run_converter(
        config,
        [
            "--draft", draft_path,
            "--name", timeline_name,
            "--decryptor", DECRYPTOR,
            "--plan",
        ],
    )

    media_pool = project.GetMediaPool()
    requested_name = timeline_name
    timeline_name = unique_timeline_name(project, requested_name)
    if timeline_name != requested_name:
        log("timeline renamed to avoid duplicate: %s" % timeline_name)
    project.SetSetting("timelineFrameRate", str(plan["fps"]))
    project.SetSetting("timelineResolutionWidth", str(plan["width"]))
    project.SetSetting("timelineResolutionHeight", str(plan["height"]))
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if not timeline:
        raise RuntimeError("DaVinci Resolve 未能创建新时间线：%s" % timeline_name)
    project.SetCurrentTimeline(timeline)
    timeline.SetStartTimecode("00:00:00:00")
    timeline.SetSetting("timelineFrameRate", str(plan["fps"]))
    timeline.SetSetting("timelineResolutionWidth", str(plan["width"]))
    timeline.SetSetting("timelineResolutionHeight", str(plan["height"]))
    timeline_start = timeline.GetStartFrame()

    imported = {}
    def media_item(path):
        key = os.path.normcase(os.path.abspath(path))
        if key not in imported:
            items = resolved.GetMediaStorage().AddItemListToMediaPool([path]) or []
            if not items:
                raise RuntimeError("无法导入素材：%s" % path)
            imported[key] = items[0]
        return imported[key]

    counts = {"video": 0, "audio": 0}
    track_indexes = {"video": 0, "audio": 0}
    for source_track in plan["tracks"]:
        track_type = source_track["type"]
        track_indexes[track_type] += 1
        track_index = track_indexes[track_type]
        while timeline.GetTrackCount(track_type) < track_index:
            if not timeline.AddTrack(track_type):
                raise RuntimeError("无法创建%s轨道 %d。" % ("视频" if track_type == "video" else "音频", track_index))
        for segment in source_track["segments"]:
            item = media_item(segment["path"])
            clip_info = {
                "mediaPoolItem": item,
                "startFrame": segment["start_frame"],
                "endFrame": segment["end_frame"],
                "mediaType": 1 if track_type == "video" else 2,
                "trackIndex": track_index,
                "recordFrame": timeline_start + segment["record_frame"],
            }
            if not media_pool.AppendToTimeline([clip_info]):
                raise RuntimeError("无法放置素材：%s" % segment["path"])
            counts[track_type] += 1

        if track_type == "video":
            audible = [segment for segment in source_track["segments"] if segment.get("volume", 1) > 0]
            if audible:
                track_indexes["audio"] += 1
                audio_index = track_indexes["audio"]
                while timeline.GetTrackCount("audio") < audio_index:
                    if not timeline.AddTrack("audio"):
                        raise RuntimeError("无法创建音频轨道 %d。" % audio_index)
                for segment in audible:
                    clip_info = {
                        "mediaPoolItem": media_item(segment["path"]),
                        "startFrame": segment["start_frame"],
                        "endFrame": segment["end_frame"],
                        "mediaType": 2,
                        "trackIndex": audio_index,
                        "recordFrame": timeline_start + segment["record_frame"],
                    }
                    if not media_pool.AppendToTimeline([clip_info]):
                        raise RuntimeError("无法放置素材音频：%s" % segment["path"])
                    counts["audio"] += 1

    subtitle_count = len(plan.get("subtitles") or [])
    subtitle_added = 0
    subtitle_note = ""
    if subtitle_count:
        subtitle_dir = Path(tempfile.gettempdir()) / "XiaoerJianyingToResolve"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = subtitle_dir / (safe_name(timeline_name) + ".srt")
        write_srt(subtitle_path, plan["subtitles"], float(plan["fps"]))
        timeline.SetCurrentTimecode("00:00:00:00")
        log("subtitle SRT generated: %s" % subtitle_path)
        subtitle_note = "\n\n字幕已导出为 SRT，请在 Resolve 中使用 File > Import > Subtitle 导入：\n%s" % subtitle_path

    resolved.GetProjectManager().SaveProject()
    log("import done: " + json.dumps(plan, ensure_ascii=False))

    warning = ""
    if plan.get("missing_media"):
        warning = "\n\n有 %d 个素材路径不存在，需在达芬奇中重新链接。" % len(plan["missing_media"])
    message(
        "剪映 → DaVinci Resolve",
        "导入完成。\n\n时间线：%s\n视频片段：%s\n音频片段：%s\n字幕：%s/%s\n画布：%sx%s  %s fps%s%s"
        % (
            timeline_name,
            counts["video"],
            counts["audio"],
            subtitle_added,
            subtitle_count,
            plan.get("width"), plan.get("height"), plan.get("fps"), warning,
            subtitle_note,
        ),
    )


try:
    main()
except Exception as exc:
    log("ERROR: %s" % exc)
    message("剪映 → DaVinci Resolve：导入失败", str(exc), error=True)
