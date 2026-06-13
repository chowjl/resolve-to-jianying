# -*- coding: utf-8 -*-
"""External progress UI for Resolve-to-Jianying conversion."""

import argparse
import json
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True)
    parser.add_argument("--converter", required=True)
    parser.add_argument("--draft-root", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--jianying", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--subtitles")
    args = parser.parse_args()

    started = time.perf_counter()
    root = tk.Tk()
    root.title("DaVinci Resolve → 剪映")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=22)
    frame.grid(row=0, column=0, sticky="nsew")
    ttk.Label(frame, text="正在生成剪映草稿", font=("Microsoft YaHei UI", 13, "bold")).grid(
        row=0, column=0, sticky="w"
    )
    status = tk.StringVar(value="正在读取时间线并创建轨道…")
    ttk.Label(frame, textvariable=status, width=50).grid(row=1, column=0, sticky="w", pady=(12, 10))
    progress = ttk.Progressbar(frame, mode="indeterminate", length=400)
    progress.grid(row=2, column=0, sticky="ew")
    ttk.Label(frame, text="可以继续使用 DaVinci Resolve", foreground="#666666").grid(
        row=3, column=0, sticky="w", pady=(10, 0)
    )
    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
    y = max(0, (root.winfo_screenheight() - root.winfo_reqheight()) // 3)
    root.geometry("+%d+%d" % (x, y))
    progress.start(12)

    state = {"process": None, "output": None, "error": None}

    def start_conversion():
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        command = [
            sys.executable,
            args.converter,
            args.xml,
            "--draft-root",
            args.draft_root,
            "--name",
            args.name,
        ]
        if args.width and args.height:
            command.extend(["--width", str(args.width), "--height", str(args.height)])
        if args.subtitles:
            command.extend(["--subtitles", args.subtitles])
        state["process"] = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        root.after(250, poll)

    def poll():
        process = state["process"]
        if process.poll() is None:
            root.after(250, poll)
            return
        stdout, stderr = process.communicate()
        progress.stop()
        try:
            Path(args.xml).unlink(missing_ok=True)
            if args.subtitles:
                Path(args.subtitles).unlink(missing_ok=True)
        except OSError:
            pass
        if process.returncode != 0:
            error = stderr.strip() or stdout.strip() or "转换器运行失败。"
            with open(args.log, "a", encoding="utf-8") as handle:
                handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + "ERROR: " + error + "\n")
            root.withdraw()
            messagebox.showerror("达芬奇 → 剪映：转换失败", error, parent=root)
            root.destroy()
            return

        report = json.loads(stdout)
        elapsed = time.perf_counter() - started
        with open(args.log, "a", encoding="utf-8") as handle:
            handle.write(
                time.strftime("%Y-%m-%d %H:%M:%S ")
                + "convert done: "
                + json.dumps(report, ensure_ascii=False)
                + "\n"
            )
        status.set("转换完成，正在启动剪映…")
        root.update_idletasks()
        if os.path.isfile(args.jianying):
            subprocess.Popen([args.jianying], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        root.withdraw()
        skipped_adjustments = report.get("skipped_adjustment_clips", 0)
        warning_note = ""
        if skipped_adjustments:
            warning_note = "\n\n提示：已跳过 %s 个达芬奇调整图层，其他内容已正常导入。" % skipped_adjustments
        disabled_video = report.get("disabled_video_clips", 0)
        disabled_audio = report.get("disabled_audio_clips", 0)
        if disabled_video or disabled_audio:
            warning_note += "\n已保留禁用片段：视频 %s 个、音频 %s 个（保持静音/不可见）。" % (
                disabled_video, disabled_audio
            )
        retimed_clips = report.get("retimed_clips", 0)
        if retimed_clips:
            warning_note += "\n已转换 %s 个固定变速视频/音频片段。" % retimed_clips
        other_warnings = len(report.get("warnings") or [])
        if other_warnings:
            warning_note += "\n另有 %s 个不支持的片段已跳过，详情已写入日志。" % other_warnings
        messagebox.showinfo(
            "达芬奇 → 剪映",
            "转换完成！\n\n草稿：%s\n视频片段：%s\n音频片段：%s\n字幕：%s\n耗时：%.1f 秒%s\n\n已启动剪映，请在草稿列表中打开该项目。"
            % (
                args.name,
                report.get("video_clips", 0),
                report.get("audio_clips", 0),
                report.get("subtitle_clips", 0),
                elapsed,
                warning_note,
            ),
            parent=root,
        )
        root.destroy()

    root.after(100, start_conversion)
    root.mainloop()


if __name__ == "__main__":
    main()
