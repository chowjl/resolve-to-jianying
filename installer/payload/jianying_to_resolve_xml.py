# -*- coding: utf-8 -*-
"""Convert a readable Jianying timeline draft to Final Cut Pro 7 XML."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


MICROSECONDS = 1_000_000

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _read_timeline_json(path: Path, decryptor: Path | None) -> dict:
    try:
        return _read_json(path)
    except (UnicodeDecodeError, json.JSONDecodeError):
        if not decryptor or not decryptor.is_file():
            raise ValueError(
                "该草稿已加密，但解密组件未安装。请重新运行最新版安装程序。"
            )
        output = Path(tempfile.gettempdir()) / (
            "XiaoerJianyingToResolve-%s.json" % abs(hash(str(path)))
        )
        output.unlink(missing_ok=True)
        process = subprocess.run(
            [str(decryptor), "-d", str(path), str(output)],
            cwd=str(decryptor.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if process.returncode != 0 or not output.is_file():
            detail = process.stderr.strip() or process.stdout.strip()
            raise ValueError("无法解密剪映草稿。%s" % ("\n" + detail if detail else ""))
        try:
            return _read_json(output)
        finally:
            output.unlink(missing_ok=True)


def _timeline_file(draft_dir: Path) -> Path:
    layout_path = draft_dir / "timeline_layout.json"
    timeline_root = draft_dir / "Timelines"
    if layout_path.is_file():
        try:
            timeline_id = _read_json(layout_path).get("activeTimeline")
            candidate = timeline_root / str(timeline_id) / "draft_content.json"
            if timeline_id and candidate.is_file():
                return candidate
        except (OSError, ValueError, TypeError):
            pass

    candidates = sorted(
        timeline_root.glob("*/draft_content.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    fallback = draft_dir / "draft_content.json"
    if fallback.is_file():
        return fallback
    raise ValueError("未找到剪映时间线文件。")


def load_draft(draft_dir: Path, decryptor: Path | None = None) -> tuple[Path, dict]:
    timeline_path = _timeline_file(draft_dir)
    try:
        content = _read_timeline_json(timeline_path, decryptor)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("剪映草稿内容不是有效 JSON。") from exc
    if not isinstance(content.get("tracks"), list):
        raise ValueError("剪映时间线缺少轨道数据。")
    return timeline_path, content


def scan_drafts(draft_root: Path, decryptor: Path | None = None) -> list[dict]:
    results = []
    if not draft_root.is_dir():
        return results
    for draft_dir in draft_root.iterdir():
        if not draft_dir.is_dir():
            continue
        try:
            timeline_path, content = load_draft(draft_dir, decryptor)
        except (OSError, ValueError):
            continue
        nonempty = [track for track in content.get("tracks", []) if track.get("segments")]
        if not nonempty:
            continue
        results.append(
            {
                "name": draft_dir.name,
                "path": str(draft_dir),
                "timeline_file": str(timeline_path),
                "modified": timeline_path.stat().st_mtime,
                "fps": float(content.get("fps") or 30),
                "width": int((content.get("canvas_config") or {}).get("width") or 1920),
                "height": int((content.get("canvas_config") or {}).get("height") or 1080),
                "tracks": len(nonempty),
                "segments": sum(len(track.get("segments") or []) for track in nonempty),
                "locked": (draft_dir / ".locked").exists(),
            }
        )
    return sorted(results, key=lambda item: item["modified"], reverse=True)


def _rate(parent: ET.Element, fps: float) -> None:
    rate = ET.SubElement(parent, "rate")
    rounded = int(round(fps))
    ntsc = abs(fps - rounded * 1000 / 1001) < 0.02
    ET.SubElement(rate, "timebase").text = str(rounded)
    ET.SubElement(rate, "ntsc").text = "TRUE" if ntsc else "FALSE"


def _frames(microseconds: float, fps: float) -> int:
    return int(round(float(microseconds or 0) * fps / MICROSECONDS))


def _path_url(path: str) -> str:
    normalized = os.path.abspath(path).replace("\\", "/")
    return "file://localhost/" + urllib.parse.quote(normalized, safe="/:~")


def _material_maps(content: dict) -> tuple[dict, dict]:
    materials = content.get("materials") or {}
    videos = {}
    audios = {}
    for item in materials.get("videos") or []:
        if item.get("id") and item.get("path"):
            videos.setdefault(item["id"], item)
    for item in materials.get("audios") or []:
        if item.get("id") and item.get("path"):
            audios.setdefault(item["id"], item)
    return videos, audios


def _file_node(
    clipitem: ET.Element,
    material: dict,
    file_id: str,
    fps: float,
    include_audio: bool,
    media_kind: str,
) -> None:
    file_node = ET.SubElement(clipitem, "file", {"id": file_id})
    duration = max(1, _frames(material.get("duration", 0), fps))
    ET.SubElement(file_node, "duration").text = str(duration)
    _rate(file_node, fps)
    name = material.get("material_name") or material.get("name") or Path(material["path"]).name
    ET.SubElement(file_node, "name").text = name
    ET.SubElement(file_node, "pathurl").text = _path_url(material["path"])
    media = ET.SubElement(file_node, "media")
    if media_kind == "video":
        video = ET.SubElement(media, "video")
        ET.SubElement(video, "duration").text = str(duration)
        sample = ET.SubElement(video, "samplecharacteristics")
        ET.SubElement(sample, "width").text = str(int(material.get("width") or 1920))
        ET.SubElement(sample, "height").text = str(int(material.get("height") or 1080))
    if include_audio or media_kind == "audio":
        audio = ET.SubElement(media, "audio")
        ET.SubElement(audio, "channelcount").text = "2"


def _clipitem(
    track_node: ET.Element,
    segment: dict,
    material: dict,
    clip_id: str,
    file_id: str,
    fps: float,
    known_files: set[str],
    include_audio: bool,
    media_kind: str,
) -> None:
    target = segment.get("target_timerange") or {}
    source = segment.get("source_timerange") or {}
    record_start = _frames(target.get("start", 0), fps)
    record_duration = max(1, _frames(target.get("duration", 0), fps))
    source_start = _frames(source.get("start", 0), fps)
    source_duration = _frames(source.get("duration", 0), fps)
    if source_duration <= 0:
        source_duration = max(1, int(round(record_duration * float(segment.get("speed") or 1))))

    node = ET.SubElement(track_node, "clipitem", {"id": clip_id})
    name = material.get("material_name") or material.get("name") or Path(material["path"]).name
    ET.SubElement(node, "name").text = name
    ET.SubElement(node, "duration").text = str(max(1, _frames(material.get("duration", 0), fps)))
    _rate(node, fps)
    ET.SubElement(node, "start").text = str(record_start)
    ET.SubElement(node, "end").text = str(record_start + record_duration)
    ET.SubElement(node, "enabled").text = "TRUE"
    ET.SubElement(node, "in").text = str(source_start)
    ET.SubElement(node, "out").text = str(source_start + source_duration)
    if file_id in known_files:
        ET.SubElement(node, "file", {"id": file_id})
    else:
        _file_node(node, material, file_id, fps, include_audio, media_kind)
        known_files.add(file_id)
    source_track = ET.SubElement(node, "sourcetrack")
    ET.SubElement(source_track, "mediatype").text = media_kind
    ET.SubElement(source_track, "trackindex").text = "1"


def build_xml(
    draft_dir: Path,
    output: Path,
    timeline_name: str | None = None,
    decryptor: Path | None = None,
) -> dict:
    timeline_path, content = load_draft(draft_dir, decryptor)
    fps = float(content.get("fps") or 30)
    canvas = content.get("canvas_config") or {}
    width = int(canvas.get("width") or 1920)
    height = int(canvas.get("height") or 1080)
    duration = max(1, _frames(content.get("duration", 0), fps))
    videos, audios = _material_maps(content)
    name = timeline_name or draft_dir.name

    root = ET.Element("xmeml", {"version": "5"})
    sequence = ET.SubElement(root, "sequence")
    ET.SubElement(sequence, "name").text = name
    ET.SubElement(sequence, "duration").text = str(duration)
    _rate(sequence, fps)
    media = ET.SubElement(sequence, "media")
    video_root = ET.SubElement(media, "video")
    fmt = ET.SubElement(video_root, "format")
    sample = ET.SubElement(fmt, "samplecharacteristics")
    _rate(sample, fps)
    ET.SubElement(sample, "width").text = str(width)
    ET.SubElement(sample, "height").text = str(height)
    ET.SubElement(sample, "anamorphic").text = "FALSE"
    ET.SubElement(sample, "pixelaspectratio").text = "square"
    audio_root = ET.SubElement(media, "audio")
    audio_format = ET.SubElement(audio_root, "format")
    audio_sample = ET.SubElement(audio_format, "samplecharacteristics")
    ET.SubElement(audio_sample, "depth").text = "16"
    ET.SubElement(audio_sample, "samplerate").text = "48000"

    known_files: set[str] = set()
    video_count = 0
    audio_count = 0
    missing = set()
    clip_number = 0
    tracks = [track for track in content.get("tracks", []) if track.get("segments")]
    for track in tracks:
        track_type = track.get("type")
        if track_type not in ("video", "audio"):
            continue
        target_root = video_root if track_type == "video" else audio_root
        track_node = ET.SubElement(target_root, "track")
        material_map = videos if track_type == "video" else audios
        for segment in track.get("segments") or []:
            material = material_map.get(segment.get("material_id"))
            if not material:
                continue
            if not Path(material["path"]).is_file():
                missing.add(material["path"])
            clip_number += 1
            _clipitem(
                track_node,
                segment,
                material,
                "clip-%d" % clip_number,
                "file-%s" % segment["material_id"],
                fps,
                known_files,
                True,
                track_type,
            )
            if track_type == "video":
                video_count += 1
            else:
                audio_count += 1

        if track_type == "video":
            audible_segments = [
                segment for segment in (track.get("segments") or [])
                if float(segment.get("volume", 1) or 0) > 0
            ]
            if not audible_segments:
                continue
            embedded_audio_track = ET.SubElement(audio_root, "track")
            for segment in audible_segments:
                material = videos.get(segment.get("material_id"))
                if not material:
                    continue
                clip_number += 1
                _clipitem(
                    embedded_audio_track,
                    segment,
                    material,
                    "clip-%d" % clip_number,
                    "file-%s" % segment["material_id"],
                    fps,
                    known_files,
                    True,
                    "audio",
                )
                audio_count += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="    ")
    with output.open("wb") as handle:
        handle.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n')
        ET.ElementTree(root).write(handle, encoding="utf-8", xml_declaration=False)

    return {
        "draft": draft_dir.name,
        "timeline_file": str(timeline_path),
        "output": str(output),
        "timeline_name": name,
        "fps": fps,
        "width": width,
        "height": height,
        "video_tracks": len(video_root.findall("track")),
        "audio_tracks": len(audio_root.findall("track")),
        "video_clips": video_count,
        "audio_clips": audio_count,
        "missing_media": sorted(missing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Jianying draft to Resolve FCP 7 XML.")
    parser.add_argument("--draft-root", type=Path)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--decryptor", type=Path)
    args = parser.parse_args()
    try:
        if args.list:
            if not args.draft_root:
                raise ValueError("--draft-root is required with --list")
            result = scan_drafts(args.draft_root, args.decryptor)
        else:
            if not args.draft or not args.output:
                raise ValueError("--draft and --output are required")
            result = build_xml(args.draft, args.output, args.name, args.decryptor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
