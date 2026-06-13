# Changelog

## 1.2.0 - 2026-06-13

- Preserve Resolve-linked detached audio and standalone WAV/MP3 tracks.
- Avoid duplicate embedded audio using Resolve's linked-item relationships.
- Transfer constant-speed retiming with real source start/end times.
- Convert Resolve subtitle tracks into Jianying subtitle tracks.
- Preserve disabled Resolve clips as real disabled Jianying clips.
- Skip unsupported Adjustment Clips and report skipped items.
- Keep unsupported or malformed items from aborting the complete conversion.
- Update bilingual documentation and the one-click installer.

## 1.0.1 - 2026-06-12

- Read Resolve timeline resolution, including 9:16 projects.
- Handle 90-degree/270-degree source rotation metadata.
- Populate Jianying's media library and deduplicate source files.
- Keep an empty Jianying main track to prevent magnetic-track offsets.
- Add draft naming, progress UI, completion confirmation, installer, and uninstaller.
