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
from pyJianYingDraft import AudioMaterial, VideoMaterial  # noqa: E402
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


def is_adjustment_clip(clip: ET.Element) -> bool:
    file_node = clip.find("file")
    values = [
        clip.get("id", ""),
        node_text(clip.find("name")),
        file_node.get("id", "") if file_node is not None else "",
        node_text(file_node.find("name")) if file_node is not None else "",
    ]
    return any("adjustment clip" in value.lower() for value in values)


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


def timeline_clip_key(clip: ET.Element, files: dict[str, str]) -> tuple[str, str, str]:
    """Identify the same visible edit across Resolve's video and audio tracks."""
    return (
        os.path.normcase(os.path.abspath(clip_path(clip, files))),
        node_text(clip.find("start")),
        node_text(clip.find("end")),
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


def create_audio_material(path: str) -> AudioMaterial:
    """Create an audio material, including audio streams embedded in video files."""
    info = MediaInfo.parse(path, mediainfo_options={"File_TestContinuousFileNames": "0"})
    if not info.audio_tracks:
        raise ValueError(f"素材没有音频轨道：{path}")
    audio_track = info.audio_tracks[0]
    general_track = info.general_tracks[0] if info.general_tracks else None
    duration_ms = getattr(audio_track, "duration", None)
    if duration_ms is None and general_track is not None:
        duration_ms = getattr(general_track, "duration", None)
    if duration_ms is None:
        raise ValueError(f"无法读取音频时长：{path}")

    # AudioMaterial normally rejects containers that also have a video stream.
    # Jianying accepts the same MP4 path as an audio material, so populate the
    # small material object directly and preserve Resolve's separate audio edit.
    material = AudioMaterial.__new__(AudioMaterial)
    material.material_id = uuid.uuid4().hex
    material.material_name = Path(path).name
    material.path = os.path.abspath(path)
    material.duration = int(round(float(duration_ms) * 1_000))
    return material


def manifest_key(track_type: str, track_index: int, clip: ET.Element) -> tuple[str, int, int, int]:
    return (
        track_type,
        track_index,
        int(node_text(clip.find("start"), "0")),
        int(node_text(clip.find("end"), "0")),
    )


def manifest_source_timerange(item: dict | None, fallback: Timerange) -> Timerange:
    if not item:
        return fallback
    start_value = item.get("source_start_time")
    end_value = item.get("source_end_time")
    if start_value is None or end_value is None:
        return fallback
    start = round(float(start_value) * 1_000_000)
    end = round(float(end_value) * 1_000_000)
    if end <= start:
        return fallback
    return Timerange(start, end - start)


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
    subtitles_path: Path | None = None,
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

    warnings: list[str] = []
    skipped_adjustment_clips = 0
    video_paths: set[str] = set()
    for track in video_tracks:
        for clip in track.findall("clipitem"):
            if is_adjustment_clip(clip):
                continue
            try:
                video_paths.add(clip_path(clip, files))
            except Exception as exc:
                warnings.append(f"video {clip.get('id')} skipped: {exc}")
    material_cache = {
        os.path.normcase(os.path.abspath(path)): create_video_material(path)
        for path in sorted(video_paths)
    }
    audio_material_cache: dict[str, AudioMaterial] = {}
    manifest = {}
    if subtitles_path and subtitles_path.is_file():
        manifest = json.loads(subtitles_path.read_text(encoding="utf-8-sig"))
    clip_manifest = {
        (
            str(item.get("type", "")),
            int(item.get("track_index", 0)),
            int(item.get("start_frame", 0)),
            int(item.get("end_frame", 0)),
        ): item
        for item in manifest.get("clips", [])
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
    disabled_video_count = 0
    disabled_audio_count = 0
    retimed_clip_count = 0
    for track_index, track in enumerate(video_tracks):
        for clip in track.findall("clipitem"):
            if is_adjustment_clip(clip):
                skipped_adjustment_clips += 1
                continue
            try:
                target, source = clip_timeranges(clip, fps)
                enabled = node_text(clip.find("enabled"), "TRUE").upper() != "FALSE"
                clip_start = int(node_text(clip.find("start"), "0"))
                clip_end = int(node_text(clip.find("end"), "0"))
                manifest_item = clip_manifest.get(("video", track_index + 1, clip_start, clip_end))
                has_linked_audio = bool(manifest_item and manifest_item.get("linked_audio"))
                source_path = clip_path(clip, files)
                material = material_cache[os.path.normcase(os.path.abspath(source_path))]
                source = manifest_source_timerange(manifest_item, source)
                if source.end > material.duration:
                    source = Timerange(source.start, max(1, material.duration - source.start))
                segment = draft.VideoSegment(
                    material,
                    target,
                    source_timerange=source,
                    volume=0.0 if has_linked_audio else 1.0,
                    clip_settings=clip_settings(clip),
                )
                segment.visible = enabled
                script.add_segment(segment, track_name=f"V{track_index + 1}")
                video_count += 1
                if abs(segment.speed.speed - 1.0) > 0.001:
                    retimed_clip_count += 1
                if not enabled:
                    disabled_video_count += 1
            except Exception as exc:
                warnings.append(f"video {clip.get('id')}: {exc}")

    for track_index, track in enumerate(audio_tracks):
        for clip in track.findall("clipitem"):
            try:
                enabled = node_text(clip.find("enabled"), "TRUE").upper() != "FALSE"
                target, source = clip_timeranges(clip, fps)
                clip_start = int(node_text(clip.find("start"), "0"))
                clip_end = int(node_text(clip.find("end"), "0"))
                manifest_item = clip_manifest.get(("audio", track_index + 1, clip_start, clip_end))
                source_path = clip_path(clip, files)
                cache_key = os.path.normcase(os.path.abspath(source_path))
                if cache_key not in audio_material_cache:
                    audio_material_cache[cache_key] = create_audio_material(source_path)
                audio_material = audio_material_cache[cache_key]
                source = manifest_source_timerange(manifest_item, source)
                if source.end > audio_material.duration:
                    source = Timerange(source.start, max(1, audio_material.duration - source.start))
                segment = draft.AudioSegment(
                    audio_material,
                    target,
                    source_timerange=source,
                )
                segment.visible = enabled
                script.add_segment(segment, track_name=f"A{track_index + 1}")
                audio_count += 1
                if abs(segment.speed.speed - 1.0) > 0.001:
                    retimed_clip_count += 1
                if not enabled:
                    disabled_audio_count += 1
            except Exception as exc:
                warnings.append(f"audio {clip.get('id')}: {exc}")

    subtitle_count = 0
    subtitle_tracks = 0
    if subtitles_path and subtitles_path.is_file():
        subtitle_data = manifest
        for track_index, items in enumerate(subtitle_data.get("tracks", []), 1):
            if not items:
                continue
            track_name = f"Subtitle {track_index}"
            script.add_track(draft.TrackType.text, track_name, relative_index=track_index - 1)
            subtitle_tracks += 1
            for item in items:
                text = str(item.get("text") or "").strip()
                start_frame = int(round(float(item.get("start_frame", 0))))
                end_frame = int(round(float(item.get("end_frame", start_frame))))
                if not text or end_frame <= start_frame:
                    continue
                timerange = Timerange(
                    frames_to_us(start_frame, fps),
                    frames_to_us(end_frame - start_frame, fps),
                )
                script.add_segment(draft.TextSegment(text, timerange), track_name=track_name)
                subtitle_count += 1

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
        "subtitle_tracks": subtitle_tracks,
        "subtitle_clips": subtitle_count,
        "skipped_adjustment_clips": skipped_adjustment_clips,
        "disabled_video_clips": disabled_video_count,
        "disabled_audio_clips": disabled_audio_count,
        "retimed_clips": retimed_clip_count,
        "embedded_audio_clips": 0,
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
    parser.add_argument("--subtitles", type=Path)
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
            subtitles_path=args.subtitles,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
