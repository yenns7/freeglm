# Test asset provenance

These are real-world documents used only as **rendering fixtures** for
`tests/test_visualize_real.py` (each case is skipped when its asset is absent).
None is redistributed as product content. Before the public release, confirm the
license/redistribution status of every third-party file below and replace any that
cannot be shipped.

| File | Origin | License / status | Notes |
|------|--------|------------------|-------|
| `qwen3vl-tex/**` (paper sources: `.tex`, `content/`, `figures/`, `00README.json`) | Qwen3-VL technical report (this project's own paper) | Owned by the Qwen team | Safe to ship. |
| `qwen3vl-tex/colm2024_conference.{sty,bst,bib,tex}` | COLM 2024 conference LaTeX template (adapted from the ICLR/NeurIPS style chain) | Conference style files, customarily freely reusable — ⚠️ TODO: verify license | Shipped only so the paper fixture compiles. |
| `qwen3vl-tex/natbib.sty` | `natbib` package, CTAN | LPPL 1.3 | Standard LaTeX package copy, bundled for offline compile. |
| `qwen3vl-tex/fancyhdr.sty` | `fancyhdr` package, CTAN | LPPL 1.3 | Standard LaTeX package copy, bundled for offline compile. |
| `qwen3vl-tex/logo/qwen-logo.pdf`, `logo/logo.pdf` | Qwen brand assets | Owned by the Qwen team | Safe to ship. |
| `qwen3vl-tex/logo/hf-logo.pdf` | Hugging Face logo | Third-party trademark — ⚠️ TODO: verify license | Used only inside the paper fixture's title page. |
| `qwen3vl-tex/logo/github-logo.pdf` | GitHub logo | Third-party trademark — ⚠️ TODO: verify license | Used only inside the paper fixture's title page. |
| `qwen3vl-tex/logo/modelscope-logo.pdf` | ModelScope logo | Third-party trademark — ⚠️ TODO: verify license | Used only inside the paper fixture's title page. |
| `qwen3vl.pdf` | Qwen3-VL technical report, compiled PDF (this project's own paper — the `qwen3vl-tex/` sources render to this) | Owned by the Qwen team | Safe to ship. Multi-page PDF render fixture (replaced the earlier third-party competitor PDF). |
| `grand_piano.glb` | Third-party 3D model | ⚠️ **VERIFY** — source/license unknown — TODO: verify license | Replace with a CC0 model if provenance can't be confirmed. |
| `calibre-test.docx` | Calibre e-book toolkit test sample (github.com/kovidgoyal/calibre) | Calibre is GPL-3.0; test-data status — ⚠️ TODO: verify license | Confirm redistribution terms. |
| `hf-quicktour.ipynb` | Hugging Face Transformers docs quicktour (github.com/huggingface/transformers) | Apache-2.0 (HF docs) — verify | Keep attribution. |
| `llama-cpp-readme.md` | llama.cpp README (github.com/ggml-org/llama.cpp) | MIT (llama.cpp) | Keep attribution. |
| `python-docs/**` (tutorial `index.html`, `_static/` CSS+JS, `py.svg`, `robots.txt`) | docs.python.org tutorial page snapshot + static assets | PSF License / Python docs terms — verify | Public documentation snapshot; includes Sphinx theme assets (BSD). |
| `titanic.csv` | Titanic passenger dataset | Public domain | Safe to ship. |

Self-authored / procedurally generated fixtures elsewhere in `tests/assets/`
(`sample.*`, `tex_project/`, `sample-model.glb`) are original to this repo (CC0).

## Large-file management (大文件管理)

Files in this directory over 1 MB (repo-size hot spots):

| File | Size | Suggestion |
|------|------|------------|
| `qwen3vl.pdf` | ~4.2 MB | Own content (Qwen3-VL paper), safe to ship; largest single file — consider Git LFS / download-on-demand if the tree keeps growing. |
| `qwen3vl-tex/figures/qwen3vl_head.png` | ~2.8 MB | Own content; consider recompressing (lossy PNG→JPEG/WebP) — the renderer test doesn't need full resolution. |
| `grand_piano.glb` | ~1.8 MB | License-unverified; swap for a small CC0 model (a `sample-model.glb`-sized asset suffices for the 3D render path). |
| `calibre-test.docx` | ~1.3 MB | Keep only if the DOCX render path needs its embedded media; otherwise trim to a smaller document. |
| `qwen3vl-tex/figures/qwen3vl_arc.jpg` | ~1.0 MB | Own content; acceptable, recompress opportunistically. |

Guidelines: tests skip gracefully when an asset is absent, so any of these can be
moved out of the git tree (Git LFS, or fetched into place by a dev script) without
breaking CI; prefer that route over adding further >1 MB binaries directly to the
repository, and keep this directory's total size roughly where it is (~12 MB).
