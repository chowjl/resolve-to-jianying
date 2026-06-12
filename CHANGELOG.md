# Changelog

## 1.1.0 - 2026-06-12

- Add Jianying to DaVinci Resolve timeline import.
- Open the folder picker directly at Jianying's draft root.
- Support encrypted Jianying 10.8 drafts through the bundled MIT-licensed `jy-draftc` helper.
- Preserve video/audio tracks, edit positions, source ranges, frame rate, and canvas resolution.

## 1.0.1 - 2026-06-12

- Read Resolve timeline resolution, including 9:16 projects.
- Handle 90°/270° source rotation metadata.
- Populate Jianying's media library and deduplicate source files.
- Keep an empty Jianying main track to prevent magnetic-track offsets.
- Add draft naming, progress UI, completion confirmation, installer, and uninstaller.
