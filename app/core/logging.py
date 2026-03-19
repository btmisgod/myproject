import logging
import sys

from pythonjsonlogger.jsonlogger import JsonFormatter

from app.core.config import settings


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
