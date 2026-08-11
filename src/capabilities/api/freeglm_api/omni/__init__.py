"""Omni-model A/V tools: segmented captioning, the ASR family, temporal grounding, and event
counting — each reads the video frames AND the embedded audio track together via the Qwen-Omni
model (``shared.api_omni``). Every module exports ``TOOL`` + ``handle``; ``_common`` is shared
plumbing (no TOOL) and is skipped by the registry."""
