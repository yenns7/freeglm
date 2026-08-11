# Upstream provenance

FreeGLM is a derived work of [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins),
distributed under the Apache License 2.0.

## Imported baseline

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/QwenLM/Qwen-MM-Plugins` |
| Upstream commit | [`8d6ea5a1f658260743307c52c2024ec87599fa48`](https://github.com/QwenLM/Qwen-MM-Plugins/commit/8d6ea5a1f658260743307c52c2024ec87599fa48) |
| Local import form | Standalone root commit with rewritten project naming and local changes |
| Hosting relationship | **Not a GitHub formal fork** |
| License | Apache License 2.0; see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) |

The upstream commit above, rather than GitHub fork metadata, is the immutable baseline for source
comparison. The local repository was published with standalone Git history, so a normal parent/child
commit comparison is not available from the local history alone.

## Material local changes at import

- Renamed the project, package, plugin, configuration, and installation surfaces to FreeGLM.
- Added a Zhipu GLM-4.6V-Flash provider for `vision_chat`, `ocr`, and `grounding`, including provider
  routing and video-to-image-frame fallback for that backend.
- Kept DashScope-backed Qwen/Omni/ASR and media-generation integrations where those model or service
  names describe the actual implementation rather than project branding.
- Added or adapted manifests and documentation for the supported agent harnesses.
- Preserved upstream attribution and the notices for separately vendored Blender and FreeCAD code.

This list describes the import boundary; later FreeGLM commits may add further changes. Use the
upstream commit plus the current tree when performing a provenance or license review.

## Updating from upstream

Upstream updates must be reviewed as an explicit import, not described as an automatic fork sync:

1. Record the new upstream commit SHA before copying or adapting code.
2. Compare that exact upstream tree with the previous baseline and classify imported, rewritten,
   locally retained, and removed paths.
3. Preserve upstream copyright, license, patent, and trademark notices.
4. Update this file and `NOTICE` in the same change, and run the repository's tests and manifest
   checks against the resulting FreeGLM revision.

## 中文说明

FreeGLM 衍生自 Apache-2.0 许可的 Qwen-MM-Plugins，确定的导入基线是上游提交
`8d6ea5a1f658260743307c52c2024ec87599fa48`。本仓库以独立根提交和独立 Git 历史发布，
**不是 GitHub formal fork**；因此来源核对应以上游仓库、精确提交 SHA、`NOTICE` 和本文件为准，
不能依赖 GitHub fork 关系。后续同步上游时必须记录新的精确 SHA，并显式审查导入范围与许可声明。
