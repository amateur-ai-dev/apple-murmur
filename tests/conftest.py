"""
Pre-mock heavy optional dependencies so tests run without installing them.
mlx_whisper is only needed at runtime (when the engine actually transcribes).
All engine tests mock this at the attribute level — this lets those patches apply.
"""
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("mlx_whisper", MagicMock())
