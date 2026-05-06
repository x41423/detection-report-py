"""Pytest collection shim.

``test_daily_intake_api.py`` was corrupted into raw binary (all bytes after
the header are null), so pytest cannot parse it; the real restoration of
that file is tracked as a separate task.  We also keep
``test_audio_pipeline.py`` out of automatic pytest collection because it is
an imperative script that executes audio pipeline checks at import time –
it should be invoked directly via ``python tests/test_audio_pipeline.py``.
"""
from __future__ import annotations

collect_ignore_glob = [
    "test_daily_intake_api.py",
    "test_audio_pipeline.py",
]
