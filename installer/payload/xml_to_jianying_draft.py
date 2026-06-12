#!/usr/bin/env python3
"""Convert Resolve/Premiere FCP 7 XML (xmeml) into a Jianying draft."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
for vendored in (HERE / "vendor", HERE / "pyJianYingDraft"):
    if vendored.exists():
        sys.path.insert(0, str(vendored))

import pyJianYingDraft as draft  # noqa: E402
from pyJianYingDraft import ClipSettings, Timerange  # noqa: E402
from pyJianYingDraft import VideoMaterial  # noqa: E402
from pymediainfo import MediaInfo  # noqa: E402


def node_text(node: ET.Element | None, default: str = "") -> str:
    return default if node is None or node.text is None else node.text.strip()


def xml_media_path(pathurl: str) -> str:
    value = urllib.parse.unquote(pathurl)
    for prefix in ("file://localhost/", "file:///"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.replace("/", os.sep)


def effective_fps(rate: ET.Element | None) -> float:
    if rate is None:
        return 30.0
    timebase = float(node_text(rate.find("timebase"), "30"))
    return timebase * 1000.0 / 1001.0 if node_text(rate.find("ntsc")).upper() == "TRUE" else timebase


def frames_to_us(frames: int, fps: float) -> int:
    return round(frames * 1_000_000 / fps)


def parameter(effect: ET.Element, parameter_id: str) -> ET.Element | None:
    for item in effect.findall("parameter"):
        if node_text(item.find("parameterid")) == parameter_id:
            return item.find("value")
    return None


def clip_settings(clip: ET.Element) -> ClipSettings:
    scale = 1.0
    rotation = 0.0
    transform_x = 0.0
    transform_y = 0.0
    alpha = 1.0

    for effect in clip.findall("filter/effect"):
        effect_id = node_text(effect.find("effectid"))
        if effect_id == "basic":
            value = parameter(effect, "scale")
            if value is not None:
                scale = float(node_text(value, "100")) / 100.0
            value = parameter(effect, "rotation")
            if value is not None:
                rotation = float(node_text(value, "0"))
            value = parameter(effect, "center")
            if value is not None:
                # Resolve writes offsets around (0, 0); Jianying uses half-canvas units.
                transform_x = float(node_text(value.find("horiz"), "0"))
                transform_y = -float(node_text(value.find("vert"), "0"))
        elif effect_id == "opacity":
            value = parameter(effect, "opacity")
            if value is not None:
                alpha = float(node_text(value, "100")) / 100.0

    return ClipSettings(
        alpha=max(0.0, min(1.0, alpha)),
        rotation=rotation,
        scale_x=scale,
        scale_y=scale,
        transform_x=transform_x,
        transform_y=transform_y,
    )


def file_map(root: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for file_node in root.findall(".//file"):
        file_id = file_node.get("id", "")
        pathurl = node_text(file_node.find("pathurl"))
        if file_id and pathurl:
            result[file_id] = xml_media_path(pathurl)
    return result


def clip_path(clip: ET.Element, files: dict[str, str]) -> str:
    file_node = clip.find("file")
    if file_node is None:
        raise ValueError(f"clip {clip.get('id')} has no file reference")
    pathurl = node_text(file_node.find("pathurl"))
    if pathurl:
        return xml_media_path(pathurl)
    file_id = file_node.get("id", "")
    if file_id in files:
        return files[file_id]
    raise ValueError(f"clip {clip.get('id')} references unknown file {file_id!r}")


def clip_timeranges(clip: ET.Element, default_fps: float) -> tuple[Timerange, Timerange]:
    fps = effective_fps(clip.find("rate")) if clip.find("rate") is not None else default_fps
    start = int(node_text(clip.find("start"), "0"))
    end = int(node_text(clip.find("end"), "0"))
    source_in = int(node_text(clip.find("in"), "0"))
    source_out = int(node_text(clip.find("out"), str(source_in + end - start)))
    target_start = frames_to_us(start, default_fps)
    target_end = frames_to_us(end, default_fps)
    source_start = frames_to_us(source_in, fps)
    source_end = frames_to_us(source_out, fps)
    target = Timerange(target_start, target_end - target_start)
    source = Timerange(source_start, source_end - source_start)
    return target, source


def clip_signature(clip: ET.Element, files: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        os.path.normcase(clip_path(clip, files)),
        node_text(clip.find("start")),
        node_text(clip.find("end")),
        node_text(clip.find("in")),
        node_text(clip.find("out")),
    )


def sequence_dimensions(sequence: ET.Element) -> tuple[int, int]:
    sample = sequence.find("media/video/format/samplecharacteristics")
    if sample is None:
        sample = sequence.find("media/video/track/clipitem/file/media/video/samplecharacteristics")
    width = int(node_text(sample.find("width") if sample is not None else None, "1920"))
    height = int(node_text(sample.find("height") if sample is not None else None, "1080"))
    return width, height


def create_video_material(path: str) -> VideoMaterial:
    material = VideoMaterial(path)
    try:
        info = MediaInfo.parse(path, mediainfo_options={"File_TestContinuousFileNames": "0"})
        if info.video_tracks:
            rotation = float(getattr(info.video_tracks[0], "rotation", 0) or 0)
            if round(abs(rotation)) % 180 == 90:
                material.width, material.height = material.height, material.width
    except Exception:
        pass
    return material


def update_draft_meta(draft_path: Path, draft_name: str, materials: dict[str, VideoMaterial], duration: int) -> None:
    meta_path = draft_path / "draft_meta_info.json"
    with meta_path.open("r", encoding="utf-8-sig") as handle:
        meta = json.load(handle)

    material_entries = []
    for path, material in sorted(materials.items()):
        material_entries.append({
            "extra_info": Path(path).name,
            "file_Path": str(Path(path).resolve()),
            "metetype": "photo" if material.material_type == "photo" else "video",
            "id": str(uuid.uuid4()),
        })

    groups = meta.setdefault("draft_materials", [])
    video_group = next((group for group in groups if group.get("type") == 0), None)
    if video_group is None:
        video_group = {"type": 0, "value": []}
        groups.insert(0, video_group)
    video_group["value"] = material_entries

    now_us = int(time.time() * 1_000_000)
    meta.update({
        "draft_name": draft_name,
        "draft_fold_path": str(draft_path.resolve()).replace("\\", "/"),
        "draft_root_path": str(draft_path.parent.resolve()).replace("\\", "/"),
        "tm_draft_create": meta.get("tm_draft_create") or now_us,
        "tm_draft_modified": now_us,
        "tm_duration": duration,
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def convert(
    input_xml: Path,
    draft_root: Path,
    draft_name: str,
    replace: bool,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
) -> dict:
    started = time.perf_counter()
    root = ET.parse(input_xml).getroot()
    if root.tag != "xmeml":
        raise ValueError("Only Final Cut Pro 7 XML/xmeml is currently supported")
    sequence = root.find("sequence")
    if sequence is None:
        raise ValueError("No sequence found in XML")

    fps = effective_fps(sequence.find("rate"))
    detected_width, detected_height = sequence_dimensions(sequence)
    width = canvas_width or detected_width
    height = canvas_height or detected_height
    files = file_map(root)
    missing = sorted({path for path in files.values() if not Path(path).exists()})
    if missing:
        raise FileNotFoundError("Missing media:\n" + "\n".join(missing))

    video_tracks = sequence.findall("media/video/track")
    audio_tracks = sequence.findall("media/audio/track")

    folder = draft.DraftFolder(str(draft_root))
    script = folder.create_draft(
        draft_name,
        width,
        height,
        fps=round(fps),
        maintrack_adsorb=False,
        allow_replace=replace,
    )
    draft_path = draft_root / draft_name

    audio_signatures = {
        clip_signature(clip, files)
        for track in audio_tracks
        for clip in track.findall("clipitem")
        if node_text(clip.find("enabled"), "TRUE").upper() != "FALSE"
    }
    video_signatures = {
        clip_signature(clip, files)
        for track in video_tracks
        for clip in track.findall("clipitem")
        if node_text(clip.find("enabled"), "TRUE").upper() != "FALSE"
    }
    embedded_audio_signatures = audio_signatures & video_signatures
    material_cache = {
        os.path.normcase(os.path.abspath(path)): create_video_material(path)
        for path in sorted(set(files.values()))
    }
    # Jianying always treats the first video track as the magnetic main track.
    # Keep that track empty so Resolve V1 is not pulled to time zero or rippled.
    script.add_track(draft.TrackType.video, "Jianying Main (empty)", relative_index=0)
    for index, _track in enumerate(video_tracks):
        script.add_track(draft.TrackType.video, f"V{index + 1}", relative_index=index + 1)
    for index, _track in enumerate(audio_tracks):
        script.add_track(draft.TrackType.audio, f"A{index + 1}", relative_index=index)

    video_count = 0
    audio_count = 0
    embedded_audio_count = 0
    warnings: list[str] = []

    for track_index, track in enumerate(video_tracks):
        for clip in track.findall("clipitem"):
            if node_text(clip.find("enabled"), "TRUE").upper() == "FALSE":
                continue
            try:
                target, source = clip_timeranges(clip, fps)
                has_embedded_audio = clip_signature(clip, files) in embedded_audio_signatures
                source_path = clip_path(clip, files)
                material = material_cache[os.path.normcase(os.path.abspath(source_path))]
                segment = draft.VideoSegment(
                    material,
                    target,
                    source_timerange=source,
                    volume=1.0 if has_embedded_audio or not audio_tracks else 0.0,
                    clip_settings=clip_settings(clip),
                )
                script.add_segment(segment, track_name=f"V{track_index + 1}")
                video_count += 1
                if has_embedded_audio:
                    embedded_audio_count += 1
            except Exception as exc:
                warnings.append(f"video {clip.get('id')}: {exc}")

    for track_index, track in enumerate(audio_tracks):
        for clip in track.findall("clipitem"):
            if node_text(clip.find("enabled"), "TRUE").upper() == "FALSE":
                continue
            try:
                if clip_signature(clip, files) in embedded_audio_signatures:
                    # The matching video segment carries this audio without an
                    # additional extraction/transcode or duplicate media file.
                    audio_count += 1
                    continue
                target, source = clip_timeranges(clip, fps)
                segment = draft.AudioSegment(
                    clip_path(clip, files),
                    target,
                    source_timerange=source,
                )
                script.add_segment(segment, track_name=f"A{track_index + 1}")
                audio_count += 1
            except Exception as exc:
                warnings.append(f"audio {clip.get('id')}: {exc}")

    script.save()
    update_draft_meta(draft_path, draft_name, material_cache, script.duration)
    return {
        "draft_path": str(draft_path),
        "fps": fps,
        "width": width,
        "height": height,
        "materials": len(material_cache),
        "video_tracks": len(video_tracks),
        "audio_tracks": len(audio_tracks),
        "video_clips": video_count,
        "audio_clips": audio_count,
        "embedded_audio_clips": embedded_audio_count,
        "warnings": warnings,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_xml", type=Path)
    parser.add_argument("--draft-root", type=Path, required=True)
    parser.add_argument("--name")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()
    name = args.name or f"{args.input_xml.stem}-达芬奇导入-{time.strftime('%m%d-%H%M%S')}"
    try:
        result = convert(
            args.input_xml,
            args.draft_root,
            name,
            args.replace,
            canvas_width=args.width,
            canvas_height=args.height,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
