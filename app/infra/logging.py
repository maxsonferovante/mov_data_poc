import logging
import os


def setup_logging() -> None:
    # Configura logging global da aplicação com nível ajustável via LOG_LEVEL
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

