"""Pytest collection shim.

``test_audio_pipeline.py`` is kept out of automatic pytest collection because it
is an imperative script that executes audio pipeline checks at import time; it
should be invoked directly via ``python tests/test_audio_pipeline.py``.
"""
from __future__ import annotations

import os

os.environ["APP_DB_DRIVER"] = "sqlite"

collect_ignore_glob = [
    "test_audio_pipeline.py",
]
