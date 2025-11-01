import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_level: str = "INFO"):
    """Configure module-level logging for the backend.

    - Creates `backend_api/data/logs/app.log` with rotation.
    - Leaves LLM raw debug files in `backend_api/data/llm_debug/` (created by llm_service when needed).
    Call this early from the application entrypoint (main.py).
    """
    base = Path(__file__).resolve().parents[3]
    data_dir = base / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler (stream)
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    ch_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # Rotating file handler for general logs
    fh = RotatingFileHandler(logs_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    fh_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Silence overly verbose libraries if desired
    for noisy in ("uvicorn.error", "uvicorn.access", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.debug("Logging configured. Logs dir=%s", str(logs_dir))


__all__ = ["configure_logging"]
