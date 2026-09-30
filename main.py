from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.logging_setup import setup_logging


def main() -> None:
    setup_logging()
    log = logging.getLogger(__name__)

    def _excepthook(exc_type, exc_value, exc_tb):
        log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    try:
        config = load_config()
    except FileNotFoundError as exc:
        print(str(exc))
        sys.exit(1)

    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    log.info("Application started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
