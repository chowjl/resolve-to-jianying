# Changelog

## 1.2.0 - 2026-06-13

- Preserve Resolve-linked detached audio and standalone WAV/MP3 audio tracks.
- Avoid duplicate embedded audio by reading Resolve's real linked-item relationships.
- Transfer constant-speed retiming from Resolve using real source start/end times.
- Convert Resolve subtitle tracks into Jianying subtitle tracks.
- Preserve disabled Resolve video/audio clips as real disabled Jianying clips.
- Skip unsupported Resolve Adjustment Clips and report skipped items.
- Keep unsupported or malformed items from aborting the complete conversion.
- Improve bilingual documentation and clarify conversion limitations.
- Export Jianying subtitles as SRT for manual Resolve subtitle import.

## 1.1.0 - 2026-06-12

- Add Jianying to DaVinci Resolve timeline import.
- Open the folder picker directly at Jianying's draft root.
- Support encrypted Jianying 10.8 drafts through the bundled MIT-licensed `jy-draftc` helper.
- Preserve video/audio tracks, edit positions, source ranges, frame rate, and canvas resolution.

## 1.0.1 - 2026-06-12

- Read Resolve timeline resolution, including 9:16 projects.
- Handle 90-degree/270-degree source rotation metadata.
- Populate Jianying's media library and deduplicate source files.
- Keep an empty Jianying main track to prevent magnetic-track offsets.
- Add draft naming, progress UI, completion confirmation, installer, and uninstaller.
