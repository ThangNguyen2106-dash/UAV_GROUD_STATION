from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from Rigel_GCS.core.connection_manager import ConnectionManager
from Rigel_GCS.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RIGEL Ground Station")

    connection_manager = ConnectionManager()
    window = MainWindow(connection_manager)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
