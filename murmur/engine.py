import logging
from pathlib import Path

import mlx_whisper
import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = Path.home() / ".apple-murmur" / "models"

# Seed vocabulary helps Whisper bias toward IT managed services terminology
_INITIAL_PROMPT = (
    "IT managed services, ITSM, ITIL, ServiceNow, incident management, "
    "change request, SLA, MTTR, infrastructure, Azure, AWS, Active Directory, "
    "VPN, endpoint, helpdesk, L1 L2 L3 support, Kubernetes, CI/CD, DevOps"
)


class Engine:
    def __init__(self, model_name: str = "whisper-tiny-mlx", device=None):  # device unused; MLX auto-selects Neural Engine / GPU
        self.model_name = model_name
        self._model_path = str(_MODEL_DIR / model_name)
        # MLX models lazy-load on first inference call — no explicit load step needed
        logger.info("Engine initialised: model=%s path=%s", model_name, self._model_path)

    def load(self) -> None:
        # No-op for MLX — model is loaded lazily by mlx_whisper on first transcribe call.
        # This method exists so the daemon can call engine.load() without branching.
        logger.info("MLX engine ready (model loads lazily on first transcribe)")

    def transcribe(self, audio: np.ndarray) -> str:
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._model_path,
            temperature=0.0,
            beam_size=3,
            condition_on_previous_text=True,
            initial_prompt=_INITIAL_PROMPT,
        )
        return result["text"].strip()
